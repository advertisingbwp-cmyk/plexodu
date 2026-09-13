"""
Plexudo Transactional Email Service
Sends real emails via Gmail SMTP or configured SMTP provider.
Robust UTF-8 and Vercel Serverless compatible.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Plexudo").strip()
BASE_URL = os.environ.get("BASE_URL", "https://plexudo.vercel.app").strip()
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@plexudo.com").strip()


def send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
    """Dispatches email safely with full UTF-8 and serverless compatibility."""
    smtp_user = os.environ.get("SMTP_USERNAME", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
    except (ValueError, TypeError):
        smtp_port = 587
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    from_addr = os.environ.get("EMAIL_FROM_ADDRESS", "").strip() or smtp_user or "noreply@plexudo.com"
    from_name = os.environ.get("EMAIL_FROM_NAME", "Plexudo").strip()

    if not smtp_user or not smtp_pass:
        print("[EMAIL_WARN] SMTP credentials not configured in environment. Email dispatch safely skipped.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((str(Header(from_name, "utf-8")), from_addr))
        msg["To"] = to_email

        if not text_content:
            text_content = "Please view this email in an HTML-compatible client."

        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print(f"[EMAIL_SUCCESS] Successfully delivered email to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL_ERROR] Failed to send email to {to_email}: {e}")
        return False


# ─── Auth Email Flows Deprecated in Public / No-Login Mode ──────────────────
def send_verification_email(to_email: str, name: str, verify_token: str) -> bool:
    """Delegates to send_email safely."""
    return send_email(to_email, "Email Verification", f"<p>Verification token: {verify_token}</p>")


def send_password_changed_email(to_email: str, name: str) -> bool:
    """Delegates to send_email safely."""
    return send_email(to_email, "Password Changed", "<p>Your password was changed.</p>")


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Delegates to send_email safely."""
    return send_email(to_email, "Password Reset", f"<p>Reset token: {reset_token}</p>")
