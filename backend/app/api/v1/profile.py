"""
Profile & Settings API Router (/api/v1/profile/*)
==================================================
Manages authenticated user profile data, username updates, and linked account visibility.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.db.models.youtube import YoutubeConnection

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)


@router.get("/")
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full profile details for the authenticated user, including YouTube connection status.
    """
    stmt = select(YoutubeConnection).where(YoutubeConnection.user_id == user.id)
    result = await db.execute(stmt)
    yt_conn = result.scalar_one_or_none()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified_at is not None,
        "credit_balance": user.credit_balance,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "youtube": {
            "connected": yt_conn is not None,
            "channel_title": yt_conn.channel_title if yt_conn else None,
            "channel_id": yt_conn.youtube_channel_id if yt_conn else None,
            "channel_avatar_url": yt_conn.channel_avatar_url if yt_conn else None,
            "google_email": yt_conn.google_email if yt_conn else None,
            "connected_at": yt_conn.created_at.isoformat() if yt_conn and yt_conn.created_at else None,
        },
    }


@router.patch("/")
async def update_profile(
    req: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update username for the authenticated user.
    """
    if not req.username:
        return {"status": "no_changes"}

    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(username=req.username)
    )
    try:
        await db.execute(stmt)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="USERNAME_TAKEN",
        )

    return {"status": "updated", "username": req.username}
