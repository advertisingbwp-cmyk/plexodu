"""
YouTube Service Tests
=====================
Tests YouTube Data API v3 integration:
1. Video ID extraction and URL parsing.
2. Channel lookup and video fetching.
3. INVARIANT: Zero fake fallbacks (empty results return honest empty arrays).
4. Error states: Not found (404), Quota exceeded (429), Unauthorized (401).
"""

from __future__ import annotations

import httpx
import pytest

from app.services.youtube_service import (
    YouTubeApiError,
    YouTubeNotFoundError,
    YouTubeQuotaExceededError,
    YouTubeService,
    YouTubeUnauthorizedError,
    extract_channel_id_or_handle,
    extract_video_id,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit: URL & ID Extraction
# ---------------------------------------------------------------------------


async def test_extract_video_id():
    # Standard 11-char ID
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # Full watch URL
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # Shortened youtu.be URL
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # Embed URL
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # Shorts URL
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    # With extra query params
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"


async def test_extract_channel_id_or_handle():
    # Channel ID
    id_type, val = extract_channel_id_or_handle("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert id_type == "id"
    assert val == "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    # Full channel URL
    id_type, val = extract_channel_id_or_handle("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert id_type == "id"
    assert val == "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    # Handle
    id_type, val = extract_channel_id_or_handle("@mkbhd")
    assert id_type == "handle"
    assert val == "@mkbhd"

    # Handle URL
    id_type, val = extract_channel_id_or_handle("https://www.youtube.com/@mkbhd")
    assert id_type == "handle"
    assert val == "@mkbhd"


# ---------------------------------------------------------------------------
# Integration: YouTube Service with Mock Transport
# ---------------------------------------------------------------------------


async def test_get_video_info_success():
    mock_payload = {
        "items": [
            {
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "description": "The official video for Never Gonna Give You Up",
                    "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                    "channelTitle": "RickAstleyVEVO",
                    "publishedAt": "2009-10-25T06:57:33Z",
                    "tags": ["Rick Astley", "Never Gonna Give You Up"],
                    "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}},
                },
                "statistics": {
                    "viewCount": "1500000000",
                    "likeCount": "17000000",
                    "commentCount": "2500000",
                },
                "contentDetails": {"duration": "PT3M33S"},
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "videos" in str(request.url)
        return httpx.Response(200, json=mock_payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = YouTubeService(client=client)

    result = await service.get_video_info("dQw4w9WgXcQ")
    assert result["video_id"] == "dQw4w9WgXcQ"
    assert result["title"] == "Rick Astley - Never Gonna Give You Up"
    assert result["view_count"] == 1500000000
    assert result["tags"] == ["Rick Astley", "Never Gonna Give You Up"]


async def test_get_video_info_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = YouTubeService(client=client)

    with pytest.raises(YouTubeNotFoundError):
        await service.get_video_info("nonexistent11")


async def test_get_channel_videos_honest_empty_result():
    """
    CRITICAL INVARIANT: Zero fake fallbacks.
    When a channel has no uploads, the service must return an empty list [].
    """
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = YouTubeService(client=client)

    videos = await service.get_channel_videos(uploads_playlist_id="UU_empty_playlist")
    assert videos == [], "Must return an empty list without fake fallback videos"


async def test_quota_exceeded_error_handling():
    error_payload = {
        "error": {
            "code": 403,
            "message": "The request cannot be completed because you have exceeded your quota.",
            "errors": [{"reason": "quotaExceeded", "domain": "youtube.quota"}],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json=error_payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = YouTubeService(client=client)

    with pytest.raises(YouTubeQuotaExceededError):
        await service.get_channel_info("UC_any_channel")


async def test_unauthorized_token_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401, "message": "Invalid Credentials"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = YouTubeService(client=client)

    with pytest.raises(YouTubeUnauthorizedError):
        await service.get_my_channel("expired_or_invalid_access_token")
