"""
Groq AI Service
===============
Provides AI-powered YouTube creator tools using the Groq API (server-side only).
Supports title generation, SEO optimization, keyword suggestions, hooks, and descriptions.

CRITICAL INVARIANTS:
1. GROQ_API_KEY is never exposed to the frontend.
2. Model name is configurable via GROQ_MODEL / AI_MODEL environment variables.
3. Safe validation, timeouts, and error handling.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("plexudo.ai")
settings = get_settings()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Typed Exceptions
# ---------------------------------------------------------------------------


class AiServiceError(Exception):
    """Base exception for AI service errors."""

    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class AiTimeoutError(AiServiceError):
    def __init__(self, message: str = "AI request timed out"):
        super().__init__(message=message, status_code=504)


class AiRateLimitError(AiServiceError):
    def __init__(self, message: str = "AI service rate limit reached, please try again shortly"):
        super().__init__(message=message, status_code=429)


# ---------------------------------------------------------------------------
# Helper: Extract JSON from AI text response
# ---------------------------------------------------------------------------


def extract_json_payload(text: str) -> Any:
    """Safely extract JSON object or array from markdown-fenced or raw AI responses."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # If not strictly JSON, try to extract array or dict substring
        arr_match = re.search(r"(\[[\s\S]*\])", cleaned)
        if arr_match:
            try:
                return json.loads(arr_match.group(1))
            except json.JSONDecodeError:
                pass
        obj_match = re.search(r"(\{[\s\S]*\})", cleaned)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except json.JSONDecodeError:
                pass
        return {"raw_response": text}


# ---------------------------------------------------------------------------
# AI Service Implementation
# ---------------------------------------------------------------------------


class AiService:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS)

    async def _chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1500,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """Call Groq chat completion API with configured model and error handling."""
        api_key = settings.GROQ_API_KEY
        if not api_key or api_key == "your-groq-api-key":
            logger.warning("GROQ_API_KEY is not configured with a valid key")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.EFFECTIVE_AI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        client = await self._get_client()

        try:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise AiTimeoutError() from exc
        except httpx.RequestError as exc:
            raise AiServiceError(f"Network error communicating with Groq AI: {exc}", status_code=502) from exc

        if resp.status_code == 429:
            raise AiRateLimitError()

        if not resp.is_success:
            raise AiServiceError(
                f"Groq API error (HTTP {resp.status_code}): {resp.text}",
                status_code=resp.status_code,
            )

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise AiServiceError("No response returned by AI model")

        return choices[0].get("message", {}).get("content", "")

    # -----------------------------------------------------------------------
    # Creator AI Operations
    # -----------------------------------------------------------------------

    async def generate_titles(
        self,
        topic: str,
        keywords: Optional[list[str]] = None,
        style: str = "high-ctr",
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate high-performing YouTube titles with click-through rate reasoning."""
        kw_str = ", ".join(keywords) if keywords else "None specified"
        system_prompt = (
            "You are an expert YouTube strategist and algorithm specialist. "
            "Generate high-CTR, engaging YouTube video titles without misleading clickbait. "
            "Respond strictly in JSON format as an array of objects with keys: 'title', 'hook_type', 'estimated_ctr_rating'."
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"Target Keywords: {kw_str}\n"
            f"Style Preference: {style}\n"
            f"Number of Titles: {count}\n"
            "Return JSON array."
        )

        content = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        parsed = extract_json_payload(content)
        if isinstance(parsed, list):
            return parsed
        return [{"title": topic, "hook_type": "Direct", "estimated_ctr_rating": "Good"}]

    async def improve_title(self, current_title: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Analyze a current YouTube title and provide improved variants with scores."""
        ctx_str = json.dumps(context) if context else ""
        system_prompt = (
            "You are a YouTube SEO editor. Analyze the user's title and return improvements. "
            "Respond in JSON with keys: 'original_title', 'score_out_of_100', 'weaknesses', 'suggestions'."
        )
        content = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Title: {current_title}\nContext: {ctx_str}\nProvide JSON evaluation."},
        ])
        return extract_json_payload(content)

    async def generate_description(
        self,
        video_title: str,
        key_points: Optional[list[str]] = None,
        include_timestamps: bool = True,
    ) -> dict[str, Any]:
        """Generate an SEO-optimized YouTube description with hook, chapters, keywords, and CTA."""
        points = "\n- ".join(key_points) if key_points else "Cover all key aspects comprehensively"
        system_prompt = (
            "You are a YouTube SEO copywriter. Write a clean, high-ranking YouTube video description. "
            "Respond in JSON with keys: 'summary_hook', 'full_description', 'recommended_tags', 'chapters'."
        )
        user_prompt = (
            f"Video Title: {video_title}\n"
            f"Key Points:\n- {points}\n"
            f"Include Timestamps: {include_timestamps}\n"
            "Generate JSON description."
        )
        content = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return extract_json_payload(content)

    async def suggest_keywords(
        self,
        seed_keyword: str,
        region: str = "US",
        target_audience: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate categorized keyword clusters, search intent, and long-tail variants."""
        system_prompt = (
            "You are a YouTube keyword researcher. Generate relevant search terms, search clusters, and long-tail queries. "
            "Respond in JSON with keys: 'seed_keyword', 'high_volume_terms', 'long_tail_terms', 'question_keywords', 'competition_level'."
        )
        user_prompt = (
            f"Seed Keyword: {seed_keyword}\n"
            f"Target Region: {region}\n"
            f"Audience: {target_audience or 'General YouTube audience'}\n"
            "Return JSON keyword map."
        )
        content = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return extract_json_payload(content)

    async def generate_hooks(self, topic: str, format_type: str = "long_form") -> list[dict[str, Any]]:
        """Generate the first 15-second opening hooks for high viewer retention."""
        system_prompt = (
            "You are a video retention editor. Write 3 distinct opening hook scripts for the first 15 seconds. "
            "Respond in JSON as an array of objects with keys: 'hook_type', 'script', 'visual_cue', 'why_it_works'."
        )
        user_prompt = f"Topic: {topic}\nFormat: {format_type}\nReturn JSON array."
        content = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        parsed = extract_json_payload(content)
        if isinstance(parsed, list):
            return parsed
        return [{"hook_type": "Question", "script": f"Have you ever wondered about {topic}?", "visual_cue": "Fast cut"}]

    async def creator_assistant(self, prompt_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Multi-purpose creator assistant dispatcher."""
        topic = context.get("topic") or context.get("video_title") or context.get("query", "General YouTube Strategy")

        if prompt_type == "title":
            titles = await self.generate_titles(topic, context.get("keywords"), context.get("style", "high-ctr"))
            return {"titles": titles}
        elif prompt_type == "description":
            desc = await self.generate_description(topic, context.get("key_points"))
            return {"description": desc}
        elif prompt_type == "keywords":
            kw = await self.suggest_keywords(topic, context.get("region", "US"))
            return {"keywords": kw}
        elif prompt_type == "hooks":
            hooks = await self.generate_hooks(topic, context.get("format", "long_form"))
            return {"hooks": hooks}
        else:
            system_prompt = (
                "You are Plexudo AI, an elite YouTube channel growth advisor. "
                "Provide actionable, data-driven advice tailored for creators."
            )
            content = await self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Task: {prompt_type}\nContext: {json.dumps(context)}"},
            ])
            return {"suggestion": content}


# Global singleton instance
ai_service = AiService()
