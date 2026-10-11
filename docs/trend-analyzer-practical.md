# Trend Analyzer practical release

Project: Social Media Trend Analysis System (Plexudo), implemented on YouTube.

## Fixed

- Upload-date filters now reach YouTube search.list as publishedAfter.
- Global keyword searches no longer silently use the US region filter.
- Top graph uses real lifetime view totals grouped by upload age; empty buckets remain zero. It is not a daily historical views chart.
- Snapshot totals now cover the returned sample, rather than only its top video.
- History is isolated by keyword, platform, region, category, timeframe and exact video set. Existing rows remain preserved but excluded from new comparisons because their scope is unknown.
- Observations are spaced at least 24 hours apart; repeated refreshes cannot inflate confidence or unlock forecasts. Future-dated records are excluded.
- Forecasts require observations spanning 48 hours and account for elapsed time. They remain illustrative heuristics, not validated predictions.
- Historical windows require a nearby baseline instead of accepting arbitrarily old observations.
- API failures propagate proper status codes. UI shows errors and removes stale results; slower old requests cannot overwrite newer selections.
- Empty/unclassifiable comments show unavailable sentiment. Percentages below 1% are no longer multiplied by 100.
- Additive observation_key migration supports SQLite/PostgreSQL; legacy DATETIME additions use TIMESTAMP on PostgreSQL.

## Practical demo

1. Use a valid YouTube Data API v3 key in the server environment; never put it in frontend code or slides.
2. Search a topic, choose Pakistan/US/Global and a publication window. Explain that up to 18 search results are sampled, not all YouTube videos or measured keyword search volume.
3. Show actual views, likes, comments and engagement. The upper chart groups lifetime views by video age.
4. Show comment sentiment, noting that it samples the top-ranked video's comments and TextBlob is English-oriented.
5. A new cohort legitimately displays Baseline/Pending. A second comparable observation after 24 hours supports an observed-change comparison. Do not claim historical growth from a first scan.
6. Changing filters or the returned video set starts a separate baseline. No fake history has been seeded.
7. On Windows, keep the existing local SQLite database for persistence. On Vercel, verify DATABASE_URL points to persistent PostgreSQL; the existing temporary SQLite fallback remains a deployment limitation.

## Verification and limits

226 automated tests passed locally using mock keys and external HTTP blocked; JavaScript syntax and git diff whitespace checks passed. Updated three legacy tests whose fixtures/assertions relied on swallowed API errors or future-dated scans. Added 16 regression cases plus a Node-based DOM rendering check.

PDF export was rendered and inspected; PDF/CSV response and baseline contents were tested. Targeted frontend DOM rendering checks passed for momentum, escaping, tags, titles, sentiment and forecast text. Browser layout could not be verified because Chromium download failed. No real YouTube/Groq credentials, production database or Vercel deployment were validated in this environment. Distributed quota protection, AI Strategist fallback redesign, and wider app hardening are outside this focused release.

## Follow-up from the supplied live page

- Removed the growthPct/momentumScore mismatch causing -NaN%; the row now labels a finite momentum index, with Pending for missing data.
- Highest-view category and momentum-count labels no longer claim observed growth. Entertainment and Film/Animation no longer map to Comedy/Lifestyle.
- General feeds ask for a topic before suggesting titles/tags. Specific searches produce explicitly labeled editable title templates without Groq latency or unrelated AI text.
- PDF/CSV preserve Baseline/Pending; PDF text is escaped and filenames sanitized. CSV keywords starting with formula characters are escaped.
- Channel-audit action opens its input page instead of treating a topic as a channel handle.
