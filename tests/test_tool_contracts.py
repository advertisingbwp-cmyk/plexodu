"""
Tool Contract Tests
===================
Verifies that each tool API endpoint returns the exact response keys the frontend
JavaScript expects, after the normalization fixes applied in this release.

Tests:
1. /api/chat returns 'reply' key (mocked Groq)
2. /api/video-analysis response has normalized channel_title, views, published_at keys
3. /api/audit-channel response has normalized title, subscribers, channel_age_years,
   est_monthly_earnings_min keys
4. /api/search with keyword returns results.YouTube with non-error
5. /api/audit-log returns 404 (removed from public API)
6. /api/suggest?q=minecraft returns suggestions list
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


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


# --- 1. /api/chat returns 'reply' key ----------------------------------------

def test_chat_returns_reply_key(client, flask_mod):
    """Verify /api/chat response contains 'reply' key that ai-strategist.js reads."""
    mock_result = {"reply": "Here is your strategy!", "model": "llama-3.3-70b-versatile"}

    with patch.object(flask_mod, "chat_with_groq", return_value=mock_result):
        res = client.post(
            "/api/chat",
            data=json.dumps({"message": "Give me a YouTube strategy"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert "reply" in data, f"Expected 'reply' key in response, got: {list(data.keys())}"
    assert data["reply"] == "Here is your strategy!"


# --- 2. /api/video-analysis normalizes channel_title, views, published_at ----

def test_video_analysis_normalized_keys(client, flask_mod):
    """Verify /api/video-analysis response has normalized channel_title, views, published_at."""
    mock_video_result = {
        "video_id": "abc12345678",
        "title": "Test Video",
        "channel_name": "Test Channel",
        "view_count": 500000,
        "like_count": 20000,
        "comment_count": 500,
        "upload_date": "2024-01-15",
        "thumbnail": "https://img.youtube.com/vi/abc12345678/mqdefault.jpg",
        "tags": ["test", "video"],
        "comments": ["Great video!"],
        "daily_metrics": [{"date": "2024-01-15", "views": 500000, "likes": 20000, "shares": 0, "comments_count": 500}],
    }
    mock_sentiment = {
        "dominant_sentiment": "positive",
        "positive_score": 75,
        "negative_score": 10,
        "neutral_score": 15,
        "sample_comment": "Great video!",
    }

    with patch.object(flask_mod, "analyze_youtube_video", return_value=mock_video_result), \
         patch.object(flask_mod, "analyze_sentiment", return_value=mock_sentiment):

        res = client.post(
            "/api/video-analysis",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=abc12345678"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()

    assert "channel_title" in data, f"'channel_title' missing from response keys: {list(data.keys())}"
    assert data["channel_title"] == "Test Channel"

    assert "views" in data, f"'views' missing from response keys: {list(data.keys())}"
    assert data["views"] == 500000

    assert "published_at" in data, f"'published_at' missing from response keys: {list(data.keys())}"
    assert data["published_at"] == "2024-01-15"

    assert "virality_score" in data, f"'virality_score' missing from response keys: {list(data.keys())}"
    assert data["virality_score"] > 0


# --- 3. /api/audit-channel normalizes title, subscribers, earnings -----------

def test_audit_channel_normalized_keys(client, flask_mod):
    """Verify /api/audit-channel response has normalized title, subscribers, channel_age_years, earnings."""
    mock_audit_result = {
        "channel_name": "Creator Pro",
        "subscriber_count": 250000,
        "total_views": 10000000,
        "age_years": 3,
        "earn_min_monthly": 500,
        "earn_max_monthly": 2000,
        "avatar_url": "https://example.com/avatar.jpg",
        "top_videos": [],
    }

    with patch.object(flask_mod, "audit_youtube_channel", return_value=mock_audit_result):
        res = client.post(
            "/api/audit-channel",
            data=json.dumps({"identifier": "@CreatorPro"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()

    assert "title" in data, f"'title' missing from response keys: {list(data.keys())}"
    assert data["title"] == "Creator Pro"

    assert "subscribers" in data, f"'subscribers' missing from response keys: {list(data.keys())}"
    assert data["subscribers"] == 250000

    assert "channel_age_years" in data, f"'channel_age_years' missing from response keys: {list(data.keys())}"
    assert data["channel_age_years"] == 3

    assert "est_monthly_earnings_min" in data, f"'est_monthly_earnings_min' missing from response keys: {list(data.keys())}"
    assert data["est_monthly_earnings_min"] == 500

    assert "est_monthly_earnings_max" in data, f"'est_monthly_earnings_max' missing from response keys: {list(data.keys())}"
    assert data["est_monthly_earnings_max"] == 2000


# --- 4. /api/search with keyword returns results.YouTube ---------------------

def test_search_with_keyword_returns_youtube(client, flask_mod):
    """Verify /api/search with a keyword body returns results.YouTube with non-error data."""
    mock_yt_data = {
        "status": 200,
        "keyword": "minecraft",
        "platform": "YouTube",
        "total_views": 9500000,
        "daily_metrics": [{"date": "2024-01-15", "views": 9500000, "likes": 300000, "shares": 0, "comments_count": 5000}],
        "comments": ["Awesome build tutorial!"],
        "related_keywords": ["minecraft survival", "minecraft builds"],
    }

    with patch.object(flask_mod, "fetch_youtube_data", return_value=mock_yt_data):
        res = client.post(
            "/api/search",
            data=json.dumps({"keyword": "minecraft"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert "results" in data, f"Expected 'results' key, got: {list(data.keys())}"
    assert "YouTube" in data["results"], f"Expected 'YouTube' in results, got: {list(data['results'].keys())}"
    yt = data["results"]["YouTube"]
    assert not yt.get("error"), f"YouTube result has error: {yt}"
    assert yt.get("total_views", 0) > 0


# --- 5. /api/audit-log returns 404 (removed) ---------------------------------

def test_audit_log_returns_404(client):
    """Verify /api/audit-log is no longer publicly accessible (security fix)."""
    res = client.get("/api/audit-log")
    assert res.status_code == 404, (
        f"Expected 404 for removed /api/audit-log, got {res.status_code}. "
        "This endpoint was removed to prevent IP address exposure."
    )


# --- 6. /api/suggest?q=minecraft returns suggestions list --------------------

def test_suggest_returns_list(client, flask_mod):
    """Verify /api/suggest with a valid query returns a list of suggestions."""
    mock_suggestions = ["minecraft survival", "minecraft builds", "minecraft tutorial"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"snippet": {"title": s}} for s in mock_suggestions
        ]
    }

    with patch.object(flask_mod, "YOUTUBE_API_KEY", "fake-key"), \
         patch.object(flask_mod._requests, "get", return_value=mock_response):

        res = client.get("/api/suggest?q=minecraft_test_query")

    assert res.status_code == 200
    data = res.get_json()
    assert "suggestions" in data, f"Expected 'suggestions' key, got: {list(data.keys())}"
    assert isinstance(data["suggestions"], list), "suggestions must be a list"
