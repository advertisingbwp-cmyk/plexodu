"""
Phase 8 — YouTube Trend Intelligence Rebuild Tests
==================================================
Verifies the complete Trend Intelligence engine:
1. First scan establishes baseline (status='baseline', score/velocity='Pending', confidence='Low', educational banner)
2. Second+ scan calculates real velocity against prior baseline
3. Direction classification (RISING, FALLING, STABLE, BASELINE)
4. Acceleration calculation (current_velocity - prev_velocity)
5. Time-series moving averages smoothing
6. Trend score (0-100) multi-factor weighting
7. Confidence progression (Low < 7, Medium 7-29, High 30+)
8. Historical windows & 'insufficient_history' guards (1D, 7D, 30D, 90D)
9. Conservative 7-day forecast (activates only at 3+ observations, damped bounds)
10. Division-by-zero protection
11. Backward compatibility of /api/search response keys
12. Database migration schema integrity
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import inspect

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.trend_intelligence import (
    analyze_trend_intelligence,
    calculate_moving_averages,
    compute_trend_score,
    compute_historical_window_change,
    generate_conservative_forecast,
)


def get_flask_module():
    import importlib.util
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"]
    app_py_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    return flask_module


@pytest.fixture(scope="module")
def flask_mod():
    return get_flask_module()


@pytest.fixture(scope="module")
def client(flask_mod):
    app = flask_mod.app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class DummyTrend:
    def __init__(self, trend_id, total_views, timestamp, current_velocity=None, current_acceleration=None, current_trend_score=None, current_direction="STABLE", current_confidence="Low"):
        self.trend_id = trend_id
        self.total_views = total_views
        self.timestamp = timestamp
        self.last_seen_at = timestamp
        self.current_velocity = current_velocity
        self.current_acceleration = current_acceleration
        self.current_trend_score = current_trend_score
        self.current_direction = current_direction
        self.current_confidence = current_confidence


# --- 1. First scan establishes baseline ---------------------------------------

def test_first_scan_creates_baseline():
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    result = analyze_trend_intelligence(
        keyword="gaming podcast",
        platform_name="YouTube",
        current_views=150000,
        current_engagement=4.5,
        sentiment_result={"positive_score": 65.0, "dominant_sentiment": "positive"},
        past_trends=[],
        now=now,
    )

    assert result["status"] == "baseline"
    assert result["scan_count"] == 1
    assert result["current_direction"] == "BASELINE"
    assert result["current_direction_display"] == "Baseline Created"
    assert result["current_confidence"] == "Low"
    assert result["velocity"] is None
    assert result["velocity_display"] == "Pending"
    assert result["acceleration"] is None
    assert result["acceleration_display"] == "Pending"
    assert result["current_trend_score"] is None
    assert result["current_trend_score_display"] == "Pending"
    assert "Baseline observation established" in result["educational_banner"]
    assert result["historical_context"]["1d"]["status"] == "insufficient_history"
    assert result["historical_context"]["7d"]["status"] == "insufficient_history"
    assert result["historical_context"]["30d"]["status"] == "insufficient_history"
    assert result["historical_context"]["90d"]["status"] == "insufficient_history"
    assert result["forecast"]["available"] is False


# --- 2. Second scan calculates real velocity ----------------------------------

def test_second_scan_calculates_real_velocity():
    t1_time = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    past = [DummyTrend(trend_id=1, total_views=100000, timestamp=t1_time)]

    result = analyze_trend_intelligence(
        keyword="gaming podcast",
        platform_name="YouTube",
        current_views=120000,
        current_engagement=5.2,
        sentiment_result={"positive_score": 70.0, "dominant_sentiment": "positive"},
        past_trends=past,
        now=now,
    )

    assert result["status"] == "active"
    assert result["scan_count"] == 2
    assert result["velocity"] == 20.0
    assert result["velocity_display"] == "+20.0%"
    assert result["current_direction"] == "RISING"
    assert "Rising (+20.0%)" in result["current_direction_display"]
    assert result["current_trend_score"] is not None
    assert result["educational_banner"] == ""


# --- 3. Direction classification ----------------------------------------------

def test_direction_classification():
    t1_time = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    past = [DummyTrend(trend_id=1, total_views=100000, timestamp=t1_time)]

    # Rising (> +3%)
    res_rising = analyze_trend_intelligence("test", "YouTube", 110000, 5.0, {}, past, now)
    assert res_rising["current_direction"] == "RISING"

    # Falling (< -3%)
    res_falling = analyze_trend_intelligence("test", "YouTube", 90000, 5.0, {}, past, now)
    assert res_falling["current_direction"] == "FALLING"

    # Stable (-3% to +3%)
    res_stable = analyze_trend_intelligence("test", "YouTube", 101000, 5.0, {}, past, now)
    assert res_stable["current_direction"] == "STABLE"


# --- 4. Acceleration calculation ----------------------------------------------

def test_acceleration_calculation():
    t1 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    # Scan 1: 100k, Scan 2: 110k (vel=+10%), Scan 3: 132k (vel=20%)
    past = [
        DummyTrend(trend_id=1, total_views=100000, timestamp=t1, current_velocity=None),
        DummyTrend(trend_id=2, total_views=110000, timestamp=t2, current_velocity=10.0),
    ]

    result = analyze_trend_intelligence("test", "YouTube", 132000, 5.0, {}, past, now)
    assert result["velocity"] == 20.0
    assert result["acceleration"] == 10.0
    assert result["acceleration_display"] == "+10.0%"


# --- 5. Moving averages smoothing ---------------------------------------------

def test_moving_averages_smoothing():
    raw_points = [100.0, 200.0, 150.0, 300.0, 250.0]
    smoothed = calculate_moving_averages(raw_points, window_size=3)

    assert len(smoothed) == len(raw_points)
    assert smoothed[0] == 100.0
    assert smoothed[1] == 150.0  # (100 + 200) / 2
    assert smoothed[2] == 150.0  # (100 + 200 + 150) / 3
    assert smoothed[3] == round((200 + 150 + 300) / 3, 2)


# --- 6. Trend score (0-100) weighting and bounds ------------------------------

def test_trend_score_weighting_and_bounds():
    # Baseline returns 50.0 default
    assert compute_trend_score(None, None, 5.0, 1, "BASELINE", 50.0) == 50.0

    # Strong performance score
    high_score = compute_trend_score(
        velocity=25.0,
        acceleration=10.0,
        engagement_rate=8.5,
        scan_count=15,
        direction="RISING",
        positive_sentiment_score=85.0,
    )
    assert 70.0 <= high_score <= 99.0

    # Negative performance score
    low_score = compute_trend_score(
        velocity=-20.0,
        acceleration=-10.0,
        engagement_rate=1.0,
        scan_count=3,
        direction="FALLING",
        positive_sentiment_score=20.0,
    )
    assert 5.0 <= low_score <= 45.0


# --- 7. Confidence progression ------------------------------------------------

def test_confidence_progression():
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    # 4 scans -> Low (< 7)
    past_4 = [DummyTrend(i, 100000 + i * 1000, t0 + timedelta(days=i)) for i in range(3)]
    res_low = analyze_trend_intelligence("test", "YouTube", 105000, 5.0, {}, past_4, now)
    assert res_low["current_confidence"] == "Low"

    # 12 scans -> Medium (7 to 29)
    past_12 = [DummyTrend(i, 100000 + i * 1000, t0 + timedelta(days=i)) for i in range(11)]
    res_med = analyze_trend_intelligence("test", "YouTube", 115000, 5.0, {}, past_12, now)
    assert res_med["current_confidence"] == "Medium"

    # 32 scans -> High (30+)
    past_32 = [DummyTrend(i, 100000 + i * 1000, t0 + timedelta(days=i)) for i in range(31)]
    res_high = analyze_trend_intelligence("test", "YouTube", 135000, 5.0, {}, past_32, now)
    assert res_high["current_confidence"] == "High"


# --- 8. Historical windows & guards -------------------------------------------

def test_historical_windows_and_guards():
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    # Past scans 1 day ago and 8 days ago
    past = [
        DummyTrend(1, 80000, now - timedelta(days=8)),
        DummyTrend(2, 95000, now - timedelta(days=1)),
    ]

    res = analyze_trend_intelligence("test", "YouTube", 100000, 5.0, {}, past, now)
    hw = res["historical_context"]

    # 1D should be available
    assert hw["1d"]["status"] == "available"
    assert hw["1d"]["change_pct"] == round(((100000 - 95000) / 95000) * 100, 2)

    # 7D should be available (uses the 8-day old observation)
    assert hw["7d"]["status"] == "available"
    assert hw["7d"]["change_pct"] == round(((100000 - 80000) / 80000) * 100, 2)

    # 30D and 90D should guard as insufficient history
    assert hw["30d"]["status"] == "insufficient_history"
    assert hw["90d"]["status"] == "insufficient_history"


# --- 9. Conservative 7-day forecast -------------------------------------------

def test_conservative_forecast():
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    # 2 observations -> forecast not available
    past_2 = [DummyTrend(1, 100000, now - timedelta(days=2))]
    res_2 = analyze_trend_intelligence("test", "YouTube", 105000, 5.0, {}, past_2, now)
    assert res_2["forecast"]["available"] is False

    # 3+ observations -> forecast available with 7 projection days
    past_3 = [
        DummyTrend(1, 95000, now - timedelta(days=4)),
        DummyTrend(2, 100000, now - timedelta(days=2)),
    ]
    res_3 = analyze_trend_intelligence("test", "YouTube", 105000, 5.0, {}, past_3, now)
    fc = res_3["forecast"]
    assert fc["available"] is True
    assert len(fc["projection_days"]) == 7
    # Bounds check
    for day_proj in fc["projection_days"]:
        assert day_proj["lower_bound"] <= day_proj["expected_views"] <= day_proj["upper_bound"]


# --- 10. Division-by-zero protection ------------------------------------------

def test_division_by_zero_protection():
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    # Previous views = 0
    past = [DummyTrend(1, 0, now - timedelta(days=1))]
    res = analyze_trend_intelligence("test", "YouTube", 50000, 5.0, {}, past, now)
    assert res["velocity"] == 0.0
    assert res["status"] == "active"


# --- 11. Backward compatibility of /api/search response -----------------------

def test_api_search_phase8_contract(client, flask_mod):
    mock_yt_raw = {
        "status": 200,
        "title": "Top Tech Video",
        "comments": ["Great tech review!", "Really helpful tutorial.", "Not bad"],
        "daily_metrics": [
            {"date": "2026-09-09", "views": 10000, "likes": 500, "shares": 50, "comments_count": 25},
            {"date": "2026-09-10", "views": 12000, "likes": 600, "shares": 60, "comments_count": 30},
            {"date": "2026-09-11", "views": 14000, "likes": 700, "shares": 70, "comments_count": 35},
            {"date": "2026-09-12", "views": 16000, "likes": 800, "shares": 80, "comments_count": 40},
            {"date": "2026-09-13", "views": 18000, "likes": 900, "shares": 90, "comments_count": 45},
            {"date": "2026-09-14", "views": 20000, "likes": 1000, "shares": 100, "comments_count": 50},
            {"date": "2026-09-15", "views": 22000, "likes": 1100, "shares": 110, "comments_count": 55},
        ],
        "related_keywords": ["tech tips", "coding setup", "ai tools"],
    }

    with patch.object(flask_mod, "fetch_youtube_data", return_value=mock_yt_raw):
        res = client.post(
            "/api/search",
            data=json.dumps({"keyword": "modern web dev"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    body = res.get_json()
    assert "results" in body
    assert "YouTube" in body["results"]

    yt = body["results"]["YouTube"]
    # Existing backward-compatible keys
    assert "total_views" in yt
    assert "growth_rate" in yt
    assert "virality_score" in yt
    assert "daily_metrics" in yt
    assert "sentiment" in yt
    assert "youtube_tags" in yt
    assert "youtube_hashtags" in yt
    assert "seo_title_ideas" in yt

    # Phase 8 Trend Intelligence keys
    assert "trend_intelligence" in yt
    assert "status" in yt
    assert "scan_count" in yt
    assert "current_trend_score_display" in yt
    assert "velocity_display" in yt
    assert "current_direction" in yt
    assert "current_confidence" in yt
    assert "historical_context" in yt
    assert "timeline" in yt
    assert "events" in yt
    assert "forecast" in yt


# --- 12. Database migration schema integrity ----------------------------------

def test_database_migration_schema_integrity(flask_mod):
    app = flask_mod.app
    with app.app_context():
        inspector = inspect(flask_mod.db.engine)
        trend_cols = {c["name"] for c in inspector.get_columns("trends")}
        metric_cols = {c["name"] for c in inspector.get_columns("metrics")}

        required_trend_cols = {
            "trend_id", "keyword", "platform", "total_views", "first_seen_at",
            "last_seen_at", "scan_count", "current_trend_score", "current_direction",
            "current_confidence", "current_velocity", "current_acceleration"
        }
        for col in required_trend_cols:
            assert col in trend_cols, f"Missing column {col} in trends table"

        required_metric_cols = {
            "id", "trend_id", "views", "likes", "shares", "comments_count",
            "recorded_date", "captured_at", "engagement_rate", "source"
        }
        for col in required_metric_cols:
            assert col in metric_cols, f"Missing column {col} in metrics table"
