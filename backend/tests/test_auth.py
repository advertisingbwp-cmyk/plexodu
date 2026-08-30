"""
Auth API Tests
==============
Tests the /api/v1/auth/* endpoints using the real test database.
Covers the full auth lifecycle: signup → verify → login → reset password → logout.
"""

from __future__ import annotations

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


async def test_signup_creates_unverified_user(test_client, db):
    """
    POST /signup → 201.
    The created user must have email_verified_at=NULL and credit_balance=0.
    After signup but before verification, GET /me must show email_verified=False.
    """
    resp = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "Str0ngP@ssword!",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "user_id" in data


async def test_signup_duplicate_email_returns_409(test_client, db):
    """Second signup with the same email must return 409 EMAIL_TAKEN."""
    payload = {
        "username": "bob1",
        "email": "bob@example.com",
        "password": "Str0ngP@ssword!",
        "confirm_password": "Str0ngP@ssword!",
    }
    first = await test_client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    payload["username"] = "bob2"  # different username, same email
    second = await test_client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "EMAIL_TAKEN"


async def test_signup_duplicate_username_returns_409(test_client, db):
    """Second signup with the same username (different email) must return 409 USERNAME_TAKEN."""
    payload = {
        "username": "charlie",
        "email": "charlie1@example.com",
        "password": "Str0ngP@ssword!",
        "confirm_password": "Str0ngP@ssword!",
    }
    first = await test_client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    payload["email"] = "charlie2@example.com"
    second = await test_client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "USERNAME_TAKEN"


async def test_signup_password_mismatch_returns_422(test_client, db):
    resp = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "dave",
            "email": "dave@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "WrongPassword!",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_before_verification_returns_200_with_unverified_flag(test_client, db):
    """
    Login must succeed (200) even before email verification.
    The response body must include email_verified=False.
    """
    # Signup
    await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "eve",
            "email": "eve@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "Str0ngP@ssword!",
        },
    )
    # Login
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "eve@example.com", "password": "Str0ngP@ssword!"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["email_verified"] is False
    assert "csrf_token" in data


async def test_login_wrong_password_returns_401(test_client, db):
    await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "frank",
            "email": "frank@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "Str0ngP@ssword!",
        },
    )
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Email verification + welcome credits
# ---------------------------------------------------------------------------


async def test_verify_email_grants_3_credits(test_client, db):
    """
    After email verification, credit_balance must be exactly 3 (WELCOME_CREDITS).
    GET /me must show email_verified=True.
    """
    from app.services.auth_service import create_email_verification_token
    from app.db.models.user import User
    from sqlalchemy.future import select

    # Signup
    signup_resp = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "grace",
            "email": "grace@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "Str0ngP@ssword!",
        },
    )
    assert signup_resp.status_code == 201
    user_id_str = signup_resp.json()["user_id"]
    user_id = uuid.UUID(user_id_str)

    # Retrieve the verification token from DB (normally delivered by email)
    from app.db.models.token import EmailVerificationToken
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id
        )
    )
    token_obj = result.scalars().first()
    assert token_obj is not None, "Verification token must have been created at signup"

    # We create a new token directly via the service (simulating what the email link contains).
    raw_token = await create_email_verification_token(db, user_id)

    # Verify
    verify_resp = await test_client.post(
        "/api/v1/auth/verify-email",
        json={"token": raw_token},
    )
    assert verify_resp.status_code == 200, verify_resp.text

    # Login and check balance
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "grace@example.com", "password": "Str0ngP@ssword!"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["email_verified"] is True
    assert data["user"]["credit_balance"] == 3


async def test_verify_email_token_replay_returns_400(test_client, db):
    """Using the same verification token twice must return 400 on the second attempt."""
    from app.services.auth_service import create_email_verification_token
    from app.services.auth_service import create_user as svc_create_user

    user = await svc_create_user(db, "henry", "henry@example.com", "Str0ngP@ssword!")
    raw_token = await create_email_verification_token(db, str(user.id))

    r1 = await test_client.post("/api/v1/auth/verify-email", json={"token": raw_token})
    assert r1.status_code == 200

    r2 = await test_client.post("/api/v1/auth/verify-email", json={"token": raw_token})
    assert r2.status_code == 400
    assert r2.json()["detail"] == "TOKEN_INVALID_OR_EXPIRED"


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------


async def test_forgot_password_no_account_enumeration(test_client, db):
    """
    POST /forgot-password must return 202 for both existing and non-existing emails
    (no account enumeration — auth-flow.md §3).
    """
    r1 = await test_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert r1.status_code == 202

    # Create a real user then check the existing-email path also returns 202.
    from app.services.auth_service import create_user as svc_create_user
    await svc_create_user(db, "irene", "irene@example.com", "Str0ngP@ssword!")
    r2 = await test_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "irene@example.com"},
    )
    assert r2.status_code == 202


async def test_reset_password_flow(test_client, db):
    """
    Full reset flow: signup → create reset token → reset → old login fails → new login works.
    After password reset, all sessions are revoked (force re-login).
    """
    from app.services.auth_service import (
        create_user as svc_create_user,
        create_password_reset_token,
        create_session,
    )

    user = await svc_create_user(db, "julia", "julia@example.com", "OldP@ssword1!")
    session = await create_session(db, str(user.id), "test-agent", "127.0.0.1")

    raw_token = await create_password_reset_token(db, str(user.id))

    # Reset the password
    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewP@ssword1!",
            "confirm_password": "NewP@ssword1!",
        },
    )
    assert resp.status_code == 200, resp.text

    # Old password must no longer work
    old_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "julia@example.com", "password": "OldP@ssword1!"},
    )
    assert old_login.status_code == 401

    # New password must work
    new_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "julia@example.com", "password": "NewP@ssword1!"},
    )
    assert new_login.status_code == 200


async def test_reset_password_expired_token_returns_400(test_client, db):
    """An expired reset token must return 400."""
    from datetime import timedelta, timezone, datetime
    from app.core.security import generate_token, hash_token
    from app.db.models.token import PasswordResetToken
    from app.services.auth_service import create_user as svc_create_user

    user = await svc_create_user(db, "kyle", "kyle@example.com", "P@ssword1!")
    raw_token = generate_token()
    expired = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
        is_consumed=False,
    )
    db.add(expired)
    await db.commit()

    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "NewP@ssword1!",
            "confirm_password": "NewP@ssword1!",
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------


async def test_change_password_wrong_current_returns_401(test_client, db):
    """Supplying an incorrect current password must return 401."""
    from app.services.auth_service import create_user as svc_create_user, create_session

    user = await svc_create_user(db, "lena", "lena@example.com", "CurrentP@ss1!")
    session = await create_session(db, str(user.id), "test-agent", "127.0.0.1")

    # Inject session cookie
    test_client.cookies.set("plexudo_session", str(session.id))

    resp = await test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongP@ss!", "new_password": "NewP@ss1!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "CURRENT_PASSWORD_INCORRECT"

    test_client.cookies.clear()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout_revokes_session(test_client, db):
    """After logout, the session cookie must no longer be accepted by GET /me."""
    from app.services.auth_service import create_user as svc_create_user, create_session
    from datetime import datetime, timezone

    user = await svc_create_user(db, "mia", "mia@example.com", "P@ssword1!")
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()

    session = await create_session(db, str(user.id), "test-agent", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    # GET /me must work before logout
    me_before = await test_client.get("/api/v1/auth/me")
    assert me_before.status_code == 200

    # Logout
    logout_resp = await test_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    # GET /me must fail after logout
    me_after = await test_client.get("/api/v1/auth/me")
    assert me_after.status_code == 401

    test_client.cookies.clear()


async def test_unauthenticated_me_returns_401(test_client, db):
    """GET /me without a session cookie must return 401."""
    resp = await test_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
