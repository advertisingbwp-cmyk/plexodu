"""
SMTAS & Plexudo - Application Core Configuration
Centralized configuration manager loading environment credentials securely.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Determine root .env file path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(str(ENV_FILE))
else:
    load_dotenv()


class Settings:
    """
    Centralized Settings Model for SMTAS / Plexudo.
    Loads secrets securely from environment variables.
    """
    def __init__(self):
        # Core API Credentials
        self.GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
        self.GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        self.GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        self.YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()

        # Model & AI Strategy Configurations
        self.GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

        # Google OAuth / YouTube API Redirect URIs
        self.GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/api/channel-seo/auth/callback").strip()
        self.YOUTUBE_CALLBACK_URL = os.environ.get("YOUTUBE_CALLBACK_URL", "http://127.0.0.1:8000/api/v1/youtube/callback").strip()

        # Application & Server Defaults
        self.FLASK_ENV = os.environ.get("FLASK_ENV", "production" if os.environ.get("VERCEL") else "development").strip().lower()
        is_production = self.FLASK_ENV == "production" or bool(os.environ.get("VERCEL"))

        insecure_keys = {
            "smtas-secure-prod-key-2026",
            "plexudo-production-secret-key-2026",
            "dev_secret_key_change_in_production",
            "dev-insecure-secret-key-local-only",
            "change-me-secret-key-32-chars-long-plexudo-development-key",
        }
        raw_secret_key = os.environ.get("SECRET_KEY", "").strip()
        if not raw_secret_key or (is_production and raw_secret_key in insecure_keys):
            if is_production:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is missing, empty, or insecure in production/Vercel."
                )
            import secrets
            self.SECRET_KEY = f"dev-{secrets.token_hex(24)}"
        else:
            self.SECRET_KEY = raw_secret_key

        # Database Persistence Architecture
        db_url = os.environ.get("DATABASE_URL", "").strip()
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        if "+aiosqlite" in db_url:
            db_url = db_url.replace("+aiosqlite", "")
        self.DATABASE_URL = db_url
        self.IS_PRODUCTION = is_production

        self.PORT = int(os.environ.get("PORT", 5000))
        self.HOST = os.environ.get("HOST", "127.0.0.1").strip()

    def is_groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY and len(self.GROQ_API_KEY.strip()) > 0)

    def is_youtube_configured(self) -> bool:
        return bool(self.YOUTUBE_API_KEY and len(self.YOUTUBE_API_KEY.strip()) > 0)

    def is_google_oauth_configured(self) -> bool:
        return bool(
            self.GOOGLE_CLIENT_ID
            and len(self.GOOGLE_CLIENT_ID.strip()) > 0
            and self.GOOGLE_CLIENT_SECRET
            and len(self.GOOGLE_CLIENT_SECRET.strip()) > 0
        )


# Instantiate singleton settings object
settings = Settings()
