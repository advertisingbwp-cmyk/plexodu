"""
Tools API Router  (/api/v1/tools/*)
=====================================
All tool endpoints:
1. Require an authenticated, verified session.
2. Look up credit cost dynamically from TOOL_CREDIT_COSTS.
3. Atomically deduct credits BEFORE running tool operations.
4. Execute real YouTube Data API v3 and Groq AI logic (zero fake fallbacks).
5. Persist the execution in history_entries.
6. Automatically refund credits if downstream provider fails.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.session import require_verified
from app.db.base import get_db
from app.db.models.history import HistoryEntry, ToolType
from app.db.models.user import User
from app.services.ai_service import AiServiceError, ai_service
from app.services.credit_ledger_service import (
    InsufficientCreditsError,
    consume_credits,
    refund_credits,
)
from app.services.youtube_service import (
    YouTubeApiError,
    YouTubeNotFoundError,
    YouTubeQuotaExceededError,
    extract_video_id,
    youtube_service,
)

logger = logging.getLogger("plexudo.tools")
settings = get_settings()
router = APIRouter(prefix="/tools", tags=["tools"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class SeoScoreRequest(BaseModel):
    video_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)


class VideoAnalyzerRequest(BaseModel):
    video_url_or_id: str


class KeywordToolRequest(BaseModel):
    seed_keyword: str
    region: str = "US"


class TrendAnalyzerRequest(BaseModel):
    region: str = "US"


class CompetitorAnalysisRequest(BaseModel):
    channel_url_or_id: str


class AiAssistantRequest(BaseModel):
    prompt_type: str
    context: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared Tool Runner
# ---------------------------------------------------------------------------


async def _run_tool_with_credit_guard(
    tool_type: ToolType,
    cost_key: str,
    user: User,
    db: AsyncSession,
    input_params: dict[str, Any],
    tool_coro_fn: Callable[[], Coroutine[Any, Any, dict[str, Any]]],
) -> dict[str, Any]:
    """
    Executes a creator tool with atomic credit deduction and automated refund on failure:
    1. Check and deduct credits atomically via guarded UPDATE.
    2. Run real tool logic.
    3. On failure: issue REFUND ledger entry and increment user balance back.
    4. On success: record history entry.
    """
    cost = settings.TOOL_CREDIT_COSTS.get(cost_key, 1)

    # 1. Deduct credits atomically
    try:
        await consume_credits(db, user.id, tool_type.value, cost=cost)
    except InsufficientCreditsError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="INSUFFICIENT_CREDITS",
        )

    # 2. Run real tool operation
    try:
        result = await tool_coro_fn()
    except (YouTubeNotFoundError, YouTubeQuotaExceededError, YouTubeApiError, AiServiceError, Exception) as exc:
        # Downstream provider error — refund the credit atomically so user is not penalized
        logger.error("Tool '%s' execution failed: %s. Issuing refund of %d credits.", tool_type.value, exc, cost)
        await refund_credits(db, user.id, cost=cost, reference_id=f"refund_{tool_type.value}")

        if isinstance(exc, YouTubeNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        if isinstance(exc, YouTubeQuotaExceededError):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
        if isinstance(exc, YouTubeApiError):
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        if isinstance(exc, AiServiceError):
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    # 3. Store history record
    try:
        entry = HistoryEntry(
            user_id=user.id,
            tool_type=tool_type,
            input_params=input_params,
            output_results=result,
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        logger.warning("Failed to record history entry: %s", e)
        await db.rollback()

    return result


# ---------------------------------------------------------------------------
# Scoring Algorithms
# ---------------------------------------------------------------------------


def calculate_seo_breakdown(title: str, description: str, tags: list[str]) -> dict[str, Any]:
    """Calculate YouTube SEO score out of 50 based on title, description, tags, and overlap."""
    t_len = len(title)
    d_len = len(description)
    tag_count = len(tags)

    # Title score (0-10)
    title_score = 10 if (30 <= t_len <= 70) else (7 if t_len > 0 else 0)

    # Description score (0-10)
    desc_score = 10 if d_len >= 250 else (6 if d_len >= 50 else (2 if d_len > 0 else 0))

    # Tag density score (0-10)
    tag_score = 10 if (8 <= tag_count <= 25) else (5 if tag_count > 0 else 0)

    # Keyword volume indicator (0-10)
    volume_score = 8 if (title_score > 5 and tag_count > 5) else 5

    # Triple overlap (keywords in title, description, and tags) (0-10)
    title_words = set(title.lower().split())
    desc_words = set(description.lower().split())
    tags_normalized = set(" ".join(tags).lower().split())
    overlap = title_words.intersection(desc_words).intersection(tags_normalized)
    overlap_score = 10 if len(overlap) >= 2 else (5 if len(overlap) >= 1 else 2)

    total = title_score + desc_score + tag_score + volume_score + overlap_score

    return {
        "total": min(total, 50),
        "max": 50,
        "breakdown": {
            "title_optimization": title_score,
            "description_depth": desc_score,
            "tag_density": tag_score,
            "keyword_volume": volume_score,
            "triple_overlap": overlap_score,
        },
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/seo-score")
async def tool_seo_score(
    req: SeoScoreRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Score YouTube video SEO out of 50.
    Can analyze a live video ID or candidate title/description/tags.
    """
    async def _execute():
        title = req.title or ""
        description = req.description or ""
        tags = req.tags or []
        metadata = None

        if req.video_id:
            vid_info = await youtube_service.get_video_info(req.video_id)
            title = vid_info["title"]
            description = vid_info["description"]
            tags = vid_info.get("tags", [])
            metadata = {
                "video_id": vid_info["video_id"],
                "channel_title": vid_info["channel_title"],
                "view_count": vid_info["view_count"],
                "thumbnail_url": vid_info["thumbnail_url"],
            }

        score = calculate_seo_breakdown(title, description, tags)
        return {
            "seo_score": score,
            "title": title,
            "description": description,
            "tags": tags,
            "metadata": metadata,
        }

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.SEO_SCORE,
        cost_key="SEO_SCORE",
        user=user,
        db=db,
        input_params=req.model_dump(exclude_none=True),
        tool_coro_fn=_execute,
    )


@router.post("/video-analyzer")
async def tool_video_analyzer(
    req: VideoAnalyzerRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive YouTube video analysis: live metadata + SEO audit + AI optimization advice.
    """
    async def _execute():
        video_id = extract_video_id(req.video_url_or_id)
        vid_info = await youtube_service.get_video_info(video_id)

        score = calculate_seo_breakdown(
            vid_info["title"],
            vid_info["description"],
            vid_info.get("tags", []),
        )

        # AI-powered title improvement suggestions
        ai_recommendations = {}
        try:
            ai_recommendations = await ai_service.improve_title(
                vid_info["title"],
                context={"description": vid_info["description"][:200], "tags": vid_info.get("tags", [])[:5]},
            )
        except Exception as e:
            logger.info("AI title improvement skipped in video analyzer: %s", e)

        return {
            "video": vid_info,
            "seo_score": score,
            "ai_audit": ai_recommendations,
        }

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.VIDEO_ANALYZER,
        cost_key="VIDEO_ANALYZER",
        user=user,
        db=db,
        input_params=req.model_dump(),
        tool_coro_fn=_execute,
    )


@router.post("/keyword-tool")
async def tool_keyword_tool(
    req: KeywordToolRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Explore YouTube keywords with AI clustering and live video search insights.
    """
    async def _execute():
        # Get AI keyword clusters
        ai_clusters = await ai_service.suggest_keywords(req.seed_keyword, region=req.region)

        # Get top YouTube ranking videos for this seed keyword
        sample_results = await youtube_service.search_videos(
            query=req.seed_keyword,
            region=req.region,
            max_results=8,
        )

        return {
            "seed_keyword": req.seed_keyword,
            "region": req.region,
            "keyword_map": ai_clusters,
            "top_ranking_videos": sample_results,
            "volume_indicator": "estimated",
        }

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.KEYWORD_TOOL,
        cost_key="KEYWORD_TOOL",
        user=user,
        db=db,
        input_params=req.model_dump(),
        tool_coro_fn=_execute,
    )


@router.post("/trend-analyzer")
async def tool_trend_analyzer(
    req: TrendAnalyzerRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze YouTube trending topics in a specific region.
    """
    async def _execute():
        trending_videos = await youtube_service.get_trending_videos(
            region=req.region,
            max_results=20,
        )

        # Extract dominant tags and channels
        tag_frequency: dict[str, int] = {}
        for v in trending_videos:
            for tag in v.get("tags", []):
                t_lower = tag.lower()
                tag_frequency[t_lower] = tag_frequency.get(t_lower, 0) + 1

        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)[:15]

        return {
            "region": req.region,
            "trending_videos": trending_videos,
            "breakout_tags": [{"tag": tag, "frequency": count} for tag, count in sorted_tags],
        }

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.TREND_ANALYZER,
        cost_key="TREND_ANALYZER",
        user=user,
        db=db,
        input_params=req.model_dump(),
        tool_coro_fn=_execute,
    )


@router.post("/competitor-analysis")
async def tool_competitor_analysis(
    req: CompetitorAnalysisRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a competitor's public YouTube channel (stats, top uploads, upload pattern).
    """
    async def _execute():
        channel = await youtube_service.get_channel_info(req.channel_url_or_id)
        uploads = await youtube_service.get_channel_videos(
            channel_id=channel["id"],
            uploads_playlist_id=channel.get("uploads_playlist_id"),
            max_results=12,
        )

        return {
            "channel": channel,
            "recent_uploads": uploads,
            "upload_count": len(uploads),
        }

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.COMPETITOR_ANALYSIS,
        cost_key="COMPETITOR_ANALYSIS",
        user=user,
        db=db,
        input_params=req.model_dump(),
        tool_coro_fn=_execute,
    )


@router.post("/ai-assistant")
async def tool_ai_assistant(
    req: AiAssistantRequest,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    """
    AI Creator Assistant powered by Groq.
    Supports title generation, hooks, descriptions, and custom growth questions.
    """
    async def _execute():
        return await ai_service.creator_assistant(req.prompt_type, req.context)

    return await _run_tool_with_credit_guard(
        tool_type=ToolType.AI_ASSISTANT,
        cost_key="AI_ASSISTANT",
        user=user,
        db=db,
        input_params=req.model_dump(),
        tool_coro_fn=_execute,
    )
