"""
YouTube Data API v3 Service
============================
Integrates directly with the official Google YouTube Data API v3 endpoints.
Server-side only — API key is never exposed to the frontend.

CRITICAL INVARIANTS:
1. Zero fake fallback videos or hardcoded fake statistics.
2. If YouTube returns empty items, return an honest empty list with message.
3. If API fails, raise typed exceptions for clean upstream error handling.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("plexudo.youtube")
settings = get_settings()

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


# ---------------------------------------------------------------------------
# Typed Exceptions
# ---------------------------------------------------------------------------


class YouTubeApiError(Exception):
    """Base exception for YouTube Data API failures."""

    def __init__(self, message: str, status_code: int = 500, error_details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_details = error_details


class YouTubeNotFoundError(YouTubeApiError):
    """Raised when the requested video or channel does not exist."""

    def __init__(self, message: str = "YouTube resource not found"):
        super().__init__(message=message, status_code=404)


class YouTubeQuotaExceededError(YouTubeApiError):
    """Raised when YouTube Data API v3 daily quota limit is reached."""

    def __init__(self, message: str = "YouTube API quota exceeded"):
        super().__init__(message=message, status_code=429)


class YouTubeUnauthorizedError(YouTubeApiError):
    """Raised when OAuth token is invalid or expired."""

    def __init__(self, message: str = "YouTube authorization invalid or expired"):
        super().__init__(message=message, status_code=401)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def extract_video_id(url_or_id: str) -> str:
    """
    Extract a standard 11-character YouTube video ID from various URL formats
    or return the string trimmed if it's already an 11-char ID.
    """
    cleaned = url_or_id.strip()
    if len(cleaned) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", cleaned):
        return cleaned

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)

    return cleaned


def extract_channel_id_or_handle(url_or_id: str) -> tuple[str, str]:
    """
    Determine if input is a channel ID (UC...), handle (@name), or custom URL.
    Returns (identifier_type, cleaned_value).
    identifier_type in ('id', 'handle', 'username').
    """
    cleaned = url_or_id.strip()

    # Handle URL formats
    match_handle = re.search(r"youtube\.com/@([a-zA-Z0-9_.-]+)", cleaned)
    if match_handle:
        return "handle", f"@{match_handle.group(1)}"

    match_channel = re.search(r"youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})", cleaned)
    if match_channel:
        return "id", match_channel.group(1)

    if cleaned.startswith("@"):
        return "handle", cleaned

    if cleaned.startswith("UC") and len(cleaned) == 24:
        return "id", cleaned

    return "username", cleaned


# ---------------------------------------------------------------------------
# Service Implementation
# ---------------------------------------------------------------------------


class YouTubeService:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=15.0)

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any],
        access_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute an HTTP GET request to YouTube Data API v3.
        Injects API key or Bearer token securely.
        """
        req_params = dict(params)
        headers = {}

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        else:
            api_key = settings.YOUTUBE_API_KEY
            if not api_key or api_key == "your-youtube-api-key":
                logger.warning("YOUTUBE_API_KEY is not configured with a valid key")
            req_params["key"] = api_key

        url = f"{YOUTUBE_API_BASE_URL}/{endpoint}"
        client = await self._get_client()

        try:
            resp = await client.get(url, params=req_params, headers=headers)
        except httpx.TimeoutException as exc:
            raise YouTubeApiError("YouTube API request timed out", status_code=504) from exc
        except httpx.RequestError as exc:
            raise YouTubeApiError(f"Network error communicating with YouTube: {exc}", status_code=502) from exc

        if resp.status_code == 401 or resp.status_code == 403:
            err_data = resp.json().get("error", {}) if resp.headers.get("content-type", "").startswith("application/json") else {}
            reasons = [e.get("reason", "") for e in err_data.get("errors", [])]
            if "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
                raise YouTubeQuotaExceededError()
            if resp.status_code == 401:
                raise YouTubeUnauthorizedError("Invalid or expired YouTube authorization")
            raise YouTubeApiError(f"YouTube permission error: {resp.text}", status_code=resp.status_code)

        if not resp.is_success:
            raise YouTubeApiError(
                f"YouTube API responded with HTTP {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        return resp.json()

    # -----------------------------------------------------------------------
    # Public & Connected Channel Operations
    # -----------------------------------------------------------------------

    async def get_my_channel(self, access_token: str) -> dict[str, Any]:
        """
        Fetch the authenticated user's YouTube channel information using OAuth token.
        """
        data = await self._make_request(
            "channels",
            params={"part": "snippet,statistics,contentDetails", "mine": "true"},
            access_token=access_token,
        )
        items = data.get("items", [])
        if not items:
            return {
                "channel": None,
                "message": "No YouTube channel associated with this Google account",
            }

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        return {
            "id": item.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "custom_url": snippet.get("customUrl"),
            "avatar_url": snippet.get("thumbnails", {}).get("default", {}).get("url")
            or snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "published_at": snippet.get("publishedAt"),
            "view_count": int(statistics.get("viewCount", 0)),
            "subscriber_count": int(statistics.get("subscriberCount", 0)) if not statistics.get("hiddenSubscriberCount") else None,
            "video_count": int(statistics.get("videoCount", 0)),
            "uploads_playlist_id": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
        }

    async def get_channel_info(
        self,
        channel_id_or_url: str,
        access_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch public YouTube channel information by channel ID, handle, or custom URL.
        """
        id_type, val = extract_channel_id_or_handle(channel_id_or_url)
        params = {"part": "snippet,statistics,contentDetails"}

        if id_type == "id":
            params["id"] = val
        elif id_type == "handle":
            params["forHandle"] = val
        else:
            params["forUsername"] = val

        data = await self._make_request("channels", params=params, access_token=access_token)
        items = data.get("items", [])
        if not items:
            raise YouTubeNotFoundError(f"Channel '{channel_id_or_url}' was not found on YouTube")

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        return {
            "id": item.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "custom_url": snippet.get("customUrl"),
            "avatar_url": snippet.get("thumbnails", {}).get("high", {}).get("url")
            or snippet.get("thumbnails", {}).get("default", {}).get("url"),
            "country": snippet.get("country"),
            "view_count": int(statistics.get("viewCount", 0)),
            "subscriber_count": int(statistics.get("subscriberCount", 0)) if not statistics.get("hiddenSubscriberCount") else None,
            "video_count": int(statistics.get("videoCount", 0)),
            "uploads_playlist_id": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
        }

    async def get_channel_videos(
        self,
        channel_id: Optional[str] = None,
        uploads_playlist_id: Optional[str] = None,
        max_results: int = 20,
        access_token: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch uploaded videos for a channel using either the channel ID or playlist ID.
        Returns an honest empty list if no videos are found.
        """
        playlist_id = uploads_playlist_id
        if not playlist_id:
            if not channel_id:
                raise YouTubeApiError("channel_id or uploads_playlist_id required", status_code=400)
            # Find uploads playlist from channel details
            channel = await self.get_channel_info(channel_id, access_token=access_token)
            playlist_id = channel.get("uploads_playlist_id")

        if not playlist_id:
            return []

        data = await self._make_request(
            "playlistItems",
            params={
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": min(max_results, 50),
            },
            access_token=access_token,
        )

        items = data.get("items", [])
        videos = []
        for item in items:
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                continue

            videos.append({
                "video_id": video_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url")
                or snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "channel_title": snippet.get("channelTitle"),
            })

        return videos

    # -----------------------------------------------------------------------
    # Video & Search Operations
    # -----------------------------------------------------------------------

    async def get_video_info(self, video_id_or_url: str) -> dict[str, Any]:
        """
        Fetch metadata, statistics, tags, and topic details for a single video.
        """
        video_id = extract_video_id(video_id_or_url)
        data = await self._make_request(
            "videos",
            params={"part": "snippet,statistics,contentDetails,topicDetails", "id": video_id},
        )
        items = data.get("items", [])
        if not items:
            raise YouTubeNotFoundError(f"Video '{video_id}' was not found on YouTube")

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        return {
            "video_id": item.get("id"),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_id": snippet.get("channelId", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId", ""),
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "comment_count": int(statistics.get("commentCount", 0)),
            "duration": item.get("contentDetails", {}).get("duration", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("maxres", {}).get("url")
            or snippet.get("thumbnails", {}).get("high", {}).get("url")
            or snippet.get("thumbnails", {}).get("default", {}).get("url"),
        }

    async def search_videos(
        self,
        query: str,
        region: str = "US",
        max_results: int = 20,
        order: str = "relevance",
    ) -> list[dict[str, Any]]:
        """
        Search YouTube public videos for keyword research and trend analysis.
        """
        data = await self._make_request(
            "search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "regionCode": region,
                "maxResults": min(max_results, 50),
                "order": order,
            },
        )
        items = data.get("items", [])
        results = []
        for item in items:
            vid = item.get("id", {}).get("videoId")
            if not vid:
                continue
            snippet = item.get("snippet", {})
            results.append({
                "video_id": vid,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "channel_title": snippet.get("channelTitle"),
                "channel_id": snippet.get("channelId"),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            })
        return results

    async def get_trending_videos(
        self,
        region: str = "US",
        max_results: int = 20,
        category_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch most popular/trending videos for a region.
        """
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": min(max_results, 50),
        }
        if category_id:
            params["videoCategoryId"] = category_id

        data = await self._make_request("videos", params=params)
        items = data.get("items", [])
        results = []
        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            results.append({
                "video_id": item.get("id"),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "tags": snippet.get("tags", []),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            })
        return results


# Global singleton instance
youtube_service = YouTubeService()
