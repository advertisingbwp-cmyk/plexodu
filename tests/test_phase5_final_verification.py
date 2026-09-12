"""
Phase 5 — Final Production Verification Tests
==============================================
Covers: hardcoded admin removal, CORS restriction, no credentials in source,
        no synthetic analytics, auth guards, session security, credit atomicity,
        cross-tenant isolation, CI workflow verification.
"""

import json
import os
import re
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND_APP = REPO_ROOT / "backend" / "app.py"
VERCEL_JSON = REPO_ROOT / "vercel.json"
FRONTEND = REPO_ROOT / "frontend"
GITIGNORE = REPO_ROOT / ".gitignore"


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# P0 — Hardcoded admin account removed
# ─────────────────────────────────────────────────────────────────────────────
class TestHardcodedAdmin:
    def test_no_hardcoded_admin_password(self):
        src = read(BACKEND_APP)
        assert "smtas2024" not in src, \
            "P0: Hardcoded password 'smtas2024' still exists in app.py"

    def test_no_hardcoded_admin_email(self):
        src = read(BACKEND_APP)
        assert "fahad@smtas.com" not in src, \
            "P0: Hardcoded email 'fahad@smtas.com' still exists in app.py"

    def test_create_tables_no_seed_user(self):
        src = read(BACKEND_APP)
        fn_start = src.find("def create_tables()")
        fn_end   = src.find("\ncreate_tables()", fn_start)
        fn_body  = src[fn_start:fn_end]
        assert "generate_password_hash" not in fn_body, \
            "P0: create_tables() must not seed any user with generate_password_hash"


# ─────────────────────────────────────────────────────────────────────────────
# P1 — CORS restricted to known origins
# ─────────────────────────────────────────────────────────────────────────────
class TestCORSRestriction:
    def test_cors_not_wildcard(self):
        src = read(BACKEND_APP)
        assert "CORS(app, supports_credentials=True)" not in src, \
            "P1: CORS must not be open wildcard with supports_credentials=True"

    def test_cors_has_origins_restriction(self):
        src = read(BACKEND_APP)
        assert "origins=" in src, "P1: CORS must specify an origins= restriction"

    def test_cors_origins_env_configurable(self):
        src = read(BACKEND_APP)
        assert "CORS_ALLOWED_ORIGINS" in src, \
            "P1: CORS origins must be configurable via CORS_ALLOWED_ORIGINS env var"


# ─────────────────────────────────────────────────────────────────────────────
# P0 — No real secrets committed to tracked Python source files
#       (excludes test files which legitimately reference key patterns as regex)
# ─────────────────────────────────────────────────────────────────────────────
class TestNoSecretsInSource:
    def test_no_youtube_api_key_in_py(self):
        """Real YouTube API keys start with AIzaSy and are 39 chars total."""
        for f in REPO_ROOT.rglob("*.py"):
            if ".git" in f.parts or "test_" in f.name or f.parent.name == "tests":
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            # Detect literal AIzaSy... strings that are NOT from os.environ
            lines = [l for l in content.splitlines()
                     if re.search(r'AIzaSy[A-Za-z0-9_-]{33}', l)
                     and "environ" not in l
                     and not l.strip().startswith("#")]
            assert not lines, f"P0: Real YouTube API key found in {f}: {lines[:2]}"

    def test_no_groq_key_in_py(self):
        """Real Groq keys match gsk_<48 chars>."""
        for f in REPO_ROOT.rglob("*.py"):
            if ".git" in f.parts or "test_" in f.name or f.parent.name == "tests":
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = [l for l in content.splitlines()
                     if re.search(r'gsk_[0-9A-Za-z]{48}', l)
                     and "environ" not in l
                     and not l.strip().startswith("#")]
            assert not lines, f"P0: Groq API key found in {f}: {lines[:2]}"

    def test_env_files_are_git_ignored(self):
        gi = read(GITIGNORE)
        assert ".env" in gi, ".env must be listed in .gitignore"

    def test_no_smtp_password_in_py(self):
        """SMTP passwords must not appear as literals in Python source."""
        for f in REPO_ROOT.rglob("*.py"):
            if ".git" in f.parts or "test_" in f.name or f.parent.name == "tests":
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            # Look for Gmail app-password pattern (16 lowercase chars with spaces)
            lines = [l for l in content.splitlines()
                     if re.search(r'"[a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4}"', l)
                     and not l.strip().startswith("#")]
            assert not lines, f"P0: SMTP app password pattern found in {f}: {lines[:2]}"


# ─────────────────────────────────────────────────────────────────────────────
# P1 — No synthetic/fake analytics presented as real
# ─────────────────────────────────────────────────────────────────────────────
class TestNoSyntheticAnalytics:
    SYNTHETIC_PATTERNS = [
        r"random\.randint\s*\(",
        r"random\.uniform\s*\(",
        r"fake_views",
        r"simulated_metric",
        r"generate_fake",
    ]

    def test_no_synthetic_data_generators_in_real_api(self):
        real_api = REPO_ROOT / "backend" / "services" / "real_api.py"
        src = read(real_api)
        for pat in self.SYNTHETIC_PATTERNS:
            assert not re.search(pat, src), \
                f"P1: Synthetic data pattern '{pat}' found in real_api.py"

    def test_no_faker_import(self):
        for f in (REPO_ROOT / "backend").rglob("*.py"):
            src = f.read_text(encoding="utf-8", errors="ignore")
            if "from faker import" in src or "import faker" in src.lower():
                assert "test_" in f.name or "tests/" in str(f), \
                    f"P1: faker import in non-test file {f}"


# ─────────────────────────────────────────────────────────────────────────────
# BOLA / Cross-tenant isolation
# ─────────────────────────────────────────────────────────────────────────────
class TestCrossTenantIsolation:
    def test_report_route_filters_by_user(self):
        src = read(BACKEND_APP)
        idx = src.find("def generate_report(trend_id)")
        snippet = src[idx:idx + 600]
        assert "created_by=user_id" in snippet, \
            "BOLA: /api/report/<trend_id> must filter Trend by created_by=user_id"

    def test_csv_export_route_filters_by_user(self):
        src = read(BACKEND_APP)
        idx = src.find("def export_csv(trend_id)")
        snippet = src[idx:idx + 600]
        assert "created_by=user_id" in snippet, \
            "BOLA: /api/export-csv/<trend_id> must filter Trend by created_by=user_id"

    def test_compare_keywords_filters_by_user(self):
        src = read(BACKEND_APP)
        idx = src.find("def compare_keywords()")
        snippet = src[idx:idx + 800]
        assert "created_by == user_id" in snippet or "created_by=user_id" in snippet, \
            "BOLA: /api/compare-keywords must filter results by user_id"

    def test_list_trends_filters_by_user(self):
        src = read(BACKEND_APP)
        idx = src.find("def list_trends()")
        snippet = src[idx:idx + 400]
        assert "created_by=user_id" in snippet, \
            "BOLA: /api/trends must filter by created_by=user_id"


# ─────────────────────────────────────────────────────────────────────────────
# Auth guards on all protected endpoints
# ─────────────────────────────────────────────────────────────────────────────
class TestAuthGuards:
    def test_search_requires_login(self):
        src = read(BACKEND_APP)
        idx = src.find("def search_trend()")
        snippet = src[idx:idx + 400]
        assert "login_required()" in snippet

    def test_report_requires_login(self):
        src = read(BACKEND_APP)
        idx = src.find("def generate_report(trend_id)")
        snippet = src[idx:idx + 300]
        assert "login_required()" in snippet

    def test_ai_chat_requires_login(self):
        src = read(BACKEND_APP)
        idx = src.find("def ai_chat()")
        snippet = src[idx:idx + 300]
        assert "login_required()" in snippet

    def test_video_analysis_requires_login(self):
        src = read(BACKEND_APP)
        idx = src.find("def video_analysis()")
        snippet = src[idx:idx + 300]
        assert "login_required()" in snippet

    def test_audit_channel_requires_login(self):
        src = read(BACKEND_APP)
        idx = src.find("def audit_channel()")
        snippet = src[idx:idx + 300]
        assert "login_required()" in snippet


# ─────────────────────────────────────────────────────────────────────────────
# Session security
# ─────────────────────────────────────────────────────────────────────────────
class TestSessionSecurity:
    def test_session_httponly(self):
        src = read(BACKEND_APP)
        assert 'SESSION_COOKIE_HTTPONLY"] = True' in src

    def test_session_samesite_lax(self):
        src = read(BACKEND_APP)
        assert 'SESSION_COOKIE_SAMESITE"] = "Lax"' in src

    def test_session_secure_in_production(self):
        src = read(BACKEND_APP)
        assert "SESSION_COOKIE_SECURE" in src and "IS_PRODUCTION" in src

    def test_logout_clears_session(self):
        src = read(BACKEND_APP)
        idx = src.find("def logout()")
        snippet = src[idx:idx + 200]
        assert "session.clear()" in snippet


# ─────────────────────────────────────────────────────────────────────────────
# Credit atomicity
# ─────────────────────────────────────────────────────────────────────────────
class TestCreditAtomicity:
    def test_deduct_uses_sql_where_credits_gte(self):
        src = read(BACKEND_APP)
        idx = src.find("def _deduct_credits_atomic")
        snippet = src[idx:idx + 600]
        assert "credits >= amount" in snippet or "User.credits >= amount" in snippet

    def test_refund_on_search_failure(self):
        src = read(BACKEND_APP)
        idx = src.find("def search_trend()")
        # Use a larger window — the refund call is after the API call
        snippet = src[idx:idx + 1500]
        assert "_refund_credits_atomic" in snippet, \
            "search_trend must refund credits on API failure"

    def test_refund_on_pdf_failure(self):
        src = read(BACKEND_APP)
        idx = src.find("def generate_report(trend_id)")
        snippet = src[idx:idx + 2200]
        assert "_refund_credits_atomic" in snippet, \
            "generate_report must refund credits if PDF generation fails"


# ─────────────────────────────────────────────────────────────────────────────
# Suspicious ad scripts absent
# ─────────────────────────────────────────────────────────────────────────────
class TestNoSuspiciousAdScripts:
    SUSPECT_DOMAINS = [
        "doubleclick.net",
        "adnxs.com",
        "taboola.com",
        "outbrain.com",
        "criteo.com",
        "exoclick.com",
        "trafficjunky.com",
        "popads.net",
        "propellerads.com",
    ]
    # Legitimate external script CDNs / ad networks
    ALLOWED_SCRIPT_DOMAINS = {
        "pagead2.googlesyndication.com",
        "adservice.google.com",
        "cdn.jsdelivr.net",       # Chart.js and other OSS libraries
        "cdnjs.cloudflare.com",   # OSS libraries
        "unpkg.com",              # OSS libraries
    }

    def test_no_suspect_ad_networks(self):
        for html_file in FRONTEND.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8", errors="ignore")
            for domain in self.SUSPECT_DOMAINS:
                assert domain not in content, \
                    f"Suspect ad network '{domain}' found in {html_file.name}"

    def test_external_scripts_are_from_known_safe_domains(self):
        for html_file in FRONTEND.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8", errors="ignore")
            script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content)
            for src in script_srcs:
                if not src.startswith("http"):
                    continue  # relative URL — fine
                # Google services
                if any(g in src for g in ["googleapis.com", "gstatic.com", "google.com"]):
                    continue
                # Known safe CDNs and ad networks
                if any(d in src for d in self.ALLOWED_SCRIPT_DOMAINS):
                    continue
                pytest.fail(
                    f"Unexpected external script in {html_file.name}: {src}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# CI workflow exists and is correct
# ─────────────────────────────────────────────────────────────────────────────
class TestCIWorkflow:
    def test_github_actions_workflow_exists(self):
        workflow_dir = REPO_ROOT / ".github" / "workflows"
        yml_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
        assert len(yml_files) > 0, "No GitHub Actions workflow found"

    def test_ci_workflow_runs_tests(self):
        workflow_dir = REPO_ROOT / ".github" / "workflows"
        for f in workflow_dir.glob("*.yml"):
            if "pytest" in f.read_text(encoding="utf-8"):
                return
        pytest.fail("No workflow runs pytest")

    def test_ci_workflow_has_secret_scanning(self):
        workflow_dir = REPO_ROOT / ".github" / "workflows"
        found = any(
            "gitleaks" in f.read_text(encoding="utf-8") or "trufflehog" in f.read_text(encoding="utf-8")
            for f in workflow_dir.glob("*.yml")
        )
        assert found, "No secret-scanning step found in any CI workflow"

    def test_ci_does_not_hardcode_real_secrets(self):
        workflow_dir = REPO_ROOT / ".github" / "workflows"
        for f in workflow_dir.glob("*.yml"):
            content = f.read_text(encoding="utf-8")
            assert not re.search(r'AIzaSy[A-Za-z0-9_-]{33}', content), \
                f"Real YouTube API key in CI workflow {f.name}"
            assert not re.search(r'gsk_[0-9A-Za-z]{48}', content), \
                f"Real Groq key in CI workflow {f.name}"
