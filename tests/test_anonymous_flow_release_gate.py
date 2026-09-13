"""
Final No-Login Release Gate — Comprehensive Anonymous User Flow Tests
===================================================================
Tests all acceptance criteria:
- AUTH: No login/register/logout/pw-reset/email-verify/Google OAuth required for any tool
- DATABASE: Anonymous DB persistence (user_id=None), no auth columns, no token stores, no credit races
- API: Anonymous requests, IP rate limits, input validation, quota/timeout handling, CORS, secret isolation
- FRONTEND: Zero auth UI/scripts, direct tool access, XSS sanitizers present
- SEO: Indexable homepage, protected dashboard, valid sitemap/robots, canonical tags
- SECURITY: Zero hardcoded secrets, no auth remnants, no unauthorized private-data endpoints
"""

import os
import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
import importlib.util

# Setup environment for test mode before importing app
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-12345"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_flask_module():
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"]
    app_py_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = mod
    spec.loader.exec_module(mod)
    return mod


flask_mod = get_flask_module()
app = flask_mod.app
db = flask_mod.db
from models import User, Trend, Report, AuditLog
from services.security_guard import rate_limiter


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
            if hasattr(rate_limiter, "requests"):
                rate_limiter.requests.clear()
            yield c
            db.session.remove()
            db.drop_all()


# =============================================================================
# 1. AUTH ACCEPTANCE CRITERIA
# =============================================================================
class TestAuthAcceptance:
    """Verify zero login, registration, password reset, or OAuth requirements."""

    def test_no_login_required_for_public_api_endpoints(self, client):
        """Purged auth endpoints return 404, while public tool endpoints succeed anonymously."""
        purged_endpoints = [
            ("/api/session", "get", None),
            ("/api/login", "post", {"email": "any@example.com"}),
            ("/api/register", "post", {"email": "any@example.com"}),
            ("/api/logout", "post", {}),
        ]
        for ep, method, payload in purged_endpoints:
            func = getattr(client, method)
            resp = func(ep, json=payload or {})
            assert resp.status_code in (404, 405), f"{ep} expected 404/405 (purged), got {resp.status_code}"


        # Public endpoints work without credentials
        resp_trends = client.get("/api/trends")
        assert resp_trends.status_code == 200
        resp_comp = client.get("/api/compare-keywords")
        assert resp_comp.status_code == 200

    def test_no_google_oauth_dependency_in_config(self):
        """Backend config must have no Google OAuth client configuration attributes."""
        from app.core.config import settings
        assert not hasattr(settings, "GOOGLE_CLIENT_ID")
        assert not hasattr(settings, "GOOGLE_CLIENT_SECRET")
        assert not hasattr(settings, "GOOGLE_REDIRECT_URI")
        assert not hasattr(settings, "YOUTUBE_CALLBACK_URL")

    def test_no_auth_routes_in_flask_rules(self):
        """There must be no active password reset or email verification routes."""
        active_routes = [rule.rule for rule in app.url_map.iter_rules()]
        forbidden_endpoints = [
            "/api/auth/reset-password",
            "/api/auth/forgot-password",
            "/api/auth/verify-email",
            "/api/auth/send-verification",
            "/api/auth/google",
            "/api/auth/google/callback",
        ]
        for forbidden in forbidden_endpoints:
            assert forbidden not in active_routes, f"Forbidden auth route '{forbidden}' is active"


# =============================================================================
# 2. DATABASE ACCEPTANCE CRITERIA
# =============================================================================
class TestDatabaseAcceptance:
    """Verify clean database architecture without authentication dependencies."""

    def test_user_table_columns_have_no_auth_fields(self):
        """User model must not include password_hash, google_id, credits, etc."""
        columns = [c.name for c in User.__table__.columns]
        auth_fields = [
            "password_hash", "google_id", "login_attempts",
            "is_locked", "email_verified", "credits"
        ]
        for field in auth_fields:
            assert field not in columns, f"Auth field '{field}' still in User model"

    def test_anonymous_database_persistence_with_none_user(self, client):
        """DB writes succeed without requiring an authenticated user ID."""
        with app.app_context():
            trend = Trend(
                keyword="AI Automation",
                platform="YouTube",
                total_views=50000,
                growth_rate=45.2,
                virality_score=88.5,
                created_by=None
            )
            db.session.add(trend)
            db.session.commit()
            assert trend.trend_id is not None
            assert trend.created_by is None

            report = Report(
                trend_id=trend.trend_id,
                generated_by=None,
                format="PDF",
                file_path="/tmp/test.pdf"
            )
            db.session.add(report)
            db.session.commit()
            assert report.report_id is not None
            assert report.generated_by is None

    def test_zero_credit_race_conditions_or_credit_tables(self):
        """Credits tables or credit decrement logic must not exist."""
        table_names = db.metadata.tables.keys()
        assert "credits" not in table_names
        assert "user_credits" not in table_names


# =============================================================================
# 3. API ACCEPTANCE CRITERIA
# =============================================================================
class TestApiAcceptance:
    """Verify anonymous access, rate limiting, validation, error handling, CORS."""

    def test_anonymous_trend_search_succeeds(self, client):
        """Anonymous user can search trends without credentials."""
        mock_resp = {
            "status": 200,
            "videos": [{"video_id": "vid123", "title": "Test Video", "views": 1000}],
            "total_views": 1000,
            "average_views": 1000,
            "tags": ["seo", "video"],
            "daily_metrics": [
                {"date": "2026-09-01", "views": 100, "likes": 10, "shares": 2, "comments_count": 5},
                {"date": "2026-09-02", "views": 200, "likes": 20, "shares": 4, "comments_count": 8},
            ],
            "comments": ["Great tutorial on YouTube SEO! Very helpful.", "Loved the tags guide."],
            "related_keywords": ["python beginner", "learn python"],
            "title": "Python Tutorial 2026",
        }
        with patch.object(flask_mod, "fetch_youtube_data", return_value=mock_resp):
            resp = client.post("/api/search", json={"keyword": "python tutorial"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["keyword"] == "python tutorial"
            assert "YouTube" in data["results"]

    def test_ip_rate_limiting_enforced(self, client):
        """Anonymous rate limiter blocks excessive requests by client IP."""
        for _ in range(100):
            rate_limiter.is_allowed("search_ip_192.168.1.100", 100, 60)
        
        allowed, retry_after = rate_limiter.is_allowed("search_ip_192.168.1.100", 100, 60)
        assert not allowed
        assert retry_after > 0

    def test_validation_rejects_malformed_input(self, client):
        """Invalid or malicious inputs must return 400 with safe JSON errors."""
        resp = client.post("/api/search", json={"keyword": "x" * 200})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

        resp = client.post("/api/search", data="")
        assert resp.status_code == 400

    def test_youtube_quota_exceeded_handled_gracefully(self, client):
        """429 quota exceeded returns graceful user message, not 500 crash."""
        quota_err = {
            "status": 429,
            "error": "YouTube API daily quota reached. Please try again later.",
            "quota_exceeded": True
        }
        with patch.object(flask_mod, "fetch_youtube_data", return_value=quota_err):
            resp = client.post("/api/search", json={"keyword": "trending tech"})
            assert resp.status_code == 429
            data = resp.get_json()
            assert data["quota_exceeded"] is True
            assert "quota" in data["error"].lower()

    def test_groq_ai_error_handled_gracefully(self):
        """Groq failure triggers intelligent fallback without crashing or leaking keys."""
        from services.groq_service import chat_with_groq
        import requests
        with patch("requests.post", side_effect=requests.Timeout("Connection timeout")):
            res = chat_with_groq("How to optimize tags?", trend_context=None)
            assert res.get("error") is False
            assert "reply" in res
            assert len(res["reply"]) > 0
            assert "gsk_" not in json.dumps(res)

    def test_no_secrets_in_response_headers_or_body(self, client):
        """Responses must never contain private keys or system secrets."""
        resp = client.get("/api/trends")
        body_text = resp.get_data(as_text=True)
        assert "AIzaSy" not in body_text
        assert "gsk_" not in body_text

    def test_cors_headers_are_restricted(self, client):
        """CORS must not allow arbitrary untrusted origins."""
        resp = client.options("/api/search", headers={
            "Origin": "https://evil-hacker-site.com",
            "Access-Control-Request-Method": "POST"
        })
        allowed_origin = resp.headers.get("Access-Control-Allow-Origin")
        assert allowed_origin != "https://evil-hacker-site.com"
        assert allowed_origin != "*"


# =============================================================================
# 4. FRONTEND ACCEPTANCE CRITERIA
# =============================================================================
class TestFrontendAcceptance:
    """Verify complete removal of auth UI, login scripts, and preservation of XSS defenses."""

    def test_index_html_has_no_auth_modals(self):
        """Landing page index.html must not have login/register/password modals."""
        content = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        assert 'id="loginModal"' not in content
        assert 'id="registerModal"' not in content
        assert 'id="authModal"' not in content
        assert 'id="forgotPasswordModal"' not in content

    def test_dashboard_html_purged_and_tools_have_no_auth_modals(self):
        """Dashboard page is purged, and standalone tool pages have no login modals."""
        assert not (REPO_ROOT / "frontend" / "dashboard.html").exists()
        tools_content = (REPO_ROOT / "frontend" / "tools" / "index.html").read_text(encoding="utf-8")
        assert 'id="loginModal"' not in tools_content
        assert 'id="registerModal"' not in tools_content
        assert 'id="authModal"' not in tools_content

    def test_login_js_file_deleted(self):
        """Legacy login.js script must be completely deleted from repository."""
        login_js = REPO_ROOT / "frontend" / "js" / "login.js"
        assert not login_js.exists(), "frontend/js/login.js still exists!"

    def test_xss_protection_utilities_exist(self):
        """Frontend JS common module must contain robust XSS protection routines."""
        common_js = (REPO_ROOT / "frontend" / "js" / "tools" / "common.js").read_text(encoding="utf-8")
        assert "escapeHtml" in common_js
        assert "escapeAttr" in common_js
        assert "sanitizeUrl" in common_js


# =============================================================================
# 5. SEO ACCEPTANCE CRITERIA
# =============================================================================
class TestSeoAcceptance:
    """Verify indexability, robots.txt, sitemap.xml, canonical URLs."""

    def test_homepage_indexable_and_canonical(self):
        """Homepage must be indexable and contain canonical URL."""
        content = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        assert 'content="index, follow' in content
        assert '<link rel="canonical" href="https://plexudo.vercel.app/">' in content

    def test_dashboard_page_purged_and_tools_indexable(self):
        """Legacy dashboard is purged, tools directory is indexable."""
        assert not (REPO_ROOT / "frontend" / "dashboard.html").exists()
        tools_content = (REPO_ROOT / "frontend" / "tools" / "index.html").read_text(encoding="utf-8")
        assert 'content="index, follow' in tools_content


    def test_sitemap_xml_valid(self):
        """sitemap.xml must be valid XML and contain no auth-only paths."""
        sitemap_path = REPO_ROOT / "frontend" / "sitemap.xml"
        assert sitemap_path.exists()
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        urls = [elem.text for elem in root.iter() if elem.tag.endswith("loc")]
        assert len(urls) > 0
        for u in urls:
            assert "login" not in u
            assert "register" not in u
            assert "dashboard" not in u

    def test_robots_txt_valid(self):
        """robots.txt must allow public routes and disallow private/tool endpoints."""
        robots_path = REPO_ROOT / "frontend" / "robots.txt"
        assert robots_path.exists()
        content = robots_path.read_text(encoding="utf-8")
        assert "Disallow: /api/" in content
        assert "Disallow: /dashboard" in content
        assert "Sitemap: https://plexudo.vercel.app/sitemap.xml" in content


# =============================================================================
# 6. SECURITY ACCEPTANCE CRITERIA
# =============================================================================
class TestSecurityAcceptance:
    """Verify no leaked secrets, no hardcoded API keys, no private data leaks."""

    def test_no_hardcoded_youtube_keys_in_tracked_source(self):
        for py_file in REPO_ROOT.rglob("*.py"):
            if ".git" in py_file.parts or "test" in py_file.name:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = [line for line in content.splitlines()
                       if re.search(r'AIzaSy[A-Za-z0-9_-]{33}', line) and "environ" not in line]
            assert not matches, f"Hardcoded YouTube key in {py_file}"

    def test_no_hardcoded_groq_keys_in_tracked_source(self):
        for py_file in REPO_ROOT.rglob("*.py"):
            if ".git" in py_file.parts or "test" in py_file.name:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = [line for line in content.splitlines()
                       if re.search(r'gsk_[0-9A-Za-z]{48}', line) and "environ" not in line]
            assert not matches, f"Hardcoded Groq key in {py_file}"

    def test_no_unauthorized_user_pii_endpoints(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 404, "User PII endpoint /api/admin/users still exists!"

    def test_env_file_not_committed_or_tracked(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".env" in gitignore
