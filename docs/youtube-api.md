# YouTube Data API v3 Integration

## 1. Overview
Plexudo uses the official Google YouTube Data API v3 strictly server-side for:
- Video metadata and statistics lookup (`/api/v1/tools/video-analyzer`, `/api/v1/tools/seo-score`)
- Channel metrics and uploads inspection (`/api/v1/youtube/channel`, `/api/v1/youtube/videos`, `/api/v1/tools/competitor-analysis`)
- Keyword search and trending video discovery (`/api/v1/tools/keyword-tool`, `/api/v1/tools/trend-analyzer`)

## 2. Security & Invariants
- `YOUTUBE_API_KEY` is maintained strictly on the server and never sent to the browser.
- **Zero Fake Fallbacks**: If a channel has no uploads or a query yields no items, an honest empty list `[]` is returned. No hardcoded or placeholder video data is ever served.
- When querying user-specific YouTube data (e.g., connected channel metrics), the user's encrypted OAuth access token is decrypted and used.

## 3. Error States
- `404 Not Found`: Returned when a video ID or channel handle does not exist.
- `429 Too Many Requests`: Returned when Google API quota is exceeded (`quotaExceeded` / `rateLimitExceeded`).
- `401 Unauthorized`: Returned when OAuth token is expired or revoked.
- `502 / 504`: Returned on upstream network or timeout errors.

## 4. Configuration
Add to `.env`:
```env
YOUTUBE_API_KEY=AIzaSy...your-real-key
```
