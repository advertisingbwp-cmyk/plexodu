# PLEXUDO

Plexudo is a public, anonymous YouTube creator-utility platform. It provides four standalone tools backed by the real YouTube Data API v3 and optional Groq AI.

## Live

Production: https://plexudo.vercel.app/

## Tools

- **Trend Analyzer** — live YouTube search metrics, sentiment, virality and related keyword insights.
- **Video Analyzer** — analyze an individual YouTube video for views, engagement, tags, comments and virality.
- **Competitor Audit** — inspect a public YouTube channel and compare creator-facing metrics.
- **AI Strategist** — get creator strategy and optimization guidance from Groq AI.

All tools are intentionally anonymous; no login, registration or Google OAuth is required.

## Architecture

```text
Browser
  │
  ├── Static frontend (HTML/CSS/JS)
  │
  └── /api/*
        │
        ▼
     Flask API
        │
        ├── YouTube Data API v3
        ├── Groq AI (optional)
        ├── PostgreSQL (production)
        └── SQLite (local development fallback)
```

The Vercel entry point is `api/index.py`. Production deployments must provide a persistent PostgreSQL `DATABASE_URL` and a stable `SECRET_KEY` in Vercel environment variables. The application must not use Vercel `/tmp` as a production database.

## Repository layout

```text
plexodu/
├── api/index.py                 # Vercel Flask entry point
├── backend/
│   ├── app.py                   # Flask routes and application setup
│   ├── models.py                # SQLAlchemy models
│   ├── app/core/config.py       # Environment configuration
│   └── services/                # YouTube, Groq, NLP, scoring and security services
├── frontend/
│   ├── index.html               # Public landing page
│   ├── tools/                   # Standalone tool pages
│   ├── css/                     # Shared styles
│   └── js/tools/                # Shared and tool-specific JavaScript
├── tests/                       # Security, architecture, SEO and tool-contract tests
├── database/                    # SQL schema/migration references
├── docs/                        # Current project documentation and audit notes
└── vercel.json                  # Vercel deployment configuration
```

## Local development

### 1. Requirements

- Python 3.10+
- A YouTube Data API v3 key for live YouTube analysis
- A Groq API key only if AI Strategist is to use Groq
- PostgreSQL is recommended for persistent development; SQLite is supported as a local fallback

### 2. Configure environment

Copy `.env.example` to `.env` and set the required values:

```text
SECRET_KEY=replace-with-a-long-random-secret
YOUTUBE_API_KEY=your-youtube-api-key
GROQ_API_KEY=your-groq-api-key
DATABASE_URL=postgresql://user:password@localhost/plexudo
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5000,http://localhost:5000
```

Never commit `.env` or real credentials.

### 3. Install and run

```bash
pip install -r requirements.txt
python backend/app.py
```

Open `http://127.0.0.1:5000/`.

## Production deployment

Plexudo is configured for Vercel. Set these environment variables in the Vercel project:

- `SECRET_KEY` — stable, high-entropy production secret.
- `DATABASE_URL` — persistent PostgreSQL connection string.
- `YOUTUBE_API_KEY` — YouTube Data API v3 key.
- `GROQ_API_KEY` — Groq API key, if AI Strategist is enabled.
- `CORS_ALLOWED_ORIGINS` — comma-separated trusted browser origins.

Do not place secrets in `vercel.json`, `render.yaml`, source code or frontend JavaScript.

## Security

The project includes:

- Server-side input validation for public API inputs.
- YouTube URL hostname validation.
- IP-based API rate limiting.
- Secure error responses without stack traces to clients.
- Security headers and API no-index directives.
- Secret scanning through GitHub Actions/Gitleaks.
- Dependency vulnerability scanning with `pip-audit`.
- XSS-safe DOM rendering in standalone tool interfaces.
- No authentication or private user-data requirement for public tools.

For production, distributed rate limiting and a persistent PostgreSQL database are recommended when operating at meaningful traffic volume.

## Testing

Run the complete test suite with:

```bash
python -m pytest tests/ -v
```

The GitHub Actions workflow runs static checks, secret scanning, dependency auditing, the complete test suite, production startup checks and SEO validation.

## Data integrity

Plexudo does not fabricate YouTube analytics. Current YouTube API totals are stored as snapshots. A single scan is explicitly treated as an initial snapshot; genuine historical growth requires repeated snapshots over time.

## Advertising / disclosure

`ads.txt`, privacy and terms pages are included for the public website. Plexudo is an independent platform and is not officially affiliated with or endorsed by YouTube or Google LLC.
