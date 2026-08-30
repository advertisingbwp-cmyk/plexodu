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
    Normalized to a 0-100 scale for dashboard display.
    """
    if not daily_metrics:
        return 0.0

    growth_rate = calculate_growth_rate(daily_metrics)
    latest = daily_metrics[-1]

    like_ratio = (latest["likes"] / latest["views"]) * 100 if latest["views"] else 0
    share_ratio = (latest["shares"] / latest["views"]) * 100 if latest["views"] else 0

    raw_index = (growth_rate * 0.6) + (like_ratio * 0.2) + (share_ratio * 0.2)
    v_index = max(0, min(100, raw_index))
    return round(v_index, 2)


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
