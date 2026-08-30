# Plexudo — Database Schema (v1)

Postgres DDL below; the actual source of truth will be the SQLAlchemy models +
Alembic migrations, but this is the contract they implement.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive email

CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username          TEXT NOT NULL UNIQUE,
    email             CITEXT NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,                -- account creation is email/password only
    email_verified_at TIMESTAMPTZ,
    credit_balance    INTEGER NOT NULL DEFAULT 0,   -- authoritative counter, see below
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- YouTube authorization. Account login is email/password only (no "Sign in with
-- Google") — this is the only table Google OAuth ever writes to (§16).
CREATE TABLE youtube_connections (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    google_email   TEXT NOT NULL,
    access_token   BYTEA NOT NULL,     -- encrypted with TOKEN_ENCRYPTION_KEY
    refresh_token  BYTEA NOT NULL,     -- encrypted with TOKEN_ENCRYPTION_KEY
    scopes         TEXT NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    connected_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- the cookie value
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_agent    TEXT,
    ip_address    INET,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    revoked_at    TIMESTAMPTZ
);
CREATE INDEX ON sessions (user_id);

CREATE TABLE email_verification_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,   -- sha256(raw); raw token exists only in the email
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE credit_txn_type AS ENUM (
    'WELCOME_CREDIT', 'AD_REWARD', 'TOOL_USAGE', 'REFUND', 'ADMIN_ADJUSTMENT'
);

-- Append-only audit trail. Never UPDATE or DELETE a row here.
CREATE TABLE credit_ledger (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type         credit_txn_type NOT NULL,
    amount       INTEGER NOT NULL,     -- signed: +3 welcome, +1 ad reward, -1 tool usage
    reference_id TEXT,                 -- idempotency key: ad event id, tool request id, etc.
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON credit_ledger (user_id, created_at DESC);

CREATE TABLE ad_reward_events (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider               TEXT NOT NULL,
    provider_reference_id  TEXT NOT NULL,   -- the ad network's unique reward/impression id
    verified_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload            JSONB,
    UNIQUE (provider, provider_reference_id)
);

CREATE TYPE tool_type AS ENUM (
    'SEO_SCORE', 'VIDEO_ANALYZER', 'KEYWORD_TOOL', 'TREND_ANALYZER',
    'COMPETITOR_ANALYSIS', 'AI_ASSISTANT'
);

CREATE TABLE history_entries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_type   tool_type NOT NULL,
    input       JSONB NOT NULL,       -- request params (video url, keyword, region, ...)
    result      JSONB NOT NULL,       -- derived output only — never the raw YouTube payload
    credit_cost INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON history_entries (user_id, created_at DESC);
```

---

## Key invariants (enforced at the DB level, not just in application code)

**1. Exactly one welcome grant, ever (§8)**
```sql
CREATE UNIQUE INDEX one_welcome_credit_per_user
    ON credit_ledger (user_id) WHERE type = 'WELCOME_CREDIT';
```
A retried or duplicated signup-completion call cannot insert a second row — the DB
rejects it, so the application doesn't have to get this right on its own.

**2. No replaying an ad reward (§7)**
```sql
UNIQUE (provider, provider_reference_id)   -- on ad_reward_events
```
The ad network's own event id is the idempotency key. The same completed-ad event
can only ever be credited once, regardless of how many times the client resubmits it.

**3. `users.credit_balance` is the authoritative number; `credit_ledger` is history**
Both are written in the same transaction on every grant/consume. The balance column
exists specifically so a credit-consuming request can be an atomic guarded decrement:

```sql
UPDATE users
   SET credit_balance = credit_balance - 1
 WHERE id = :user_id AND credit_balance >= 1
RETURNING credit_balance;
```
If this returns no row, the request is rejected as `INSUFFICIENT_CREDITS` before
anything else runs. Postgres's row-level locking during the UPDATE is what actually
prevents two simultaneous requests from both succeeding on the last credit (§9) —
no explicit `SELECT ... FOR UPDATE` needed, and no separate cache to keep in sync
with the ledger.

**4. OAuth tokens are encrypted at rest**
`youtube_connections.access_token` / `refresh_token` are stored as `BYTEA`,
encrypted with `TOKEN_ENCRYPTION_KEY` before insert and decrypted only inside
`youtube_service` — never returned by any API response (§3, §16).

**5. Credit cost is config, not a hardcoded number**
The *current* price per tool lives in one place — `TOOL_CREDIT_COSTS` in the
backend's `core/config.py` — not scattered across endpoints or the frontend.
`history_entries.credit_cost` still stores what was actually charged on that
specific call, so changing `TOOL_CREDIT_COSTS` later never rewrites history.
