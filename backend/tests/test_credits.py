"""
Credit System Tests
===================
Tests the credit balance, ledger pagination, ad reward claims,
and tool credit deduction via the API.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(test_client, email: str, password: str) -> str:
    """Log in and return the session cookie value."""
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.cookies.get("plexudo_session", "")


async def _signup_and_verify(test_client, db, username: str, email: str, password: str):
    """Sign up and verify email for a fresh user, returning the User ORM object."""
    from app.services.auth_service import (
        create_user as svc_create_user,
        create_email_verification_token,
        verify_email_token,
    )
    user = await svc_create_user(db, username, email, password)
    raw_token = await create_email_verification_token(db, str(user.id))
    await verify_email_token(db, raw_token)
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


async def test_get_balance_returns_current_balance(test_client, db):
    """GET /credits/balance returns the user's current credit_balance."""
    from app.services.auth_service import create_session

    user = await _signup_and_verify(test_client, db, "credit_u1", "credit_u1@example.com", "P@ss1234!")
    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.get("/api/v1/credits/balance")
    assert resp.status_code == 200, resp.text
    assert resp.json()["balance"] == 3  # WELCOME_CREDITS

    test_client.cookies.clear()


# ---------------------------------------------------------------------------
# Ledger pagination
# ---------------------------------------------------------------------------


async def test_ledger_pagination(test_client, db):
    """
    Create 5 ledger entries (welcome + 4 ad rewards) and verify the ledger
    endpoint returns them with correct pagination.
    """
    from app.services.auth_service import create_session
    from app.services.credit_ledger_service import verify_and_grant_ad_reward

    user = await _signup_and_verify(test_client, db, "ledger_u1", "ledger_u1@example.com", "P@ss1234!")

    # Add 4 ad rewards (unique provider reference IDs)
    for i in range(4):
        await verify_and_grant_ad_reward(db, str(user.id), "prov", f"ref_{i}")

    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.get("/api/v1/credits/ledger")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "entries" in data
    # Should have 5 entries: 1 WELCOME + 4 AD_REWARD
    assert len(data["entries"]) == 5

    test_client.cookies.clear()


# ---------------------------------------------------------------------------
# Ad reward replay
# ---------------------------------------------------------------------------


async def test_ad_reward_replay_rejected(test_client, db):
    """
    POST /credits/claim-ad-reward with the same reward token twice must return
    200 on first call and 409 REWARD_ALREADY_CLAIMED on the second.
    """
    from app.services.auth_service import create_session

    user = await _signup_and_verify(test_client, db, "reward_u1", "reward_u1@example.com", "P@ss1234!")
    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    # First claim
    r1 = await test_client.post(
        "/api/v1/credits/claim-ad-reward",
        json={"provider": "test_prov", "provider_reference_id": "event_xyz"},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["balance"] == 4  # 3 welcome + 1 reward

    # Replay — must be rejected
    r2 = await test_client.post(
        "/api/v1/credits/claim-ad-reward",
        json={"provider": "test_prov", "provider_reference_id": "event_xyz"},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "REWARD_ALREADY_CLAIMED"

    test_client.cookies.clear()


# ---------------------------------------------------------------------------
# Tool credit deduction
# ---------------------------------------------------------------------------


async def test_tool_deducts_credits(test_client, db):
    """
    POST /tools/seo-score on a verified user must:
    - Succeed (200)
    - Deduct exactly TOOL_CREDIT_COSTS['SEO_SCORE'] credits
    """
    from app.services.auth_service import create_session
    from app.core.config import get_settings

    settings = get_settings()
    cost = settings.TOOL_CREDIT_COSTS["SEO_SCORE"]

    user = await _signup_and_verify(test_client, db, "tool_u1", "tool_u1@example.com", "P@ss1234!")
    initial_balance = user.credit_balance  # 3 after verification

    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={
            "title": "How to Grow on YouTube in 2026",
            "description": "Complete breakdown of YouTube algorithm strategy and SEO tips.",
            "tags": ["youtube", "growth", "seo", "algorithm"],
        },
    )
    assert resp.status_code == 200, resp.text

    # Verify balance was decremented
    balance_resp = await test_client.get("/api/v1/credits/balance")
    new_balance = balance_resp.json()["balance"]
    assert new_balance == initial_balance - cost, (
        f"Expected balance {initial_balance - cost}, got {new_balance}"
    )

    test_client.cookies.clear()


async def test_insufficient_credits_returns_402(test_client, db):
    """
    A user with 0 credits attempting to use a tool must receive 402 INSUFFICIENT_CREDITS.
    """
    from app.services.auth_service import create_session
    from app.db.models.user import User
    from sqlalchemy import update

    user = await _signup_and_verify(test_client, db, "broke_u1", "broke_u1@example.com", "P@ss1234!")

    # Drain the balance to 0
    await db.execute(
        update(User).where(User.id == user.id).values(credit_balance=0)
    )
    await db.commit()

    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={"video_id": "dQw4w9WgXcQ"},
    )
    assert resp.status_code == 402
    assert resp.json()["detail"] == "INSUFFICIENT_CREDITS"

    test_client.cookies.clear()


async def test_credit_cost_is_from_config(test_client, db):
    """
    The credit cost deducted by tool endpoints must match TOOL_CREDIT_COSTS,
    not a hardcoded value.
    """
    from app.core.config import get_settings
    settings = get_settings()

    # This test verifies the config-driven cost is reflected in the ledger.
    from app.services.auth_service import create_session
    from app.db.models.credit import CreditLedger, CreditTxnType
    from sqlalchemy.future import select

    cost = settings.TOOL_CREDIT_COSTS["SEO_SCORE"]
    user = await _signup_and_verify(test_client, db, "cfg_u1", "cfg_u1@example.com", "P@ss1234!")

    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    await test_client.post(
        "/api/v1/tools/seo-score",
        json={
            "title": "Config Cost Test Video",
            "description": "Validating dynamic TOOL_CREDIT_COSTS configuration.",
            "tags": ["config", "test"],
        },
    )

    # Check the ledger row amount matches the configured cost
    result = await db.execute(
        select(CreditLedger).where(
            CreditLedger.user_id == user.id,
            CreditLedger.type == CreditTxnType.TOOL_USAGE,
        )
    )
    ledger_rows = result.scalars().all()
    assert len(ledger_rows) == 1
    assert ledger_rows[0].amount == -cost, (
        f"Ledger amount {ledger_rows[0].amount} must equal -{cost} (from TOOL_CREDIT_COSTS)"
    )

    test_client.cookies.clear()


async def test_unverified_user_cannot_use_tools(test_client, db):
    """An unverified user must receive 403 EMAIL_NOT_VERIFIED when using a tool."""
    from app.services.auth_service import create_user as svc_create_user, create_session

    user = await svc_create_user(db, "unv_tool", "unv_tool@example.com", "P@ss1234!")
    session = await create_session(db, str(user.id), "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={"video_id": "dQw4w9WgXcQ"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "EMAIL_NOT_VERIFIED"

    test_client.cookies.clear()
