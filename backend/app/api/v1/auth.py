"""
Auth API Router  (/api/v1/auth/*)
==================================
Account creation and login: email + password only.
Google OAuth is NOT a login method — it is only used for the
Connect-YouTube flow at /api/v1/youtube/connect.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_csrf_token, verify_csrf_token
from app.core.session import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.services.auth_service import (
    EmailTakenError,
    InvalidCredentialsError,
    TokenInvalidOrExpiredError,
    UsernameTakenError,
    authenticate_user,
    change_password,
    consume_password_reset_token,
    create_email_verification_token,
    create_password_reset_token,
    create_session,
    get_user_by_email,
    create_user,
    revoke_session,
    verify_email_token,
)
from app.services.email_service import email_service

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    pass  # identity resolved from session


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=(settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_DAYS * 24 * 60 * 60,
    )


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup", status_code=201)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new Plexudo account (email + password only).
    No session is created; the user must verify their email first.
    """
    if req.password != req.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match")

    try:
        user = await create_user(db, req.username, str(req.email), req.password)
    except EmailTakenError:
        raise HTTPException(status_code=409, detail="EMAIL_TAKEN")
    except UsernameTakenError:
        raise HTTPException(status_code=409, detail="USERNAME_TAKEN")

    # Issue a verification token and send real verification email
    raw_token = await create_email_verification_token(db, user.id)
    await email_service.send_verification_email(user.email, raw_token)

    return {"user_id": str(user.id)}


@router.post("/login")
async def login(
    req: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email + password.
    Returns a session cookie (HttpOnly) + a CSRF token in the body.
    Login succeeds even if the email is unverified; downstream routes
    independently reject unverified users with 403 EMAIL_NOT_VERIFIED.
    """
    user = await authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")

    session = await create_session(
        db,
        user_id=str(user.id),
        user_agent=request.headers.get("user-agent"),
        ip_address=_get_client_ip(request),
    )
    csrf_token = generate_csrf_token(str(session.id))
    _set_session_cookie(response, str(session.id))

    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "email_verified": user.email_verified_at is not None,
            "credit_balance": user.credit_balance,
        },
        "csrf_token": csrf_token,
    }


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current session and clear the cookie."""
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_id:
        await revoke_session(db, session_id)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return the authenticated user's profile and credit balance."""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified_at is not None,
        "credit_balance": user.credit_balance,
    }


@router.post("/verify-email")
async def verify_email_endpoint(req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Consume an email verification token. Grants 3 welcome credits on success."""
    try:
        await verify_email_token(db, req.token)
    except TokenInvalidOrExpiredError:
        raise HTTPException(status_code=400, detail="TOKEN_INVALID_OR_EXPIRED")
    return {"status": "ok"}


@router.post("/resend-verification", status_code=202)
async def resend_verification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resend the verification email to the authenticated user.
    Rate limiting is applied at the middleware layer (security-model.md §6).
    """
    if user.email_verified_at is not None:
        # Already verified — silently succeed (idempotent)
        return {"status": "ok"}

    raw_token = await create_email_verification_token(db, user.id)
    await email_service.send_verification_email(user.email, raw_token)
    return {"status": "ok"}


@router.post("/forgot-password", status_code=202)
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Request a password reset email.
    Always returns 202 regardless of whether the email exists
    (no account enumeration — security-model.md §3, auth-flow.md §3).
    """
    user = await get_user_by_email(db, str(req.email))
    if user:
        raw_token = await create_password_reset_token(db, user.id)
        await email_service.send_password_reset_email(user.email, raw_token)
    # Always 202 — body is empty to avoid leaking account existence.


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Consume a password reset token and set a new password."""
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match")
    try:
        await consume_password_reset_token(db, req.token, req.new_password)
    except TokenInvalidOrExpiredError:
        raise HTTPException(status_code=400, detail="TOKEN_INVALID_OR_EXPIRED")
    return {"status": "ok"}


@router.post("/change-password")
async def api_change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the authenticated user. Keeps current session alive."""
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    try:
        await change_password(db, user, req.current_password, req.new_password, session_id)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="CURRENT_PASSWORD_INCORRECT")
    return {"status": "ok"}
