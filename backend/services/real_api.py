"""
Platform Connector (Live Mode - YouTube)
-----------------------------------------
Real implementation of fetch_youtube_data() and audit_youtube_channel()
using the YouTube Data API v3.
"""

import os
import math
import requests
from datetime import datetime, timedelta
from app.core.config import settings

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY", "").strip()
SEARCH_URL   = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL   = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
PLAYLIST_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


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


# ─── Daily Series Estimator ──────────────────────────────────────────────────
def _estimate_daily_series(total_views, total_likes, total_comments, upload_date_str, days_window=10):
    try:
        upload_date = datetime.strptime(upload_date_str[:10], "%Y-%m-%d")
    except ValueError:
        upload_date = datetime.utcnow() - timedelta(days=days_window)

    age_days = max(1, (datetime.utcnow() - upload_date).days)
    window   = min(days_window, age_days)

    # Dynamic decay rate based on video age, view count, and deterministic metric seed
    base_decay = min(0.35, max(0.06, 1.8 / math.sqrt(age_days + 1)))
    variance   = ((total_views * 7 + total_likes * 13 + total_comments * 29) % 120) / 1000.0
    decay_rate = round(base_decay + variance, 3)

    weights    = [math.exp(-decay_rate * (window - i)) for i in range(window)]
    weight_sum = sum(weights)

    series = []
    cumulative_views = 0
    for i, w in enumerate(weights):
        share = w / weight_sum
        day_views = int(total_views * share)
        cumulative_views += day_views
        date = (datetime.utcnow() - timedelta(days=window - i)).strftime("%Y-%m-%d")
        series.append({
            "date": date,
            "views": max(cumulative_views, 1),
            "likes": int(total_likes * (cumulative_views / max(total_views, 1))),
            "shares": int(total_comments * 0.3 * (cumulative_views / max(total_views, 1))),
            "comments_count": int(total_comments * (cumulative_views / max(total_views, 1))),
        })

    series[-1]["views"]         = total_views
    series[-1]["likes"]         = total_likes
    series[-1]["comments_count"] = total_comments
    return series


# ─── Keyword Trend Fetch ─────────────────────────────────────────────────────
def fetch_youtube_data(keyword: str):
    if not YOUTUBE_API_KEY:
        raise YouTubeAPIError("YOUTUBE_API_KEY is not set. Add it to your .env file.")

    search_res = requests.get(SEARCH_URL, params={
        "part": "snippet", "q": keyword, "type": "video",
        "order": "viewCount", "maxResults": 1, "key": YOUTUBE_API_KEY,
    }, timeout=10)

    if search_res.status_code == 403:
        return {"status": 403, "platform": "YouTube", "error": "Invalid YouTube API key or quota exceeded."}
    if search_res.status_code != 200:
        return {"status": search_res.status_code, "platform": "YouTube", "error": search_res.text[:200]}

    items = search_res.json().get("items", [])
    if not items:
        return {"status": 404, "platform": "YouTube", "error": f'No videos found for "{keyword}".'}

    video_id = items[0]["id"]["videoId"]
    snippet  = items[0]["snippet"]

    stats_res   = requests.get(VIDEOS_URL, params={"part": "statistics,snippet", "id": video_id, "key": YOUTUBE_API_KEY}, timeout=10)
    stats_items = stats_res.json().get("items", [])
    if not stats_items:
        return {"status": 404, "platform": "YouTube", "error": "Video statistics unavailable."}

    stats         = stats_items[0]["statistics"]
    total_views   = int(stats.get("viewCount", 0))
    total_likes   = int(stats.get("likeCount", 0))
    total_comments = int(stats.get("commentCount", 0))
    upload_date   = snippet["publishedAt"]

    comments = []
    try:
        comments_res = requests.get(COMMENTS_URL, params={
            "part": "snippet", "videoId": video_id,
            "maxResults": 50, "order": "relevance", "key": YOUTUBE_API_KEY,
        }, timeout=10)
        if comments_res.status_code == 200:
            for item in comments_res.json().get("items", []):
                text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(text)
    except requests.RequestException:
        pass

    if not comments:
        comments = ["No comments available for this video."]

    related_keywords = _fetch_related_keywords(keyword)

    return {
        "status": 200, "platform": "YouTube",
        "keyword": keyword, "video_id": video_id,
        "title": snippet.get("title", keyword),
        "upload_date": upload_date,
        "daily_metrics": _estimate_daily_series(total_views, total_likes, total_comments, upload_date),
        "comments": comments,
        "related_keywords": related_keywords,
    }


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

    import re

    # Extract video ID from various URL formats
    video_id = None
    patterns = [
        r"(?:v=|youtu\.be/|/shorts/|/embed/|/v/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            video_id = m.group(1)
            break

    if not video_id:
        # Maybe raw video ID was passed
        if re.match(r"^[A-Za-z0-9_-]{11}$", url.strip()):
            video_id = url.strip()
        else:
            return {"error": True, "message": "Could not extract video ID from URL. Please paste a valid YouTube video link."}

    # Fetch video details
    vid_res = requests.get(VIDEOS_URL, params={
        "part": "snippet,statistics,contentDetails",
        "id": video_id,
        "key": api_key,
    }, timeout=10)

    if vid_res.status_code == 429:
        err = vid_res.json()
        return {"error": True, "message": f"YouTube API Error: {err}"}
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
    description   = snippet.get("description", "")[:500]
    channel_name  = snippet.get("channelTitle", "")
    channel_id    = snippet.get("channelId", "")
    upload_date   = snippet.get("publishedAt", "")
    tags          = snippet.get("tags", [])[:15]
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
            "key": YOUTUBE_API_KEY,
        }, timeout=10)
        if cm_res.status_code == 200:
            for c in cm_res.json().get("items", []):
                text = c["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                author = c["snippet"]["topLevelComment"]["snippet"].get("authorDisplayName", "")
                likes = c["snippet"]["topLevelComment"]["snippet"].get("likeCount", 0)
                comments_raw.append({"text": text, "author": author, "likes": likes})
    except Exception:
        pass

    comment_texts = [c["text"] for c in comments_raw] if comments_raw else ["No comments available."]

    # Daily metrics estimate
    daily_metrics = _estimate_daily_series(view_count, like_count, comment_count, upload_date)

    # Channel subscriber count (quick fetch)
    subscriber_count = 0
    try:
        ch_res = requests.get(CHANNELS_URL, params={
            "part": "statistics",
            "id": channel_id,
            "key": YOUTUBE_API_KEY,
        }, timeout=8)
        if ch_res.status_code == 200:
            ch_items = ch_res.json().get("items", [])
            if ch_items:
                subscriber_count = int(ch_items[0]["statistics"].get("subscriberCount", 0))
    except Exception:
        pass

    return {
        "error": False,
        "video_id":         video_id,
        "title":            title,
        "thumbnail":        thumbnail,
        "description":      description,
        "channel_name":     channel_name,
        "channel_id":       channel_id,
        "channel_url":      f"https://www.youtube.com/channel/{channel_id}",
        "subscriber_count": subscriber_count,
        "upload_date":      upload_date[:10] if upload_date else "—",
        "duration":         duration_fmt,
        "duration_sec":     duration_sec,
        "is_short":         is_short,
        "tags":             tags,
        "category_id":      category_id,
        "view_count":       view_count,
        "like_count":       like_count,
        "comment_count":    comment_count,
        "engagement_rate":  engagement_rate,
        "daily_metrics":    daily_metrics,
        "comments":         comment_texts,
        "top_comments":     comments_raw[:10],
    }


# ─── Channel Audit ───────────────────────────────────────────────────────────
def get_yt_api_key():
    return (settings.YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY", "")).strip()

def audit_youtube_channel(identifier: str, is_handle: bool = True) -> dict:
    """
    Comprehensive YouTube channel audit.
    Fetches real stats, subscriber count, total views, top 10 videos,
    view velocity, 28-day growth curve, and SocialBlade-style earnings.
    """
    api_key = get_yt_api_key()
    if not api_key:
        return {"error": True, "message": "YOUTUBE_API_KEY is not set."}

    channel_id = None

    # 1. Resolve channel ID from handle or URL
    if is_handle:
        handle = identifier.lstrip("@")
        # Try with @ prefix
        try:
            res = requests.get(CHANNELS_URL, params={
                "part": "id,snippet,statistics,brandingSettings",
                "forHandle": f"@{handle}",
                "key": api_key,
            }, timeout=10)
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
        pub_date  = datetime.strptime(published_at[:10], "%Y-%m-%d")
        age_years = round((datetime.utcnow() - pub_date).days / 365.25, 1)
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
                                "video_id":  v_id,
                                "title":     v_title,
                                "views":     v_views,
                                "likes":     v_likes,
                                "thumbnail": v_thumb,
                                "vph":       vph,
                                "is_short":  is_short,
                                "duration":  dur_sec,
                            })

        except Exception:
            pass

    # Sort top videos by views
    top_videos = sorted(top_videos, key=lambda x: x["views"], reverse=True)[:10]

    # 4. 28-day growth series (estimated from total views)
    avg_daily = total_views_ch / max(1, age_years * 365)
    growth_28d = []
    for i in range(28, 0, -1):
        day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        variation = 1.0 + (math.sin(i * 0.7) * 0.3)
        growth_28d.append({"date": day, "views": int(avg_daily * variation)})

    # 7-day and 3-month series
    growth_7d  = growth_28d[-7:]
    avg_daily_3m = avg_daily * 0.85
    growth_3m  = []
    for i in range(90, 0, -1):
        day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        variation = 1.0 + (math.sin(i * 0.4) * 0.25)
        growth_3m.append({"date": day, "views": int(avg_daily_3m * variation)})

    # 5. SocialBlade-style earnings estimate
    # YouTube pays ~$1–$3 CPM on avg (varies heavily)
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

    return {
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
        # Top videos
        "top_videos": top_videos,
    }


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
