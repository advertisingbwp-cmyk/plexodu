"""
Plexudo Phase 1 Security Test Suite
Validates:
a) Missing or insecure production SECRET_KEY causes startup failure
b) Registration API response never exposes password hashes, verification tokens, or internal secrets
c) Public HTML contains zero references to untrusted ad networks / push scripts, while preserving Google AdSense
d) Email service safely handles missing SMTP credentials without hardcoded fallbacks
"""

import os
import sys
import json
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── A. SECRET_KEY HARDENING TESTS ──────────────────────────────────────────

def test_production_secret_key_missing_fails():
    """Verify production mode refuses to start when SECRET_KEY is missing."""
    from app.core.config import Settings
    old_env = os.environ.copy()
    try:
        os.environ["FLASK_ENV"] = "production"
        os.environ.pop("VERCEL", None)
        os.environ["SECRET_KEY"] = ""

        with pytest.raises(RuntimeError) as exc_info:
            Settings()
        assert "SECRET_KEY" in str(exc_info.value)
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_vercel_secret_key_missing_fails():
    """Verify Vercel environment refuses to start when SECRET_KEY is missing."""
    old_env = os.environ.copy()
    try:
        os.environ["VERCEL"] = "1"
        os.environ.pop("FLASK_ENV", None)
        os.environ.pop("SECRET_KEY", None)

        from app.core.config import Settings
        with pytest.raises(RuntimeError) as exc_info:
            Settings()
        assert "SECRET_KEY" in str(exc_info.value)
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_production_secret_key_insecure_default_fails():
    """Verify production mode rejects known insecure/default SECRET_KEY strings."""
    old_env = os.environ.copy()
    try:
        os.environ["FLASK_ENV"] = "production"
        os.environ["SECRET_KEY"] = "smtas-secure-prod-key-2026"

        from app.core.config import Settings
        with pytest.raises(RuntimeError) as exc_info:
            Settings()
        assert "insecure" in str(exc_info.value).lower()
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_production_valid_secret_key_succeeds():
    """Verify production mode boots cleanly with a valid high-entropy secret."""
    old_env = os.environ.copy()
    try:
        os.environ["FLASK_ENV"] = "production"
        os.environ["SECRET_KEY"] = "a-very-strong-and-secure-random-token-for-prod-32chars"

        from app.core.config import Settings
        s = Settings()
        assert s.SECRET_KEY == "a-very-strong-and-secure-random-token-for-prod-32chars"
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_development_secret_key_fallback():
    """Verify development mode allows a dev-only fallback without crashing."""
    old_env = os.environ.copy()
    try:
        os.environ["FLASK_ENV"] = "development"
        os.environ.pop("VERCEL", None)
        os.environ.pop("SECRET_KEY", None)

        from app.core.config import Settings
        s = Settings()
        assert s.SECRET_KEY.startswith("dev-") and len(s.SECRET_KEY) >= 32
    finally:
        os.environ.clear()
        os.environ.update(old_env)


# ─── B. REGISTRATION RESPONSE SANITIZATION TESTS ─────────────────────────────

def test_registration_response_excludes_secrets():
    """Verify POST /api/register never leaks verification tokens, password hashes, or internal fields."""
    import secrets
    import time
    import importlib.util

    app_py_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    app = flask_module.app

    app.config["TESTING"] = True
    client = app.test_client()

    unique_email = f"sec_test_{int(time.time())}_{secrets.token_hex(4)}@example.com"
    payload = {
        "name": "Security Tester",
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "Creator"
    }

    res = client.post("/api/register", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    data = res.get_json()

    # Assert verification_token is NOT exposed in the response
    assert "verification_token" not in data, "CRITICAL: verification_token leaked in registration response!"

    # Assert no password or hashes leaked anywhere in top-level JSON
    for forbidden in ["password", "password_hash", "reset_token", "secret", "tokens"]:
        assert forbidden not in data, f"CRITICAL: '{forbidden}' found in registration response!"

    # Assert user sub-dictionary contains only whitelisted public fields
    user_data = data.get("user", {})
    allowed_fields = {"id", "name", "email", "role", "credits", "email_verified", "avatar_url"}
    extra_fields = set(user_data.keys()) - allowed_fields
    assert len(extra_fields) == 0, f"CRITICAL: Non-whitelisted user fields exposed: {extra_fields}"

    assert data.get("public_mode") is True


# ─── C. UNTRUSTED AD SCRIPT EXCLUSION TESTS ──────────────────────────────────

def test_absence_of_suspicious_ad_scripts():
    """Verify all public HTML files contain zero references to untrusted ad networks / push scripts."""
    forbidden_terms = [
        "effectivegatecontent",
        "pl25807973",
        "bibleearthquake.com",
        "highperformanceformat.com",
        "atOptions",
        "container-731e98cea50f9b0991741cae4bd4a724",
    ]

    html_files = list(REPO_ROOT.glob("**/*.html"))
    assert len(html_files) > 0, "No HTML files found to inspect!"

    for html_path in html_files:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        for term in forbidden_terms:
            assert term not in content, (
                f"CRITICAL: Untrusted ad script/identifier '{term}' found in {html_path.relative_to(REPO_ROOT)}!"
            )


def test_google_adsense_preserved():
    """Verify legitimate Google AdSense tag is preserved in public HTML pages."""
    index_html = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8", errors="ignore")
    assert "pagead2.googlesyndication.com" in index_html, "Google AdSense script was unintentionally removed from index.html!"


# ─── D. EMAIL SERVICE CREDENTIAL SECURITY TESTS ─────────────────────────────

def test_email_service_without_smtp_credentials():
    """Verify email service fails safely when credentials are missing, without crashing or using hardcoded defaults."""
    old_env = os.environ.copy()
    try:
        os.environ["SMTP_USERNAME"] = ""
        os.environ["SMTP_PASSWORD"] = ""

        from services import email_service
        result = email_service.send_email("recipient@example.com", "Test Subject", "<p>Hello</p>")
        assert result is False, "send_email should return False when SMTP credentials are not configured"

        # Test helper functions
        assert email_service.send_verification_email("recipient@example.com", "Creator", "token123") is False
        assert email_service.send_password_changed_email("recipient@example.com", "Creator") is False
        assert email_service.send_password_reset_email("recipient@example.com", "token123") is False
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def test_email_service_source_has_no_hardcoded_passwords():
    """Verify email_service.py source code contains no hardcoded SMTP passwords or fallback credential literals."""
    service_path = BACKEND_DIR / "services" / "email_service.py"
    source = service_path.read_text(encoding="utf-8")

    import re
    matches = re.findall(r'os\.environ\.get\s*\(\s*["\']SMTP_PASSWORD["\']\s*,\s*["\']([^"\']+)["\']\s*\)', source)
    assert len(matches) == 0, f"Found hardcoded fallback for SMTP_PASSWORD: {matches}"
