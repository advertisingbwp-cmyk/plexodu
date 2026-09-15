"""
Trend Intelligence Engine (Phase 8 Rebuild)
Accumulates multi-scan time-series observations, computes day-over-day velocity,
acceleration, direction, confidence, smoothed moving averages, historical windows,
and conservative forecasts.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional


def calculate_moving_averages(data_points: List[float], window_size: int = 3) -> List[float]:
    """
    Computes a simple moving average to smooth time-series noise.
    """
    if not data_points:
        return []
    if len(data_points) < 2:
        return [round(data_points[0], 2)]

    smoothed = []
    for i in range(len(data_points)):
        start_idx = max(0, i - window_size + 1)
        sub_list = data_points[start_idx : i + 1]
        avg = sum(sub_list) / len(sub_list)
        smoothed.append(round(avg, 2))
    return smoothed


def compute_historical_window_change(
    observations: List[Dict[str, Any]],
    current_views: int,
    now: datetime,
    window_days: int,
) -> Dict[str, Any]:
    """
    Computes change percentage against an observation within the given day window.
    Returns status='insufficient_history' if no observation exists in that range.
    """
    if len(observations) < 2:
        return {
            "status": "insufficient_history",
            "change_pct": None,
            "display": "Insufficient history",
        }

    cutoff = now - timedelta(days=window_days)
    valid_past = [
        obs for obs in observations[:-1]
        if obs.get("timestamp") and obs["timestamp"] <= cutoff + timedelta(hours=12)
    ]

    if not valid_past:
        return {
            "status": "insufficient_history",
            "change_pct": None,
            "display": "Insufficient history",
        }

    baseline_obs = valid_past[-1]
    past_views = baseline_obs.get("views", 0)
    if past_views <= 0:
        return {
            "status": "insufficient_history",
            "change_pct": None,
            "display": "Insufficient history",
        }

    change_pct = round(((current_views - past_views) / past_views) * 100, 2)
    sign = "+" if change_pct > 0 else ""
    return {
        "status": "available",
        "change_pct": change_pct,
        "display": f"{sign}{change_pct}%",
        "baseline_date": baseline_obs["timestamp"].strftime("%Y-%m-%d"),
    }


def compute_trend_score(
    velocity: Optional[float],
    acceleration: Optional[float],
    engagement_rate: float,
    scan_count: int,
    direction: str,
    positive_sentiment_score: float,
) -> float:
    """
    Computes a normalized 0-100 Trend Score based on 6 weighted factors:
    - Velocity (30%)
    - Acceleration (20%)
    - Engagement (20%)
    - Consistency (10%)
    - Momentum (10%)
    - Sentiment (10%)
    """
    if velocity is None:
        return 50.0

    # 1. Velocity component (30%)
    vel_norm = min(100.0, max(0.0, 50.0 + (velocity * 1.5)))

    # 2. Acceleration component (20%)
    acc = acceleration if acceleration is not None else 0.0
    acc_norm = min(100.0, max(0.0, 50.0 + (acc * 2.0)))

    # 3. Engagement component (20%)
    eng_norm = min(100.0, max(0.0, engagement_rate * 12.0))

    # 4. Consistency component (10%)
    cons_norm = min(100.0, 30.0 + min(scan_count * 2.5, 70.0))

    # 5. Directional Momentum (10%)
    if direction == "RISING":
        mom_norm = 85.0
    elif direction == "STABLE":
        mom_norm = 50.0
    elif direction == "FALLING":
        mom_norm = 20.0
    else:
        mom_norm = 50.0

    # 6. Sentiment component (10%)
    sent_norm = min(100.0, max(0.0, positive_sentiment_score))

    raw_score = (
        (vel_norm * 0.30)
        + (acc_norm * 0.20)
        + (eng_norm * 0.20)
        + (cons_norm * 0.10)
        + (mom_norm * 0.10)
        + (sent_norm * 0.10)
    )
    return round(max(5.0, min(99.0, raw_score)), 1)


def generate_conservative_forecast(
    observations: List[Dict[str, Any]],
    current_views: int,
    velocity: Optional[float],
) -> Dict[str, Any]:
    """
    Generates a conservative 7-day projection only when observations >= 3.
    Applies logarithmic dampening towards the mean.
    """
    if len(observations) < 3 or velocity is None:
        return {
            "available": False,
            "reason": "Requires at least 3 historical scans for projection",
            "projection_days": [],
        }

    capped_vel = max(-25.0, min(25.0, velocity))
    daily_rate = (capped_vel / 100.0) / 7.0

    projections = []
    running_views = float(current_views)
    for day in range(1, 8):
        dampener = 0.85 ** (day - 1)
        expected_views = int(round(running_views * (1.0 + (daily_rate * dampener))))
        margin = max(500, int(expected_views * (0.03 + (0.015 * day))))
        projections.append({
            "day": f"+{day}d",
            "expected_views": expected_views,
            "lower_bound": max(0, expected_views - margin),
            "upper_bound": expected_views + margin,
        })
        running_views = expected_views

    return {
        "available": True,
        "reason": None,
        "projection_days": projections,
    }


def analyze_trend_intelligence(
    keyword: str,
    platform_name: str,
    current_views: int,
    current_engagement: float,
    sentiment_result: Dict[str, Any],
    past_trends: List[Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Main entry point for Phase 8 Trend Intelligence Engine.
    Evaluates historical observations, computes velocity, acceleration, direction,
    confidence, events, historical windows, smoothed data, and forecasts.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    observations = []
    for pt in past_trends:
        ts = pt.timestamp or pt.last_seen_at or now
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        observations.append({
            "id": pt.trend_id,
            "timestamp": ts,
            "views": pt.total_views or 0,
            "velocity": pt.current_velocity,
            "acceleration": pt.current_acceleration,
            "trend_score": pt.current_trend_score,
            "direction": pt.current_direction or "STABLE",
            "confidence": pt.current_confidence or "Low",
        })

    observations.append({
        "id": None,
        "timestamp": now,
        "views": current_views,
        "velocity": None,
        "acceleration": None,
        "trend_score": None,
        "direction": "BASELINE",
        "confidence": "Low",
    })

    scan_count = len(observations)
    first_seen_at = observations[0]["timestamp"]
    last_seen_at = now

    if scan_count == 1:
        status = "baseline"
        direction = "BASELINE"
        confidence = "Low"
        velocity = None
        acceleration = None
        trend_score = None
        velocity_display = "Pending"
        acceleration_display = "Pending"
        trend_score_display = "Pending"
        direction_display = "Baseline Created"
        educational_banner = (
            "Baseline observation established. Scan again in 24–48 hours to measure "
            "real-world growth velocity, momentum, and curve progression."
        )

        timeline = [{
            "date": now.strftime("%Y-%m-%d %H:%M"),
            "views": current_views,
            "smoothed_views": current_views,
            "engagement_rate": current_engagement,
        }]

        events = [{
            "date": now.strftime("%b %d, %Y"),
            "title": "Baseline Created",
            "description": f"Initial snapshot established with {current_views:,} views.",
            "type": "baseline",
        }]

        historical_context = {
            "1d": {"status": "insufficient_history", "change_pct": None, "display": "Insufficient history"},
            "7d": {"status": "insufficient_history", "change_pct": None, "display": "Insufficient history"},
            "30d": {"status": "insufficient_history", "change_pct": None, "display": "Insufficient history"},
            "90d": {"status": "insufficient_history", "change_pct": None, "display": "Insufficient history"},
        }

        forecast = generate_conservative_forecast(observations, current_views, None)

        return {
            "status": status,
            "scan_count": scan_count,
            "first_seen_at": first_seen_at.isoformat(),
            "last_seen_at": last_seen_at.isoformat(),
            "current_trend_score": trend_score,
            "current_trend_score_display": trend_score_display,
            "current_direction": direction,
            "current_direction_display": direction_display,
            "current_confidence": confidence,
            "velocity": velocity,
            "velocity_display": velocity_display,
            "acceleration": acceleration,
            "acceleration_display": acceleration_display,
            "educational_banner": educational_banner,
            "historical_context": historical_context,
            "timeline": timeline,
            "events": events,
            "forecast": forecast,
        }

    # MULTI-SCAN CASE (scan_count >= 2)
    status = "active"
    prev_obs = observations[-2]
    prev_views = prev_obs["views"]

    if prev_views > 0:
        velocity = round(((current_views - prev_views) / prev_views) * 100, 2)
    else:
        velocity = 0.0

    if len(observations) >= 3:
        prev_prev_obs = observations[-3]
        prev_prev_views = prev_prev_obs["views"]
        if prev_obs["velocity"] is not None:
            prev_velocity = prev_obs["velocity"]
        elif prev_prev_views > 0:
            prev_velocity = round(((prev_views - prev_prev_views) / prev_prev_views) * 100, 2)
        else:
            prev_velocity = 0.0
        acceleration = round(velocity - prev_velocity, 2)
    else:
        acceleration = 0.0

    if velocity > 3.0:
        direction = "RISING"
        direction_display = f"Rising (+{velocity}%)"
    elif velocity < -3.0:
        direction = "FALLING"
        direction_display = f"Falling ({velocity}%)"
    else:
        direction = "STABLE"
        direction_display = f"Stable ({'+' if velocity > 0 else ''}{velocity}%)"

    if scan_count < 7:
        confidence = "Low"
    elif scan_count < 30:
        confidence = "Medium"
    else:
        confidence = "High"

    pos_sent = sentiment_result.get("positive_score", 50.0) if sentiment_result else 50.0
    trend_score = compute_trend_score(
        velocity=velocity,
        acceleration=acceleration,
        engagement_rate=current_engagement,
        scan_count=scan_count,
        direction=direction,
        positive_sentiment_score=pos_sent,
    )

    trend_score_display = str(int(round(trend_score)))
    velocity_display = f"{'+' if velocity > 0 else ''}{velocity}%"
    acceleration_display = f"{'+' if acceleration > 0 else ''}{acceleration}%"

    educational_banner = ""

    all_views = [obs["views"] for obs in observations]
    smoothed_views = calculate_moving_averages(all_views, window_size=3)

    timeline = []
    for i, obs in enumerate(observations):
        timeline.append({
            "date": obs["timestamp"].strftime("%Y-%m-%d %H:%M"),
            "views": obs["views"],
            "smoothed_views": int(round(smoothed_views[i])),
            "engagement_rate": current_engagement if i == len(observations) - 1 else 0.0,
        })

    events = []
    events.append({
        "date": first_seen_at.strftime("%b %d, %Y"),
        "title": "Baseline Created",
        "description": f"First tracked scan with {observations[0]['views']:,} views.",
        "type": "baseline",
    })

    if velocity >= 15.0:
        events.append({
            "date": now.strftime("%b %d, %Y"),
            "title": "Velocity Spike Detected",
            "description": f"Views surged by +{velocity}% since the previous scan.",
            "type": "spike",
        })
    elif velocity <= -15.0:
        events.append({
            "date": now.strftime("%b %d, %Y"),
            "title": "Velocity Drop Observed",
            "description": f"Views dropped by {velocity}% compared to previous scan.",
            "type": "drop",
        })

    if direction == "RISING" and prev_obs.get("direction") != "RISING":
        events.append({
            "date": now.strftime("%b %d, %Y"),
            "title": "Momentum Shifted to Rising",
            "description": f"Positive acceleration detected with velocity of {velocity_display}.",
            "type": "shift",
        })

    if current_engagement >= 8.0:
        events.append({
            "date": now.strftime("%b %d, %Y"),
            "title": "High Audience Engagement",
            "description": f"Audience engagement reached a robust {current_engagement}%.",
            "type": "engagement",
        })

    events.append({
        "date": now.strftime("%b %d, %Y"),
        "title": f"Scan #{scan_count} Recorded",
        "description": f"Current snapshot: {current_views:,} views • Score {trend_score_display}/100.",
        "type": "scan",
    })

    historical_context = {
        "1d": compute_historical_window_change(observations, current_views, now, 1),
        "7d": compute_historical_window_change(observations, current_views, now, 7),
        "30d": compute_historical_window_change(observations, current_views, now, 30),
        "90d": compute_historical_window_change(observations, current_views, now, 90),
    }

    forecast = generate_conservative_forecast(observations, current_views, velocity)

    return {
        "status": status,
        "scan_count": scan_count,
        "first_seen_at": first_seen_at.isoformat(),
        "last_seen_at": last_seen_at.isoformat(),
        "current_trend_score": trend_score,
        "current_trend_score_display": trend_score_display,
        "current_direction": direction,
        "current_direction_display": direction_display,
        "current_confidence": confidence,
        "velocity": velocity,
        "velocity_display": velocity_display,
        "acceleration": acceleration,
        "acceleration_display": acceleration_display,
        "educational_banner": educational_banner,
        "historical_context": historical_context,
        "timeline": timeline,
        "events": events,
        "forecast": forecast,
    }
