# Plexudo — API Contracts (v1)

Base path: `/api/v1`. All responses are JSON. All private endpoints require a valid,
non-revoked session cookie (frontend sends `credentials: 'include'`); `user_id` is
always resolved from the session server-side — **never** from the request body or
query string (§29). Errors follow `{ "error": "CODE", "message": "..." }`.

---

## Auth

**POST /auth/signup**
Auth: none · Body: `{ username, email, password, confirm_password }`
→ 201 `{ user_id }` · 409 `{ error: "EMAIL_TAKEN" | "USERNAME_TAKEN" }`
Does not create a session. Sends the verification email; account starts unverified.

**POST /auth/login**
Auth: none · Body: `{ email, password }`
→ 200 `{ user }`, sets session cookie · 401 `{ error: "INVALID_CREDENTIALS" }`
Succeeds even if unverified (see architecture.md §7.4) — downstream routes gate on it.

**POST /auth/logout**
Auth: session · → 204, revokes the current session row.

**GET /auth/me**
Auth: session · → 200 `{ user, credit_balance, email_verified }`

**POST /auth/verify-email**
Auth: none · Body: `{ token }`
→ 200 · 400 `{ error: "TOKEN_INVALID_OR_EXPIRED" }`

**POST /auth/resend-verification**
Auth: session · Rate limited (see security-model.md) · → 202

**POST /auth/forgot-password**
Auth: none · Body: `{ email }`
→ 202 always, regardless of whether the email exists (§13 — no account enumeration)

**POST /auth/reset-password**
Auth: none · Body: `{ token, new_password, confirm_password }`
→ 200 · 400 `{ error: "TOKEN_INVALID_OR_EXPIRED" }`
Invalidates the token and, per security-model.md, all existing sessions for that user.

**POST /auth/change-password**
Auth: session · Body: `{ current_password, new_password }`
→ 200 · 401 `{ error: "CURRENT_PASSWORD_INCORRECT" }`

---

## YouTube connection (the only OAuth flow in this app — §16)

**GET /youtube/connect**
Auth: session · Redirects to Google consent with YouTube scope only.

**GET /youtube/callback**
Auth: session · Exchanges code, encrypts + stores tokens in `youtube_connections`
scoped to the session's `user_id`.

**GET /youtube/status**
Auth: session · → 200 `{ connected: bool, google_email?, connected_at? }`

**DELETE /youtube/disconnect**
Auth: session · Revokes + deletes the stored tokens · → 204

---

## Credits

**GET /credits/balance**
Auth: session · → 200 `{ balance }`

**GET /credits/ledger?cursor=**
Auth: session · → 200 `{ entries: [{ type, amount, created_at }], next_cursor }`

**POST /credits/claim-ad-reward**
Auth: session · Body: `{ reward_token }`
→ 200 `{ balance }` on first valid claim
→ 409 `{ error: "REWARD_ALREADY_CLAIMED" }` on replay
→ 503 `{ error: "AD_PROVIDER_NOT_CONFIGURED" }` if no provider is wired up yet (§7 —
never fabricate a successful reward)
Backend calls `ad_provider_service.verify(reward_token)` against the real provider;
the frontend button click is never itself treated as proof.

---

## Tools

Shared shape: `POST /tools/{tool}` · Auth: session + `email_verified` · consumes
credits per the central `TOOL_CREDIT_COSTS` config (checked and deducted atomically
before the tool runs, see database-schema.md invariant 3 — never hardcoded per
endpoint or in the frontend) · on any failure after the credit was reserved, the
service issues a `REFUND` ledger entry (§26).

| Endpoint | Body | Result (abbreviated) |
|---|---|---|
| `/tools/seo-score` | `{ video_id }` or `{ title, description, tags }` | `{ total, max: 50, breakdown: { tag_count, keyword_volume, title_keywords, description_keywords, triple_overlap } }` |
| `/tools/video-analyzer` | `{ video_url_or_id }` | `{ metadata, seo_score, recommendations, mobile_preview }` |
| `/tools/keyword-tool` | `{ seed_keyword, region }` | `{ related[], long_tail[], clusters[], volume_indicator }` — volume labeled `"estimated"` unless the source genuinely provides exact figures (§22) |
| `/tools/trend-analyzer` | `{ region }` | `{ trending_topics[], breakout_topics[] }`, each item tagged `source: "official" \| "plexudo_derived"` (§23) |
| `/tools/competitor-analysis` | `{ channel_url_or_id }` | `{ channel_summary, top_videos[], tag_gaps[], upload_patterns }` — public data only (§24) |
| `/tools/ai-assistant` | `{ prompt_type, context }` | `{ suggestion }` — Groq-backed, key stays server-side |

404 `{ error: "NOT_FOUND" }` if the YouTube API returns nothing — never a fake
fallback video or channel (§17).
402 `{ error: "INSUFFICIENT_CREDITS" }` if the guarded decrement fails.

---

## History

**GET /history?tool_type=&cursor=**
Auth: session · Always scoped to the session's `user_id`, regardless of any
`user_id` present elsewhere in the request (§29) · → 200 `{ entries[], next_cursor }`

---

## Profile

**GET /profile** → 200 `{ username, email, email_verified }`
**PATCH /profile** → Body: `{ username }` → 200 (email change intentionally out of
scope for v1 — not specified)

---

## Public (served as HTML by FastAPI + Jinja2, not JSON)

`GET /`, `/blog`, `/blog/{slug}`, `/youtube-seo-tool`, `/youtube-keyword-tool`,
`/youtube-trend-analyzer`, `/youtube-competitor-analysis`, `/youtube-video-analyzer`,
`/privacy`, `/terms`, `/sitemap.xml`, `/robots.txt` — no auth, no private data ever
rendered into these templates (§3).
