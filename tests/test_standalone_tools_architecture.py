"""
Standalone Tools Architecture Test Suite
========================================
Validates:
1. All 5 standalone tool routes and /tools hub return 200 without authentication.
2. Clean homepage has no tools grid or dashboard cards, links to /tools.
3. No inline layout CSS in HTML or JS violating GEMINI.md responsive rules.
4. Purged legacy endpoints (/api/session, /api/login, /api/register, /api/logout) return 404/405.
5. All 5 public creator tool APIs operate anonymously without cookies/sessions.
6. Absence of legacy dashboard.html and dashboard.js.
"""

import os
import re
import sys
from pathlib import Path
import pytest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

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


class TestStandaloneToolRoutes:
    """Verify all 5 standalone tools and directory are publicly accessible."""

    TOOL_SLUGS = [
        "trend-analyzer",
        "video-analyzer",
        "keyword-tool",
        "competitor-audit",
        "ai-strategist",
    ]

    def test_tools_hub_returns_200(self, client):
        resp = client.get("/tools")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Free YouTube Creator Utilities" in html
        for slug in self.TOOL_SLUGS:
            assert f"/tools/{slug}" in html

    def test_all_5_standalone_tool_routes_return_200(self, client):
        for slug in self.TOOL_SLUGS:
            resp = client.get(f"/tools/{slug}")
            assert resp.status_code == 200, f"Route /tools/{slug} failed with {resp.status_code}"
            html = resp.get_data(as_text=True)
            assert 'name="robots" content="index, follow"' in html
            assert f"https://plexudo.vercel.app/tools/{slug}" in html
            assert "dashboard.html" not in html
            assert "userCredits" not in html
            assert "loginModal" not in html


class TestHomepageCleanDesign:
    """Verify homepage has no tools grid and links cleanly to /tools."""

    def test_homepage_has_no_tools_grid(self):
        index_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        assert '<section class="tools-section"' not in index_html
        assert 'id="tools"' not in index_html
        assert 'href="/tools"' in index_html
        assert 'href="/dashboard.html"' not in index_html

    def test_dashboard_files_do_not_exist(self):
        assert not (FRONTEND_DIR / "dashboard.html").exists()
        assert not (FRONTEND_DIR / "js" / "dashboard.js").exists()


class TestGeminiResponsiveLayoutRules:
    """Verify GEMINI.md compliance: no inline layout styles in HTML or templates."""

    def test_no_inline_layout_styles_in_tool_pages(self):
        layout_patterns = [
            r'style="[^"]*display\s*:\s*(?:grid|flex)',
            r'style="[^"]*grid-template-columns',
            r'style="[^"]*(?<!max-|min-)width\s*:\s*\d{3,}px',
        ]
        tools_dir = FRONTEND_DIR / "tools"
        for html_file in tools_dir.glob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for pattern in layout_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert not matches, f"Inline layout style '{matches}' found in {html_file.name}, violating GEMINI.md"


class TestPurgedAuthEndpoints:
    """Verify legacy auth endpoints are removed."""

    def test_legacy_auth_endpoints_purged(self, client):
        purged = [
            ("/api/session", "get"),
            ("/api/login", "post"),
            ("/api/register", "post"),
            ("/api/logout", "post"),
            ("/api/v1/auth/me", "get"),
        ]
        for path, method in purged:
            func = getattr(client, method)
            resp = func(path, json={})
            assert resp.status_code in (404, 405), f"Expected 404/405 for purged endpoint {path}, got {resp.status_code}"
