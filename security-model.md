# Plexudo — Security Model (v1)

## 1. Password hashing
Argon2id, tuned to OWASP's current baseline: `time_cost=3`, `memory_cost=65536`
(64 MB), `parallelism=4`. Never bcrypt-truncate-72-bytes surprises — Argon2id has no
such limit. Passwords are never logged, returned by any API, or stored anywhere but
`users.password_hash`.

## 2. Session cookies
- `HttpOnly`, `Secure`, `SameSite=Lax` — host-only cookie, no `Domain` attribute
  needed now that everything sits behind the single-domain Vercel rewrite
  (architecture.md §3)
- Opaque random session id (the `sessions.id` UUID) — not a JWT, so revocation is a
  simple `UPDATE`, not a token-blacklist problem
- Sliding expiry: `expires_at` extended on activity up to a hard cap (e.g. 30 days);
  `last_seen_at` tracked for a future "sign out of all devices" view
- Revoked wholesale on password reset; revoked for *other* sessions on password change

## 3. CSRF
Everything is same-origin now (§4), but `SameSite=Lax` alone still isn't sufficient
protection for state-changing requests. Approach unchanged:
- Double-submit token: on login, also return a `csrf_token` in the response body
  (not a cookie); frontend stores it in memory and sends it as an `X-CSRF-Token`
  header on every mutating request (POST/PATCH/DELETE)
- Backend rejects mutating requests where the header doesn't match a value derived
  from the session

## 4. CORS
Production needs none — the browser only ever talks to `plexudo.vercel.app`, and
the Vercel rewrite (architecture.md §3) makes the API same-origin. `CORS_ALLOWED_ORIGINS`
still exists for local dev (`http://localhost:5173` while the SPA runs unproxied),
`allow_credentials=True`, explicit method/header lists — never `*` with credentials
enabled.

## 5. Verification & reset tokens
- 32 bytes from a CSPRNG, url-safe encoded
- Only `sha256(token)` is stored; the raw value exists solely in the emailed link
- Verification tokens: 24h TTL · reset tokens: 1h TTL
- Single-use: `consumed_at` set on first successful use, checked on every lookup
- Constant-time comparison isn't needed here (it's a DB equality lookup on a hash,
  not a secret compared in application code)

## 6. Rate limiting

| Action | Limit |
|---|---|
| Login attempts | 5 / 15 min per (email, IP) pair, then exponential backoff |
| Resend verification | 1 / 60s, 5 / day per account |
| Forgot-password requests | 3 / hour per email, 10 / hour per IP |
| Ad-reward claims | 1 in-flight claim per user at a time (mutex on user_id) |
| Tool endpoints | generous per-user cap (e.g. 60/min) mainly to blunt scripted abuse, separate from the credit system itself |

## 7. Credit ledger atomicity (§9)
See database-schema.md invariant 3 — the guarded atomic decrement:
```sql
UPDATE users SET credit_balance = credit_balance - 1
 WHERE id = :user_id AND credit_balance >= 1
RETURNING credit_balance;
```
No row returned → reject with `402 INSUFFICIENT_CREDITS` before any tool logic
runs. The ledger insert and the decrement happen in the same DB transaction as each
other and as the eventual `history_entries` insert, so a mid-request crash can't
leave credits deducted with no record of why (or vice versa).

**Refund path (§26):** if the downstream call (YouTube API, Groq) fails *after* the
decrement, a second transaction inserts a `REFUND` ledger row and increments
`credit_balance` back. The user is never charged for a failed operation.

## 8. Ad-reward anti-abuse (§7)
- The frontend "Watch Ad" button click is never treated as proof of completion
- `ad_provider_service.verify(reward_token)` calls the real provider's verification
  API (or validates its signed callback, provider-dependent) before anything is
  credited
- `ad_reward_events (provider, provider_reference_id)` is unique — the same
  provider-issued reward id can be submitted any number of times and will only ever
  be credited once
- If `AD_PROVIDER` isn't configured, the endpoint returns `503
  AD_PROVIDER_NOT_CONFIGURED` — it never fabricates a successful reward

## 9. OAuth token storage
`youtube_connections.access_token` / `refresh_token` are encrypted with
`TOKEN_ENCRYPTION_KEY` (AES-GCM or Fernet) before insert, decrypted only inside
`youtube_service`, and never included in any API response or log line. Each row is
scoped to exactly one `user_id` — there is no shared/global token, and this is the
only OAuth token this app ever stores (§16).

## 10. Input validation
Every endpoint has a Pydantic request model; FastAPI rejects malformed input before
a handler runs. No manual dict access into raw request bodies.

## 11. Authorization / data scoping (§29)
Every private query filters by the `user_id` resolved from the session dependency.
A client-supplied `user_id` anywhere in a request body or query string is ignored
for authorization purposes — it's never trusted as the identity to act on.

## 12. Secrets management
All values in architecture.md §4 live in environment variables / a secrets manager,
never in source control. `.env.example` ships with placeholder keys only.

## 13. Logging & PII
No passwords, raw tokens, session ids, or OAuth tokens in logs. Request logging
captures method/path/status/duration and the *authenticated user id* (not raw
credentials) for anything auth-related.
