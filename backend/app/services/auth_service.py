"""
Auth Service
============
All account creation and login is email + password only.
Google OAuth is used exclusively for the Connect-YouTube flow (youtube.py).
There is NO 'Sign in with Google'.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.db.models.session import Session
from app.db.models.token import EmailVerificationToken, PasswordResetToken
from app.db.models.user import User
from app.services.credit_ledger_service import grant_welcome_credits

settings = get_settings()


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class EmailTakenError(Exception):
    pass


class UsernameTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class TokenInvalidOrExpiredError(Exception):
    pass


def _to_uuid(val: str | uuid.UUID | None) -> uuid.UUID | None:
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------


async def create_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    """Create a new user with an unverified email and zero credits."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        email_verified_at=None,
        credit_balance=0,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError as exc:
        await db.rollback()
        # Inspect constraint violation to surface the right error.
        msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
        if "email" in msg:
            raise EmailTakenError() from exc
        raise UsernameTakenError() from exc


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Return user if credentials are valid, None otherwise (constant-time)."""
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def create_session(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> Session:
    session = Session(
        user_id=_to_uuid(user_id),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.SESSION_MAX_AGE_DAYS),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str | uuid.UUID) -> Session | None:
    sid = _to_uuid(session_id)
    result = await db.execute(
        select(Session).where(
            Session.id == sid,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(db: AsyncSession, session_id: str | uuid.UUID) -> None:
    sid = _to_uuid(session_id)
    await db.execute(delete(Session).where(Session.id == sid))
    await db.commit()


async def revoke_all_sessions(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    except_session_id: str | uuid.UUID | None = None,
) -> None:
    uid = _to_uuid(user_id)
    stmt = delete(Session).where(Session.user_id == uid)
    if except_session_id:
        stmt = stmt.where(Session.id != _to_uuid(except_session_id))
    await db.execute(stmt)
    await db.commit()


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------


async def create_email_verification_token(
    db: AsyncSession, user_id: str | uuid.UUID
) -> str:
    """Create a new email verification token and return the raw (unstore) value."""
    raw_token = generate_token()
    token = EmailVerificationToken(
        user_id=_to_uuid(user_id),
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(token)
    await db.commit()
    return raw_token


async def verify_email_token(db: AsyncSession, token: str) -> User:
    """
    Validate a verification token, mark it consumed, set email_verified_at,
    and grant the 3 welcome credits.

    Raises TokenInvalidOrExpiredError if the token is missing, expired, or already used.
    """
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_token(token),
            EmailVerificationToken.is_consumed == False,  # noqa: E712
            EmailVerificationToken.expires_at > datetime.now(timezone.utc),
        )
    )
    token_obj = result.scalar_one_or_none()
    if not token_obj:
        raise TokenInvalidOrExpiredError()

    # Mark consumed and set verified timestamp atomically.
    token_obj.is_consumed = True

    user_result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = user_result.scalar_one()
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()

    # Grant welcome credits (idempotent — DB index prevents double-grant).
    await grant_welcome_credits(db, user.id)
    return user


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------


async def create_password_reset_token(
    db: AsyncSession, user_id: str | uuid.UUID
) -> str:
    """Create a 1-hour password reset token. Returns the raw (unsaved) token value."""
    raw_token = generate_token()
    token = PasswordResetToken(
        user_id=_to_uuid(user_id),
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(token)
    await db.commit()
    return raw_token


async def consume_password_reset_token(
    db: AsyncSession, token: str, new_password: str
) -> User:
    """
    Validate token, update password, revoke ALL sessions (force re-login everywhere).

    Raises TokenInvalidOrExpiredError if invalid/expired/already used.
    """
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(token),
            PasswordResetToken.is_consumed == False,  # noqa: E712
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    token_obj = result.scalar_one_or_none()
    if not token_obj:
        raise TokenInvalidOrExpiredError()

    token_obj.is_consumed = True

    user_result = await db.execute(select(User).where(User.id == token_obj.user_id))
    user = user_result.scalar_one()
    user.password_hash = hash_password(new_password)
    await db.commit()

    # Revoke all sessions — a password reset means old sessions can't be trusted.
    await revoke_all_sessions(db, user.id)
    return user


# ---------------------------------------------------------------------------
# Change Password (authenticated)
# ---------------------------------------------------------------------------


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    current_session_id: str | uuid.UUID | None,
) -> None:
    """
    Verify current password, update hash, revoke all OTHER sessions.

    Raises InvalidCredentialsError if current_password is wrong.
    """
    if not verify_password(current_password, user.password_hash):
        raise InvalidCredentialsError()

    user.password_hash = hash_password(new_password)
    await db.commit()

    # Keep the current session alive; revoke all others.
    await revoke_all_sessions(db, user.id, except_session_id=current_session_id)
