"""
Email Service Tests
===================
Tests:
1. Transactional verification and reset email link generation.
2. Integration with /auth/signup (dispatches verification email).
3. Integration with /auth/forgot-password (dispatches password reset email).
4. Outbox recording and verification token delivery.
"""

from __future__ import annotations

import pytest

from app.services.email_service import email_service

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit: Email Generation
# ---------------------------------------------------------------------------


async def test_send_verification_email_records_in_outbox():
    email_service.outbox.clear()

    raw_token = "secure_token_12345"
    res = await email_service.send_verification_email("user@example.com", raw_token)
    assert res is True
    assert len(email_service.outbox) == 1

    entry = email_service.outbox[0]
    assert entry["to"] == "user@example.com"
    assert "Verify your Plexudo account" in entry["subject"]
    assert raw_token in entry["text"]
    assert raw_token in entry["html"]


async def test_send_password_reset_email_records_in_outbox():
    email_service.outbox.clear()

    raw_token = "reset_token_67890"
    res = await email_service.send_password_reset_email("user@example.com", raw_token)
    assert res is True
    assert len(email_service.outbox) == 1

    entry = email_service.outbox[0]
    assert entry["to"] == "user@example.com"
    assert "Reset your Plexudo password" in entry["subject"]
    assert raw_token in entry["text"]
    assert raw_token in entry["html"]


# ---------------------------------------------------------------------------
# Integration: Real Email Delivery on API Endpoints
# ---------------------------------------------------------------------------


async def test_signup_dispatches_real_email(test_client, db):
    email_service.outbox.clear()

    resp = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "username": "email_user",
            "email": "email_user@example.com",
            "password": "Str0ngP@ssword!",
            "confirm_password": "Str0ngP@ssword!",
        },
    )
    assert resp.status_code == 201
    assert len(email_service.outbox) >= 1

    entry = email_service.outbox[-1]
    assert entry["to"] == "email_user@example.com"
    assert "Verify" in entry["subject"]


async def test_forgot_password_dispatches_email(test_client, db, test_user):
    email_service.outbox.clear()

    resp = await test_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user.email},
    )
    assert resp.status_code == 202
    assert len(email_service.outbox) >= 1

    entry = email_service.outbox[-1]
    assert entry["to"] == test_user.email
    assert "Reset" in entry["subject"]
