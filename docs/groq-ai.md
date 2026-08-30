# Groq AI Service

## 1. Overview
Plexudo utilizes the Groq AI API server-side for YouTube creator optimizations:
- High-CTR video title generation & title score auditing
- SEO descriptions with chapter markers and hashtag recommendations
- Keyword clustering & search intent mapping
- Retention hook generation (first 15 seconds opening scripts)
- General creator growth assistant

## 2. Model & Key Configuration
- Configurable via `GROQ_MODEL` or `AI_MODEL` environment variable (defaults to `llama-3.3-70b-versatile`).
- Centralized timeout handling (`AI_TIMEOUT_SECONDS = 20.0`) and error handling.
- `GROQ_API_KEY` is maintained strictly server-side.

## 3. Atomic Credit Ledger Integration
- Every AI tool operation looks up its cost dynamically from `TOOL_CREDIT_COSTS`.
- Credits are deducted atomically before invoking Groq AI.
- If Groq returns a rate limit (429), timeout (504), or provider error (502), the system **automatically refunds the consumed credits** to the user and writes a `REFUND` ledger row.

## 4. Configuration
Add to `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=20.0
```
