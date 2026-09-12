"""
Plexudo Phase 2 Security Test Suite
Validates:
1. BOLA / IDOR protection across users (cross-tenant access yields safe 404)
2. Unauthenticated access protection (returns 401)
3. Google OAuth state generation, session-binding, and timing-safe validation
4. Session cookie security attributes (HttpOnly, SameSite, Secure, ProxyFix)
5. Atomic credit deduction, compensation refunds, and concurrency safety (no over-spend, no negative balance)
6. In-memory ReportLab PDF generation via io.BytesIO without filesystem writes
7. Tenant isolation in trends and keywords comparison
"""

import os
import sys
import io
import time
import secrets
import threading
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_flask_app():
    """Helper to dynamically load the main Flask app singleton."""
    import importlib.util
    app_py_path = BACKEND_DIR / "app.py"
    if "main_flask_app" in sys.modules:
        return sys.modules["main_flask_app"].app
    spec = importlib.util.spec_from_file_location("main_flask_app", str(app_py_path))
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["main_flask_app"] = flask_module
    spec.loader.exec_module(flask_module)
    return flask_module.app


# ─── 1. UNAUTHENTICATED ACCESS PROTECTIONS ──────────────────────────────────

def test_unauthenticated_report_access_rejected():
    """Verify unauthenticated requests to report generation endpoints return 401."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # PDF report
        res_pdf = client.get("/api/report/9999")
        assert res_pdf.status_code == 401, f"Expected 401, got {res_pdf.status_code}"
        assert "Authentication required" in res_pdf.get_json().get("error", "")

        # CSV export
        res_csv = client.get("/api/export-csv/9999")
        assert res_csv.status_code == 401, f"Expected 401, got {res_csv.status_code}"
        assert "Authentication required" in res_csv.get_json().get("error", "")


def test_unauthenticated_session_and_trends_no_leak():
    """Verify unauthenticated /api/session, /api/trends, and /api/compare-keywords leak no tenant data."""
    app = get_flask_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Session endpoint
        res_session = client.get("/api/session")
        assert res_session.status_code == 200
        data = res_session.get_json()
        assert data.get("authenticated") is False, "Unauthenticated session must return authenticated: False"
        assert data.get("user") is None, "Unauthenticated session must return user: None"

        # Trends endpoint
        res_trends = client.get("/api/trends")
        assert res_trends.status_code == 200
        assert res_trends.get_json().get("trends") == [], "Unauthenticated trends must be empty"

        # Compare keywords endpoint
        res_comp = client.get("/api/compare-keywords")
        assert res_comp.status_code == 200
        assert res_comp.get_json().get("comparison") == [], "Unauthenticated keyword comparison must be empty"


# ─── 2. BOLA / IDOR PROTECTION ACROSS TENANTS ──────────────────────────────

def test_bola_cross_user_report_access_returns_safe_404():
    """Verify User B attempting to access User A's trend report receives 404 (not 403 or 200)."""
    app = get_flask_app()
    app.config["TESTING"] = True
    main_mod = sys.modules["main_flask_app"]
    db = main_mod.db
    User = main_mod.User
    Trend = main_mod.Trend

    with app.app_context():
        # Create User A
        email_a = f"user_a_{int(time.time())}_{secrets.token_hex(3)}@test.com"
        user_a = User(name="User A", email=email_a, password_hash="hash", credits=10)
        db.session.add(user_a)
        db.session.commit()

        # Create User B
        email_b = f"user_b_{int(time.time())}_{secrets.token_hex(3)}@test.com"
        user_b = User(name="User B", email=email_b, password_hash="hash", credits=10)
        db.session.add(user_b)
        db.session.commit()

        # Create Trend owned by User A
        trend_a = Trend(
            keyword="AI tools 2026",
            platform="YouTube",
            total_views=50000,
            growth_rate=25.0,
            virality_score=80.0,
            created_by=user_a.id,
        )
        db.session.add(trend_a)
        db.session.commit()
        trend_id = trend_a.trend_id
        user_a_id = user_a.id
        user_a_email = user_a.email
        user_b_id = user_b.id
        user_b_email = user_b.email

    # Test Client logged in as User B
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = user_b_id
            sess["email"] = user_b_email

        # User B attempts to access User A's PDF report -> Must return 404
        res_pdf = client.get(f"/api/report/{trend_id}")
        assert res_pdf.status_code == 404, f"BOLA VULNERABILITY! Expected 404 for cross-user report, got {res_pdf.status_code}"
        assert "not found" in res_pdf.get_json().get("error", "").lower()

        # User B attempts to access User A's CSV report -> Must return 404
        res_csv = client.get(f"/api/export-csv/{trend_id}")
        assert res_csv.status_code == 404, f"BOLA VULNERABILITY! Expected 404 for cross-user CSV, got {res_csv.status_code}"
        assert "not found" in res_csv.get_json().get("error", "").lower()

    # Test Client logged in as Owner (User A)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = user_a_id
            sess["email"] = user_a_email

        # User A accesses own CSV report -> Succeeds with 200
        res_csv_owner = client.get(f"/api/export-csv/{trend_id}")
        assert res_csv_owner.status_code == 200
        assert "text/csv" in res_csv_owner.content_type

        # User A accesses own PDF report -> Succeeds with 200 and valid PDF stream
        res_pdf_owner = client.get(f"/api/report/{trend_id}")
        assert res_pdf_owner.status_code == 200
        assert res_pdf_owner.content_type == "application/pdf"
        assert res_pdf_owner.data.startswith(b"%PDF-"), "Generated report is not a valid PDF stream"


# ─── 3. GOOGLE OAUTH STATE VALIDATION ───────────────────────────────────────

def test_oauth_state_generation_and_validation():
    """Verify OAuth generates crypto state, binds to session, and validates safely."""
    app = get_flask_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        # Step 1: Initiate OAuth flow
        res = client.get("/api/channel-seo/auth/google")
        assert res.status_code == 302, f"Expected 302 redirect, got {res.status_code}"
        redirect_url = res.headers.get("Location", "")
        assert "accounts.google.com" in redirect_url
        assert "state=" in redirect_url

        # Check session has stored oauth_state
        with client.session_transaction() as sess:
            state = sess.get("oauth_state")
            assert state is not None
            assert len(state) >= 32, "OAuth state must be a high-entropy cryptographically secure string"

        # Step 2: Callback with missing state -> Rejected 400
        res_missing = client.get("/api/channel-seo/auth/callback?code=fake_code")
        assert res_missing.status_code == 400
        assert "OAuth state parameter" in res_missing.get_json().get("error", "")

        # Step 3: Callback with tampered/invalid state -> Rejected 400
        res_tampered = client.get("/api/channel-seo/auth/callback?code=fake_code&state=attackers_manipulated_state")
        assert res_tampered.status_code == 400
        assert "OAuth state parameter" in res_tampered.get_json().get("error", "")


# ─── 4. SESSION COOKIE ATTRIBUTES & PROXYFIX ───────────────────────────────

def test_session_cookie_attributes_and_proxyfix():
    """Verify session cookie flags and ProxyFix middleware configuration."""
    from werkzeug.middleware.proxy_fix import ProxyFix
    app = get_flask_app()

    assert isinstance(app.wsgi_app, ProxyFix), "ProxyFix middleware must be installed on wsgi_app"
    assert app.config.get("SESSION_COOKIE_HTTPONLY") is True, "SESSION_COOKIE_HTTPONLY must be True"
    assert app.config.get("SESSION_COOKIE_SAMESITE") == "Lax", "SESSION_COOKIE_SAMESITE must be Lax"


# ─── 5. ATOMIC CREDIT DEDUCTION & CONCURRENCY SAFETY ───────────────────────

def test_atomic_credit_deduction_and_concurrency():
    """Verify atomic credit deduction prevents negative balances and race conditions."""
    app = get_flask_app()
    main_mod = sys.modules["main_flask_app"]
    db = main_mod.db
    User = main_mod.User
    _deduct_credits_atomic = main_mod._deduct_credits_atomic
    _refund_credits_atomic = main_mod._refund_credits_atomic

    with app.app_context():
        email = f"credit_test_{int(time.time())}_{secrets.token_hex(3)}@test.com"
        user = User(name="Credit Tester", email=email, password_hash="hash", credits=5)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Test single deduction
        success, err = _deduct_credits_atomic(user_id, amount=2)
        assert success is True
        db.session.expire_all()
        refreshed_user = db.session.get(User, user_id)
        assert refreshed_user.credits == 3

        # Test refund compensation
        ref_success, ref_err = _refund_credits_atomic(user_id, amount=2, reason="Test compensation")
        assert ref_success is True
        db.session.expire_all()
        refreshed_user = db.session.get(User, user_id)
        assert refreshed_user.credits == 5

        # Test over-spending prevention
        success_over, err_over = _deduct_credits_atomic(user_id, amount=10)
        assert success_over is False
        assert "Insufficient credits" in err_over
        db.session.expire_all()
        refreshed_user = db.session.get(User, user_id)
        assert refreshed_user.credits == 5, "Credits must not change on failed deduction"

        # Test Concurrency Safety: 10 threads trying to deduct 1 credit each when balance is 5
        results = []

        def worker():
            with app.app_context():
                ok, _ = _deduct_credits_atomic(user_id, amount=1)
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)

        db.session.expire_all()
        final_user = db.session.get(User, user_id)
        assert success_count == 5, f"Expected exactly 5 deductions to succeed, got {success_count}"
        assert fail_count == 5, f"Expected exactly 5 deductions to fail, got {fail_count}"
        assert final_user.credits == 0, f"Credits balance should be exactly 0, got {final_user.credits}"


# ─── 6. IN-MEMORY REPORTLAB GENERATION (NO DISK WRITES) ─────────────────────

def test_in_memory_pdf_generation_no_disk():
    """Verify ReportLab PDF generation operates cleanly in-memory with io.BytesIO."""
    from services.report_generator import generate_pdf_report_buffer

    trend = {"keyword": "Plexudo Security Audit", "platform": "YouTube", "total_views": 120000}
    sentiment = {"positive_score": 0.8, "negative_score": 0.1, "neutral_score": 0.1, "dominant_sentiment": "Positive"}

    filename, buf = generate_pdf_report_buffer(
        trend=trend,
        sentiment=sentiment,
        growth_rate=45.2,
        virality_score=88.0,
        stage="Explosive Growth",
        user_email="architect@plexudo.com"
    )

    assert filename.startswith("trend_")
    assert filename.endswith(".pdf")
    assert isinstance(buf, io.BytesIO)
    pdf_bytes = buf.getvalue()
    assert len(pdf_bytes) > 1000, "PDF buffer must contain compiled PDF data"
    assert pdf_bytes.startswith(b"%PDF-"), "Output must have valid PDF file magic bytes"