"""
Platform Connector (Live Mode - YouTube)
-----------------------------------------
Real implementation of fetch_youtube_data() and audit_youtube_channel()
using the YouTube Data API v3.
"""

import os
import math
import time
import re
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
from app.core.config import settings

def get_yt_api_key():
    return (settings.YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY", "")).strip()

YOUTUBE_API_KEY = get_yt_api_key()
SEARCH_URL   = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL   = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
PLAYLIST_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

# Thread-safe in-memory TTL caching to prevent quota exhaustion
_YT_CACHE = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes


def _get_from_cache(cache_key: str):
    cached = _YT_CACHE.get(cache_key)
    if cached:
        timestamp, data = cached
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            return data
        try:
            del _YT_CACHE[cache_key]
        except KeyError:
            pass
    return None


def _save_to_cache(cache_key: str, data: dict):
    if isinstance(data, dict) and (data.get("status") == 200 or data.get("error") is False):
        _YT_CACHE[cache_key] = (time.time(), data)


def _is_quota_error(res) -> bool:
    try:
        if res.status_code == 403:
            body = res.json()
            errors = body.get("error", {}).get("errors", [])
            for err in errors:
                if err.get("reason") in ["quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"]:
                    return True
            if "quota" in str(body).lower():
                return True
    except Exception:
        pass
    return False


def _build_authentic_snapshot(total_views: int, total_likes: int, total_comments: int, upload_date_str: str = None) -> list:
    """
    Returns authentic recorded snapshot for today.
    Never fabricates synthetic historical decay curves or imaginary past daily points.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [{
        "date": today_str,
        "views": int(total_views or 0),
        "likes": int(total_likes or 0),
        "shares": 0,
        "comments_count": int(total_comments or 0),
    }]


class YouTubeAPIError(Exception):
    pass


# ─── Related Keywords ────────────────────────────────────────────────────────
def _fetch_related_keywords(keyword: str) -> list:
    related = []
    seen = set()

    try:
        ac_res = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "ds": "yt", "q": keyword},
            timeout=5,
        )
        if ac_res.status_code == 200:
            suggestions = ac_res.json()[1] if len(ac_res.json()) > 1 else []
            for item in suggestions:
                cleaned = item.strip()
                if cleaned and cleaned.lower() != keyword.lower() and cleaned.lower() not in seen:
                    related.append(cleaned)
                    seen.add(cleaned.lower())
    except Exception:
        pass

    if YOUTUBE_API_KEY and len(related) < 8:
        try:
            yt_res = requests.get(SEARCH_URL, params={
                "part": "snippet", "q": keyword, "type": "video",
                "order": "viewCount", "maxResults": 6, "key": YOUTUBE_API_KEY,
            }, timeout=5)
            if yt_res.status_code == 200:
                for item in yt_res.json().get("items", []):
                    title = item["snippet"].get("title", "")
                    words = title.split()
                    for w in words:
                        if w.startswith("#") and len(w) > 2 and w.lower() not in seen:
                            related.append(w); seen.add(w.lower())
                    phrase = " ".join([w for w in words if not w.startswith("#")][:3])
                    if phrase and phrase.lower() != keyword.lower() and phrase.lower() not in seen:
                        related.append(phrase); seen.add(phrase.lower())
        except Exception:
            pass

    return related[:10]


# ─── Category & Region Metadata ──────────────────────────────────────────────
CATEGORY_MAP = {
    "10": ("Music", "#FF6B4A"),
    "20": ("Gaming", "#8B5CF6"),
    "23": ("Comedy", "#FBBF24"),
    "24": ("Comedy", "#FBBF24"),
    "28": ("Tech", "#38BDF8"),
    "2":  ("Tech", "#38BDF8"),
    "27": ("Education", "#4ADE80"),
    "26": ("Education", "#4ADE80"),
    "17": ("Sports", "#F472B6"),
    "25": ("News", "#94A3B8"),
    "22": ("Lifestyle", "#FB923C"),
    "1":  ("Lifestyle", "#FB923C"),
    "19": ("Lifestyle", "#FB923C"),
}

CATEGORY_TO_YT_ID = {
    "Music": "10",
    "Gaming": "20",
    "Comedy": "23",
    "Tech": "28",
    "Education": "27",
    "Sports": "17",
    "News": "25",
    "Lifestyle": "22",
}

REGION_MAP = {
    "Global": "US",
    "United States": "US",
    "India": "IN",
    "Pakistan": "PK",
    "United Kingdom": "GB",
}

DEFAULT_CATEGORIES = [
    {"name": "Music", "hue": "#FF6B4A"},
    {"name": "Gaming", "hue": "#8B5CF6"},
    {"name": "Comedy", "hue": "#FBBF24"},
    {"name": "Tech", "hue": "#38BDF8"},
    {"name": "Education", "hue": "#4ADE80"},
    {"name": "Sports", "hue": "#F472B6"},
    {"name": "News", "hue": "#94A3B8"},
    {"name": "Lifestyle", "hue": "#FB923C"},
]


# ─── Keyword Trend Fetch ─────────────────────────────────────────────────────
def fetch_youtube_data(keyword: str, region: str = "Global", category: str = "All", timeframe: str = "7d"):
    api_key = get_yt_api_key()
    if not api_key:
        raise YouTubeAPIError("YOUTUBE_API_KEY is not set. Add it to your .env file.")

    raw_kw = (keyword or "").strip()
    is_trending_mode = not raw_kw or raw_kw.lower() in ["trending", "all", "pulsecheck"]
    search_keyword = category if (is_trending_mode and category != "All") else raw_kw

    region_code = REGION_MAP.get(region, "US")
    yt_cat_id = CATEGORY_TO_YT_ID.get(category) if category != "All" else None

    cache_key = f"yt_pulse_{search_keyword.lower()}_{region}_{category}_{timeframe}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    items = []
    # If in trending mode without specific keyword and All categories, use chart=mostPopular
    if is_trending_mode and category == "All":
        try:
            params = {
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "regionCode": region_code,
                "maxResults": 18,
                "key": api_key,
            }
            res = requests.get(VIDEOS_URL, params=params, timeout=8)
            if _is_quota_error(res):
                return {"status": 429, "platform": "YouTube", "error": "YouTube API daily quota reached. Trend analytics are temporarily paused. Please try again later.", "quota_exceeded": True}
            if res.status_code == 200:
                items = res.json().get("items", [])
        except Exception:
            items = []

    # If items not populated from mostPopular, query search.list
    if not items:
        q_term = search_keyword if search_keyword else (category if category != "All" else "trending")
        search_params = {
            "part": "snippet",
            "q": q_term,
            "type": "video",
            "order": "viewCount",
            "maxResults": 18,
            "regionCode": region_code,
            "key": api_key,
        }
        if yt_cat_id:
            search_params["videoCategoryId"] = yt_cat_id

        try:
            search_res = requests.get(SEARCH_URL, params=search_params, timeout=8)
        except requests.Timeout:
            return {"status": 504, "platform": "YouTube", "error": "YouTube API request timed out. Please try again."}
        except requests.RequestException:
            return {"status": 502, "platform": "YouTube", "error": "Failed to connect to YouTube service."}

        if _is_quota_error(search_res):
            return {"status": 429, "platform": "YouTube", "error": "YouTube API daily quota reached. Trend analytics are temporarily paused. Please try again later.", "quota_exceeded": True}
        if search_res.status_code == 403:
            return {"status": 403, "platform": "YouTube", "error": "YouTube API access forbidden. Check API configuration."}
        if search_res.status_code != 200:
            return {"status": search_res.status_code, "platform": "YouTube", "error": "YouTube API request failed."}

        search_items = search_res.json().get("items", [])
        if not search_items:
            return {"status": 404, "platform": "YouTube", "error": f'No videos found for "{q_term}".'}

        video_ids = [it["id"]["videoId"] for it in search_items if isinstance(it.get("id"), dict) and "videoId" in it["id"]]
        if not video_ids and search_items:
            # Fallback if id is string
            video_ids = [it.get("id") for it in search_items if isinstance(it.get("id"), str)]

        if video_ids:
            try:
                stats_res = requests.get(VIDEOS_URL, params={
                    "part": "snippet,statistics",
                    "id": ",".join(video_ids[:18]),
                    "key": api_key,
                }, timeout=8)
                if stats_res.status_code == 200:
                    items = stats_res.json().get("items", [])
            except Exception:
                pass

        # If stats_res failed or empty, fallback to search_items directly
        if not items and search_items:
            items = search_items

    if not items:
        return {"status": 404, "platform": "YouTube", "error": f'No videos found for "{search_keyword}".'}

    # Build parsed top_videos list
    top_videos = []
    now_utc = datetime.now(timezone.utc)
    for i, it in enumerate(items):
        v_id = it.get("id") if isinstance(it.get("id"), str) else it.get("id", {}).get("videoId", f"yt-{i}")
        snip = it.get("snippet", {})
        stat = it.get("statistics", {})

        v_title = snip.get("title", f"Trending Video #{i+1}")
        v_channel = snip.get("channelTitle", "YouTube Creator")
        cat_id = snip.get("categoryId", "")
        cat_info = CATEGORY_MAP.get(cat_id)
        if category != "All":
            cat_name = category
            cat_hue = next((c["hue"] for c in DEFAULT_CATEGORIES if c["name"] == category), "#38BDF8")
        else:
            cat_name = cat_info[0] if cat_info else "Tech"
            cat_hue = cat_info[1] if cat_info else "#38BDF8"

        v_views = int(stat.get("viewCount", 0))
        v_likes = int(stat.get("likeCount", 0))
        v_comments = int(stat.get("commentCount", 0))

        v_published = snip.get("publishedAt", "")
        try:
            pub_dt = datetime.fromisoformat(v_published.replace("Z", "+00:00"))
            hours_ago = max(1, int((now_utc - pub_dt).total_seconds() / 3600))
        except Exception:
            hours_ago = 24

        v_eng = round(((v_likes + v_comments) / max(1, v_views)) * 100, 1)
        velocity = v_views / max(1, hours_ago)
        # Single-snapshot estimate: current view velocity relative to a fixed
        # baseline (1500 views/hr), NOT growth measured between two points in
        # time. Do not rename this back to "growth" without adding real
        # snapshot-over-time tracking first.
        momentum_score = round((velocity / 1500 - 1) * 100)
        momentum_score = max(-95, min(950, momentum_score))
        trend_score = round(velocity / 100 + momentum_score * 8)

        top_videos.append({
            "id": v_id,
            "rank": i + 1,
            "title": v_title,
            "channel": v_channel,
            "category": cat_name,
            "hue": cat_hue,
            "region": region,
            "hoursAgo": hours_ago,
            "views": v_views,
            "likes": v_likes,
            "comments": v_comments,
            "engagement": v_eng,
            "momentumScore": momentum_score,
            "trendScore": trend_score,
            "published_at": v_published[:10] if v_published else "—",
        })

    # Sort videos by trend score
    top_videos.sort(key=lambda x: x["trendScore"], reverse=True)
    for idx, v in enumerate(top_videos):
        v["rank"] = idx + 1

    # Aggregate KPIs & Category Breakdown
    total_views_sum = sum(v["views"] for v in top_videos) if top_videos else int(items[0].get("statistics", {}).get("viewCount", 0))
    avg_eng = round(sum(v["engagement"] for v in top_videos) / max(1, len(top_videos)), 1)
    rising_count = len([v for v in top_videos if v["momentumScore"] > 40])

    cat_breakdown = []
    for c in DEFAULT_CATEGORIES:
        c_vids = [v for v in top_videos if v["category"] == c["name"]]
        c_val = sum(v["views"] for v in c_vids)
        cat_breakdown.append({"name": c["name"], "hue": c["hue"], "value": c_val})
    cat_breakdown.sort(key=lambda x: x["value"], reverse=True)
    top_cat_name = cat_breakdown[0]["name"] if cat_breakdown and cat_breakdown[0]["value"] > 0 else (category if category != "All" else "Trending")

    # Time series points: 12 for 24h, 7 for 7d, 30 for 30d
    points_count = 12 if timeframe == "24h" else (7 if timeframe == "7d" else 30)
    time_series = []
    bucket_views = [0] * points_count
    for v in top_videos:
        h = v.get("hoursAgo", 24)
        b_idx = min(points_count - 1, max(0, h // 2 if timeframe == "24h" else h // 24))
        bucket_views[b_idx] += v.get("views", 0)

    base_fill = max(1000, total_views_sum // (points_count * 4)) if total_views_sum > 0 else 50000
    for p_idx in range(points_count):
        if timeframe == "24h":
            lbl = f"{p_idx * 2:02d}:00"
        elif timeframe == "7d":
            lbl = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][p_idx % 7]
        else:
            lbl = f"Day {p_idx + 1}"
        actual_val = bucket_views[p_idx] if bucket_views[p_idx] > 0 else base_fill
        time_series.append({"label": lbl, "views": actual_val})

    kpis = {
        "totalViews": total_views_sum,
        "avgEngagement": avg_eng,
        "topCategory": top_cat_name,
        "risingCount": rising_count,
        "topCategoryViews": cat_breakdown[0]["value"] if cat_breakdown else 0,
        "totalTracked": len(top_videos),
    }

    # Backward compatibility anchor from top video
    v0 = top_videos[0] if top_videos else {}
    video_id = v0.get("id") or (items[0].get("id") if isinstance(items[0].get("id"), str) else items[0].get("id", {}).get("videoId", "yt-placeholder"))
    snippet0 = items[0].get("snippet", {}) if items else {}
    upload_date = v0.get("published_at") or snippet0.get("publishedAt", "")
    total_views = v0.get("views", 0)
    total_likes = v0.get("likes", 0)
    total_comments = v0.get("comments", 0)

    comments = []
    try:
        comments_res = requests.get(COMMENTS_URL, params={
            "part": "snippet", "videoId": video_id,
            "maxResults": 50, "order": "relevance", "key": api_key,
        }, timeout=8)
        if comments_res.status_code == 200:
            for item in comments_res.json().get("items", []):
                text = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {}).get("textDisplay", "")
                if text:
                    comments.append(text)
    except Exception:
        pass

    related_keywords = _fetch_related_keywords(search_keyword or "trending")

    result = {
        "status": 200, "platform": "YouTube",
        "keyword": search_keyword or "Trending",
        "video_id": video_id,
        "title": v0.get("title") or snippet0.get("title", "YouTube Trending"),
        "upload_date": upload_date,
        "daily_metrics": _build_authentic_snapshot(total_views, total_likes, total_comments, upload_date),
        "comments": comments,
        "related_keywords": related_keywords,
        "top_videos": top_videos,
        "kpis": kpis,
        "cat_breakdown": cat_breakdown,
        "time_series": time_series,
        "region": region,
        "category": category,
        "timeframe": timeframe,
    }
    _save_to_cache(cache_key, result)
    return result


def extract_video_id(url: str) -> str | None:
    """Safely extracts a YouTube video ID, rejecting SSRF or non-YouTube formats."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if url.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"):
            return None
    patterns = [
        r"(?:v=|youtu\.be/|/shorts/|/embed/|/v/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url
    return None


# ─── YouTube Video Analysis ───────────────────────────────────────────────────
def analyze_youtube_video(url: str):
    """
    Full deep analysis of a single YouTube video URL.
    Returns title, thumbnail, stats, tags, description, comments,
    channel info, and estimated daily metrics.
    """
    api_key = get_yt_api_key()
    if not api_key:
        return {"error": True, "message": "YOUTUBE_API_KEY is not set."}

    video_id = extract_video_id(url)
    if not video_id:
        return {"error": True, "message": "Could not extract video ID from URL. Please paste a valid YouTube video link."}

    cache_key = f"vid_{video_id}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    # Fetch video details
    try:
        vid_res = requests.get(VIDEOS_URL, params={
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": api_key,
        }, timeout=8)
    except requests.Timeout:
        return {"error": True, "message": "YouTube API request timed out."}
    except requests.RequestException:
        return {"error": True, "message": "Failed to connect to YouTube service."}

    if _is_quota_error(vid_res):
        return {"error": True, "message": "YouTube API daily quota reached. Please try again later.", "quota_exceeded": True}
    if vid_res.status_code == 429:
        return {"error": True, "message": "YouTube API rate limit reached. Please wait a moment."}
    if vid_res.status_code != 200:
        return {"error": True, "message": f"YouTube API error: {vid_res.status_code}"}

    vid_items = vid_res.json().get("items", [])
    if not vid_items:
        return {"error": True, "message": "Video not found. Please check the URL."}

    item    = vid_items[0]
    snippet = item["snippet"]
    stats   = item.get("statistics", {})
    content = item.get("contentDetails", {})

    title         = snippet.get("title", "")
    description   = snippet.get("description", "")
    channel_name  = snippet.get("channelTitle", "")
    channel_id    = snippet.get("channelId", "")
    upload_date   = snippet.get("publishedAt", "")
    tags          = snippet.get("tags", [])
    category_id   = snippet.get("categoryId", "")
    thumbnail     = (
        snippet.get("thumbnails", {}).get("maxres", {}).get("url") or
        snippet.get("thumbnails", {}).get("high", {}).get("url") or
        snippet.get("thumbnails", {}).get("medium", {}).get("url") or ""
    )

    view_count    = int(stats.get("viewCount", 0))
    like_count    = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))
    duration_sec  = _parse_duration(content.get("duration", "PT0S"))

    # Format duration
    dur_h = duration_sec // 3600
    dur_m = (duration_sec % 3600) // 60
    dur_s = duration_sec % 60
    if dur_h > 0:
        duration_fmt = f"{dur_h}:{dur_m:02d}:{dur_s:02d}"
    else:
        duration_fmt = f"{dur_m}:{dur_s:02d}"

    is_short = duration_sec <= 60

    # Engagement rate
    engagement_rate = round(((like_count + comment_count) / max(1, view_count)) * 100, 2)

    # Fetch comments
    comments_raw = []
    try:
        cm_res = requests.get(COMMENTS_URL, params={
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 50,
            "order": "relevance",
            "key": api_key,
        }, timeout=8)
        if cm_res.status_code == 200:
            for c in cm_res.json().get("items", []):
                text = c["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                author = c["snippet"]["topLevelComment"]["snippet"].get("authorDisplayName", "")
                likes = c["snippet"]["topLevelComment"]["snippet"].get("likeCount", 0)
                comments_raw.append({"text": text, "author": author, "likes": likes})
    except Exception:
        pass

    comment_texts = [c["text"] for c in comments_raw] if comments_raw else ["No comments available."]

    # Authentic single-point snapshot
    daily_metrics = _build_authentic_snapshot(view_count, like_count, comment_count, upload_date)

    # Channel subscriber count (quick fetch)
    subscriber_count = 0
    if channel_id:
        try:
            ch_res = requests.get(CHANNELS_URL, params={
                "part": "statistics",
                "id": channel_id,
                "key": api_key,
            }, timeout=8)
            if ch_res.status_code == 200:
                ch_items = ch_res.json().get("items", [])
                if ch_items:
                    subscriber_count = int(ch_items[0]["statistics"].get("subscriberCount", 0))
        except Exception:
            pass

    result = {
        "error": False,
        "video_id":         video_id,
        "title":            title,
        "thumbnail":        thumbnail,
        "description":      description,
        "channel_name":     channel_name,
        "channel_title":    channel_name,
        "channel_id":       channel_id,
        "channel_url":      f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
        "subscriber_count": subscriber_count,
        "upload_date":      upload_date[:10] if upload_date else "—",
        "published_at":     upload_date[:10] if upload_date else "—",
        "duration":         duration_fmt,
        "duration_sec":     duration_sec,
        "is_short":         is_short,
        "tags":             tags,
        "category_id":      category_id,
        "view_count":       view_count,
        "views":            view_count,
        "like_count":       like_count,
        "comment_count":    comment_count,
        "engagement_rate":  engagement_rate,
        "daily_metrics":    daily_metrics,
        "comments":         comment_texts,
        "top_comments":     comments_raw[:10],
    }
    _save_to_cache(cache_key, result)
    return result


# ─── Channel Audit ───────────────────────────────────────────────────────────
def audit_youtube_channel(identifier: str, is_handle: bool = True) -> dict:
    """
    Comprehensive YouTube channel audit.
    Fetches real stats, subscriber count, total views, top 10 videos,
    view velocity, and SocialBlade-style earnings.
    """
    api_key = get_yt_api_key()
    if not api_key:
        return {"error": True, "message": "YOUTUBE_API_KEY is not set."}

    clean_id = (identifier or "").strip()
    if not clean_id:
        return {"error": True, "message": "Channel identifier is required."}

    cache_key = f"ch_{clean_id.lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    channel_id = None

    # 1. Resolve channel ID from handle or URL
    if is_handle:
        handle = clean_id.lstrip("@")
        # Try with @ prefix
        try:
            res = requests.get(CHANNELS_URL, params={
                "part": "id,snippet,statistics,brandingSettings",
                "forHandle": f"@{handle}",
                "key": api_key,
            }, timeout=8)
            if _is_quota_error(res):
                return {"error": True, "message": "YouTube API daily quota reached. Please try again later.", "quota_exceeded": True}
            if res.status_code == 200:
                items = res.json().get("items", [])
                if items:
                    channel_id = items[0]["id"]
        except Exception:
            pass

        # Try without @ prefix if not found
        if not channel_id:
            try:
                res = requests.get(CHANNELS_URL, params={
                    "part": "id,snippet,statistics,brandingSettings",
                    "forHandle": handle,
                    "key": api_key,
                }, timeout=10)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    if items:
                        channel_id = items[0]["id"]
            except Exception:
                pass

        # fallback: search by name
        if not channel_id:
            try:
                sr = requests.get(SEARCH_URL, params={
                    "part": "snippet", "q": handle, "type": "channel",
                    "maxResults": 1, "key": YOUTUBE_API_KEY,
                }, timeout=10)
                if sr.status_code == 200:
                    sr_items = sr.json().get("items", [])
                    if sr_items:
                        channel_id = sr_items[0]["snippet"]["channelId"]
            except Exception:
                pass
    else:
        # Extract from URL: /channel/UCxxxxx or /c/name or /@handle or watch?v= or /shorts/
        import re

        # Handle video URL: youtube.com/watch?v=VIDEO_ID
        m_watch = re.search(r"[?&]v=([\w-]+)", identifier)
        if m_watch:
            video_id = m_watch.group(1)
            try:
                vid_res = requests.get(VIDEOS_URL, params={
                    "part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY,
                }, timeout=10)
                if vid_res.status_code == 200:
                    vid_items = vid_res.json().get("items", [])
                    if vid_items:
                        channel_id = vid_items[0]["snippet"]["channelId"]
            except Exception:
                pass
            if not channel_id:
                return {"error": True, "message": f"Could not find channel for video: {identifier}"}

        # Handle shorts URL: youtube.com/shorts/VIDEO_ID
        elif re.search(r"/shorts/([\w-]+)", identifier):
            m_shorts = re.search(r"/shorts/([\w-]+)", identifier)
            video_id = m_shorts.group(1)
            try:
                vid_res = requests.get(VIDEOS_URL, params={
                    "part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY,
                }, timeout=10)
                if vid_res.status_code == 200:
                    vid_items = vid_res.json().get("items", [])
                    if vid_items:
                        channel_id = vid_items[0]["snippet"]["channelId"]
            except Exception:
                pass
            if not channel_id:
                return {"error": True, "message": f"Could not find channel for short: {identifier}"}

        # Handle /channel/UCxxxxx
        elif re.search(r"/channel/(UC[\w-]+)", identifier):
            channel_id = re.search(r"/channel/(UC[\w-]+)", identifier).group(1)

        # Handle /@handle
        elif re.search(r"/@([^/?&]+)", identifier):
            return audit_youtube_channel(re.search(r"/@([^/?&]+)", identifier).group(1), is_handle=True)

        # Handle /c/name or /user/name
        elif re.search(r"/(?:c|user)/([^/?&]+)", identifier):
            return audit_youtube_channel(re.search(r"/(?:c|user)/([^/?&]+)", identifier).group(1), is_handle=True)

    if not channel_id:
        return {"error": True, "message": f"Could not resolve channel for: {identifier}. Please enter a valid YouTube channel @handle or channel URL."}


    # 2. Fetch full channel details
    ch_res = requests.get(CHANNELS_URL, params={
        "part": "snippet,statistics,brandingSettings,contentDetails",
        "id": channel_id,
        "key": YOUTUBE_API_KEY,
    }, timeout=10)

    if ch_res.status_code != 200:
        return {"error": True, "message": f"YouTube API error: {ch_res.status_code}"}

    ch_items = ch_res.json().get("items", [])
    if not ch_items:
        return {"error": True, "message": "Channel not found."}

    ch = ch_items[0]
    snippet    = ch["snippet"]
    stats      = ch["statistics"]
    branding   = ch.get("brandingSettings", {})
    content    = ch.get("contentDetails", {})

    subscriber_count = int(stats.get("subscriberCount", 0))
    total_views_ch   = int(stats.get("viewCount", 0))
    video_count      = int(stats.get("videoCount", 0))

    published_at  = snippet.get("publishedAt", "")
    channel_name  = snippet.get("title", "Unknown")
    description   = snippet.get("description", "")[:200]
    country       = snippet.get("country", "—")
    avatar_url    = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
    banner_url    = branding.get("image", {}).get("bannerExternalUrl", "")

    # Channel age in years
    try:
        pub_date  = datetime.strptime(published_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        age_years = round((datetime.now(timezone.utc) - pub_date).days / 365.25, 1)
    except Exception:
        age_years = 0

    # 3. Top videos from uploads playlist
    uploads_playlist = content.get("relatedPlaylists", {}).get("uploads", "")
    top_videos = []
    longform_count = 0
    shorts_count   = 0
    longform_views = 0
    shorts_views   = 0

    if uploads_playlist:
        try:
            pl_res = requests.get(PLAYLIST_URL, params={
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist,
                "maxResults": 15,
                "key": YOUTUBE_API_KEY,
            }, timeout=10)
            if pl_res.status_code == 200:
                pl_items = pl_res.json().get("items", [])
                video_ids = [it["contentDetails"]["videoId"] for it in pl_items]

                if video_ids:
                    vids_res = requests.get(VIDEOS_URL, params={
                        "part": "snippet,statistics,contentDetails",
                        "id": ",".join(video_ids),
                        "key": YOUTUBE_API_KEY,
                    }, timeout=10)
                    if vids_res.status_code == 200:
                        for v in vids_res.json().get("items", []):
                            v_stats  = v.get("statistics", {})
                            v_snip   = v["snippet"]
                            v_cd     = v.get("contentDetails", {})
                            v_views  = int(v_stats.get("viewCount", 0))
                            v_likes  = int(v_stats.get("likeCount", 0))
                            v_thumb  = v_snip.get("thumbnails", {}).get("medium", {}).get("url", "")
                            v_title  = v_snip.get("title", "Untitled")
                            v_id     = v["id"]
                            v_dur    = v_cd.get("duration", "PT0S")

                            # Parse ISO 8601 duration to seconds
                            dur_sec = _parse_duration(v_dur)
                            is_short = dur_sec <= 60

                            if is_short:
                                shorts_count  += 1
                                shorts_views  += v_views
                            else:
                                longform_count += 1
                                longform_views += v_views

                            # Views per hour estimate (simplified)
                            vph = round(v_views / max(1, age_years * 8760), 1)

                            top_videos.append({
                                "video_id":   v_id,
                                "title":      v_title,
                                "views":      v_views,
                                "likes":      v_likes,
                                "thumbnail":  v_thumb,
                                "vph":        vph,
                                "is_short":   is_short,
                                "duration":   dur_sec,
                                "published_at": v_snip.get("publishedAt", "")[:10] if v_snip.get("publishedAt") else "—",
                            })

        except Exception:
            pass

    # Sort top videos by views
    top_videos = sorted(top_videos, key=lambda x: x["views"], reverse=True)[:10]

    # 4. Authentic channel timeline (never fabricate artificial sine-wave curves)
    growth_28d = []
    growth_7d  = []
    growth_3m  = []

    # 5. SocialBlade-style earnings estimate
    # YouTube pays ~$1–$3 CPM on avg (varies heavily)
    avg_daily = total_views_ch / max(1, age_years * 365)
    monthly_views    = int(avg_daily * 30)
    earn_min_monthly = round(monthly_views / 1000 * 1.0, 0)
    earn_max_monthly = round(monthly_views / 1000 * 5.0, 0)

    # 6. Rank estimates (heuristic based on subscriber count)
    country_rank   = _estimate_rank(subscriber_count, country, "country")
    worldwide_rank = _estimate_rank(subscriber_count, country, "worldwide")

    # 7. Totals for timeframe display
    total_longform_pct = round(longform_count / max(1, longform_count + shorts_count) * 100)
    total_shorts_pct   = 100 - total_longform_pct
    longform_views_pct = round(longform_views / max(1, longform_views + shorts_views) * 100)
    shorts_views_pct   = 100 - longform_views_pct

    result = {
        "error": False,
        "channel_id":       channel_id,
        "channel_name":     channel_name,
        "description":      description,
        "avatar_url":       avatar_url,
        "banner_url":       banner_url,
        "country":          country,
        "age_years":        age_years,
        "published_at":     published_at[:10] if published_at else "—",
        "subscriber_count": subscriber_count,
        "total_views":      total_views_ch,
        "video_count":      video_count,
        "country_rank":     country_rank,
        "worldwide_rank":   worldwide_rank,
        "earn_min_monthly": int(earn_min_monthly),
        "earn_max_monthly": int(earn_max_monthly),
        # Content breakdown
        "longform_count":       longform_count,
        "shorts_count":         shorts_count,
        "longform_views":       longform_views,
        "shorts_views":         shorts_views,
        "longform_pct":         total_longform_pct,
        "shorts_pct":           total_shorts_pct,
        "longform_views_pct":   longform_views_pct,
        "shorts_views_pct":     shorts_views_pct,
        # Time series
        "growth_7d":  growth_7d,
        "growth_28d": growth_28d,
        "growth_3m":  growth_3m,
        "historical_growth_available": False,
        "historical_notice": "Historical view curve requires continuous snapshot tracking or channel owner OAuth authorization.",
        # Top videos
        "top_videos": top_videos,
    }
    _save_to_cache(cache_key, result)
    return result


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to total seconds."""
    import re
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, iso_duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s


def _estimate_rank(subscriber_count: int, country: str, scope: str) -> str:
    """Heuristic rank estimate based on subscriber count."""
    if scope == "worldwide":
        if subscriber_count >= 100_000_000:   return "#1 – #10"
        elif subscriber_count >= 50_000_000:  return "#10 – #50"
        elif subscriber_count >= 10_000_000:  return "#50 – #500"
        elif subscriber_count >= 1_000_000:   return "#500 – #5K"
        elif subscriber_count >= 100_000:     return "#5K – #50K"
        elif subscriber_count >= 10_000:      return "#50K – #500K"
        else:                                  return "#500K+"
    else:  # country
        if subscriber_count >= 10_000_000:   return "#1 – #10"
        elif subscriber_count >= 1_000_000:  return "#10 – #100"
        elif subscriber_count >= 100_000:    return "#100 – #1K"
        elif subscriber_count >= 10_000:     return "#1K – #10K"
        else:                                 return "#10K+"
