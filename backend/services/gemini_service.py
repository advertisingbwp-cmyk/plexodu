"""
Gemini AI Chat Service — Optimized for Free Tier
- Primary model: gemini-2.0-flash-lite (30 RPM free tier)
- NO auto-retry on 429 (retries wasted quota)
- Server-side global throttle (min 5s between calls)
- In-memory response cache (avoids duplicate calls)
"""

import os
import time
import json
import hashlib
import threading
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# gemini-2.0-flash-lite has 30 RPM free tier (vs 15 RPM for regular flash)
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",   # 30 RPM free — best for free tier
    "gemini-2.0-flash",        # 15 RPM free — fallback
]

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# ── Cache: avoid repeating identical questions ────────────────────────────────
_cache: dict = {}
_CACHE_MAX = 60

# ── Global throttle: enforce minimum gap between API calls ────────────────────
_throttle_lock = threading.Lock()
_last_api_call  = 0.0
MIN_API_INTERVAL = 5.0   # seconds — hard minimum between any two Gemini calls


def _cache_key(message: str, context: dict) -> str:
    raw = message.strip().lower() + json.dumps(context or {}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _wait_for_throttle():
    """Block until the minimum interval since the last API call has passed."""
    with _throttle_lock:
        global _last_api_call
        elapsed = time.time() - _last_api_call
        if elapsed < MIN_API_INTERVAL:
            time.sleep(MIN_API_INTERVAL - elapsed)
        _last_api_call = time.time()


def _call_model(model: str, payload: dict) -> dict:
    """Single API call — NO retry on 429 (caller decides what to do)."""
    url = BASE_URL.format(model=model)
    try:
        res = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=25,
        )
        return {"status": res.status_code, "body": res.json() if res.content else {}}
    except requests.Timeout:
        return {"status": -1, "body": {}, "timeout": True}
    except Exception as e:
        return {"status": -2, "body": {}, "exception": str(e)}


def chat_with_gemini(user_message: str, trend_context: dict = None) -> dict:
    """
    Sends a message to Gemini. Returns { "reply": str, "error": bool }.
    Rate-limit errors are returned immediately — NO server-side retry.
    """
    if not GEMINI_API_KEY:
        return {
            "reply": (
                "⚠️ **Gemini API key not set.**\n\n"
                "`.env` file mein `GEMINI_API_KEY=` ke baad apni key paste karein.\n"
                "Free key milti hai: https://aistudio.google.com"
            ),
            "error": True,
        }

    # ── Cache check ───────────────────────────────────────────────────────────
    ck = _cache_key(user_message, trend_context)
    if ck in _cache:
        return {"reply": _cache[ck], "error": False, "cached": True}

    # ── Build prompt ──────────────────────────────────────────────────────────
    system_ctx = (
        "You are SMTAS AI — an expert social media trend analyst. "
        "Help with viral trends, sentiment, virality scores, YouTube vs TikTok. "
        "Be concise, use emojis. Max 3 short paragraphs."
    )

    if trend_context:
        ctx_str = json.dumps(trend_context, indent=2)
        prompt = f"{system_ctx}\n\nTrend data:\n{ctx_str}\n\nUser: {user_message}"
    else:
        prompt = f"{system_ctx}\n\nUser: {user_message}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }

    # ── Throttle ──────────────────────────────────────────────────────────────
    _wait_for_throttle()

    # ── Try each model once (no retries) ─────────────────────────────────────
    for model in GEMINI_MODELS:
        result = _call_model(model, payload)
        status = result["status"]

        if result.get("timeout"):
            return {"reply": "⏱ Request timed out. Please try again.", "error": True}

        if result.get("exception"):
            return {"reply": f"❌ Error: {result['exception']}", "error": True}

        if status == 200:
            try:
                reply = result["body"]["candidates"][0]["content"]["parts"][0]["text"]
                # Save to cache
                if len(_cache) >= _CACHE_MAX:
                    del _cache[next(iter(_cache))]
                _cache[ck] = reply
                return {"reply": reply, "error": False}
            except (KeyError, IndexError):
                return {"reply": "⚠ Gemini returned unexpected format.", "error": True}

        if status == 429:
            # Return immediately — frontend will show countdown
            return {
                "reply": "RATE_LIMIT",
                "error": True,
                "rate_limited": True,
            }

        if status == 404:
            continue   # try next model

        if status == 400:
            return {
                "reply": "❌ Bad request. Check your API key or try again.",
                "error": True,
            }

        # Other error
        detail = str(result["body"])[:200]
        return {"reply": f"❌ API error {status}: {detail}", "error": True}

    # All models exhausted
    return {
        "reply": "RATE_LIMIT",
        "error": True,
        "rate_limited": True,
    }
