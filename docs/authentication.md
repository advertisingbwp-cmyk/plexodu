# Authentication & Closed-App Security Model

## 1. Overview
Plexudo enforces a **Closed-App Privacy Model**:
- **Public Surface**: Landing pages, blog posts, SEO tool overview pages, `robots.txt`, and `sitemap.xml` rendered server-side with FastAPI + Jinja2.
- **Private Surface**: User dashboard, profile settings, connected YouTube channel, credits balance, history, and AI operations.

## 2. Authentication Rules
- **Signup & Login**: Email + Password using Argon2id password hashing.
- **Session Architecture**: Server-side sessions table with HttpOnly, Secure, SameSite=Lax cookie (`plexudo_session`).
- **CSRF Protection**: HMAC-SHA256 tokens derived from session ID and `CSRF_SECRET`.
- **Verification Guard**: Unverified users can log in and view their profile, but protected creator tools return `403 EMAIL_NOT_VERIFIED`.
- **Unauthenticated Protection**: Unauthenticated API calls return `401 Unauthorized`.
- **User Scoping**: Every database lookup (history, YouTube tokens, credits) resolves `user.id` directly from the validated session cookie. Client-supplied IDs are never trusted.

## 3. Endpoints Summary
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/signup` | Public | Create account |
| `POST` | `/api/v1/auth/login` | Public | Login with email/pass |
| `POST` | `/api/v1/auth/logout` | Authenticated | Revoke session |
| `GET` | `/api/v1/auth/me` | Authenticated | Current user info |
| `POST` | `/api/v1/auth/verify-email` | Public | Verify token & grant 3 credits |
| `POST` | `/api/v1/auth/resend-verification` | Authenticated | Resend verification email |
| `POST` | `/api/v1/auth/forgot-password` | Public | Request reset link (uniform 202) |
| `POST` | `/api/v1/auth/reset-password` | Public | Set new password via token |
| `POST` | `/api/v1/auth/change-password` | Authenticated | Change password |
| `GET` | `/api/v1/profile/` | Authenticated | Full profile & YouTube connection |
| `PATCH` | `/api/v1/profile/` | Authenticated | Update profile |
| `GET` | `/api/v1/credits/balance` | Authenticated | Current credit balance |
| `GET` | `/api/v1/credits/ledger` | Authenticated | Paginated credit transactions |
| `POST` | `/api/v1/credits/claim-ad-reward`| Verified | Claim verified ad credit (+1) |
| `GET` | `/api/v1/youtube/connect` | Verified | Start Google OAuth flow |
| `GET` | `/api/v1/youtube/callback` | Verified | Complete OAuth flow |
| `GET` | `/api/v1/youtube/status` | Authenticated | Check YouTube connection |
| `DELETE`| `/api/v1/youtube/disconnect`| Authenticated | Revoke & remove YouTube connection |
| `GET` | `/api/v1/youtube/channel` | Verified | Connected / public channel metrics |
| `GET` | `/api/v1/youtube/videos` | Verified | Channel video uploads |
| `POST` | `/api/v1/tools/seo-score` | Verified | Score video SEO (consumes credit) |
| `POST` | `/api/v1/tools/video-analyzer` | Verified | Analyze video (consumes credit) |
| `POST` | `/api/v1/tools/keyword-tool` | Verified | Explore keywords (consumes credit) |
| `POST` | `/api/v1/tools/trend-analyzer` | Verified | Regional trends (consumes credit) |
| `POST` | `/api/v1/tools/competitor-analysis` | Verified | Analyze channel (consumes credit) |
| `POST` | `/api/v1/tools/ai-assistant` | Verified | Groq creator assistant (consumes credit) |
| `GET` | `/api/v1/history/` | Authenticated | Paginated tool history |
