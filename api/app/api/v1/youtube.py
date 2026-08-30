"""
YouTube API Router  (/api/v1/youtube/*)
========================================
Endpoints for managing YouTube OAuth connections and fetching channel/video metrics.

INVARIANTS:
1. Google OAuth is used strictly for YouTube channel authorization, never account login.
2. Tokens are stored encrypted at rest, per-user, and NEVER returned to the client.
3. Zero fake fallback videos or statistics.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.session import get_current_user, require_verified
from app.db.base import get_db
from app.db.models.user import User
from app.db.models.youtube import YoutubeConnection
from app.services.google_oauth_service import (
    GoogleOAuthError,
    google_oauth_service,
    verify_oauth_state,
)
from app.services.youtube_service import (
    YouTubeApiError,
    YouTubeNotFoundError,
    YouTubeQuotaExceededError,
    YouTubeUnauthorizedError,
    youtube_service,
)

logger = logging.getLogger("plexudo.youtube_api")
settings = get_settings()
router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/connect")
async def connect_youtube(
    user: User = Depends(require_verified),
):
    """
    Generate Google OAuth consent URL for connecting a YouTube channel.
    Embeds a secure signed state token tied to the current session's user ID.
    """
    auth_url = google_oauth_service.get_authorization_url(user.id)
    return {"url": auth_url}


@router.get("/callback")
async def youtube_callback(
    code: str = Query(..., description="Google OAuth authorization code"),
    state: str = Query(..., description="Signed OAuth state parameter"),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    Validates state parameter, exchanges code, encrypts tokens, and stores connection.
    """
    if not verify_oauth_state(state, user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter",
        )

    try:
        tokens = await google_oauth_service.exchange_code(code)
        conn = await google_oauth_service.store_connection(db, user.id, tokens)
    except GoogleOAuthError as exc:
        logger.error("OAuth exchange failed for user %s: %s", user.id, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "status": "connected",
        "channel_title": conn.channel_title,
        "channel_id": conn.youtube_channel_id,
        "channel_avatar_url": conn.channel_avatar_url,
    }


@router.get("/status")
async def youtube_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if the user has an active YouTube connection.
    Returns safe channel metadata. NEVER returns OAuth tokens.
    """
    stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == user.id)
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if not conn:
        return {"connected": False}

    return {
        "connected": True,
        "google_email": conn.google_email,
        "channel_id": conn.youtube_channel_id,
        "channel_title": conn.channel_title,
        "channel_avatar_url": conn.channel_avatar_url,
        "connected_at": conn.created_at.isoformat() if conn.created_at else None,
    }


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_youtube(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke Google OAuth tokens and remove YouTube connection from database.
    """
    await google_oauth_service.disconnect(db, user.id)
    return None


@router.get("/channel")
async def get_channel_metrics(
    channel_id_or_url: Optional[str] = Query(None, description="Optional public channel ID or handle"),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Get YouTube channel information.
    If no channel identifier is provided, returns the user's connected YouTube channel metrics.
    """
    try:
        if channel_id_or_url:
            return await youtube_service.get_channel_info(channel_id_or_url)

        # Use connected account's access token
        access_token = await google_oauth_service.get_valid_access_token(db, user.id)
        return await youtube_service.get_my_channel(access_token)
    except YouTubeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except YouTubeUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    except YouTubeQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
    except YouTubeApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/videos")
async def get_channel_videos(
    channel_id: Optional[str] = Query(None, description="Optional public channel ID"),
    max_results: int = Query(20, ge=1, le=50),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Get uploaded videos for a channel.
    If no channel_id is provided, returns uploads from the connected YouTube channel.
    """
    try:
        access_token = None
        if not channel_id:
            # Need connected channel
            stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == user.id)
            result = await db.execute(stmt)
            conn = result.scalar_one_or_none()
            if not conn or not conn.youtube_channel_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No YouTube channel connected")
            channel_id = conn.youtube_channel_id
            access_token = await google_oauth_service.get_valid_access_token(db, user.id)

        videos = await youtube_service.get_channel_videos(
            channel_id=channel_id,
            max_results=max_results,
            access_token=access_token,
        )
        return {"videos": videos, "count": len(videos)}
    except YouTubeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except YouTubeUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    except YouTubeQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
    except YouTubeApiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
