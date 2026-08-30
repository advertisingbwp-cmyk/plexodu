import uuid
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.base import get_db
from app.db.models.user import User
from app.db.models.session import Session
from datetime import datetime, timezone
from app.core.config import get_settings

settings = get_settings()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    session_id_str = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        session_uuid = uuid.UUID(str(session_id_str))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    stmt = (
        select(Session)
        .options(selectinload(Session.user))
        .where(
            Session.id == session_uuid,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if session_obj is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    # Touch last_seen_at — best-effort
    session_obj.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return session_obj.user


async def require_verified(user: User = Depends(get_current_user)) -> User:
    if not user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
        )
    return user
