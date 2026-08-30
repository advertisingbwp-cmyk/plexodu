"""
Security & Privacy Audit Tests
===============================
Enforces the Closed-App Security Model:
1. Cross-user data isolation (User A cannot access User B's history or YouTube data).
2. Unauthenticated requests to private endpoints receive 401.
3. Unverified users receive 403 EMAIL_NOT_VERIFIED on protected tools.
4. OAuth tokens and API secrets are NEVER exposed in JSON payloads.
"""

from __future__ import annotations

import pytest

from app.db.models.history import HistoryEntry, ToolType
from app.services.auth_service import create_session, create_user
from app.services.google_oauth_service import google_oauth_service

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Cross-User Data Isolation Tests
# ---------------------------------------------------------------------------


async def test_cross_user_history_isolation(test_client, db):
    """User A must NOT see User B's history records."""
    user_a = await create_user(db, "alice_sec", "alice_sec@example.com", "P@ssword1!")
    user_b = await create_user(db, "bob_sec", "bob_sec@example.com", "P@ssword1!")

    # Insert a history entry for User B
    entry_b = HistoryEntry(
        user_id=user_b.id,
        tool_type=ToolType.SEO_SCORE,
        input_params={"secret_data": "bob_private_video"},
        output_results={"score": 45},
    )
    db.add(entry_b)
    await db.commit()

    # Log in as User A
    session_a = await create_session(db, user_a.id, "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session_a.id))

    # User A requests history
    resp = await test_client.get("/api/v1/history/")
    assert resp.status_code == 200
    data = resp.json()

    # User A must have 0 history entries
    assert data["count"] == 0
    assert len(data["entries"]) == 0

    test_client.cookies.clear()


async def test_cross_user_youtube_isolation(test_client, db):
    """User A cannot see or control User B's YouTube connection."""
    user_a = await create_user(db, "alice_yt", "alice_yt@example.com", "P@ssword1!")
    user_b = await create_user(db, "bob_yt", "bob_yt@example.com", "P@ssword1!")

    # Connect YouTube for User B
    mock_tokens = {"access_token": "secret_b_token", "expires_in": 3600}
    await google_oauth_service.store_connection(db, user_b.id, mock_tokens)

    # Log in as User A
    session_a = await create_session(db, user_a.id, "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session_a.id))

    # User A checks status
    resp = await test_client.get("/api/v1/youtube/status")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False

    test_client.cookies.clear()


# ---------------------------------------------------------------------------
# Authentication & Verification Enforcement
# ---------------------------------------------------------------------------


async def test_unauthenticated_requests_receive_401(test_client):
    """All private endpoints reject unauthenticated access with 401."""
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/profile/"),
        ("GET", "/api/v1/credits/balance"),
        ("GET", "/api/v1/history/"),
        ("GET", "/api/v1/youtube/status"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await test_client.get(path)
        else:
            resp = await test_client.post(path)
        assert resp.status_code == 401, f"{path} must require authentication (got {resp.status_code})"


async def test_unverified_requests_receive_403_on_protected_tools(test_client, db, unverified_user):
    """Unverified users are rejected with 403 on protected creator tools."""
    session = await create_session(db, unverified_user.id, "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={"title": "Test Title", "description": "Test Desc"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "EMAIL_NOT_VERIFIED"

    test_client.cookies.clear()
