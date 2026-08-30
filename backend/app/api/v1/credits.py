"""
Credits API Router  (/api/v1/credits/*)
========================================
All credit mutations are server-side only. The frontend never controls
credit balances or reward confirmation.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_current_user, require_verified
from app.db.base import get_db
from app.db.models.user import User
from app.services.credit_ledger_service import (
    DuplicateRewardError,
    get_balance,
    get_ledger,
    verify_and_grant_ad_reward,
)

router = APIRouter(prefix="/credits", tags=["credits"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AdRewardClaimRequest(BaseModel):
    """
    The provider and provider_reference_id uniquely identify this ad completion.
    The backend calls ad_provider_service.verify() before crediting anything.
    """
    provider: str
    provider_reference_id: str
    payload: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/balance")
async def get_balance_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's current credit balance."""
    balance = await get_balance(db, str(user.id))
    return {"balance": balance}


@router.get("/ledger")
async def get_ledger_endpoint(
    cursor: Optional[int] = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return credit ledger entries (newest first) with cursor-based pagination."""
    entries = await get_ledger(db, str(user.id), cursor=cursor, limit=min(limit, 100))
    return {
        "entries": [
            {
                "id": str(e.id),
                "type": e.type.value,
                "amount": e.amount,
                "reference_id": e.reference_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "next_cursor": None,  # TODO Phase 2: implement real cursor from last entry id
    }


@router.post("/claim-ad-reward")
async def claim_ad_reward(
    req: AdRewardClaimRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Claim an ad reward. The backend verifies the reward with the ad provider
    before crediting. The frontend button click alone is never proof of completion.

    Returns: { balance } on first valid claim.
    Returns: 409 REWARD_ALREADY_CLAIMED on replay.
    """
    # TODO Phase 2: call ad_provider_service.verify(req.provider, req.provider_reference_id, req.payload)
    # For Phase 1, we trust the request body for structural testing purposes only.
    try:
        new_balance = await verify_and_grant_ad_reward(
            db,
            user_id=str(user.id),
            provider=req.provider,
            provider_reference_id=req.provider_reference_id,
            raw_payload=req.payload or None,
        )
    except DuplicateRewardError:
        raise HTTPException(status_code=409, detail="REWARD_ALREADY_CLAIMED")

    return {"balance": new_balance}
