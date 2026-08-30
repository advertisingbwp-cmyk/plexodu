"""
Google OAuth Service — Connect YouTube Flow
============================================
Handles Google OAuth 2.0 specifically for connecting a user's YouTube account.
All OAuth tokens are strictly isolated per user and encrypted at rest with Fernet.

CRITICAL INVARIANTS:
1. No global OAuth token pool — all tokens are strictly bound to one Plexudo user ID.
2. Tokens are encrypted at rest with TOKEN_ENCRYPTION_KEY.
3. State parameter is HMAC-signed to prevent CSRF during callback.
4. Tokens are never sent in API responses or logs.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_bytes, encrypt_bytes
from app.db.models.youtube import YoutubeConnection
from app.services.youtube_service import YouTubeApiError, YouTubeUnauthorizedError, youtube_service

logger = logging.getLogger("plexudo.oauth")
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class OAuthStateError(Exception):
    """Raised when OAuth state validation fails (expired or tampered)."""


class GoogleOAuthError(Exception):
    """Raised when Google token exchange or revocation fails."""


def _to_uuid(val: str | uuid.UUID) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


def generate_oauth_state(user_id: str | uuid.UUID) -> str:
    """
    Generate an HMAC-signed state token containing user_id and expiration timestamp.
    Prevents CSRF and ensures the callback belongs to the current user session.
    """
    uid_str = str(_to_uuid(user_id))
    exp = int(time.time()) + 900  # 15 minutes TTL
    payload = f"{uid_str}:{exp}"
    sig = hmac.new(settings.CSRF_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_oauth_state(state: str, expected_user_id: str | uuid.UUID) -> bool:
    """
    Verify the HMAC signature, expiration timestamp, and matching user_id.
    """
    try:
        parts = state.split(":")
        if len(parts) != 3:
            return False
        uid_str, exp_str, sig = parts
        exp = int(exp_str)
        if time.time() > exp:
            return False

        if uid_str != str(_to_uuid(expected_user_id)):
            return False

        payload = f"{uid_str}:{exp_str}"
        expected_sig = hmac.new(settings.CSRF_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


class GoogleOAuthService:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=15.0)

    def get_authorization_url(self, user_id: str | uuid.UUID) -> str:
        """
        Build the Google OAuth consent screen URL.
        Requests offline access and minimal YouTube scopes.
        """
        state = generate_oauth_state(user_id)
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.YOUTUBE_CONNECT_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for Google access and refresh tokens.
        """
        client = await self._get_client()
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.YOUTUBE_CONNECT_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        try:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        except Exception as exc:
            raise GoogleOAuthError(f"Failed to communicate with Google token endpoint: {exc}") from exc

        if not resp.is_success:
            raise GoogleOAuthError(f"Google token exchange failed: {resp.text}")

        return resp.json()

    async def fetch_google_email(self, access_token: str) -> Optional[str]:
        """Fetch email address of the connected Google account."""
        client = await self._get_client()
        try:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.is_success:
                return resp.json().get("email")
        except Exception:
            pass
        return None

    async def store_connection(
        self,
        db: AsyncSession,
        user_id: str | uuid.UUID,
        tokens: dict[str, Any],
    ) -> YoutubeConnection:
        """
        Encrypt tokens at rest and persist/update the user's YouTube connection.
        """
        uid = _to_uuid(user_id)
        raw_access_token = tokens["access_token"]
        raw_refresh_token = tokens.get("refresh_token")
        expires_in = int(tokens.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Encrypt tokens with AES/Fernet
        encrypted_access = encrypt_bytes(raw_access_token.encode())
        encrypted_refresh = encrypt_bytes(raw_refresh_token.encode()) if raw_refresh_token else None

        # Fetch safe channel info and email to store for fast dashboard display
        google_email = await self.fetch_google_email(raw_access_token)
        channel_info = {}
        try:
            channel_info = await youtube_service.get_my_channel(raw_access_token)
        except Exception as e:
            logger.warning("Could not fetch channel details during OAuth connect: %s", e)

        # Check for existing connection
        stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == uid)
        result = await db.execute(stmt)
        conn = result.scalar_one_or_none()

        if conn is None:
            conn = YoutubeConnection(
                user_id=uid,
                google_email=google_email,
                youtube_channel_id=channel_info.get("id"),
                channel_title=channel_info.get("title"),
                channel_avatar_url=channel_info.get("avatar_url"),
                scopes=tokens.get("scope"),
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                token_expires_at=expires_at,
            )
            db.add(conn)
        else:
            conn.google_email = google_email or conn.google_email
            conn.youtube_channel_id = channel_info.get("id") or conn.youtube_channel_id
            conn.channel_title = channel_info.get("title") or conn.channel_title
            conn.channel_avatar_url = channel_info.get("avatar_url") or conn.channel_avatar_url
            conn.scopes = tokens.get("scope") or conn.scopes
            conn.access_token_encrypted = encrypted_access
            if encrypted_refresh:
                conn.refresh_token_encrypted = encrypted_refresh
            conn.token_expires_at = expires_at

        await db.commit()
        await db.refresh(conn)
        return conn

    async def get_valid_access_token(
        self,
        db: AsyncSession,
        user_id: str | uuid.UUID,
    ) -> str:
        """
        Retrieve and decrypt the user's access token.
        If expired, automatically refreshes it via the refresh token.
        """
        uid = _to_uuid(user_id)
        stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == uid)
        result = await db.execute(stmt)
        conn = result.scalar_one_or_none()
        if not conn:
            raise YouTubeUnauthorizedError("No YouTube account connected")

        # Check if token is expired or about to expire in next 60s
        now = datetime.now(timezone.utc)
        if conn.token_expires_at:
            expires_at = conn.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at <= now + timedelta(seconds=60):
                if not conn.refresh_token_encrypted:
                    raise YouTubeUnauthorizedError("YouTube authorization expired, please reconnect")

                # Decrypt refresh token and call Google to refresh
                decrypted_refresh = decrypt_bytes(conn.refresh_token_encrypted).decode()
                refreshed = await self._refresh_access_token(decrypted_refresh)

                raw_access = refreshed["access_token"]
                expires_in = int(refreshed.get("expires_in", 3600))
                conn.access_token_encrypted = encrypt_bytes(raw_access.encode())
                conn.token_expires_at = now + timedelta(seconds=expires_in)
                await db.commit()
                return raw_access

        return decrypt_bytes(conn.access_token_encrypted).decode()

    async def _refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        client = await self._get_client()
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        if not resp.is_success:
            raise GoogleOAuthError(f"Failed to refresh YouTube token: {resp.text}")
        return resp.json()

    async def disconnect(self, db: AsyncSession, user_id: str | uuid.UUID) -> None:
        """
        Revoke the OAuth token at Google and delete the database record.
        """
        uid = _to_uuid(user_id)
        stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == uid)
        result = await db.execute(stmt)
        conn = result.scalar_one_or_none()

        if conn:
            try:
                # Attempt best-effort revocation with Google
                raw_token = decrypt_bytes(conn.access_token_encrypted).decode()
                client = await self._get_client()
                await client.post(
                    GOOGLE_REVOKE_URL,
                    params={"token": raw_token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
            except Exception as e:
                logger.info("Token revocation warning during disconnect: %s", e)

            await db.execute(delete(YoutubeConnection).where(YoutubeConnection.user_id == uid))
            await db.commit()


# Global singleton instance
google_oauth_service = GoogleOAuthService()
