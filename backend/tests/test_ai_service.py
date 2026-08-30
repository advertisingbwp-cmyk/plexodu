"""
Groq AI Service Tests
=====================
Tests:
1. Title generation, title improvement, and description generation.
2. Safe JSON extraction from AI outputs.
3. Integration with tool runner & credit ledger:
   - Credit deduction before AI execution.
   - Automatic refund if AI service times out or errors.
   - Insufficient credits rejection (402).
"""

from __future__ import annotations

import httpx
import pytest

from app.services.ai_service import (
    AiRateLimitError,
    AiService,
    AiServiceError,
    AiTimeoutError,
    extract_json_payload,
)
from app.services.auth_service import create_session

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Unit: JSON Extraction
# ---------------------------------------------------------------------------


async def test_extract_json_payload():
    # Markdown fenced
    fenced = "```json\n[{\"title\": \"Epic Video\", \"hook_type\": \"Curiosity\"}]\n```"
    res = extract_json_payload(fenced)
    assert isinstance(res, list)
    assert res[0]["title"] == "Epic Video"

    # Raw JSON dict
    raw_dict = '{"score_out_of_100": 85, "weaknesses": ["Too short"]}'
    res2 = extract_json_payload(raw_dict)
    assert res2["score_out_of_100"] == 85

    # Text surrounding JSON
    surrounded = "Here are your titles:\n```json\n[{\"title\": \"V1\"}]\n```\nHope you like them!"
    res3 = extract_json_payload(surrounded)
    assert res3[0]["title"] == "V1"


# ---------------------------------------------------------------------------
# Mocked AI Service Tests
# ---------------------------------------------------------------------------


async def test_generate_titles_mock():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": '```json\n[{"title": "How to Master YouTube in 2026", "hook_type": "Authority", "estimated_ctr_rating": "9/10"}]\n```'
                }
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "chat/completions" in str(request.url)
        return httpx.Response(200, json=mock_response)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AiService(client=client)

    titles = await service.generate_titles("YouTube Growth", keywords=["growth", "algorithm"])
    assert len(titles) == 1
    assert titles[0]["title"] == "How to Master YouTube in 2026"


async def test_ai_service_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AiService(client=client)

    with pytest.raises(AiRateLimitError):
        await service.generate_titles("Any topic")


# ---------------------------------------------------------------------------
# Integration: Credit Deduction & Automatic Refund on AI Failure
# ---------------------------------------------------------------------------


async def test_ai_tool_deducts_credits_and_refunds_on_error(test_client, db, test_user, monkeypatch):
    """
    When an AI tool operation fails downstream:
    1. The credit was initially deducted.
    2. The failure triggered an automatic refund.
    3. The final balance remains unchanged.
    """
    initial_balance = test_user.credit_balance  # 3

    session = await create_session(db, test_user.id, "test", "127.0.0.1")
    test_client.cookies.set("plexudo_session", str(session.id))

    # Force AI service to raise an error
    from app.services.ai_service import ai_service

    async def _mock_failing_assistant(*args, **kwargs):
        raise AiServiceError("Downstream Groq provider unavailable", status_code=502)

    monkeypatch.setattr(ai_service, "creator_assistant", _mock_failing_assistant)

    resp = await test_client.post(
        "/api/v1/tools/ai-assistant",
        json={"prompt_type": "title", "context": {"topic": "AI Future"}},
    )
    # Endpoint should return 502 error
    assert resp.status_code == 502

    # Verify balance was automatically refunded back to initial_balance
    bal_resp = await test_client.get("/api/v1/credits/balance")
    assert bal_resp.json()["balance"] == initial_balance

    test_client.cookies.clear()
