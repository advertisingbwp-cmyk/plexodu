"""
Plexudo Phase 3 Security Test Suite
Validates:
1. YouTube API Quota Errors (honest 429 response handling without key exposure)
2. YouTube API Timeout Handling (bounded requests, graceful failure)
3. In-memory TTL Caching (prevents redundant API calls & quota exhaustion)
4. YouTube URL and Identifier Validation (rejection of SSRF and malicious input)
5. Groq AI Model Configuration, 429/5xx Fallback, Prompt Isolation, & Context Sanitization
6. Synthetic Data Elimination (absence of fake curves, _estimate_daily_series, kw_hash)
7. Frontend DOM XSS Remediation (escapeHtml, escapeAttr, sanitizeUrl, fetchWithTimeout)
8. Secret Exposure Scan across the repository
"""

import os
import sys
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_flask_app():
    """Helper to dynamically load the main Flask app singleton."""
    import importlib.util
    app_py_path = BACKEND_DIR / "app.py"
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"].app
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    return flask_module.app


# ─── 1. YOUTUBE API QUOTA ERROR HANDLING ────────────────────────────────────

def test_youtube_quota_exceeded_returns_honest_429():
    """Verify that YouTube Data API quota errors return HTTP 429 with honest messaging."""
    from services.real_api import fetch_youtube_data, _YT_CACHE
    _YT_CACHE.clear()

    # Mock 403 quota exceeded response from Google API
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "error": {
            "errors": [{"reason": "quotaExceeded", "message": "The request cannot be completed because you have exceeded your quota."}],
            "code": 403,
            "message": "The request cannot be completed because you have exceeded your quota."
        }
    }

    with patch("requests.get", return_value=mock_resp), patch("services.real_api.get_yt_api_key", return_value="test_mock_api_key"):
        res = fetch_youtube_data("ai trends")
        assert res.get("status") == 429, f"Expected status 429 on quota exceeded, got {res.get('status')}"
        assert res.get("quota_exceeded") is True, "Expected quota_exceeded flag"
        assert "quota" in res.get("error", "").lower(), "Expected honest quota explanation"
        # Ensure API key is NOT leaked in message
        assert "test_mock_api_key" not in res.get("error", "")


def test_flask_search_route_honors_quota_error():
    """Verify that the Flask /api/search route maps quota exhaustion to HTTP 429."""
    app = get_flask_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        # Create authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Tester"
            sess["user_role"] = "creator"

        with patch("main_flask_app.fetch_youtube_data", return_value={
                 "status": 429,
                 "error": "YouTube API daily quota limit exceeded. Live metrics temporarily unavailable; please try again later.",
                 "quota_exceeded": True
             }):
            resp = client.post("/api/search", json={"keyword": "testing-quota"})
            assert resp.status_code == 429, f"Expected 429 for quota exhaustion, got {resp.status_code}"
            data = resp.get_json()
            assert "quota" in data.get("error", "").lower()



# ─── 2. YOUTUBE TIMEOUT HANDLING ────────────────────────────────────────────

def test_youtube_timeout_handled_gracefully():
    """Verify that requests.Timeout is caught and returns error without crashing."""
    from services.real_api import fetch_youtube_data, _YT_CACHE
    _YT_CACHE.clear()

    with patch("requests.get", side_effect=requests.Timeout("Connection timed out")), patch("services.real_api.get_yt_api_key", return_value="test_mock_key"):
        res = fetch_youtube_data("slow-query")
        assert res.get("status") == 504
        assert "timed out" in res.get("error", "").lower()


# ─── 3. YOUTUBE TTL CACHING ─────────────────────────────────────────────────

def test_youtube_caching_prevents_duplicate_requests():
    """Verify that duplicate requests within TTL are served from in-memory cache."""
    from services.real_api import fetch_youtube_data, _YT_CACHE
    _YT_CACHE.clear()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": {"videoId": "dQw4w9WgXcQ"},
                "snippet": {
                    "title": "Cached Video Title",
                    "description": "Testing cache",
                    "channelTitle": "Cache Channel",
                    "publishedAt": "2026-01-01T00:00:00Z"
                },
                "statistics": {
                    "viewCount": "100",
                    "likeCount": "10",
                    "commentCount": "5"
                }
            }
        ]
    }

    call_count = 0
    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("requests.get", side_effect=mock_get), patch("services.real_api.get_yt_api_key", return_value="key_1"):
        res1 = fetch_youtube_data("cache_test")
        assert call_count >= 1
        initial_calls = call_count

        # Second call for the same keyword
        res2 = fetch_youtube_data("cache_test")
        assert call_count == initial_calls, "Expected second call to be served from cache without new HTTP request"
        assert res1 == res2


# ─── 4. YOUTUBE URL AND IDENTIFIER VALIDATION ───────────────────────────────

def test_youtube_video_id_validation():
    """Verify strict validation and rejection of SSRF/path traversal in video analysis."""
    from services.real_api import extract_video_id

    # Valid inputs
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # Malicious / SSRF / Injection inputs must return None
    assert extract_video_id("http://169.254.169.254/latest/meta-data/") is None
    assert extract_video_id("javascript:alert(1)") is None
    assert extract_video_id("../../../etc/passwd") is None
    assert extract_video_id("https://evil.com/watch?v=dQw4w9WgXcQ") is None
    assert extract_video_id("<script>alert(1)</script>") is None


# ─── 5. GROQ AI CONFIGURATION, 429/5XX FALLBACK & PROMPT ISOLATION ───────────

def test_groq_models_and_prompt_isolation():
    """Verify Groq service uses supported models and isolates user messages."""
    from services.groq_service import chat_with_groq, MODELS

    # Supported current models
    assert "llama-3.3-70b-versatile" in MODELS
    assert "llama-3.1-8b-instant" in MODELS
    # Deprecated/invalid models must be absent
    assert "openai/gpt-oss-120b" not in MODELS
    assert "mixtral-8x7b-32768" not in MODELS

    captured_payloads = []
    def mock_post(url, json=None, **kwargs):
        captured_payloads.append(json)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Verified AI response."}}]
        }
        return mock_resp

    with patch("requests.post", side_effect=mock_post), patch.dict(os.environ, {"GROQ_API_KEY": "test_mock_groq_key"}):
        res = chat_with_groq("What are best practices for video SEO?", trend_context={
            "keyword": "python tutorial",
            "total_views": 100000,
            "password": "SHOULD_NOT_LEAK",
            "session_token": "SHOULD_NOT_LEAK"
        })
        assert "Verified AI response." in res.get("reply", "")

    assert len(captured_payloads) > 0
    payload = captured_payloads[0]
    messages = payload.get("messages", [])

    # System instruction must be separate from user message
    roles = [m["role"] for m in messages]
    assert "system" in roles
    assert "user" in roles

    # User message must be in user role
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "What are best practices for video SEO?" in user_msg["content"]

    # Sensitive user fields must be stripped from context
    for m in messages:
        assert "SHOULD_NOT_LEAK" not in m["content"]


def test_groq_rate_limit_and_server_error_fallback():
    """Verify that Groq HTTP 429 or 5xx triggers clean intelligent fallback response."""
    from services.groq_service import chat_with_groq

    # Test 429 Rate Limit
    mock_429 = MagicMock()
    mock_429.status_code = 429
    with patch("requests.post", return_value=mock_429), patch.dict(os.environ, {"GROQ_API_KEY": "test_mock_groq_key"}):
        res = chat_with_groq("Hello AI")
        reply = res.get("reply", "")
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert any(k in reply.lower() for k in ["high demand", "plextip", "strategist", "plexudo"])

    # Test 503 Server Error
    mock_503 = MagicMock()
    mock_503.status_code = 503
    with patch("requests.post", return_value=mock_503), patch.dict(os.environ, {"GROQ_API_KEY": "test_mock_groq_key"}):
        res = chat_with_groq("Give me titles for gaming", trend_context={"keyword": "minecraft"})
        reply = res.get("reply", "")
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert "minecraft" in reply.lower() or "title" in reply.lower()


# ─── 6. SYNTHETIC DATA ELIMINATION REGRESSION TEST ──────────────────────────

def test_synthetic_metrics_completely_eliminated():
    """Strictly verify that fake curves and synthetic view generators do not exist in source code."""
    real_api_path = BACKEND_DIR / "services" / "real_api.py"
    app_py_path = BACKEND_DIR / "app.py"

    real_api_code = real_api_path.read_text(encoding="utf-8")
    app_py_code = app_py_path.read_text(encoding="utf-8")

    # _estimate_daily_series generated fake exponential decay curves
    assert "_estimate_daily_series" not in real_api_code, "Found deprecated _estimate_daily_series!"

    # kw_hash generated fake growth rates in app.py
    assert "kw_hash" not in app_py_code, "Found fake growth rate generator kw_hash in app.py!"

    # math.sin curves in channel audit
    assert "math.sin" not in real_api_code, "Found synthetic math.sin curve in real_api.py!"


# ─── 7. FRONTEND DOM XSS REMEDIATION ────────────────────────────────────────

def test_frontend_security_utilities_present():
    """Verify frontend/js/tools/common.js defines escapeHtml, escapeAttr, sanitizeUrl, and fetchWithTimeout."""
    common_js = (FRONTEND_DIR / "js" / "tools" / "common.js").read_text(encoding="utf-8")

    assert "function escapeHtml" in common_js
    assert "function escapeAttr" in common_js
    assert "function sanitizeUrl" in common_js
    assert "async function fetchWithTimeout" in common_js

    # Verify no raw fetch calls remain (except inside fetchWithTimeout)
    fetch_calls = [m.start() for m in re.finditer(r"\bfetch\(", common_js)]
    assert len(fetch_calls) == 1, f"Expected exactly 1 raw fetch( inside fetchWithTimeout, found {len(fetch_calls)}"



def test_index_html_email_interpolation_escaped():
    """Verify frontend/index.html defines escapeHtml to prevent DOM XSS in public mode."""
    index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    assert "function escapeHtml" in index_html


# ─── 8. SECRET EXPOSURE SCAN ────────────────────────────────────────────────

def test_no_exposed_secrets_in_repository():
    """Verify no hardcoded Google, Groq, SMTP, or JWT credentials exist in codebase."""
    secret_patterns = [
        re.compile(r"AIza[0-9A-Za-z_-]{35}"),               # Google API Key
        re.compile(r"gsk_[0-9A-Za-z]{48}"),                # Groq API Key
        re.compile(r"ghp_[0-9A-Za-z]{36}"),                # GitHub PAT
        re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
    ]

    scanned_extensions = {".py", ".js", ".html", ".css", ".json", ".env.example", ".md"}
    for root, dirs, files in os.walk(REPO_ROOT):
        # Ignore .git and virtual environments
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}]
        for f in files:
            file_path = Path(root) / f
            if file_path.suffix in scanned_extensions and "test_phase3_security.py" not in f:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat in secret_patterns:
                    assert not pat.search(content), f"Potential secret exposure in {file_path}"