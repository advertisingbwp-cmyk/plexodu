# Plexudo — Authentication Flow (v1)

Account creation and login are email + password only. Google OAuth is used
exclusively for the separate Connect-YouTube flow (§5) — there is no "Sign in with
Google."

## 1. Signup + email verification (§11)

```
User submits {username, email, password, confirm_password}
  ↓
Validate (uniqueness, password strength, match confirm)
  ↓
Hash password with Argon2id → INSERT users (email_verified_at = NULL)
  ↓
Generate random 32-byte token → store sha256(token) in email_verification_tokens
  (expires_at = now + 24h)
  ↓
email_service.send_verification_email(raw token, only in the link — never stored raw)
  ↓
Response: 201, no session created
  ↓
User clicks link → frontend POSTs {token} to /auth/verify-email
  ↓
Backend: sha256(token) lookup → check not expired, not consumed
  ↓
Mark consumed_at, set users.email_verified_at = now()
  ↓
User can now log in with full access
```

## 2. Login (§10)

```
User submits {email, password}
  ↓
Look up user by (case-insensitive) email
  ↓
argon2.verify(password, password_hash)  — constant-time, generic error either way
  ↓
On success: INSERT sessions row, set HttpOnly/Secure/SameSite=Lax cookie = session.id
  ↓
200 { user, email_verified }
  ↓
If email_verified = false: frontend shows a restricted "verify your email" view;
every credit-consuming API call still independently returns 403 EMAIL_NOT_VERIFIED
(never trust the frontend state alone)
```

## 3. Forgot / reset password (§13)

```
User submits {email}
  ↓
Look up user — but respond 202 either way (no account-existence signal)
  ↓
If found: generate token, store sha256(token) in password_reset_tokens
  (expires_at = now + 1h), email the reset link
  ↓
User opens link → submits {token, new_password, confirm_password}
  ↓
Backend: sha256(token) lookup → not expired, not consumed
  ↓
Hash new password, UPDATE users.password_hash
  ↓
Mark token consumed_at
  ↓
Revoke ALL existing sessions for that user (forces re-login everywhere — a password
reset is a strong signal the old sessions shouldn't be trusted)
  ↓
200 → user logs in fresh
```

## 4. Change password (authenticated, §12)

```
User submits {current_password, new_password}  (session required)
  ↓
Verify current_password against stored hash
  ↓
Hash + store new_password
  ↓
Revoke all OTHER sessions (keep the current one alive)
  ↓
200
```

## 5. YouTube connect — the only OAuth flow in this app (§16)

```
GET /youtube/connect   (session required — this is authorization, not login)
  ↓
Redirect to Google consent — YouTube scope only, requested only at this point,
never bundled into the login flow
  ↓
Google redirects to /youtube/callback?code=...
  ↓
Exchange code for access + refresh tokens
  ↓
Encrypt both with TOKEN_ENCRYPTION_KEY → UPSERT youtube_connections for the
CURRENT SESSION'S user_id (never a token pool shared across users)
  ↓
Redirect back to the dashboard's YouTube-connection settings view
```

## 6. Session lifecycle & logout

```
Every request with a session cookie:
  ↓
Look up sessions.id → check revoked_at IS NULL AND expires_at > now()
  ↓
Valid: touch last_seen_at, proceed as that session's user_id
Invalid/missing: 401, frontend redirects to login

Logout:
  ↓
POST /auth/logout → UPDATE sessions SET revoked_at = now() WHERE id = <this session>
  ↓
Clear the cookie client-side
  ↓
204
```
