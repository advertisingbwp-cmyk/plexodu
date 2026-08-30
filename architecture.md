# Plexudo — Architecture (v1)

Stack, as specified:
- **Frontend**: React + Vite, Tailwind CSS, React Router, TanStack Query
- **Backend**: Python + FastAPI, Pydantic, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **Auth**: server-side HTTP-only session cookies, Argon2id, Google OAuth 2.0
- **AI**: Groq API (server-side only)
- **Testing**: pytest, Playwright

---

## 1. Monorepo layout

```
/frontend
  src/
    routes/          route-level pages (React Router) — dashboard only
    components/
    lib/             api client, TanStack Query setup, auth context
    hooks/
  vite.config.ts
  package.json

/backend
  app/
    api/v1/          auth.py, youtube.py, credits.py, tools.py, history.py, profile.py
    core/            config.py, security.py, session.py, rate_limit.py
    db/              base.py, session.py, models/
    services/        seo_score_service.py, credit_ledger_service.py, email_service.py,
                      ad_provider_service.py, youtube_service.py, ai_assistant_service.py
    templates/       Jinja2 — public site + blog (see §2)
    static/          public-site assets (css, og-images)
    main.py
  alembic/
  requirements.txt / pyproject.toml

/docs                this document set (+ keyword-map.md later, in the SEO/content phase)
/tests
  backend/           pytest
  e2e/               Playwright
```

---

## 2. Public vs. private rendering — key decision

Your spec's public layer needs to be crawlable: per-page titles, meta descriptions,
canonical URLs, Open Graph, Article/BreadcrumbList JSON-LD, and a real `sitemap.xml`
(§31–39). A pure Vite SPA can't deliver that on its own — most social-preview bots
and some crawlers never execute JS, so every route collapses to one generic
`index.html` with no per-page metadata.

**Recommendation:** split rendering along the exact PUBLIC/PRIVATE line your spec
already draws in §2 — no new framework, just use the backend you already chose for
both jobs:

- **Public** (`/`, `/blog`, `/blog/{slug}`, `/youtube-seo-tool`, `/youtube-keyword-tool`,
  `/youtube-trend-analyzer`, `/youtube-competitor-analysis`, `/youtube-video-analyzer`,
  `/sitemap.xml`, `/robots.txt`) → **FastAPI + Jinja2**, rendered server-side. Full
  control over meta/OG/JSON-LD per §37, trivial sitemap generation, indexable with
  zero JS execution.
- **Private** (everything behind login) → the **React/Vite SPA**. Never needs SEO,
  so client rendering is the right tool there.

This is the one spot where "React + Vite" as stated doesn't cover the whole product
by itself — flagging it now rather than after the blog ships and can't be indexed.

---

## 3. Domain & deployment topology — confirmed

Domain: **https://plexudo.vercel.app** (single domain, no subdomains).

This still satisfies "backend: persistent host, not Vercel serverless" via Vercel's
own `rewrites` — the backend keeps running on a real persistent service, the user
just never sees its URL:

- `/dashboard`, `/settings`, `/profile`, `/history` (+ anything under them) → served
  natively by Vercel as the built SPA (`index.html`; client-side routing takes over
  from there). This is Vercel's default static hosting — no rewrite involved.
- `/`, `/blog`, `/blog/:slug`, `/youtube-seo-tool`, `/youtube-keyword-tool`,
  `/youtube-trend-analyzer`, `/youtube-competitor-analysis`, `/youtube-video-analyzer`,
  `/privacy`, `/terms`, `/sitemap.xml`, `/robots.txt` → `vercel.json` rewrite to the
  FastAPI backend's real host (Render/Railway/Fly/etc).
- `/api/:path*` → same rewrite, to the FastAPI backend.

```json
{
  "rewrites": [
    { "source": "/api/:path*",        "destination": "https://<backend-host>/api/:path*" },
    { "source": "/sitemap.xml",       "destination": "https://<backend-host>/sitemap.xml" },
    { "source": "/robots.txt",        "destination": "https://<backend-host>/robots.txt" },
    { "source": "/blog",              "destination": "https://<backend-host>/blog" },
    { "source": "/blog/:path*",       "destination": "https://<backend-host>/blog/:path*" },
    { "source": "/youtube-:tool",     "destination": "https://<backend-host>/youtube-:tool" },
    { "source": "/privacy",           "destination": "https://<backend-host>/privacy" },
    { "source": "/terms",             "destination": "https://<backend-host>/terms" },
    { "source": "/",                  "destination": "https://<backend-host>/" },
    { "source": "/(.*)",              "destination": "/index.html" }
  ]
}
```
(rewrites are matched top-to-bottom — the SPA catch-all has to be last)

**This buys a nice simplification over my original subdomain proposal:** since the
browser only ever talks to `plexudo.vercel.app`, the SPA's API calls are same-origin.
No CORS allow-list needed in production, and the session cookie doesn't need
cross-subdomain `Domain` scoping. Updated in security-model.md §2 and §4.

---

## 4. Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `SECRET_KEY` | session cookie signing |
| `SESSION_COOKIE_DOMAIN` | e.g. `.plexudo.com` |
| `CORS_ALLOWED_ORIGINS` | e.g. `https://app.plexudo.com` |
| `TOKEN_ENCRYPTION_KEY` | encrypts stored Google/YouTube OAuth tokens at rest |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth app credentials — used only for Connect-YouTube; there is no "Sign in with Google" |
| `YOUTUBE_CONNECT_REDIRECT_URI` | callback for the Connect-YouTube flow |
| `TOOL_CREDIT_COST_*` (optional, one per tool) | overrides the `TOOL_CREDIT_COSTS` defaults in `core/config.py` without a code change |
| `YOUTUBE_API_KEY` | server-side key, public/unauthenticated lookups only |
| `GROQ_API_KEY` / `GROQ_MODEL` | AI assistant — never sent to the browser |
| `EMAIL_PROVIDER` / `EMAIL_PROVIDER_API_KEY` / `EMAIL_FROM_ADDRESS` | verification + reset email |
| `AD_PROVIDER` / provider-specific keys | rewarded-ad verification |
| `FRONTEND_URL` | for building redirect/email links |
| `ENVIRONMENT` | dev / staging / prod |

Everything above is read server-side only. `GOOGLE_CLIENT_ID` is the sole exception
that's safe to expose (it's a public identifier, not a secret) — every other value
never reaches the frontend.

---

## 5. Request flow — example: a private tool call

```
Browser (SPA)
  → TanStack Query mutation
  → POST api.plexudo.com/api/v1/tools/video-analyzer   (cookie sent automatically)
  → FastAPI: resolve session → user
  → check email_verified
  → check credit_balance
  → youtube_service (API key or user's stored OAuth token)
  → seo_score_service (canonical scoring engine, see database-schema.md)
  → single DB transaction: insert history_entries row + insert credit_ledger row
    + decrement users.credit_balance
  → return result
  → SPA renders it; TanStack Query caches it
```

---

## 6. Testing strategy

- **pytest** — service-level unit tests (SEO score math, credit ledger atomicity,
  token validation, welcome-credit idempotency) + API contract tests against a real
  test Postgres DB (not mocks, given how much of this spec is about server-side
  correctness).
- **Playwright** — the flows most likely to silently break: signup → verify →
  login, forgot/reset password, Google login, insufficient-credits path, ad-reward
  claim (against a mocked provider).

---

## 7. Decisions (confirmed)

1. **No "Sign in with Google."** Email + password (with verification/reset) is the
   only account creation/login path. Google OAuth's sole role is the Connect-YouTube
   flow, always initiated from an already-logged-in Plexudo session — never a way to
   create or access an account. This narrows the original spec's §10/§15 (which
   listed Google OAuth as a login option too); noted here for traceability, not
   re-litigating it.
2. Rendering split (§2) and the single-domain-with-rewrites topology (§3).
3. Credit costs are centralized and configurable — `TOOL_CREDIT_COSTS` in
   `core/config.py` (see Phase 1 code and database-schema.md) — rather than
   hardcoded anywhere, per-frontend or per-endpoint. Current defaults: video
   analyzer, keyword tool, trend analyzer, competitor analysis, and the AI
   assistant each cost 1 credit; dashboard/history/profile viewing is free.
4. Login succeeds even while unverified; every credit-consuming/private route
   independently returns `403 EMAIL_NOT_VERIFIED` until verification completes —
   satisfies "no full dashboard access before verification" (§11) without also
   blocking someone from logging in just to resend the verification email.
