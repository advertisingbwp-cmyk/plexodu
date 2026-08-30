# Google OAuth — Connect YouTube Flow

## 1. Overview & Architecture
Plexudo account authentication and YouTube channel connection are **strictly separate**:
- **Primary Authentication**: Email + Password + Email Verification + HttpOnly Session Cookie.
- **YouTube Connection**: A logged-in, verified Plexudo user initiates "Connect YouTube" via Google OAuth 2.0.

## 2. OAuth Lifecycle
```
Logged-in User
      ↓
GET /api/v1/youtube/connect
      ↓
Signed HMAC State + Google Consent Screen
      ↓
User Grants YouTube Scopes
      ↓
GET /api/v1/youtube/callback?code=...&state=...
      ↓
Validate State Signature (CSRF Check)
      ↓
Exchange Code for Access & Refresh Tokens
      ↓
Encrypt Tokens with AES/Fernet (TOKEN_ENCRYPTION_KEY)
      ↓
Persist to youtube_connections (Scoped to user_id)
```

## 3. Minimum Required Scopes
Only the minimum required scopes are requested:
- `https://www.googleapis.com/auth/youtube.readonly` — Read channel statistics and video metrics.
- `https://www.googleapis.com/auth/userinfo.email` — Display the linked Google email safely in settings.

## 4. Encryption & Privacy Invariants
- Tokens are encrypted at rest with `TOKEN_ENCRYPTION_KEY` using AES-128/Fernet.
- Raw tokens are **never** returned in API responses, stored in cookies, or sent to frontend JavaScript.
- Tokens are strictly isolated per user; User A can never query or use User B's credentials.

## 5. Configuration
Add to `.env`:
```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
YOUTUBE_CONNECT_REDIRECT_URI=http://localhost:8000/api/v1/youtube/callback
TOKEN_ENCRYPTION_KEY=your-random-32-byte-secret
```
