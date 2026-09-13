"""
Trend Scoring & Growth Component (Trend Engine)
Implements Virality Index, Engagement Rate, and YouTube SEO Opportunity Score calculations.
"""


def calculate_growth_rate(daily_metrics):
    """Growth rate between the last two recorded days."""
    if len(daily_metrics) < 2:
        return 0.0
    current_views = daily_metrics[-1]["views"]
    past_views = daily_metrics[-2]["views"]
    if past_views <= 0:
        return 0.0
    return round(((current_views - past_views) / past_views) * 100, 2)


def calculate_virality_index(daily_metrics):
    """
    Weighted Virality Index:
    vIndex = (growthRate * 0.6) + (likes * 0.2) + (shares * 0.2)
    Normalized to a 0-100 scale for display.
    """
    if not daily_metrics:
        return 0.0

    latest = daily_metrics[-1]
    views = latest.get("views", 0)

    if len(daily_metrics) < 2:
        # Authentic snapshot fallback based on view volume and audience engagement
        import math
        likes = latest.get("likes", 0)
        comments = latest.get("comments_count", 0)
        vol = min(50.0, math.log10(max(1, views)) * 7.0) if views > 0 else 0
        eng = min(40.0, (((likes + comments) / max(1, views)) * 100) * 5.0) if views > 0 else 0
        return round(min(98.0, max(10.0, vol + eng)), 1)

    growth_rate = calculate_growth_rate(daily_metrics)
    like_ratio = (latest["likes"] / latest["views"]) * 100 if latest["views"] else 0
    share_ratio = (latest["shares"] / latest["views"]) * 100 if latest["views"] else 0

    raw_index = (growth_rate * 0.6) + (like_ratio * 0.2) + (share_ratio * 0.2)
    v_index = max(0, min(100, raw_index))
    return round(v_index, 2)


def calculate_video_virality(view_count: int, like_count: int, comment_count: int, upload_date_str: str = "") -> float:
    """
    Computes a realistic 0-100 Virality Index for an individual YouTube video based on
    total view volume, view velocity (views/day since publication), and audience engagement.
    """
    if not view_count or view_count <= 0:
        return 0.0

    import math
    from datetime import datetime, timezone

    # 1. Volume score (0-40 points) on log scale
    vol_score = min(40.0, max(0.0, math.log10(view_count) * 5.0))

    # 2. View velocity score (0-35 points)
    days_active = 30.0
    if upload_date_str:
        try:
            pub_dt = datetime.strptime(upload_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_active = max(1.0, (datetime.now(timezone.utc) - pub_dt).days)
        except Exception:
            days_active = 30.0
    views_per_day = view_count / days_active
    vel_score = min(35.0, max(0.0, math.log10(max(1.0, views_per_day)) * 6.0))

    # 3. Engagement score (0-25 points)
    eng_pct = ((like_count + comment_count) / max(1, view_count)) * 100.0
    eng_score = min(25.0, max(0.0, eng_pct * 3.0))

    v_score = round(vol_score + vel_score + eng_score, 1)
    return min(99.0, max(5.0, v_score))


def calculate_engagement_rate(daily_metrics):
    """
    Calculates YouTube Audience Engagement Rate (%):
    ((Likes + Comments) / Total Views) * 100
    """
    if not daily_metrics or not daily_metrics[-1]["views"]:
        return 0.0
    latest = daily_metrics[-1]
    eng = ((latest["likes"] + latest["comments_count"]) / latest["views"]) * 100
    return round(eng, 2)


def calculate_seo_score(daily_metrics, keyword: str):
    """
    Calculates YouTube Keyword SEO Opportunity Score (0-100).
    Considers Demand (View Growth), Audience Engagement, and Competition factor.
    Returns: {"score": float, "rating": str, "competition": str}
    """
    if not daily_metrics:
        return {"score": 50.0, "rating": "MODERATE", "competition": "Medium"}

    growth = calculate_growth_rate(daily_metrics)
    virality = calculate_virality_index(daily_metrics)
    engagement = calculate_engagement_rate(daily_metrics)

    # Base score calculated from market demand + engagement signals
    base_score = (growth * 0.4) + (virality * 0.35) + (engagement * 5.0)

    # Long-tail keyword bonus (less competitive)
    word_count = len(keyword.split())
    kw_bonus = min(15, (word_count - 1) * 5)

    final_score = round(max(15, min(98, base_score + 40 + kw_bonus)), 1)

    if final_score >= 75:
        rating = "HIGH OPPORTUNITY"
        competition = "Low (Great to target)"
    elif final_score >= 55:
        rating = "GOOD OPPORTUNITY"
        competition = "Medium"
    elif final_score >= 35:
        rating = "MODERATE"
        competition = "High"
    else:
        rating = "SATURATED"
        competition = "Very High"

    return {
        "score": final_score,
        "rating": rating,
        "competition": competition,
    }


def classify_trend_stage(growth_rate):
    """Classifies a trend as emerging, peaking, or fading."""
    if growth_rate > 15:
        return "Rising"
    elif growth_rate >= 0:
        return "Peaking"
    else:
        return "Fading"


def total_views(daily_metrics):
    return sum(day["views"] for day in daily_metrics)
