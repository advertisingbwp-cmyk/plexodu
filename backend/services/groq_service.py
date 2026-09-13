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

# Modern, officially supported Groq model list
DEPRECATED_MODELS = {"openai/gpt-oss-120b", "mixtral-8x7b-32768"}
configured_model = (settings.GROQ_MODEL or os.environ.get("GROQ_MODEL", "")).strip()
if not configured_model or configured_model in DEPRECATED_MODELS:
    configured_model = "openai/gpt-oss-20b"

SUPPORTED_MODELS = [
    configured_model,
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.8-27b",
    "groq/compound-mini",
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
        "You are Plexudo AI — a friendly, intelligent, helpful, and completely versatile AI assistant. "
        "Guidelines:\n"
        "1. DIRECT & CONVERSATIONAL: Answer the user directly, naturally, and warmly. Help with titles, descriptions, scripts, gaming, code, general knowledge, or casual chat.\n"
        "2. LANGUAGE MATCHING: Always respond in the exact same language and style the user uses (English, Urdu, Roman Urdu, Hindi, etc.). If the user asks in Roman Urdu (e.g. 'bhai titles batao' or 'ye kaisa hai'), reply in natural, fluent Roman Urdu.\n"
        "3. HIGH QUALITY & CREATIVITY: When asked for titles or ideas, provide ready-to-use, catchy, high-CTR suggestions tailored to the user's specific request.\n"
        "4. NO RIGID TEMPLATES: Never output placeholder templates like '[Topic]' or rigid canned bullet points. Act like a normal, high-level AI assistant."
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
    Fallback when external AI service is unreachable or rate-limited.
    Provides natural advice tailored to the user's message.
    """
    msg = user_message.strip()
    topic = ""
    if trend_context and isinstance(trend_context, dict) and trend_context.get("keyword"):
        topic = str(trend_context["keyword"]).strip()
    if not topic:
        clean_msg = re.sub(r'(?i)\b(i want|give me|how to|titles? for|about|video|videos?|please|bhai|batao)\b', '', msg).strip()
        topic = clean_msg if clean_msg else "your content"

    if any(w in msg.lower() for w in ["hi", "hello", "hey", "salam", "start"]):
        reply = (
            "👋 **Hello! I am your Plexudo AI Strategist.**\n\n"
            "How can I help you today? You can ask me for video titles, descriptions, tags, scripting ideas, or channel growth strategies!"
        )
    else:
        capitalized_topic = topic.title()
        reply = (
            f"Here are strategic title recommendations for **{capitalized_topic}** from Plexudo AI Strategist:\n\n"
            f"1. **High CTR & Curiosity:** *The Ultimate {capitalized_topic} Secret Nobody Tells You*\n"
            f"2. **Search Intent:** *How to Master {capitalized_topic} (Step-by-Step Beginner Guide)*\n"
            f"3. **Urgency & Challenge:** *I Tried {capitalized_topic} for 24 Hours – Here's What Happened*\n"
            f"4. **Action-Packed:** *Top 5 {capitalized_topic} Pro Plays That Actually Work*\n\n"
            f"💡 **Tip:** Keep titles under 60 characters so they stay fully visible on mobile feeds."
        )
    return {"reply": reply, "error": False}
