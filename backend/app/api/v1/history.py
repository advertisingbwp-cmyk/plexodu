"""
History API Router (/api/v1/history/*)
=======================================
Provides paginated access to the authenticated user's tool execution history.

SECURITY INVARIANT:
Every query is strictly scoped to the session's user.id.
A client-supplied user_id in the query or body is NEVER used.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_current_user
from app.db.base import get_db
from app.db.models.history import HistoryEntry, ToolType
from app.db.models.user import User

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def get_history(
    tool_type: Optional[str] = Query(None, description="Optional filter by ToolType"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve tool execution history for the currently logged-in user.
    """
    stmt = (
        select(HistoryEntry)
        .where(HistoryEntry.user_id == user.id)
        .order_by(HistoryEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if tool_type:
        try:
            tool_enum = ToolType(tool_type.upper())
            stmt = stmt.where(HistoryEntry.tool_type == tool_enum)
        except ValueError:
            pass

    result = await db.execute(stmt)
    entries = result.scalars().all()

    return {
        "entries": [
            {
                "id": str(e.id),
                "tool_type": e.tool_type.value,
                "input": e.input_params,
                "result": e.output_results,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "count": len(entries),
        "offset": offset,
        "limit": limit,
    }
