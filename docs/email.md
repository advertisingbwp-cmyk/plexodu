# Transactional Email Delivery

## 1. Overview
Plexudo delivers transactional emails for:
- Account email verification on signup (grants 3 welcome credits on verification)
- Resending verification emails for unverified users
- Secure password resets

## 2. Supported Providers
Configured via `EMAIL_PROVIDER`:
- `smtp`: Standard async SMTP delivery via `aiosmtplib` (Gmail, AWS SES, Postmark, Mailgun SMTP).
- `sendgrid`: SendGrid v3 API (`SENDGRID_API_KEY`).
- `resend`: Resend API (`RESEND_API_KEY`).
- `console` / `test`: Logs to console and in-memory outbox for local testing.

## 3. Token Security & Privacy
- Verification tokens (24h TTL) and password reset tokens (1h TTL) are generated with 32 secure random bytes.
- The raw token is included in the email link sent to the user.
- The database stores **only** the SHA-256 hash of the token (`token_hash`).
- Tokens are strictly single-use (`is_consumed`).
- Password reset requests always return `202 Accepted` uniformly to prevent account enumeration.

## 4. Configuration
Add to `.env`:
```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM_ADDRESS=noreply@plexudo.com
EMAIL_FROM_NAME=Plexudo
FRONTEND_URL=https://plexudo.vercel.app
```
