"""
Plexudo Transactional Email Service
Sends real emails via Gmail SMTP or configured SMTP provider.
"""

import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "advertisingbwp@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "kehkdtrtkolwebup")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "advertisingbwp@gmail.com")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Plexudo")
BASE_URL = os.environ.get("BASE_URL", "https://plexudo.vercel.app")


def _send_smtp_email_async(to_email: str, subject: str, html_content: str, text_content: str = ""):
    """Internal worker to dispatch SMTP emails safely in background."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM_ADDRESS}>"
        msg["To"] = to_email

        if text_content:
            part1 = MIMEText(text_content, "plain", "utf-8")
            msg.attach(part1)

        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part2)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM_ADDRESS, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL_ERROR] Failed to send email to {to_email}: {e}")
        return False


def send_async(to_email: str, subject: str, html_content: str, text_content: str = ""):
    """Dispatches email in a background thread so UI/API remains blazing fast."""
    t = threading.Thread(
        target=_send_smtp_email_async,
        args=(to_email, subject, html_content, text_content),
        daemon=True
    )
    t.start()


# ─── 1. Welcome & Email Verification Email ─────────────────────────────────────
def send_welcome_email(to_email: str, name: str, verify_token: str = ""):
    verify_link = f"{BASE_URL}/api/verify-email?token={verify_token}" if verify_token else f"{BASE_URL}/dashboard.html"
    subject = "Welcome to Plexudo! 🚀 Your 3 Free Credits Are Ready"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color:#edf2fb; margin:0; padding:30px 15px; color:#0f172a;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border-radius:24px; padding:36px 30px; box-shadow:0 10px 30px rgba(67,73,191,0.06); border:1px solid #e2e8f0;">
        
        <!-- Header -->
        <div style="text-align:center; margin-bottom:28px;">
          <div style="display:inline-flex; align-items:center; gap:8px;">
            <div style="background:#4349bf; color:#ffffff; font-weight:900; font-size:16px; padding:8px 12px; border-radius:10px;">P</div>
            <span style="font-size:22px; font-weight:800; color:#0f172a; letter-spacing:-0.02em;">PLEXUDO</span>
          </div>
        </div>

        <!-- Body -->
        <h1 style="font-size:22px; font-weight:800; color:#0f172a; margin-top:0; margin-bottom:12px;">Welcome aboard, {name or 'Creator'}! 🎉</h1>
        <p style="font-size:14.5px; color:#475569; line-height:1.6; margin-bottom:20px;">
          Your Plexudo account is now active. You have been credited with <strong>3 Free AI &amp; YouTube SEO Credits</strong> to start optimizing your channel and discovering high-ranking keywords.
        </p>

        <!-- Feature Highlights -->
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px 20px; margin-bottom:24px;">
          <div style="font-size:12px; font-weight:800; color:#4349bf; text-transform:uppercase; margin-bottom:8px;">What you can do right now:</div>
          <ul style="margin:0; padding-left:20px; font-size:13.5px; color:#334155; line-height:1.7;">
            <li>🎯 Calculate real <strong>50/50 YouTube SEO Scores</strong></li>
            <li>💡 Generate trending, high-CTR <strong>AI Creator Titles</strong></li>
            <li>📈 Track 28-day <strong>View Growth Velocity</strong> curves</li>
            <li>💬 Extract NLP <strong>Audience Sentiment &amp; Reactions</strong></li>
          </ul>
        </div>

        <!-- CTA Button -->
        <div style="text-align:center; margin-bottom:24px;">
          <a href="{BASE_URL}/dashboard.html" style="background:#4349bf; color:#ffffff; text-decoration:none; padding:13px 32px; border-radius:14px; font-weight:700; font-size:14px; display:inline-block; box-shadow:0 4px 14px rgba(67,73,191,0.25);">
            Launch Plexudo Dashboard ➔
          </a>
        </div>

        <!-- Footer Notice -->
        <div style="border-top:1px solid #f1f5f9; padding-top:18px; text-align:center; font-size:12px; color:#94a3b8;">
          If you didn't create this account, you can safely ignore this email.<br>
          &copy; 2026 Plexudo • YouTube Creator SEO &amp; Analytics
        </div>
      </div>
    </body>
    </html>
    """
    send_async(to_email, subject, html, f"Welcome to Plexudo! Log in at {BASE_URL}/dashboard.html")


# ─── 2. Password Changed Security Alert ────────────────────────────────────────
def send_password_changed_email(to_email: str, name: str):
    subject = "Security Alert: Your Plexudo Password Was Changed"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color:#edf2fb; margin:0; padding:30px 15px; color:#0f172a;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border-radius:24px; padding:36px 30px; box-shadow:0 10px 30px rgba(67,73,191,0.06); border:1px solid #e2e8f0;">
        
        <!-- Header -->
        <div style="text-align:center; margin-bottom:28px;">
          <div style="display:inline-flex; align-items:center; gap:8px;">
            <div style="background:#4349bf; color:#ffffff; font-weight:900; font-size:16px; padding:8px 12px; border-radius:10px;">P</div>
            <span style="font-size:22px; font-weight:800; color:#0f172a; letter-spacing:-0.02em;">PLEXUDO</span>
          </div>
        </div>

        <!-- Body -->
        <div style="text-align:center; margin-bottom:18px;">
          <div style="width:50px; height:50px; border-radius:50%; background:#ecfdf5; color:#10b981; font-size:24px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:10px;">🔒</div>
          <h1 style="font-size:20px; font-weight:800; color:#0f172a; margin:0;">Password Updated Successfully</h1>
        </div>

        <p style="font-size:14.5px; color:#475569; line-height:1.6; margin-bottom:18px;">
          Hello {name or 'Creator'}, this is a confirmation that the password for your Plexudo account (<strong>{to_email}</strong>) was just changed.
        </p>

        <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:14px; padding:14px 18px; margin-bottom:24px; font-size:13px; color:#991b1b; line-height:1.5;">
          ⚠️ <strong>Didn't make this change?</strong><br>
          If you did not authorize this password update, please reset your password immediately or contact our support team at <a href="mailto:advertisingbwp@gmail.com" style="color:#b91c1c; font-weight:700;">advertisingbwp@gmail.com</a>.
        </div>

        <!-- CTA Button -->
        <div style="text-align:center; margin-bottom:24px;">
          <a href="{BASE_URL}/dashboard.html" style="background:#4349bf; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:14px; font-weight:700; font-size:13.5px; display:inline-block;">
            Sign In to Dashboard ➔
          </a>
        </div>

        <!-- Footer -->
        <div style="border-top:1px solid #f1f5f9; padding-top:18px; text-align:center; font-size:12px; color:#94a3b8;">
          This is an automated security notification from Plexudo.
        </div>
      </div>
    </body>
    </html>
    """
    send_async(to_email, subject, html, f"Your Plexudo password was changed. If this wasn't you, reset it at {BASE_URL}")


# ─── 3. Password Reset Request Email ───────────────────────────────────────────
def send_password_reset_email(to_email: str, reset_token: str):
    reset_link = f"{BASE_URL}/?reset_token={reset_token}"
    subject = "Reset Your Plexudo Password"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color:#edf2fb; margin:0; padding:30px 15px; color:#0f172a;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border-radius:24px; padding:36px 30px; box-shadow:0 10px 30px rgba(67,73,191,0.06); border:1px solid #e2e8f0;">
        
        <!-- Header -->
        <div style="text-align:center; margin-bottom:28px;">
          <div style="display:inline-flex; align-items:center; gap:8px;">
            <div style="background:#4349bf; color:#ffffff; font-weight:900; font-size:16px; padding:8px 12px; border-radius:10px;">P</div>
            <span style="font-size:22px; font-weight:800; color:#0f172a; letter-spacing:-0.02em;">PLEXUDO</span>
          </div>
        </div>

        <h1 style="font-size:20px; font-weight:800; color:#0f172a; margin-top:0; margin-bottom:12px;">Reset Your Password</h1>
        <p style="font-size:14.5px; color:#475569; line-height:1.6; margin-bottom:20px;">
          We received a request to reset the password for your Plexudo account. Click the button below to choose a new password:
        </p>

        <!-- CTA Button -->
        <div style="text-align:center; margin-bottom:24px;">
          <a href="{reset_link}" style="background:#4349bf; color:#ffffff; text-decoration:none; padding:13px 32px; border-radius:14px; font-weight:700; font-size:14px; display:inline-block; box-shadow:0 4px 14px rgba(67,73,191,0.25);">
            Reset My Password ➔
          </a>
        </div>

        <p style="font-size:12.5px; color:#64748b; margin-bottom:20px; line-height:1.5;">
          This link will expire in <strong>1 hour</strong>. If you did not request a password reset, you can safely ignore this email.
        </p>

        <!-- Footer -->
        <div style="border-top:1px solid #f1f5f9; padding-top:18px; text-align:center; font-size:12px; color:#94a3b8;">
          &copy; 2026 Plexudo • YouTube Creator SEO &amp; Analytics
        </div>
      </div>
    </body>
    </html>
    """
    send_async(to_email, subject, html, f"Reset your password at: {reset_link}")
