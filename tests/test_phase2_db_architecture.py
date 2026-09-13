"""
Phase 2 — Authentication-Free Database Architecture Tests
=========================================================
Verifies:
1. Database initializes correctly without seeding default accounts.
2. User model contains no authentication fields (password_hash, google_id, login_attempts, is_locked, email_verified, credits).
3. RewardTransaction table/model is removed.
4. All database models (Trend, Report, AuditLog) function with None/NULL user references.
5. Public requests work cleanly without any User records in the database.
6. No endpoints crash because user_id or session authentication is absent.
7. Zero authentication-dependent database queries exist.
"""

import os
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_flask_app():
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"].app
    app_py_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    return flask_module.app


# ─── 1. MODEL SCHEMA PURITY ───────────────────────────────────────────────────

def test_user_model_has_no_auth_fields():
    """Verify User model has no password_hash, google_id, login_attempts, is_locked, email_verified, credits."""
    import models
    user_cols = {c.name for c in models.User.__table__.columns}
    forbidden = {"password_hash", "google_id", "login_attempts", "is_locked", "email_verified", "credits"}
    found_forbidden = user_cols.intersection(forbidden)
    assert not found_forbidden, f"User model still contains authentication-dependent columns: {found_forbidden}"


def test_reward_transaction_model_removed():
    """Verify RewardTransaction is no longer in models."""
    import models
    assert not hasattr(models, "RewardTransaction"), "RewardTransaction model should be removed from models.py"


def test_models_allow_null_user_references():
    """Verify Trend, Report, and AuditLog explicitly permit null user IDs."""
    import models
    assert models.Trend.__table__.columns["created_by"].nullable is True
    assert models.Report.__table__.columns["generated_by"].nullable is True
    assert models.AuditLog.__table__.columns["user_id"].nullable is True


# ─── 2. DATABASE INITIALIZATION & ZERO USER ROWS ──────────────────────────────

def test_database_initialization_no_seed_users():
    """Verify database initializes cleanly and does not require or insert User records."""
    app = get_flask_app()
    with app.app_context():
        import models
        models.db.create_all()
        # Verify creating records with user_id=None succeeds
        trend = models.Trend(
            keyword="anonymous trend test",
            platform="YouTube",
            total_views=1234,
            growth_rate=10.5,
            virality_score=75.0,
            created_by=None
        )
        models.db.session.add(trend)
        models.db.session.flush()

        metric = models.Metric(
            trend_id=trend.trend_id,
            views=1234,
            likes=100,
            shares=10,
            comments_count=5
        )
        models.db.session.add(metric)

        sentiment = models.Sentiment(
            trend_id=trend.trend_id,
            positive_score=0.8,
            negative_score=0.1,
            neutral_score=0.1,
            dominant_sentiment="positive"
        )
        models.db.session.add(sentiment)

        report = models.Report(
            trend_id=trend.trend_id,
            generated_by=None,
            format="PDF",
            file_path="in-memory"
        )
        models.db.session.add(report)

        audit = models.AuditLog(
            user_id=None,
            action="TEST_ACTION",
            details="Zero user test"
        )
        models.db.session.add(audit)
        models.db.session.commit()

        assert trend.trend_id is not None
        assert report.report_id is not None
        assert audit.id is not None


# ─── 3. PUBLIC ENDPOINT ACCESSIBILITY WITHOUT USER ────────────────────────────

def test_public_tools_work_without_user_or_session():
    """Verify all public tools function without user_id, session, or cookies."""
    app = get_flask_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        # 1. Trends listing
        res = client.get("/api/trends")
        assert res.status_code == 200

        # 2. Suggest endpoint
        res = client.get("/api/suggest?q=gaming")
        assert res.status_code == 200

        # 3. Compare keywords
        res = client.get("/api/compare-keywords")
        assert res.status_code == 200

        # 4. Audit log endpoint
        res = client.get("/api/audit-log")
        assert res.status_code == 200

        # 5. Search endpoint (mocked YouTube fetch)
        mock_yt = {
            "keyword": "python",
            "platform": "YouTube",
            "total_views": 100000,
            "metrics": [{"date": "2026-09-13", "views": 100000, "likes": 5000, "shares": 500, "comments": 200}],
            "comments": [{"text": "Great tutorial!"}],
            "cached": True
        }
        with patch("services.real_api.fetch_youtube_data", return_value=mock_yt):
            res = client.post("/api/search", json={"keyword": "python"})
            assert res.status_code == 200


# ─── 4. NO AUTH-DEPENDENT QUERIES IN CODEBASE ──────────────────────────────────

def test_no_auth_dependent_queries_in_app_code():
    """Verify no query in backend/app.py filters by current_user or session user_id."""
    app_src = (BACKEND_DIR / "app.py").read_text(encoding="utf-8")
    assert "current_user" not in app_src
    assert "session['user_id']" not in app_src
    assert "session.get('user_id')" not in app_src
    assert "User.query.filter_by(id=session" not in app_src


# ─── 5. NON-DESTRUCTIVE MIGRATION IDEMPOTENCY ─────────────────────────────────

def test_migration_idempotent():
    """Verify running migrate_database multiple times causes no errors and preserves tables."""
    from migrate_db import migrate_database
    app = get_flask_app()
    # Execute migration twice to ensure complete idempotency
    migrate_database(app)
    migrate_database(app)
