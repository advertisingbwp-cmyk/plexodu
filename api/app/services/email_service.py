"""
Transactional Email Service
============================
Handles sending real transactional emails for email verification and password resets.

Supported Providers:
- 'smtp': Asynchronous SMTP delivery via aiosmtplib.
- 'sendgrid': SendGrid v3 Mail Send API.
- 'resend': Resend API.
- 'console' / 'test': In-memory outbox recording for development and testing.

CRITICAL INVARIANTS:
1. Credentials are loaded strictly from environment variables.
2. Email verification links contain the raw one-time token; database only stores SHA-256 hash.
3. Errors are logged and handled cleanly without exposing credentials.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("plexudo.email")
settings = get_settings()


class EmailDeliveryError(Exception):
    """Raised when sending an email fails."""


class EmailService:
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._client = http_client
        # In-memory record of sent emails for test environments
        self.outbox: list[dict[str, Any]] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=10.0)

    def _build_verification_link(self, raw_token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/verify-email?token={raw_token}"

    def _build_reset_link(self, raw_token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/reset-password?token={raw_token}"

    async def send_verification_email(self, to_email: str, raw_token: str) -> bool:
        """
        Send an account verification email containing the unique 24-hour verification link.
        """
        link = self._build_verification_link(raw_token)
        subject = "Verify your Plexudo account"

        text_body = (
            f"Welcome to Plexudo!\n\n"
            f"Please verify your email address to activate your 3 welcome credits and access YouTube creator tools:\n"
            f"{link}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you did not create a Plexudo account, you can safely ignore this email."
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px 20px;">
  <div style="max-width: 540px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155;">
    <h1 style="color: #6366f1; margin-top: 0; font-size: 24px;">Welcome to Plexudo</h1>
    <p style="color: #cbd5e1; font-size: 16px; line-height: 1.5;">
      Thanks for signing up. Please verify your email address to activate your account and claim your <strong>3 free welcome credits</strong>.
    </p>
    <div style="margin: 32px 0;">
      <a href="{link}" style="display: inline-block; background-color: #6366f1; color: #ffffff; padding: 12px 28px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 16px;">
        Verify Email Address
      </a>
    </div>
    <p style="color: #64748b; font-size: 13px; line-height: 1.4;">
      Or copy and paste this link into your browser:<br>
      <a href="{link}" style="color: #818cf8; word-break: break-all;">{link}</a>
    </p>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
      This link will expire in 24 hours. If you did not sign up for Plexudo, please disregard this email.
    </p>
  </div>
</body>
</html>"""

        return await self._dispatch_email(to_email, subject, text_body, html_body)

    async def send_password_reset_email(self, to_email: str, raw_token: str) -> bool:
        """
        Send a password reset email with the 1-hour secure reset link.
        """
        link = self._build_reset_link(raw_token)
        subject = "Reset your Plexudo password"

        text_body = (
            f"You requested a password reset for your Plexudo account.\n\n"
            f"Click the link below to set a new password:\n"
            f"{link}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request a password reset, please secure your account immediately."
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px 20px;">
  <div style="max-width: 540px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155;">
    <h1 style="color: #6366f1; margin-top: 0; font-size: 24px;">Password Reset Request</h1>
    <p style="color: #cbd5e1; font-size: 16px; line-height: 1.5;">
      We received a request to reset the password for your Plexudo account.
    </p>
    <div style="margin: 32px 0;">
      <a href="{link}" style="display: inline-block; background-color: #6366f1; color: #ffffff; padding: 12px 28px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 16px;">
        Reset Password
      </a>
    </div>
    <p style="color: #64748b; font-size: 13px; line-height: 1.4;">
      Or copy and paste this link into your browser:<br>
      <a href="{link}" style="color: #818cf8; word-break: break-all;">{link}</a>
    </p>
    <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
      This link is valid for 1 hour. If you did not make this request, you can safely ignore this email.
    </p>
  </div>
</body>
</html>"""

        return await self._dispatch_email(to_email, subject, text_body, html_body)

    async def _dispatch_email(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        """Route to appropriate email provider based on configuration."""
        current_settings = get_settings()
        provider = current_settings.EMAIL_PROVIDER.lower()

        # Always record in outbox (for test assertions and dev inspection)
        self.outbox.append({
            "to": to_email,
            "subject": subject,
            "text": text_body,
            "html": html_body,
            "provider": provider,
        })

        if provider in ("console", "test") or current_settings.ENVIRONMENT == "test":
            logger.info("EMAIL DISPATCHED [%s] to %s: %s\n%s", provider, to_email, subject, text_body)
            print(f"EMAIL DISPATCHED [{provider}] to {to_email}: {subject}\n{text_body}", flush=True)
            return True

        if provider == "smtp":
            return await self._send_smtp(to_email, subject, text_body, html_body)
        elif provider == "sendgrid":
            return await self._send_sendgrid(to_email, subject, text_body, html_body)
        elif provider == "resend":
            return await self._send_resend(to_email, subject, text_body, html_body)

        logger.warning("Unrecognized EMAIL_PROVIDER '%s', logged to outbox", provider)
        return True

    async def _send_smtp(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        """Send via aiosmtplib SMTP."""
        try:
            import aiosmtplib

            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME or None,
                password=settings.SMTP_PASSWORD or None,
                start_tls=settings.SMTP_USE_TLS,
            )
            return True
        except Exception as exc:
            logger.error("Failed to send email via SMTP: %s", exc)
            return False

    async def _send_sendgrid(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        if not settings.SENDGRID_API_KEY:
            logger.warning("SENDGRID_API_KEY missing")
            return False
        client = await self._get_client()
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.EMAIL_FROM_ADDRESS, "name": settings.EMAIL_FROM_NAME},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": text_body},
                {"type": "text/html", "value": html_body},
            ],
        }
        try:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
            )
            return resp.is_success
        except Exception as exc:
            logger.error("Failed to send email via SendGrid: %s", exc)
            return False

    async def _send_resend(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY missing")
            return False
        client = await self._get_client()
        payload = {
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
            "to": [to_email],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }
        try:
            resp = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            )
            return resp.is_success
        except Exception as exc:
            logger.error("Failed to send email via Resend: %s", exc)
            return False


# Global singleton instance
email_service = EmailService()
