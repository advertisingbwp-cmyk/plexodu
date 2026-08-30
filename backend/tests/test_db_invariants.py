"""
DB Invariant Tests
==================
Tests the critical database-level invariants documented in database-schema.md.
These tests run against a real PostgreSQL database — not mocks — because the
invariants are enforced by DB constraints, not application code alone.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.future import select

from app.db.models.credit import CreditLedger, CreditTxnType
from app.db.models.token import EmailVerificationToken, PasswordResetToken
from app.db.models.user import User
from app.services.auth_service import (
    TokenInvalidOrExpiredError,
    create_user,
    verify_email_token,
    create_email_verification_token,
    create_password_reset_token,
    consume_password_reset_token,
)
from app.services.credit_ledger_service import (
    DuplicateRewardError,
    InsufficientCreditsError,
    consume_credits,
    get_balance,
    grant_welcome_credits,
    verify_and_grant_ad_reward,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Invariant 1: Exactly one WELCOME_CREDIT per user (unique partial index)
# ---------------------------------------------------------------------------


async def test_welcome_credit_idempotency(db, unverified_user):
    """
    Calling grant_welcome_credits twice must result in exactly one ledger row
    and a balance of exactly WELCOME_CREDITS (3).
    The DB partial index enforces this atomically.
    """
    user_id = str(unverified_user.id)

    await grant_welcome_credits(db, user_id)
    # Second call must silently no-op (IntegrityError swallowed internally).
    await grant_welcome_credits(db, user_id)

    await db.refresh(unverified_user)
    assert unverified_user.credit_balance == 3, "Balance must be exactly 3 after one grant"

    result = await db.execute(
        select(CreditLedger).where(
            CreditLedger.user_id == unverified_user.id,
            CreditLedger.type == CreditTxnType.WELCOME_CREDIT,
        )
    )
    ledger_rows = result.scalars().all()
    assert len(ledger_rows) == 1, "Must have exactly one WELCOME_CREDIT ledger row"


# ---------------------------------------------------------------------------
# Invariant 2: No replaying an ad reward (unique constraint on ad_reward_events)
# ---------------------------------------------------------------------------


async def test_no_duplicate_ad_reward(db, test_user):
    """
    The same (provider, provider_reference_id) pair can only be credited once.
    The second attempt must raise DuplicateRewardError and leave balance unchanged.
    """
    user_id = str(test_user.id)
    provider = "test_provider"
    ref_id = "unique_event_abc123"

    initial_balance = test_user.credit_balance  # 3

    await verify_and_grant_ad_reward(db, user_id, provider, ref_id)

    with pytest.raises(DuplicateRewardError):
        await verify_and_grant_ad_reward(db, user_id, provider, ref_id)

    await db.refresh(test_user)
    assert test_user.credit_balance == initial_balance + 1, (
        "Balance must increase by exactly 1 (one reward, not two)"
    )


# ---------------------------------------------------------------------------
# Invariant 3: Guarded credit decrement prevents negative balances
# ---------------------------------------------------------------------------


async def test_guarded_credit_decrement_insufficient(db, test_user):
    """
    A user with 1 credit cannot have 2 credits consumed. The second consume
    must raise InsufficientCreditsError and leave the balance at 0.
    """
    # Set balance to 1
    test_user.credit_balance = 1
    await db.commit()

    await consume_credits(db, str(test_user.id), "SEO_SCORE", cost=1)

    with pytest.raises(InsufficientCreditsError):
        await consume_credits(db, str(test_user.id), "SEO_SCORE", cost=1)

    await db.refresh(test_user)
    assert test_user.credit_balance == 0, "Balance must be 0, never negative"


async def test_guarded_credit_decrement_exact_balance(db, test_user):
    """Consuming exactly the available balance must succeed and leave 0."""
    balance = test_user.credit_balance  # 3
    new_balance = await consume_credits(db, str(test_user.id), "SEO_SCORE", cost=balance)
    assert new_balance == 0

    await db.refresh(test_user)
    assert test_user.credit_balance == 0


# ---------------------------------------------------------------------------
# Invariant 4: users.credit_balance matches SUM(credit_ledger.amount)
# ---------------------------------------------------------------------------


async def test_credit_balance_matches_ledger_sum(db):
    """
    After a sequence of grants and consumes, the users.credit_balance must
    equal the sum of all credit_ledger.amount rows for that user.
    """
    # Create a fresh user so the ledger starts clean.
    user = await create_user(db, "ledger_test_user", "ledger@example.com", "Str0ngP@ssword!")
    user_id = str(user.id)

    # Grant welcome credits (3)
    await grant_welcome_credits(db, user_id)
    # Grant ad reward (+1)
    await verify_and_grant_ad_reward(db, user_id, "p1", "r1")
    # Grant another ad reward (+1)
    await verify_and_grant_ad_reward(db, user_id, "p1", "r2")
    # Consume 2
    await consume_credits(db, user_id, "SEO_SCORE", cost=2)

    await db.refresh(user)

    # Expected: 3 + 1 + 1 - 2 = 3
    assert user.credit_balance == 3

    # Verify ledger sum matches
    result = await db.execute(
        select(CreditLedger).where(CreditLedger.user_id == user.id)
    )
    ledger_rows = result.scalars().all()
    ledger_sum = sum(row.amount for row in ledger_rows)
    assert ledger_sum == user.credit_balance, (
        f"Ledger sum {ledger_sum} must equal credit_balance {user.credit_balance}"
    )


# ---------------------------------------------------------------------------
# Invariant 5: Verification token is single-use
# ---------------------------------------------------------------------------


async def test_token_single_use(db, unverified_user):
    """
    Consuming an email verification token twice must raise
    TokenInvalidOrExpiredError on the second call.
    """
    raw_token = await create_email_verification_token(db, str(unverified_user.id))

    # First use — must succeed.
    user = await verify_email_token(db, raw_token)
    assert user.email_verified_at is not None

    # Second use — must fail.
    with pytest.raises(TokenInvalidOrExpiredError):
        await verify_email_token(db, raw_token)


# ---------------------------------------------------------------------------
# Invariant 6: Password reset token expires
# ---------------------------------------------------------------------------


async def test_reset_token_expiry(db, test_user):
    """
    A password reset token with expires_at in the past must raise
    TokenInvalidOrExpiredError.
    """
    from app.core.security import generate_token, hash_token

    raw_token = generate_token()
    expired_token = PasswordResetToken(
        user_id=test_user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),  # already expired
        is_consumed=False,
    )
    db.add(expired_token)
    await db.commit()

    with pytest.raises(TokenInvalidOrExpiredError):
        await consume_password_reset_token(db, raw_token, "NewP@ssword123!")
