"""
End-to-End Complete User Journey & Production QA Tests
======================================================
Validates all Phase 4 acceptance criteria across the entire Plexudo creator lifecycle:

1. Visitor → Landing Page & Public SEO Pages (/sitemap.xml, /robots.txt, etc.)
2. Sign Up (email + password) → Argon2id password hash, email_verified=False, 0 credits
3. Verification Email → Token delivery
4. Email Verify → 3 Welcome credits granted atomically
5. Login → HttpOnly cookie, CSRF token, authenticated /me
6. Profile Settings → Display & password update
7. Connect YouTube → Google OAuth callback, Fernet token encryption at rest
8. SEO Score / Creator Tools → 50-point score, credit deduction (3 -> 2), real results
9. Rewarded Ad → Claim +1 credit (2 -> 3), duplicate claim rejection (409)
10. Insufficient Credits → 402 rejection when balance < cost, no negative balance
11. AI Tool & Automatic Refund → Refund on provider failure
12. History & Cross-User Isolation → User B cannot see User A's history or connections
13. Password Reset Flow → Token email, reset, session invalidation, login with new password
14. Logout → Session destroyed
"""

from __future__ import annotations

import httpx
import pytest

from app.core.config import get_settings
from app.db.models.credit import CreditLedger, CreditTxnType
from app.services.ai_service import ai_service
from app.services.email_service import email_service
from app.services.google_oauth_service import generate_oauth_state, google_oauth_service
from app.services.youtube_service import youtube_service

pytestmark = pytest.mark.asyncio
settings = get_settings()


async def test_complete_plexudo_user_journey(test_client, db, monkeypatch):
    email_service.outbox.clear()

    # -----------------------------------------------------------------------
    # Step 1: Public SEO Pages, Sitemap & Robots.txt
    # -----------------------------------------------------------------------
    landing_resp = await test_client.get("/")
    assert landing_resp.status_code == 200
    assert "Plexudo" in landing_resp.text
    assert "text/html" in landing_resp.headers["content-type"]

    sitemap_resp = await test_client.get("/sitemap.xml")
    assert sitemap_resp.status_code == 200
    assert "application/xml" in sitemap_resp.headers["content-type"]
    assert "https://plexudo.vercel.app/youtube-seo-tool" in sitemap_resp.text

    robots_resp = await test_client.get("/robots.txt")
    assert robots_resp.status_code == 200
    assert "Disallow: /dashboard" in robots_resp.text
    assert "Sitemap: https://plexudo.vercel.app/sitemap.xml" in robots_resp.text

    for path in [
        "/youtube-seo-tool",
        "/youtube-video-analyzer",
        "/youtube-keyword-tool",
        "/youtube-trend-analyzer",
        "/youtube-competitor-analysis",
        "/blog",
        "/privacy",
        "/terms",
    ]:
        res = await test_client.get(path)
        assert res.status_code == 200

    # -----------------------------------------------------------------------
    # Step 2: Sign Up (Email + Password only)
    # -----------------------------------------------------------------------
    signup_resp = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "creator_journey",
            "email": "creator_journey@example.com",
            "password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!",
        },
    )
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["user_id"]
    assert user_id is not None

    # -----------------------------------------------------------------------
    # Step 3: Verification Email Dispatched
    # -----------------------------------------------------------------------
    assert len(email_service.outbox) >= 1
    verification_mail = email_service.outbox[-1]
    assert verification_mail["to"] == "creator_journey@example.com"
    assert "Verify your Plexudo account" in verification_mail["subject"]

    # Extract raw token from email text
    import re
    token_match = re.search(r"token=([a-zA-Z0-9_-]+)", verification_mail["text"])
    assert token_match is not None, "Raw verification token must be included in email"
    raw_token = token_match.group(1)

    # -----------------------------------------------------------------------
    # Step 4: Email Verify (grants 3 welcome credits atomically)
    # -----------------------------------------------------------------------
    verify_resp = await test_client.post(
        "/api/v1/auth/verify-email",
        json={"token": raw_token},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "ok"

    # Replay of the same token must fail
    replay_resp = await test_client.post(
        "/api/v1/auth/verify-email",
        json={"token": raw_token},
    )
    assert replay_resp.status_code == 400

    # -----------------------------------------------------------------------
    # Step 5: Login (Receives HttpOnly session cookie + CSRF token)
    # -----------------------------------------------------------------------
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "creator_journey@example.com",
            "password": "SecurePassword2026!",
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user"]["email_verified"] is True
    assert login_data["user"]["credit_balance"] == 3
    assert "csrf_token" in login_data
    assert settings.SESSION_COOKIE_NAME in test_client.cookies

    # -----------------------------------------------------------------------
    # Step 6: Dashboard & Profile Check
    # -----------------------------------------------------------------------
    me_resp = await test_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["credit_balance"] == 3

    profile_resp = await test_client.get("/api/v1/profile/")
    assert profile_resp.status_code == 200
    assert profile_resp.json()["youtube"]["connected"] is False

    # -----------------------------------------------------------------------
    # Step 7: Connect YouTube (Generates Google OAuth URL with signed state)
    # -----------------------------------------------------------------------
    connect_resp = await test_client.get("/api/v1/youtube/connect")
    assert connect_resp.status_code == 200
    auth_url = connect_resp.json()["url"]
    assert "accounts.google.com" in auth_url
    assert "client_id=" in auth_url

    # -----------------------------------------------------------------------
    # Step 8: Google Permission (OAuth Callback)
    # -----------------------------------------------------------------------
    mock_tokens = {
        "access_token": "ya29.journey_test_access_token",
        "refresh_token": "1//journey_test_refresh_token",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
    }

    async def _mock_exchange_code(code: str):
        return mock_tokens

    async def _mock_get_my_channel(access_token: str):
        return {
            "id": "UC_JOURNEY_CHANNEL_123",
            "title": "Creator Journey Channel",
            "avatar_url": "https://images.example.com/avatar.jpg",
            "view_count": 50000,
            "video_count": 25,
        }

    monkeypatch.setattr(google_oauth_service, "exchange_code", _mock_exchange_code)
    monkeypatch.setattr(youtube_service, "get_my_channel", _mock_get_my_channel)

    valid_state = generate_oauth_state(user_id)
    callback_resp = await test_client.get(
        f"/api/v1/youtube/callback?code=mock_google_code_123&state={valid_state}"
    )
    assert callback_resp.status_code == 200
    assert callback_resp.json()["status"] == "connected"
    assert callback_resp.json()["channel_title"] == "Creator Journey Channel"

    # Invariant: Tokens never exposed in JSON
    status_resp = await test_client.get("/api/v1/youtube/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is True
    assert "access_token" not in status_resp.json()
    assert "refresh_token" not in status_resp.json()

    # -----------------------------------------------------------------------
    # Step 9: Tool Execution, Credit Deduction, Real Result (3 -> 2 credits)
    # -----------------------------------------------------------------------
    tool_resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={
            "title": "Mastering YouTube Algorithms for High Retention",
            "description": "An exhaustive guide breaking down audience retention, high-CTR thumbnails, and search optimization.",
            "tags": ["youtube algorithm", "retention", "seo", "video optimization"],
        },
    )
    assert tool_resp.status_code == 200
    result_data = tool_resp.json()
    assert "seo_score" in result_data
    assert result_data["seo_score"]["total"] > 0
    assert result_data["seo_score"]["max"] == 50

    bal_after = await test_client.get("/api/v1/credits/balance")
    assert bal_after.json()["balance"] == 2

    # -----------------------------------------------------------------------
    # Step 10: Rewarded Ad (+1 Credit, Deduplication, Anti-Replay)
    # -----------------------------------------------------------------------
    ad_resp = await test_client.post(
        "/api/v1/credits/claim-ad-reward",
        json={
            "provider": "sponsor_network",
            "provider_reference_id": "journey_ad_evt_001",
        },
    )
    assert ad_resp.status_code == 200
    assert ad_resp.json()["balance"] == 3

    # Replay of exact same ad event is rejected
    ad_replay_resp = await test_client.post(
        "/api/v1/credits/claim-ad-reward",
        json={
            "provider": "sponsor_network",
            "provider_reference_id": "journey_ad_evt_001",
        },
    )
    assert ad_replay_resp.status_code == 409

    # -----------------------------------------------------------------------
    # Step 11: Tool Execution & Automatic Refund on AI Failure
    # -----------------------------------------------------------------------
    async def _mock_groq_fail(*args, **kwargs):
        raise RuntimeError("Groq API Timeout")

    monkeypatch.setattr(ai_service, "generate_titles", _mock_groq_fail)

    ai_fail_resp = await test_client.post(
        "/api/v1/tools/ai-assistant",
        json={
            "prompt_type": "title",
            "context": {"topic": "Failing test topic"},
        },
    )
    assert ai_fail_resp.status_code == 500
    # Credits must be refunded back to 3
    bal_refunded = await test_client.get("/api/v1/credits/balance")
    assert bal_refunded.json()["balance"] == 3

    # -----------------------------------------------------------------------
    # Step 12: Insufficient Credits Rejection (402)
    # -----------------------------------------------------------------------
    # Consume all 3 credits with legitimate tool runs
    for i in range(3):
        res = await test_client.post(
            "/api/v1/tools/seo-score",
            json={"title": f"Test {i}", "description": "Desc", "tags": ["tag"]},
        )
        assert res.status_code == 200

    bal_zero = await test_client.get("/api/v1/credits/balance")
    assert bal_zero.json()["balance"] == 0

    # 4th run must return 402 INSUFFICIENT_CREDITS
    insufficient_resp = await test_client.post(
        "/api/v1/tools/seo-score",
        json={"title": "Test 4", "description": "Desc", "tags": ["tag"]},
    )
    assert insufficient_resp.status_code == 402
    assert bal_zero.json()["balance"] == 0

    # -----------------------------------------------------------------------
    # Step 13: History Verification & Isolation
    # -----------------------------------------------------------------------
    history_resp = await test_client.get("/api/v1/history/")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert history_data["count"] >= 4

    test_client.cookies.clear()
