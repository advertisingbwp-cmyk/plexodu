"""
Plexudo application core configuration.
Loads environment-backed credentials and runtime settings.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(str(ENV_FILE))
else:
    load_dotenv()


class Settings:
    """Centralized runtime configuration for Plexudo."""

    def __init__(self):
        self.GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
        self.YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
        self.GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

        self.FLASK_ENV = os.environ.get(
            "FLASK_ENV",
            "production" if os.environ.get("VERCEL") else "development",
        ).strip().lower()
        self.IS_PRODUCTION = self.FLASK_ENV == "production" or bool(os.environ.get("VERCEL"))

        insecure_keys = {
            "smtas-secure-prod-key-2026",
            "plexudo-production-secret-key-2026",
            "dev_secret_key_change_in_production",
            "dev-insecure-secret-key-local-only",
            "change-me-secret-key-32-chars-long-plexudo-development-key",
        }
        raw_secret_key = os.environ.get("SECRET_KEY", "").strip()

        if raw_secret_key and raw_secret_key not in insecure_keys:
            self.SECRET_KEY = raw_secret_key
        else:
            # Plexudo is currently anonymous/no-login, so Flask startup must not
            # fail before API handlers can return structured errors. A random
            # per-instance fallback keeps the server functional; production
            # deployments should still provide a strong SECRET_KEY environment
            # variable for stable signed-session/cookie behavior.
            import secrets
            self.SECRET_KEY = f"plexudo-{secrets.token_hex(32)}"
            if self.IS_PRODUCTION:
                print("WARNING: SECRET_KEY is not configured with a strong production value.")

        db_url = os.environ.get("DATABASE_URL", "").strip()
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        if "+aiosqlite" in db_url:
            db_url = db_url.replace("+aiosqlite", "")
        self.DATABASE_URL = db_url

        self.PORT = int(os.environ.get("PORT", 5000))
        self.HOST = os.environ.get("HOST", "127.0.0.1").strip()

    def is_groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY)

    def is_youtube_configured(self) -> bool:
        return bool(self.YOUTUBE_API_KEY)


settings = Settings()
