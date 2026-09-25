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


def test_chat_topic_detection_and_fallback(client, flask_mod):
    """Verify /api/chat automatically detects trending topic and calls fallback if groq fails."""
    # When Groq request fails, fallback is called
    with patch("backend.services.groq_service.requests.post", side_effect=Exception("API key unavailable")):
        res = client.post(
            "/api/chat",
            data=json.dumps({"message": 'Help me create a content strategy and viral video ideas for the trending topic: "free fire tips"'}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert "reply" in data
    reply = data["reply"]
    # Check 2026 year grounding and high-CTR structure
    assert "2026" in reply
    assert "CTR Strength" in reply
    assert "Hook" in reply
    assert "Thumbnail" in reply
    # Must never mention outdated year or fake characters
    assert "2024" not in reply
    assert "Zofia" not in reply
    assert "Raptor" not in reply


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


# --- 7. /api/video-analysis preserves description & success flag --------------

def test_video_analysis_preserves_description(client, flask_mod):
    """Verify /api/video-analysis preserves video description and success flag in response."""
    mock_result = {
        "video_id": "test_desc_1",
        "title": "GTA V Video",
        "channel_name": "XAshuX",
        "description": "#gta #gtav #gtavonline #song #karanaujla",
        "view_count": 1600000,
        "like_count": 6000,
        "comment_count": 42,
        "upload_date": "2025-03-22",
        "thumbnail": "https://example.com/thumb.jpg",
        "daily_metrics": [{"date": "2025-03-22", "views": 1600000, "likes": 6000, "shares": 0, "comments_count": 42}],
        "comments": ["Awesome edit!"],
    }

    with patch.object(flask_mod, "analyze_youtube_video", return_value=mock_result), \
         patch.object(flask_mod, "analyze_sentiment", return_value={"dominant_sentiment": "positive"}):

        res = client.post(
            "/api/video-analysis",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=5mHXWZLZVeE"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True, "Expected success: True in response"
    assert data.get("description") == "#gta #gtav #gtavonline #song #karanaujla"
    assert data.get("channel_title") == "XAshuX"
    assert data.get("views") == 1600000
    assert data.get("published_at") == "2025-03-22"
    assert "virality_score" in data
    assert "engagement_rate" in data


# --- 8. /api/video-analysis handles empty/missing description ------------------

def test_video_analysis_handles_empty_description(client, flask_mod):
    """Verify /api/video-analysis handles empty or None description safely."""
    mock_result = {
        "video_id": "test_empty_desc",
        "title": "No Desc Video",
        "channel_name": "Channel1",
        "description": "",
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 5,
        "upload_date": "2025-01-01",
        "thumbnail": "https://example.com/thumb.jpg",
        "daily_metrics": [],
        "comments": [],
    }

    with patch.object(flask_mod, "analyze_youtube_video", return_value=mock_result), \
         patch.object(flask_mod, "analyze_sentiment", return_value={"dominant_sentiment": "neutral"}):

        res = client.post(
            "/api/video-analysis",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=abc12345678"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True
    assert data.get("description") == ""


# --- 9. UTF-8 & Emoji encoding validation on video-analyzer.html -------------

def test_video_analyzer_html_utf8_and_description():
    """Verify video-analyzer.html contains correct UTF-8 emojis, no mojibake, and #videoDescription container."""
    html_path = REPO_ROOT / "frontend" / "tools" / "video-analyzer.html"
    assert html_path.exists(), "video-analyzer.html must exist"

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # UTF-8 charset declaration
    assert '<meta charset="UTF-8">' in html, "HTML must declare <meta charset='UTF-8'>"

    # Valid emoji verification
    assert "🎬" in html, "🎬 emoji must be present in HTML"
    assert "💬" in html, "💬 emoji must be present in HTML"
    assert "🏷️" in html, "🏷️ emoji must be present in HTML"
    assert "📝" in html, "📝 emoji must be present in HTML"

    # Zero mojibake verification
    mojibake_fragments = ["ðŸŽ¬", "ðŸ’¬", "ðŸ ·ï¸", "ðŸ“", "â€”", "âž”", "â€¦"]
    for m in mojibake_fragments:
        assert m not in html, f"Corrupted mojibake character '{m}' found in video-analyzer.html"

    # Description container verification
    assert 'id="videoDescription"' in html, "HTML must include element with id='videoDescription'"
    assert 'class="video-description-box"' in html, "HTML must style description with class 'video-description-box'"


# --- 10. Untruncated full description & special character preservation --------

def test_full_description_fetch_no_truncation(client, flask_mod):
    """Verify description is NOT truncated even if > 2500 chars, with emojis, line breaks, and URLs."""
    long_description = (
        "🔥 Official Music Video by Karan Aujla performing 'Softly'.\n\n"
        "Stream / Download:\n"
        "https://example.com/music/softly\n\n"
        "Connect with Karan Aujla:\n"
        "Instagram: https://instagram.com/karanaujla\n"
        "Twitter: https://twitter.com/karanaujla\n\n"
        "Lyrics & Credits:\n" + ("Song line with details & credits...\n" * 80) +
        "\n#KaranAujla #Softly #Trending #Music #PunjabiSong #GTA5"
    )
    assert len(long_description) > 2500, "Test payload must be > 2500 characters"

    mock_result = {
        "video_id": "long_desc_vid",
        "title": "GTA V | SOFTLY | KARAN AUJLA",
        "channel_name": "XAshuX",
        "description": long_description,
        "view_count": 1618854,
        "like_count": 6000,
        "comment_count": 42,
        "upload_date": "2025-03-22",
        "thumbnail": "https://example.com/thumb.jpg",
        "tags": ["gta", "gtav", "song", "karan aujla"],
        "daily_metrics": [{"date": "2025-03-22", "views": 1618854, "likes": 6000, "shares": 0, "comments_count": 42}],
        "comments": ["Great edit!"],
    }

    with patch.object(flask_mod, "analyze_youtube_video", return_value=mock_result), \
         patch.object(flask_mod, "analyze_sentiment", return_value={"dominant_sentiment": "positive"}):

        res = client.post(
            "/api/video-analysis",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=5mHXWZLZVeE"}),
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data.get("success") is True
    # Verify description is 100% complete with no truncation
    assert data.get("description") == long_description
    assert len(data.get("description")) == len(long_description)
    assert "🔥" in data.get("description")
    assert "\n\n" in data.get("description")
    assert "#GTA5" in data.get("description")
    assert "https://example.com/music/softly" in data.get("description")


# --- 11. HTML copy buttons present -------------------------------------------

def test_video_analyzer_html_contains_copy_buttons():
    """Verify video-analyzer.html contains Copy Title, Copy Description, and Copy Tags buttons."""
    html_path = REPO_ROOT / "frontend" / "tools" / "video-analyzer.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="copyTitleBtn"' in html, "copyTitleBtn must be present in HTML"
    assert 'Copy Title' in html, "Copy Title text must be present"

    assert 'id="copyDescBtn"' in html, "copyDescBtn must be present in HTML"
    assert 'Copy Description' in html, "Copy Description text must be present"

    assert 'id="copyTagsBtn"' in html, "copyTagsBtn must be present in HTML"
    assert 'Copy Tags' in html, "Copy Tags text must be present"


# --- 12. Frontend JS XSS safety and copy functions ----------------------------

def test_video_analyzer_js_xss_safety_and_clipboard():
    """Verify video-analyzer.js uses textContent for XSS protection and includes safe clipboard fallback."""
    js_path = REPO_ROOT / "frontend" / "js" / "tools" / "video-analyzer.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # XSS Protection: textContent used on videoDescription
    assert "videoDescription.textContent = decoded" in js or "videoDescription.textContent =" in js, (
        "videoDescription must use textContent for safe plain-text rendering with zero XSS"
    )

    # Clipboard functions and fallback
    assert "navigator.clipboard.writeText" in js, "Must use navigator.clipboard.writeText"
    assert "document.execCommand" in js, "Must provide fallback for older/non-secure contexts"

    # Tags formatting for clipboard
    assert 'join(", ")' in js, "Tags must be formatted as comma-separated list for clipboard"

    # Copied feedback
    assert '"Copied!"' in js, "Must give user temporary 'Copied!' feedback"


# --- 13. Competitor Audit Video Count & Clean Copy ---------------------------

def test_competitor_audit_video_count_and_clean_copy():
    """Verify competitor-audit.html has videoCountVal, tool-grid-4col, and no fake 28-day copy."""
    html_path = REPO_ROOT / "frontend" / "tools" / "competitor-audit.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="videoCountVal"' in html, "videoCountVal must be present in HTML"
    assert "Video Count" in html, "Video Count label must be present in HTML"
    assert "tool-grid-4col" in html, "tool-grid-4col class must be used for 4-card metric layout"
    assert "28-day" not in html, "competitor-audit.html must not contain misleading 28-day claims"

    js_path = REPO_ROOT / "frontend" / "js" / "tools" / "competitor-audit.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()
    assert "videoCountVal" in js, "competitor-audit.js must reference videoCountVal"
    assert "data.video_count" in js, "competitor-audit.js must populate from data.video_count"


# --- 14. Trend Analyzer First Scan & Plexudo CSV Branding ---------------------

def test_trend_analyzer_first_scan_and_csv_export_branding(client, flask_mod):
    """Verify trend-analyzer.js has 'First Scan' fallback and /api/export-csv produces Plexudo branding."""
    js_path = REPO_ROOT / "frontend" / "js" / "tools" / "trend-analyzer.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "First Scan" in js, "trend-analyzer.js must display 'First Scan' for single-point queries"

    # Test CSV export route for Plexudo branding
    # Mock a trend record or search to generate a trend_id
    mock_yt_raw = {
        "status": 200,
        "videos": [{"video_id": "test1", "title": "Test Gaming", "views": 10000, "likes": 500, "shares": 50, "comments": 25}],
        "daily_metrics": [{"date": "2026-09-13", "views": 10000, "likes": 500, "shares": 50, "comments_count": 25}],
        "tags": ["gaming"],
        "hashtags": ["#gaming"],
        "related_keywords": ["gaming"],
        "comments": ["Epic game!"],
    }
    mock_sentiment = {
        "dominant_sentiment": "positive",
        "positive_score": 80,
        "negative_score": 10,
        "neutral_score": 10,
        "sample_comment": "Epic game!",
    }

    with patch.object(flask_mod, "fetch_youtube_data", return_value=mock_yt_raw), \
         patch.object(flask_mod, "analyze_sentiment", return_value=mock_sentiment):
        search_res = client.post("/api/search", data=json.dumps({"keyword": "pytest-brand-test"}), content_type="application/json")

    assert search_res.status_code == 200
    s_data = search_res.get_json()
    trend_id = s_data.get("results", {}).get("YouTube", {}).get("trend_id")
    assert trend_id is not None, "Search should return a trend_id"

    csv_res = client.get(f"/api/export-csv/{trend_id}")
    assert csv_res.status_code == 200
    csv_text = csv_res.get_data(as_text=True)

    assert "Plexudo - YouTube Trend Analysis CSV Export" in csv_text, "CSV header must have Plexudo branding"
    assert "SMTAS" not in csv_text, "CSV must not contain legacy SMTAS branding"
    content_disp = csv_res.headers.get("Content-Disposition", "")
    assert "plexudo_" in content_disp, f"CSV filename must start with plexudo_, got: {content_disp}"


# --- 15. Video Analyzer Zero Tags Fallback ------------------------------------

def test_video_analyzer_zero_tags_fallback():
    """Verify video-analyzer.js displays friendly fallback when a video has zero tags."""
    js_path = REPO_ROOT / "frontend" / "js" / "tools" / "video-analyzer.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "No tags provided for this upload" in js, "video-analyzer.js must contain zero-tag fallback message"


# --- 16. Tools Hub Has Exactly 4 Tools ----------------------------------------

def test_tools_index_has_4_tools_only():
    """Verify tools/index.html contains exactly the 4 intended tools and no Keyword Tool."""
    html_path = REPO_ROOT / "frontend" / "tools" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "/tools/trend-analyzer" in html
    assert "/tools/video-analyzer" in html
    assert "/tools/competitor-audit" in html
    assert "/tools/ai-strategist" in html
    assert "/tools/keyword-tool" not in html
    assert "28-day" not in html, "tools/index.html must not contain misleading 28-day claims"


# --- 17. Trend Analyzer Search Only On Button / Enter (No Quota Drain On Input) ---

def test_trend_analyzer_search_only_on_button_or_enter():
    """Verify trend-analyzer.js does not auto-search while typing (prevents API quota burn)."""
    js_path = REPO_ROOT / "frontend" / "js" / "tools" / "trend-analyzer.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "searchDebounce" not in js, "trend-analyzer.js must not contain searchDebounce on input"
    assert "analyzeBtn" in js, "trend-analyzer.js must bind search to analyzeBtn"
    assert "fetchTrendingFeed();" in js, "trend-analyzer.js must run auto-scan once on initial page load"


# --- 18. Trend Analyzer Mobile Search Bar Layout (No Squished Input) -----------

def test_trend_analyzer_mobile_search_bar_layout():
    """Verify style.css keeps search input visible and button compact on mobile devices."""
    css_path = REPO_ROOT / "frontend" / "css" / "style.css"
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # The mobile 100% button rule must be scoped to .tool-input-row, not globally
    assert ".tool-input-row .tool-primary-btn" in css, "Mobile full-width button must be scoped to .tool-input-row"
    # pulsecheck-search-btn must have width: auto !important to prevent stretching across flex row
    assert ".pulsecheck-search-btn" in css
    assert "width: auto !important" in css
    # input must have min-width: 0 and flex: 1
    assert "min-width: 0" in css

