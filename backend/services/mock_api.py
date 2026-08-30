"""
Platform Connector (Mock Mode)
------------------------------
This module simulates the YouTube Data API v3 and TikTok Research API,
following the same structure described in SDD Section 5.2 (fetchPlatformData).

WHY MOCK MODE:
Real API access requires a Google Cloud project (YouTube Data API v3 key)
and TikTok for Developers approval (Research API access), which can take
time to obtain. This module returns realistic, randomized JSON so the rest
of the system (Preprocessing -> Sentiment -> Trend Scoring -> Dashboard)
works end-to-end right now.

HOW TO GO LIVE LATER:
Create `real_api.py` in this same folder implementing the same two
functions below (fetch_youtube_data, fetch_tiktok_data) using
`requests` + your API keys, then change the single import line in
`app.py` from:
    from services.mock_api import fetch_youtube_data, fetch_tiktok_data
to:
    from services.real_api import fetch_youtube_data, fetch_tiktok_data
No other file needs to change - this is the whole point of the
"Connectivity Subsystem" being modular (SDD Section 3.3).
"""

import random
from datetime import datetime, timedelta

SAMPLE_COMMENTS_POOL = [
    "This is absolutely amazing, best trend ever!",
    "I don't really understand why this is popular",
    "So overrated, not impressed at all",
    "Love this so much, watched it 10 times",
    "This is okay I guess, nothing special",
    "Worst trend of the year, waste of time",
    "Incredible content, made my day",
    "Meh, seen better",
    "This deserves way more views honestly",
    "Not a fan of this at all",
    "Pretty average content but okay",
    "This blew up for a reason, so good",
    "I'm so tired of seeing this everywhere",
    "Genuinely creative and well made",
    "Disappointed, expected more from this",
]


def _generate_daily_series(base_views, days=10):
    """Simulates a growth curve like the SDD's trend growth chart."""
    series = []
    current = base_views
    for i in range(days):
        change = random.uniform(-0.05, 0.35)  # mostly upward, viral bias
        current = max(1000, int(current * (1 + change)))
        date = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        series.append({
            "date": date,
            "views": current,
            "likes": int(current * random.uniform(0.05, 0.15)),
            "shares": int(current * random.uniform(0.01, 0.05)),
            "comments_count": int(current * random.uniform(0.005, 0.02)),
        })
    return series


def _sample_comments(n=25):
    return [random.choice(SAMPLE_COMMENTS_POOL) for _ in range(n)]


def fetch_youtube_data(keyword: str):
    """Simulates a YouTube Data API v3 search + statistics response."""
    base_views = random.randint(50_000, 5_000_000)
    return {
        "status": 200,
        "platform": "YouTube",
        "keyword": keyword,
        "video_id": f"yt_{random.randint(10000,99999)}",
        "title": f"{keyword} - Trending Now",
        "upload_date": (datetime.utcnow() - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d"),
        "daily_metrics": _generate_daily_series(base_views),
        "comments": _sample_comments(30),
    }


def fetch_tiktok_data(keyword: str):
    """Simulates a TikTok Research API hashtag/trend response."""
    base_views = random.randint(100_000, 20_000_000)  # TikTok tends to spike faster
    return {
        "status": 200,
        "platform": "TikTok",
        "keyword": keyword,
        "video_id": f"tt_{random.randint(10000,99999)}",
        "caption": f"#{keyword.replace(' ', '')} is everywhere right now",
        "upload_date": (datetime.utcnow() - timedelta(days=random.randint(1, 15))).strftime("%Y-%m-%d"),
        "daily_metrics": _generate_daily_series(base_views),
        "comments": _sample_comments(30),
    }
