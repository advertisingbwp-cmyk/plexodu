"""
pytest configuration for the Plexudo backend test suite.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

# Point pydantic-settings at .env.test so tests don't need a real .env
os.environ.setdefault("ENV_FILE", ".env.test")

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base, get_db
from app.db.models import __all__ as _models_all  # noqa: F401 — ensures all models loaded
from app.db.models.user import User
from app.main import app

settings = get_settings()
TEST_DB_FILE = Path(__file__).parent / "test_plexudo.db"


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    db_url = settings.TEST_DATABASE_URL
    is_postgres = db_url.startswith("postgresql")

    _engine = None
    if is_postgres:
        try:
            test_eng = create_async_engine(db_url, echo=False, pool_pre_ping=True)
            async with test_eng.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
            _engine = test_eng
        except Exception:
            _engine = None

    if _engine is None:
        sqlite_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
        _engine = create_async_engine(sqlite_url, echo=False)

    yield _engine

    await _engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest_asyncio.fixture(autouse=True)
async def setup_db_tables(engine):
    """Ensure all tables and partial indexes are freshly prepared for each test."""
    async with engine.begin() as conn:
        if engine.url.drivername.startswith("postgresql"):
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS citext"))

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(
            sa.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS one_welcome_credit_per_user "
                "ON credit_ledger (user_id) WHERE type = 'WELCOME_CREDIT'"
            )
        )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_client(db: AsyncSession):
    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unverified_user(db: AsyncSession) -> User:
    user = User(
        username="unverified_user",
        email="unverified@example.com",
        password_hash=hash_password("Str0ngP@ssword!"),
        email_verified_at=None,
        credit_balance=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    from datetime import datetime, timezone

    user = User(
        username="test_user",
        email="testuser@example.com",
        password_hash=hash_password("Str0ngP@ssword!"),
        email_verified_at=datetime.now(timezone.utc),
        credit_balance=3,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
