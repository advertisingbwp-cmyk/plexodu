"""Regression checks for production hardening and runtime compatibility."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_vercel_entrypoint_does_not_hard_crash_before_flask_can_respond():
    src = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "spec.loader.exec_module(flask_module)" in src
    assert "raise RuntimeError" not in src


def test_production_config_has_a_secure_secret_path():
    src = (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    assert "secrets.token_hex(32)" in src
    assert "SECRET_KEY" in src


def test_tool_renderers_do_not_use_inline_event_handlers():
    for path in [
        ROOT / "frontend" / "js" / "tools" / "trend-analyzer.js",
        ROOT / "frontend" / "js" / "tools" / "video-analyzer.js",
    ]:
        src = path.read_text(encoding="utf-8")
        assert not re.search(r"\bonclick\s*=", src, re.IGNORECASE), path.name
        assert "addEventListener" in src


def test_shared_fetch_handles_non_json_server_responses():
    src = (ROOT / "frontend" / "js" / "tools" / "common.js").read_text(encoding="utf-8")
    assert "response.json = async () =>" in src
    assert "Server error. Please try again in a moment." in src


def test_pytest_and_postgres_driver_are_declared_for_ci_and_vercel():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^pytest==", requirements, re.MULTILINE)
    assert re.search(r"^psycopg2-binary==", requirements, re.MULTILINE)
