"""
Credit Ledger Service
=====================
All credit mutations follow the invariants documented in database-schema.md:

1. users.credit_balance is the authoritative counter.
2. Every mutation writes a credit_ledger row AND updates users.credit_balance
   in the SAME database transaction.
3. Guarded decrement prevents negative balances without explicit locking.
4. The unique partial index on credit_ledger ensures only one WELCOME_CREDIT per user.
5. Ad reward deduplication is enforced by a unique constraint on ad_reward_events.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.credit import AdRewardEvent, CreditLedger, CreditTxnType
from app.db.models.user import User

settings = get_settings()


class InsufficientCreditsError(Exception):
    """Raised when a user does not have enough credits for an operation."""


class DuplicateRewardError(Exception):
    """Raised when an ad reward has already been claimed."""


def _to_uuid(val: str | uuid.UUID) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


async def _execute_credit_mutation(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    ledger_type: CreditTxnType,
    signed_amount: int,  # positive = grant, negative = consume
    reference_id: Optional[str] = None,
    extra_objects: Optional[list] = None,
) -> int:
    """
    Atomically:
      1. Increments/decrements users.credit_balance by `signed_amount`.
      2. Inserts a credit_ledger row.
      3. Inserts any extra_objects (e.g. AdRewardEvent).

    For decrements (signed_amount < 0) uses a guarded UPDATE that only
    succeeds when the current balance is sufficient.

    Returns the new balance.
    Raises InsufficientCreditsError if guarded decrement matches 0 rows.
    """
    uid = _to_uuid(user_id)

    if signed_amount < 0:
        # Guarded atomic decrement — Postgres row-level lock prevents races.
        cost = abs(signed_amount)
        stmt = (
            update(User)
            .where(User.id == uid, User.credit_balance >= cost)
            .values(credit_balance=User.credit_balance - cost)
            .returning(User.credit_balance)
        )
        result = await db.execute(stmt)
        new_balance = result.scalar_one_or_none()
        if new_balance is None:
            await db.rollback()
            raise InsufficientCreditsError(
                f"Insufficient credits: cost={cost} for user {uid}"
            )
    else:
        stmt = (
            update(User)
            .where(User.id == uid)
            .values(credit_balance=User.credit_balance + signed_amount)
            .returning(User.credit_balance)
        )
        result = await db.execute(stmt)
        new_balance = result.scalar_one()

    ledger_row = CreditLedger(
        user_id=uid,
        amount=signed_amount,
        type=ledger_type,
        reference_id=reference_id,
    )
    db.add(ledger_row)

    for obj in extra_objects or []:
        db.add(obj)

    await db.commit()
    return new_balance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def grant_welcome_credits(db: AsyncSession, user_id: str | uuid.UUID) -> None:
    """
    Grant WELCOME_CREDITS to a newly verified user.

    Idempotent: the unique partial index on credit_ledger
    (WHERE type = 'WELCOME_CREDIT') causes a second call to silently no-op.
    """
    try:
        await _execute_credit_mutation(
            db,
            user_id=user_id,
            ledger_type=CreditTxnType.WELCOME_CREDIT,
            signed_amount=settings.WELCOME_CREDITS,
            reference_id="welcome",
        )
    except IntegrityError:
        # Unique partial index violation → already granted, swallow silently.
        await db.rollback()


async def verify_and_grant_ad_reward(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    provider: str,
    provider_reference_id: str,
    raw_payload: Optional[dict] = None,
) -> int:
    """
    Grant AD_REWARD_CREDITS for a verified ad completion.

    Raises DuplicateRewardError if (provider, provider_reference_id) was already
    credited — enforced by a unique constraint on ad_reward_events.

    Returns the new credit balance.
    """
    uid = _to_uuid(user_id)
    event = AdRewardEvent(
        user_id=uid,
        provider=provider,
        provider_reference_id=provider_reference_id,
        raw_payload=raw_payload,
    )
    try:
        return await _execute_credit_mutation(
            db,
            user_id=uid,
            ledger_type=CreditTxnType.AD_REWARD,
            signed_amount=settings.AD_REWARD_CREDITS,
            reference_id=f"{provider}:{provider_reference_id}",
            extra_objects=[event],
        )
    except IntegrityError:
        await db.rollback()
        raise DuplicateRewardError(
            f"Reward already claimed: {provider}/{provider_reference_id}"
        )


async def consume_credits(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    tool_type: str,
    cost: int,
    reference_id: Optional[str] = None,
) -> int:
    """
    Atomically deduct `cost` credits from the user's balance.

    Raises InsufficientCreditsError if the balance is too low.
    Returns the new balance.
    """
    return await _execute_credit_mutation(
        db,
        user_id=user_id,
        ledger_type=CreditTxnType.TOOL_USAGE,
        signed_amount=-cost,
        reference_id=reference_id or tool_type,
    )


async def refund_credits(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    cost: int,
    reference_id: Optional[str] = None,
) -> None:
    """
    Issue a REFUND for a failed tool operation.
    Called after a downstream failure (YouTube API, Groq) that occurred after
    credits were already consumed.
    """
    await _execute_credit_mutation(
        db,
        user_id=user_id,
        ledger_type=CreditTxnType.REFUND,
        signed_amount=cost,
        reference_id=reference_id,
    )


async def get_balance(db: AsyncSession, user_id: str | uuid.UUID) -> int:
    uid = _to_uuid(user_id)
    stmt = select(User.credit_balance).where(User.id == uid)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() or 0


async def get_ledger(
    db: AsyncSession,
    user_id: str | uuid.UUID,
    cursor: Optional[int] = None,
    limit: int = 20,
) -> list[CreditLedger]:
    """Return ledger entries for a user, newest first, with cursor-based pagination."""
    uid = _to_uuid(user_id)
    stmt = (
        select(CreditLedger)
        .where(CreditLedger.user_id == uid)
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
