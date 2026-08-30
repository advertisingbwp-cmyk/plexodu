"""
Application Settings
====================
All configuration is loaded from environment variables (or .env / .env.test).
No secret values are ever hardcoded here.

The TOOL_CREDIT_COSTS property is the single source of truth for per-tool
credit costs. Tool endpoints must look up their cost here — never hardcode it.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Database ----
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/plexudo_dev.db" if os.environ.get("VERCEL") else "sqlite+aiosqlite:///plexudo_dev.db"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///plexudo_test.db"


    # ---- Session ----
    SECRET_KEY: str = "change-me-secret-key-32-chars-long"
    SESSION_COOKIE_NAME: str = "plexudo_session"
    SESSION_MAX_AGE_DAYS: int = 30

    # ---- CSRF ----
    CSRF_SECRET: str = "change-me-csrf-secret-32-chars-long"

    # ---- CORS (local dev only — production is same-origin via Vercel rewrite) ----
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # ---- Encryption (YouTube OAuth tokens at rest) ----
    TOKEN_ENCRYPTION_KEY: str = "change-me-32-bytes-aaaaaaaaaaaaa"  # must be 32 or 44 bytes

    # ---- Google OAuth — Connect-YouTube ONLY, never for account login ----
    GOOGLE_CLIENT_ID: str = "your-google-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "your-google-client-secret"
    YOUTUBE_CONNECT_REDIRECT_URI: str = "http://localhost:8000/api/v1/youtube/callback"
    GOOGLE_OAUTH_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    # ---- YouTube Data API v3 ----
    YOUTUBE_API_KEY: str = "your-youtube-api-key"

    # ---- AI (Groq) ----
    GROQ_API_KEY: str = "your-groq-api-key"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_MODEL: Optional[str] = None
    AI_TIMEOUT_SECONDS: float = 20.0

    # ---- Email Delivery ----
    EMAIL_PROVIDER: str = "console"  # 'smtp', 'sendgrid', 'resend', 'console'
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "test@example.com"
    SMTP_PASSWORD: str = "test-password"
    SMTP_USE_TLS: bool = True
    SENDGRID_API_KEY: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "noreply@plexudo.com"
    EMAIL_FROM_NAME: str = "Plexudo"

    # ---- URLs ----
    FRONTEND_URL: str = "http://localhost:5173"
    PUBLIC_APP_URL: str = "https://plexudo.vercel.app"

    # ---- Environment ----
    ENVIRONMENT: str = "development"

    # ---- Redis (rate limiting) ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Per-tool credit costs (overridable via env vars without code changes) ----
    TOOL_CREDIT_COST_VIDEO_ANALYZER: int = 1
    TOOL_CREDIT_COST_KEYWORD_TOOL: int = 1
    TOOL_CREDIT_COST_TREND_ANALYZER: int = 1
    TOOL_CREDIT_COST_COMPETITOR_ANALYSIS: int = 1
    TOOL_CREDIT_COST_AI_ASSISTANT: int = 1
    TOOL_CREDIT_COST_SEO_SCORE: int = 1

    # ---- Credit constants ----
    WELCOME_CREDITS: int = 3
    AD_REWARD_CREDITS: int = 1

    @model_validator(mode="after")
    def resolve_ai_model(self) -> Settings:
        if self.AI_MODEL:
            self.GROQ_MODEL = self.AI_MODEL
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.DATABASE_URL.startswith("postgresql://") and not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


    @property
    def EFFECTIVE_AI_MODEL(self) -> str:
        return self.AI_MODEL or self.GROQ_MODEL

    @property
    def TOOL_CREDIT_COSTS(self) -> dict[str, int]:
        """
        Central mapping of tool name → credit cost.
        Tool endpoints MUST look up their cost here rather than hardcoding a number.
        Costs can be changed per-environment via TOOL_CREDIT_COST_* env vars.
        """
        return {
            "VIDEO_ANALYZER": self.TOOL_CREDIT_COST_VIDEO_ANALYZER,
            "KEYWORD_TOOL": self.TOOL_CREDIT_COST_KEYWORD_TOOL,
            "TREND_ANALYZER": self.TOOL_CREDIT_COST_TREND_ANALYZER,
            "COMPETITOR_ANALYSIS": self.TOOL_CREDIT_COST_COMPETITOR_ANALYSIS,
            "AI_ASSISTANT": self.TOOL_CREDIT_COST_AI_ASSISTANT,
            "SEO_SCORE": self.TOOL_CREDIT_COST_SEO_SCORE,
        }

    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
