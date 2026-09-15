"""Regression checks for production hardening changes."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_vercel_entrypoint_requires_stable_secret_and_database():
    src = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "SECRET_KEY must be configured in Vercel environment variables" in src
    assert "DATABASE_URL must point to a persistent PostgreSQL database in Vercel" in src
    assert 'os.environ["DATA_DIR"] = "/tmp"' not in src


def test_tool_renderers_do_not_use_inline_event_handlers():
    for path in [
        ROOT / "frontend" / "js" / "tools" / "trend-analyzer.js",
        ROOT / "frontend" / "js" / "tools" / "video-analyzer.js",
    ]:
        src = path.read_text(encoding="utf-8")
        assert not re.search(r"\bonclick\s*=", src, re.IGNORECASE), path.name
        assert "addEventListener" in src


def test_pytest_is_declared_for_ci():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^pytest==", requirements, re.MULTILINE)
