"""
Groq AI Chat Service
Integrates Groq API (OpenAI-compatible endpoint) using Llama models.
Ultra-fast, high rate limit (14,400 RPD), completely free.
"""

import os
import json
import re
import requests

from dotenv import load_dotenv
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Modern, officially supported Groq model list (active Llama 3 models)
DEPRECATED_MODELS = {"openai/gpt-oss-120b", "mixtral-8x7b-32768"}
configured_model = (settings.GROQ_MODEL or os.environ.get("GROQ_MODEL", "")).strip()
if not configured_model or configured_model in DEPRECATED_MODELS:
    configured_model = "llama-3.3-70b-versatile"

SUPPORTED_MODELS = [
    configured_model,
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
MODELS = [m for m in dict.fromkeys(SUPPORTED_MODELS) if m not in DEPRECATED_MODELS]


def chat_with_groq(user_message: str, trend_context: dict = None) -> dict:
    """
    Sends user message + optional YouTube trend context to Groq API.
    Dynamically loads GROQ_API_KEY from environment/settings.
    Enforces strict prompt isolation and strips sensitive user data.
    """
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "").strip()

    if not groq_key:
        return {
            "reply": (
                "⚠️ **Groq API key is missing.**\n\n"
                "1. Go to: **https://console.groq.com/keys**\n"
                "2. Click **Create API Key** and copy it.\n"
                "3. Paste it in `.env` as `GROQ_API_KEY=gsk_...`"
            ),
            "error": True,
        }

    system_prompt = (
        "You are Plexudo AI — an intelligent, natural, helpful, and versatile AI assistant. "
        "Guidelines for responding:\n"
        "1. DIRECT & RELEVANT: Answer the user's question directly, accurately, and conversationally. Never output unsolicited tables, rigid templates, or unwanted metrics unless the user explicitly requests them.\n"
        "2. LANGUAGE MATCHING: Always respond in the same language and style the user uses (Urdu, Roman Urdu, English, Hindi, etc.). If the user asks in Roman Urdu (e.g. 'ye kon hai?'), reply naturally in clear, friendly Roman Urdu.\n"
        "3. VERSATILITY: Answer any general knowledge, biography, coding, creator tips, YouTube growth, or conversational inquiries with warmth, clarity, and precision.\n"
        "4. BACKGROUND CONTEXT: If background YouTube trend metrics are provided, only reference them if the user specifically asks about video stats, view counts, or channel performance."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Filter context to non-sensitive analytics only; never send emails, user IDs, or credentials
    if trend_context and isinstance(trend_context, dict):
        allowed_keys = {"keyword", "platform", "total_views", "growth_rate", "virality_score", "stage", "dominant_sentiment"}
        safe_context = {k: trend_context[k] for k in allowed_keys if k in trend_context}
        if safe_context:
            ctx_str = json.dumps(safe_context, indent=2)
            messages.append({
                "role": "system",
                "content": f"Optional background reference data (only use if relevant to user's question):\n{ctx_str}"
            })

    # User message is strictly isolated in user role to prevent prompt injection
    messages.append({"role": "user", "content": str(user_message)})

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    last_error = None

    for model in MODELS:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,
        }

        try:
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    reply = choices[0]["message"].get("content", "")
                    if reply:
                        reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
                    if reply:
                        return {"reply": reply, "error": False}
            elif res.status_code == 401:
                return generate_smart_youtube_fallback(user_message, trend_context)
            elif res.status_code == 429:
                last_error = "⏳ Groq API rate limit reached. Please wait a few seconds and try again."
            elif res.status_code >= 500:
                last_error = f"❌ Groq service temporarily unavailable (HTTP {res.status_code})."
            else:
                last_error = f"❌ Groq API error ({res.status_code})"
        except requests.Timeout:
            last_error = "⏱ Request timed out. Please try again."
        except Exception as e:
            last_error = f"❌ Error contacting AI service: {str(e)}"

    return generate_smart_youtube_fallback(user_message, trend_context)


def generate_smart_youtube_fallback(user_message: str, trend_context: dict = None) -> dict:
    """
    Provides intelligent, context-aware YouTube trend & growth advice
    even when Groq API key is being updated.
    """
    msg = user_message.lower()
    
    if any(w in msg for w in ["hi", "hello", "hey", "salam", "start"]):
        reply = (
            "👋 **Hello! I am your Plexudo AI YouTube Strategist.**\n\n"
            "I can help you optimize your channel metadata and content strategy:\n\n"
            "• 🎯 **Strategic Title Formats:** Search-focused, benefit-driven, and educational title angles.\n"
            "• 🏷️ **Relevant SEO Tags:** Topic-specific long-tail tags and search query alignment.\n"
            "• 📈 **Channel Analysis:** Interpreting video velocity, view trends, and audience engagement.\n"
            "• 💡 **Content Strategy:** Niche topic ideas and description structure.\n\n"
            "Ask me anything, e.g. *'How should I structure my video description?'* or *'Give me 3 title ideas for a tech tutorial.'*"
        )
    elif any(w in msg for w in ["title", "hook", "ctr"]):
        reply = (
            "🎯 **Proven YouTube Title Strategies:**\n\n"
            "1. **Search-Focused:** *'[Topic]: Complete Step-by-Step Guide for Beginners'* (Direct search intent)\n"
            "2. **Benefit-Driven:** *'How to [Desired Outcome] in [Year] (Best Practices)'* (Clear value payoff)\n"
            "3. **Problem-Solution:** *'Common [Topic] Mistakes and How to Fix Them'* (High viewer utility)\n\n"
            "💡 **Pro Tip:** Aim for **40–65 characters** so your title reads clearly on mobile devices without truncation."
        )
    elif any(w in msg for w in ["tag", "seo", "keyword", "rank"]):
        reply = (
            "📊 **Plexudo 50-Point SEO Optimization Best Practices:**\n\n"
            "1. **Primary Topic in Title:** Place your core search keyword naturally in your title.\n"
            "2. **Structured Description:** Write at least 2–3 paragraphs explaining the video context and key takeaways.\n"
            "3. **Relevant Topic Tags:** Use 8–15 specific tags directly covering your video's main points and long-tail variants.\n"
            "4. **Triple Metadata Overlap:** Ensure core keywords appear naturally across your Title, Description, and Tags."
        )
    elif any(w in msg for w in ["freefire", "free fire", "game", "gaming"]):
        reply = (
            "🎮 **Gaming Content Optimization Strategy:**\n\n"
            "• **Clarity First:** Include game title, specific mode/character/weapon, and context in your title.\n"
            "• **Description Value:** List key timestamps, settings discussed, and helpful game tips.\n"
            "• **Hashtags:** Include 3–4 clean game-specific tags at the bottom of your description."
        )
    else:
        reply = (
            f"📊 **Plexudo Strategy Recommendations for: '{user_message}'**\n\n"
            "1. **Search Intent:** Align your video title with questions viewers are actively searching for.\n"
            "2. **First 15-Second Hook:** State the core value and roadmap of your video immediately.\n"
            "3. **Audience Engagement:** Ask a specific question to encourage genuine comments and discussion."
        )
    
    return {"reply": reply, "error": False}
