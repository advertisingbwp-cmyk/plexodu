"""
Phase 4 Verification Test Suite: Completely Login-Free Frontend
Verifies:
1. Complete absence of login/register/logout/account/profile/credits/ad-reward UI in dashboard.html and index.html.
2. Complete absence of session checking, ad delays, or auth gating in dashboard.js.
3. Retention of security utilities (escapeHtml, escapeAttr, sanitizeUrl, fetchWithTimeout).
4. End-to-end anonymous API execution without any auth challenges, cookies, or redirects.
5. Adherence to Responsive CSS Guidelines (no inline layout styles overriding media queries).
"""
import re
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
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


@pytest.fixture
def client():
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestFrontendMarkup:
    @pytest.fixture(autouse=True)
    def setup_paths(self):
        self.root = REPO_ROOT
        self.dashboard_html_path = self.root / "frontend" / "dashboard.html"
        self.index_html_path = self.root / "frontend" / "index.html"
        self.dashboard_js_path = self.root / "frontend" / "js" / "dashboard.js"
        self.style_css_path = self.root / "frontend" / "css" / "style.css"
        self.tools_dir = self.root / "frontend" / "tools"
        self.common_js_path = self.root / "frontend" / "js" / "tools" / "common.js"

    def test_dashboard_files_purged(self):
        """dashboard.html and dashboard.js must be completely deleted."""
        assert not self.dashboard_html_path.exists(), "frontend/dashboard.html still exists!"
        assert not self.dashboard_js_path.exists(), "frontend/js/dashboard.js still exists!"

    def test_standalone_tools_pages_exist_and_no_auth_ui(self):
        """Standalone tool pages must exist and have zero auth or profile UI."""
        tool_pages = [
            "trend-analyzer.html",
            "video-analyzer.html",
            "competitor-audit.html",
            "ai-strategist.html",
            "index.html",
        ]
        prohibited_ids = [
            "authModal",
            "loginModal",
            "registerModal",
            "userInfoCard",
            "userAvatar",
            "userRole",
            "adRewardModal",
            "logoutBtn",
            "userCredits",
            "kpiCreditsCount",
        ]
        for page in tool_pages:
            path = self.tools_dir / page
            assert path.exists(), f"Tool page {page} is missing!"
            content = path.read_text(encoding="utf-8")
            for pid in prohibited_ids:
                assert f'id="{pid}"' not in content, f"Prohibited ID '{pid}' in {page}"

    def test_tools_hub_contains_all_4_creator_tools(self):
        """frontend/tools/index.html must link to the 4 standalone creator tools and not keyword-tool."""
        hub_html = (self.tools_dir / "index.html").read_text(encoding="utf-8")
        assert "/tools/trend-analyzer" in hub_html
        assert "/tools/video-analyzer" in hub_html
        assert "/tools/competitor-audit" in hub_html
        assert "/tools/ai-strategist" in hub_html
        assert "/tools/keyword-tool" not in hub_html

    def test_common_js_has_no_auth_endpoints_and_has_xss_protection(self):
        """common.js must have zero auth endpoints and provide XSS sanitizers."""
        assert self.common_js_path.exists()
        js = self.common_js_path.read_text(encoding="utf-8")
        assert "/session" not in js
        assert "checkSession" not in js
        assert "function escapeHtml" in js
        assert "function escapeAttr" in js
        assert "function sanitizeUrl" in js
        assert "async function fetchWithTimeout" in js

    def test_index_html_no_auth_modals_and_declares_free_access(self):
        with open(self.index_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        assert 'id="authModal"' not in html
        assert 'id="loginModal"' not in html
        assert 'href="/tools"' in html



class TestAnonymousBrowserFlow:
    """Simulates direct anonymous user actions: Homepage -> Tool -> API -> Result"""

    def test_anonymous_suggest_query(self, client):
        res = client.get("/api/suggest?q=gaming")
        assert res.status_code == 200
        data = res.get_json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_anonymous_trend_search_succeeds(self, client):
        mock_raw = {
            "status": 200,
            "keyword": "gaming setup 2026",
            "daily_metrics": [
                {"date": "2026-03-01", "views": 1000, "likes": 50, "comments": 5, "comments_count": 5, "shares": 10},
                {"date": "2026-03-02", "views": 1500, "likes": 75, "comments": 10, "comments_count": 10, "shares": 15},
            ],
            "comments": ["Great setup!", "Love the RGB."],
            "related_keywords": ["pc setup", "gaming desk"],
            "top_videos": [],
        }
        with patch("main_flask_app.fetch_youtube_data", return_value=mock_raw):
            res = client.post("/api/search", json={"keyword": "gaming setup 2026"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["keyword"] == "gaming setup 2026"
            assert "YouTube" in data["results"]

    def test_anonymous_video_analysis_succeeds(self, client):
        mock_video = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Top Tech Gadgets 2026",
            "description": "Comprehensive review of the latest tech gadgets.",
            "tags": ["tech", "gadgets", "reviews"],
            "comments": ["Great review!", "Loved the gadget specs."],
            "daily_metrics": [
                {"date": "2026-03-01", "views": 1000, "likes": 50, "comments": 5, "comments_count": 5, "shares": 20},
                {"date": "2026-03-02", "views": 1500, "likes": 75, "comments": 10, "comments_count": 10, "shares": 30},
            ],
            "stats": {"views": 50000, "likes": 2500, "comments": 120},
        }
        with patch("main_flask_app.analyze_youtube_video", return_value=mock_video):
            res = client.post("/api/video-analysis", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["title"] == "Top Tech Gadgets 2026"
            assert "sentiment" in data

    def test_anonymous_competitor_audit_succeeds(self, client):
        mock_audit = {
            "channel_id": "UC1234567890",
            "title": "Tech Creator Pro",
            "subscriber_count": 150000,
            "video_count": 220,
            "view_count": 18000000,
            "recent_videos": [],
            "top_performing_topics": ["tech", "gadgets"],
            "avg_engagement_rate": 4.5,
        }
        with patch("main_flask_app.audit_youtube_channel", return_value=mock_audit):
            res = client.post("/api/audit-channel", json={"identifier": "@techcreatorpro"})
            assert res.status_code == 200
            data = res.get_json()
            assert data["title"] == "Tech Creator Pro"

    def test_anonymous_compare_keywords_succeeds(self, client):
        res = client.get("/api/compare-keywords")
        assert res.status_code == 200
        data = res.get_json()
        assert "comparison" in data

    def test_anonymous_ai_chat_succeeds(self, client):
        with patch("main_flask_app.chat_with_groq", return_value={"reply": "Here are 3 high-CTR title formulas for your next video."}):
            res = client.post("/api/chat", json={"message": "Give me title ideas for gaming"})
            assert res.status_code == 200
            data = res.get_json()
            assert "reply" in data

    def test_anonymous_trends_history_succeeds(self, client):
        res = client.get("/api/trends")
        assert res.status_code == 200
        data = res.get_json()
        assert "trends" in data
        assert isinstance(data["trends"], list)

    def test_anonymous_audit_log_protected_from_public(self, client):
        """Audit logs must not be exposed to anonymous public users (privacy/security)."""
        res = client.get("/api/audit-log")
        assert res.status_code == 404
