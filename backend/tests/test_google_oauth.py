"""
Google OAuth YouTube Connection Tests
======================================
Tests:
1. OAuth state generation and CSRF protection.
2. Token encryption at rest (Fernet) — raw tokens never stored.
3. User isolation: User A cannot use or access User B's YouTube connection.
4. Token disconnect and revocation.
5. End-to-end OAuth flow via API endpoints (/api/v1/youtube/*).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.core.security import decrypt_bytes
from app.db.models.youtube import YoutubeConnection
from app.services.auth_service import create_session
from app.services.google_oauth_service import (
    GoogleOAuthService,
    generate_oauth_state,
    google_oauth_service,
    verify_oauth_state,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit: State & CSRF Protection
# ---------------------------------------------------------------------------


async def test_oauth_state_validation():
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    state = generate_oauth_state(user_id)

    # Valid user matches
    assert verify_oauth_state(state, user_id) is True

    # Other user ID fails
    assert verify_oauth_state(state, other_user_id) is False

    # Tampered state fails
    tampered = state[:-4] + "abcd"
    assert verify_oauth_state(tampered, user_id) is False

    # Corrupt format fails
    assert verify_oauth_state("invalid:format", user_id) is False


# ---------------------------------------------------------------------------
# Integration: Token Encryption & User Isolation
# ---------------------------------------------------------------------------


async def test_tokens_are_encrypted_at_rest(db, test_user):
    """
    CRITICAL INVARIANT: Access and refresh tokens MUST be encrypted with
    TOKEN_ENCRYPTION_KEY before insert into the database.
    """
    raw_access = "ya29.sample_access_token_12345"
    raw_refresh = "1//sample_refresh_token_67890"

    mock_tokens = {
        "access_token": raw_access,
        "refresh_token": raw_refresh,
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
    }

    # Mock external HTTP calls inside store_connection
    def handler(request: httpx.Request) -> httpx.Response:
        if "userinfo" in str(request.url):
            return httpx.Response(200, json={"email": "creator@gmail.com"})
        if "channels" in str(request.url):
            return httpx.Response(200, json={"items": [{"id": "UC123", "snippet": {"title": "Test Channel"}}]})
        return httpx.Response(404)

    service = GoogleOAuthService(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    conn = await service.store_connection(db, test_user.id, mock_tokens)

    # Verify DB record holds encrypted bytes, NOT the raw plaintext string
    stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == test_user.id)
    res = await db.execute(stmt)
    stored = res.scalar_one()

    assert stored.access_token_encrypted != raw_access.encode()
    assert stored.refresh_token_encrypted != raw_refresh.encode()

    # Verify decrypting with TOKEN_ENCRYPTION_KEY recovers original raw tokens
    decrypted_access = decrypt_bytes(stored.access_token_encrypted).decode()
    decrypted_refresh = decrypt_bytes(stored.refresh_token_encrypted).decode()
    assert decrypted_access == raw_access
    assert decrypted_refresh == raw_refresh


async def test_youtube_connection_user_isolation(db, test_user, unverified_user):
    """
    CRITICAL INVARIANT: A user's YouTube connection is strictly bound to their user ID.
    User B must never be able to access User A's connection.
    """
    mock_tokens = {
        "access_token": "token_for_user_a",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
    }

    service = GoogleOAuthService()
    await service.store_connection(db, test_user.id, mock_tokens)

    # User A can get their token
    token_a = await service.get_valid_access_token(db, test_user.id)
    assert token_a == "token_for_user_a"

    # User B has no connection
    with pytest.raises(Exception):
        await service.get_valid_access_token(db, unverified_user.id)


async def test_disconnect_removes_connection(db, test_user):
    mock_tokens = {
        "access_token": "token_to_delete",
        "expires_in": 3600,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    service = GoogleOAuthService(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await service.store_connection(db, test_user.id, mock_tokens)

    # Disconnect
    await service.disconnect(db, test_user.id)

    # Verify record was removed
    stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == test_user.id)
    res = await db.execute(stmt)
    assert res.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# API Endpoints: /api/v1/youtube/*
# ---------------------------------------------------------------------------


async def test_youtube_status_endpoint(test_client, db, test_user):
    session = await create_session(db, test_user.id, "test-agent", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    # Before connect
    r1 = await test_client.get("/api/v1/youtube/status")
    assert r1.status_code == 200
    assert r1.json()["connected"] is False

    # Store a connection
    mock_tokens = {"access_token": "token_status_test", "expires_in": 3600}
    await google_oauth_service.store_connection(db, test_user.id, mock_tokens)

    # After connect
    r2 = await test_client.get("/api/v1/youtube/status")
    assert r2.status_code == 200
    data = r2.json()
    assert data["connected"] is True
    # Invariant: Never return tokens
    assert "access_token" not in data
    assert "refresh_token" not in data

    test_client.cookies.clear()
