import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.credits import router as credits_router
from app.api.v1.youtube import router as youtube_router
from app.api.v1.profile import router as profile_router
from app.api.v1.history import router as history_router
from app.api.v1.tools import router as tools_router
from app.public.routes import router as public_router
from app.core.config import get_settings
from app.db.base import engine, Base
from app.db.models import __all__ as _models_all

logger = logging.getLogger("plexudo")
settings = get_settings()

app = FastAPI(
    title="Plexudo API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGINS, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(credits_router, prefix="/api/v1")
app.include_router(youtube_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")

app.include_router(public_router)

@app.on_event("startup")
async def startup_event():
    try:
        async with engine.begin() as conn:
            if engine.url.drivername.startswith("postgresql"):
                await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
                await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS citext"))
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                sa.text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS one_welcome_credit_per_user "
                    "ON credit_ledger (user_id) WHERE type = 'WELCOME_CREDIT'"
                )
            )
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning("Database initialization notice: %s", e)
