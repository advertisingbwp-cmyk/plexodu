"""
SMTAS & Plexudo - Application Core Configuration
Centralized configuration manager loading environment credentials securely.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine root .env file path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
if not ENV_FILE.exists():
    # Fallback to current working directory or parent directory
    ENV_FILE = Path(".env").resolve()


class Settings(BaseSettings):
    """
    Centralized Settings Model for SMTAS / Plexudo.
    Loads secrets securely from server-side environment (.env).
    """
    # Core API Credentials
    GROQ_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""

    # Model & AI Strategy Configurations
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Google OAuth / YouTube API Redirect URIs
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:5000/api/channel-seo/auth/callback"
    YOUTUBE_CALLBACK_URL: str = "http://127.0.0.1:8000/api/v1/youtube/callback"

    # Application & Server Defaults
    FLASK_ENV: str = "development"
    SECRET_KEY: str = "smtas-secure-prod-key-2026"
    PORT: int = 5000
    HOST: str = "127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

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
