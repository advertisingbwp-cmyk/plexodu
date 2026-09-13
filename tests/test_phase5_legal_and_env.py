"""
Phase 5 Verification Test Suite: Legal Pages & Environment Cleanliness
Verifies:
1. Privacy Policy has no obsolete account/authentication/OAuth claims.
2. Privacy Policy retains accurate YouTube API, Groq AI, and Google AdSense disclosures.
3. Privacy Policy accurately documents stateless no-login architecture, rate limiting, and backend-only secrets.
4. Terms of Service has no obsolete login or password requirements.
5. Terms of Service retains accurate YouTube API, Groq AI, and Google AdSense disclosures.
6. Terms of Service documents rate limiting, bot protection, and fair use.
7. .env.example contains no Google OAuth, SMTP, or credit variables, and retains YOUTUBE_API_KEY, GROQ_API_KEY, DATABASE_URL, CORS_ALLOWED_ORIGINS.
8. Settings in config.py has no Google OAuth attributes.
9. Static secret scanning verifies no raw API keys are committed in source files.
"""
import re
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPrivacyPolicy:
    @pytest.fixture(autouse=True)
    def setup_content(self):
        privacy_path = REPO_ROOT / "frontend" / "privacy.html"
        self.content = privacy_path.read_text(encoding="utf-8")

    def test_no_obsolete_auth_or_oauth_claims(self):
        obsolete_phrases = [
            "password hash",
            "when creating an account",
            "account preferences",
            "Google OAuth API scopes",
            "connect your Google/YouTube account",
            "Account Settings → Danger Zone",
            "delete your account",
        ]
        for phrase in obsolete_phrases:
            assert phrase.lower() not in self.content.lower(), f"Found obsolete auth claim: '{phrase}'"

    def test_declares_login_free_and_anonymous(self):
        assert "login-free" in self.content.lower()
        assert "anonymous" in self.content.lower()

    def test_retains_youtube_api_disclosure(self):
        assert "YouTube Data API v3" in self.content
        assert "youtube.com/t/terms" in self.content
        assert "policies.google.com/privacy" in self.content

    def test_retains_groq_ai_disclosure(self):
        assert "Groq" in self.content
        assert "groq.com/privacy-policy" in self.content

    def test_retains_adsense_disclosure(self):
        assert "Google AdSense" in self.content
        assert "google.com/settings/ads" in self.content
        assert "policies.google.com/technologies/partner-sites" in self.content

    def test_documents_security_and_rate_limiting(self):
        assert "Rate Limiting" in self.content
        assert "Backend-Only Secrets" in self.content or "backend server" in self.content


class TestTermsOfService:
    @pytest.fixture(autouse=True)
    def setup_content(self):
        terms_path = REPO_ROOT / "frontend" / "terms.html"
        self.content = terms_path.read_text(encoding="utf-8")

    def test_no_obsolete_account_or_password_requirements(self):
        obsolete_phrases = [
            "When you create an account with us",
            "safeguarding your password",
            "activities under your account",
        ]
        for phrase in obsolete_phrases:
            assert phrase.lower() not in self.content.lower(), f"Found obsolete account claim: '{phrase}'"

    def test_declares_public_fair_use(self):
        assert "free, public creator platform" in self.content.lower() or "public access" in self.content.lower()

    def test_retains_youtube_terms_disclosure(self):
        assert "youtube.com/t/terms" in self.content
        assert "policies.google.com/privacy" in self.content

    def test_retains_groq_and_adsense_disclosures(self):
        assert "Groq" in self.content
        assert "Google AdSense" in self.content
        assert "google.com/settings/ads" in self.content

    def test_documents_rate_limiting_and_abuse_prevention(self):
        assert "rate limit" in self.content.lower()
        assert "scraper" in self.content.lower() or "scraping" in self.content.lower()


class TestEnvironmentConfiguration:
    @pytest.fixture(autouse=True)
    def setup_files(self):
        self.example_content = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    def test_env_example_has_no_google_oauth(self):
        assert "GOOGLE_CLIENT_ID" not in self.example_content
        assert "GOOGLE_CLIENT_SECRET" not in self.example_content
        assert "GOOGLE_REDIRECT_URI" not in self.example_content

    def test_env_example_has_no_smtp_variables(self):
        assert "SMTP_HOST" not in self.example_content
        assert "SMTP_USERNAME" not in self.example_content
        assert "SMTP_PASSWORD" not in self.example_content

    def test_env_example_has_no_credit_variables(self):
        assert "TOOL_CREDIT" not in self.example_content

    def test_env_example_retains_required_variables(self):
        required = [
            "YOUTUBE_API_KEY",
            "GROQ_API_KEY",
            "DATABASE_URL",
            "CORS_ALLOWED_ORIGINS",
            "SECRET_KEY",
        ]
        for var in required:
            assert var in self.example_content, f"Missing required variable '{var}' in .env.example"

    def test_config_py_has_no_oauth_attributes(self):
        from backend.app.core.config import settings
        assert not hasattr(settings, "GOOGLE_CLIENT_ID")
        assert not hasattr(settings, "GOOGLE_CLIENT_SECRET")
        assert not hasattr(settings, "is_google_oauth_configured")

    def test_no_actual_secrets_in_tracked_source(self):
        """Scans all tracked python files for literal YouTube or Groq API keys."""
        for py_file in REPO_ROOT.rglob("*.py"):
            if ".git" in py_file.parts or "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            # Real YouTube key pattern: AIzaSy + 33 chars
            yt_matches = [
                line for line in text.splitlines()
                if re.search(r'AIzaSy[A-Za-z0-9_-]{33}', line)
                and "environ" not in line
                and not line.strip().startswith("#")
            ]
            assert not yt_matches, f"Real YouTube key pattern found in {py_file}"

            # Real Groq key pattern: gsk_ + 48 chars
            groq_matches = [
                line for line in text.splitlines()
                if re.search(r'gsk_[0-9A-Za-z]{48}', line)
                and "environ" not in line
                and not line.strip().startswith("#")
            ]
            assert not groq_matches, f"Real Groq key pattern found in {py_file}"
