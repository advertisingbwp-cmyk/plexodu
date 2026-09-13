"""
Phase 3 — Anonymous Public API Abuse Protection & Security Tests
================================================================
Verifies:
1. Anonymous API requests succeed without requiring authentication.
2. Invalid inputs (keywords, URLs, channel identifiers) are rejected with HTTP 400.
3. Rate limits are strictly enforced across public endpoints (returns HTTP 429).
4. External timeouts (YouTube and Groq) are handled gracefully (504 or fallback).
5. Quota exhaustion returns honest HTTP 429 without exposing API keys.
6. Secrets (YouTube, Groq, Google, SMTP) are never leaked in response payloads.
7. CORS wildcard is not enabled with credentials.
8. No internal exception details, tracebacks, or filesystem paths leak in errors.
9. Malformed requests return clean JSON HTTP 400.
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_flask_app():
    import importlib.util
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"].app
    app_py_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    return flask_module.app


# ─── 1. ANONYMOUS REQUEST SUCCESS ─────────────────────────────────────────────

def test_anonymous_api_requests_succeed():
    """Verify core endpoints work without login or user sessions."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Public session
        res = client.get("/api/session")
        assert res.status_code == 200
        assert res.get_json()["public_mode"] is True

        # Public trends
        res = client.get("/api/trends")
        assert res.status_code == 200
        assert "trends" in res.get_json()

        # Public keyword comparison
        res = client.get("/api/compare-keywords")
        assert res.status_code == 200
        assert "comparison" in res.get_json()


# ─── 2. INVALID INPUT REJECTION ───────────────────────────────────────────────

def test_invalid_keyword_input_rejected():
    """Verify empty, oversized, or control-character keywords return HTTP 400."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Empty keyword
        res = client.post("/api/search", json={"keyword": "   "})
        assert res.status_code == 400
        assert "error" in res.get_json()

        # Oversized keyword (> 100 chars)
        res = client.post("/api/search", json={"keyword": "a" * 105})
        assert res.status_code == 400
        assert "error" in res.get_json()

        # Control characters
        res = client.post("/api/search", json={"keyword": "test\x00malicious"})
        assert res.status_code == 400
        assert "error" in res.get_json()


def test_invalid_youtube_url_rejected():
    """Verify non-YouTube URLs or SSRF payloads are rejected with HTTP 400."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Malicious SSRF URL
        res = client.post("/api/video-analysis", json={"url": "http://169.254.169.254/latest/meta-data/"})
        assert res.status_code == 400
        assert "error" in res.get_json()

        # Phishing / foreign domain
        res = client.post("/api/video-analysis", json={"url": "https://evil-site.com/watch?v=dQw4w9WgXcQ"})
        assert res.status_code == 400
        assert "error" in res.get_json()


def test_invalid_channel_identifier_rejected():
    """Verify invalid channel identifiers are rejected with HTTP 400."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Empty identifier
        res = client.post("/api/audit-channel", json={"identifier": ""})
        assert res.status_code == 400
        assert "error" in res.get_json()

        # Identifier with control / injection characters
        res = client.post("/api/audit-channel", json={"identifier": "<script>alert(1)</script>"})
        assert res.status_code == 400
        assert "error" in res.get_json()


# ─── 3. RATE LIMITING ENFORCEMENT ─────────────────────────────────────────────

def test_rate_limiting_enforced_on_search():
    """Verify rate limiter blocks excessive requests with HTTP 429."""
    app = get_flask_app()
    app.config["TESTING"] = True
    from services.security_guard import rate_limiter

    test_ip = "192.168.1.99"
    # Exhaust search limit for test_ip
    for _ in range(105):
        allowed, _ = rate_limiter.is_allowed(f"search_ip_{test_ip}", 100, 60)

    with app.test_client() as client:
        res = client.post("/api/search", json={"keyword": "python"}, environ_overrides={"REMOTE_ADDR": test_ip})
        assert res.status_code == 429
        assert "rate limit" in res.get_json().get("error", "").lower()


def test_rate_limiting_enforced_on_reports():
    """Verify rate limiter protects expensive PDF report generation."""
    app = get_flask_app()
    app.config["TESTING"] = True
    from services.security_guard import rate_limiter

    test_ip = "192.168.1.100"
    for _ in range(35):
        rate_limiter.is_allowed(f"report_ip_{test_ip}", 30, 60)

    with app.test_client() as client:
        res = client.get("/api/report/1", environ_overrides={"REMOTE_ADDR": test_ip})
        assert res.status_code == 429
        assert "rate limit" in res.get_json().get("error", "").lower()


# ─── 4. EXTERNAL TIMEOUT & QUOTA ERROR HANDLING ───────────────────────────────

def test_youtube_timeout_returns_safe_json():
    """Verify YouTube timeout does not crash the server and returns safe JSON."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("main_flask_app.fetch_youtube_data", return_value={"status": 504, "error": "YouTube API request timed out."}):
            res = client.post("/api/search", json={"keyword": "timeout-test"})
            assert res.status_code == 200  # returns search envelope with error status inside results
            data = res.get_json()
            assert "YouTube" in data.get("results", {})
            assert data["results"]["YouTube"].get("status") == 504


def test_groq_timeout_handled_with_fallback():
    """Verify Groq timeout triggers intelligent fallback without crashing."""
    from services.groq_service import chat_with_groq
    with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
        res = chat_with_groq("How to optimize tags?", trend_context=None)
        assert res.get("error") is False
        assert "reply" in res
        assert len(res["reply"]) > 0


def test_youtube_quota_returns_429_json():
    """Verify quota exhaustion returns HTTP 429 with honest message."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("main_flask_app.fetch_youtube_data", return_value={
            "status": 429,
            "error": "YouTube API daily quota reached. Please try again later.",
            "quota_exceeded": True
        }):
            res = client.post("/api/search", json={"keyword": "quota-test"})
            assert res.status_code == 429
            data = res.get_json()
            assert data.get("quota_exceeded") is True
            assert "quota" in data.get("error", "").lower()


# ─── 5. SECRETS LEAKAGE PROTECTION ────────────────────────────────────────────

def test_api_keys_and_secrets_absent_from_responses():
    """Verify secrets are never present in response JSON bodies."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/api/session")
        body_text = res.get_data(as_text=True)
        assert "AIzaSy" not in body_text
        assert "gsk_" not in body_text
        assert "SECRET_KEY" not in body_text

        res_suggest = client.get("/api/suggest?q=gaming")
        assert "AIzaSy" not in res_suggest.get_data(as_text=True)


# ─── 6. CORS & INFO LEAKAGE PROTECTION ────────────────────────────────────────

def test_cors_wildcard_not_enabled():
    """Verify CORS does not expose open wildcard with credentials."""
    app_src = (BACKEND_DIR / "app.py").read_text(encoding="utf-8")
    assert "CORS(app, supports_credentials=True, origins='*')" not in app_src
    assert "CORS(app, supports_credentials=True)" not in app_src
    assert "origins=_CORS_ORIGINS" in app_src or "origins=" in app_src


def test_no_internal_exception_details_leak():
    """Verify 500 error returns safe generic message and never leaks tracebacks."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("main_flask_app.fetch_youtube_data", side_effect=RuntimeError("Secret internal database crash at /var/app/db")):
            res = client.post("/api/search", json={"keyword": "error-test"})
            data = res.get_json()
            assert "Secret internal database crash" not in str(data)
            assert "/var/app/db" not in str(data)
            assert "Traceback" not in str(data)


def test_malformed_json_returns_clean_400():
    """Verify malformed JSON requests receive a clean JSON 400 error instead of HTML."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.post(
            "/api/search",
            data="not-valid-json{{{",
            content_type="application/json"
        )
        assert res.status_code == 400
        assert res.is_json
        assert "error" in res.get_json()
