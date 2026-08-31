"""
Plexudo AI YouTube Creator Title Intelligence Subsystem
Analyzes any topic or keyword dynamically via Groq AI.
Generates genuine, high-CTR, niche-accurate creator video ideas and titles.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Active models on Groq API
MODELS = [
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "groq/compound"
]


def get_groq_key():
    return os.environ.get("GROQ_API_KEY", "").strip()


def generate_context_aware_titles(
    keyword: str = "",
    topic: str = "",
    description: str = "",
    tags: list = None,
    video_type: str = "",
    target_audience: str = "",
    related_queries: list = None,
    top_video_titles: list = None,
    count: int = 4
) -> list:
    """
    Dynamically analyzes keyword/topic using Groq AI.
    Understands what the subject actually is (Islamic, Gaming, News, Tech, Sports, etc.)
    and produces authentic high-CTR titles tailored for that exact subject.
    """
    keyword = (keyword or "").strip()
    topic = (topic or "").strip()
    description = (description or "").strip()
    video_type = (video_type or "").strip()
    target_audience = (target_audience or "").strip()
    tags = tags or []
    related_queries = related_queries or []
    top_video_titles = top_video_titles or []

    clean_kw = re.sub(r'[#@\(\)\[\]]', '', keyword).strip()
    clean_topic = re.sub(r'[#@\(\)\[\]]', '', topic).strip()
    primary_subject = clean_topic or clean_kw or (tags[0] if tags else "YouTube Video")

    if not related_queries and clean_kw:
        related_queries = _fetch_autocomplete(clean_kw)

    groq_key = get_groq_key()

    if groq_key:
        ai_titles = _generate_with_groq(
            groq_key=groq_key,
            primary_subject=primary_subject,
            clean_kw=clean_kw,
            clean_topic=clean_topic,
            description=description,
            tags=tags,
            video_type=video_type,
            target_audience=target_audience,
            related_queries=related_queries,
            top_video_titles=top_video_titles,
            count=count
        )
        if ai_titles and len(ai_titles) >= count:
            return ai_titles[:count]
        elif ai_titles:
            needed = count - len(ai_titles)
            fb = _generate_contextual_fallback(clean_kw, clean_topic, count=needed)
            return (ai_titles + fb)[:count]

    return _generate_contextual_fallback(
        clean_kw=clean_kw,
        clean_topic=clean_topic,
        count=count
    )


def _fetch_autocomplete(query: str) -> list:
    """Fetches real search query predictions from YouTube autocomplete."""
    if not query or len(query) < 2:
        return []
    try:
        res = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "ds": "yt", "q": query},
            timeout=4
        )
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                return [str(q).strip() for q in data[1] if q][:8]
    except Exception:
        pass
    return []


def _generate_with_groq(
    groq_key: str,
    primary_subject: str,
    clean_kw: str,
    clean_topic: str,
    description: str,
    tags: list,
    video_type: str,
    target_audience: str,
    related_queries: list,
    top_video_titles: list,
    count: int
) -> list:
    """Calls Groq AI with pure semantic understanding of the topic."""
    context_lines = []
    if clean_kw:
        context_lines.append(f"Subject / Target Keyword: '{clean_kw}'")
    if clean_topic:
        context_lines.append(f"Specific Video Angle: '{clean_topic}'")
    if related_queries:
        context_lines.append(f"Viewer Searches in Niche: {', '.join(related_queries[:6])}")
    if top_video_titles:
        context_lines.append(f"Trending Video Titles in Niche: {', '.join(top_video_titles[:3])}")
    if description:
        context_lines.append(f"Description: '{description[:200]}'")

    context_str = "\n".join(context_lines)

    system_prompt = (
        "You are an expert YouTube Creator Title Consultant and Viral Content Strategist. "
        "Analyze the provided keyword/topic, identify what category and subject it belongs to (e.g. Islamic/Naat Khawan, Gaming, Cooking, Tech, Sports, Entertainment, Biography, Vlog), "
        "and generate 4 realistic, high-CTR YouTube video title ideas that a creator in this niche should make right now.\n\n"
        "Return a valid JSON array of objects with keys: title, strategy, reason, relevance_score, ctr_score.\n"
        "Output ONLY the raw JSON array."
    )

    user_prompt = (
        f"Generate {count} relevant YouTube title ideas for:\n{context_str}\n\n"
        "Output JSON array ONLY."
    )

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.6,
            "max_tokens": 750
        }

        try:
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                content = content.replace("```json", "").replace("```", "").strip()

                start_idx = content.find("[")
                end_idx = content.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    parsed = json.loads(content[start_idx:end_idx+1])
                    if isinstance(parsed, list) and len(parsed) > 0:
                        validated = []
                        for item in parsed:
                            if isinstance(item, dict) and item.get("title"):
                                title_text = item["title"].strip('"\' ')
                                validated.append({
                                    "title": title_text,
                                    "strategy": item.get("strategy") or "Search Intent",
                                    "primary_keyword": item.get("primary_keyword") or clean_kw or primary_subject,
                                    "reason": item.get("reason") or "High search alignment and creator engagement.",
                                    "relevance_score": int(item.get("relevance_score") or 92),
                                    "ctr_score": int(item.get("ctr_score") or 88)
                                })
                        if len(validated) >= count:
                            return validated[:count]
                        elif validated:
                            return validated
        except Exception:
            continue

    return []


def _generate_contextual_fallback(
    clean_kw: str,
    clean_topic: str,
    count: int = 4
) -> list:
    """Safe generic creator fallback."""
    subject = clean_topic or clean_kw or "Trending Video"
    subject_title = subject.title()

    fallback_templates = [
        {
            "title": f"Top 10 Most Popular {subject_title} Videos & Best Moments",
            "strategy": "Best Collection",
            "reason": "Captures high viewer interest with curated compilation style."
        },
        {
            "title": f"{subject_title} (Full In-Depth Breakdown & Special Features)",
            "strategy": "Search Intent",
            "reason": "Directly targets high-volume organic search queries."
        },
        {
            "title": f"Everything You Need to Know About {subject_title} (2026 Update)",
            "strategy": "Trending Guide",
            "reason": "Strong curiosity and relevance hook for active viewers."
        },
        {
            "title": f"The Ultimate {subject_title} Guide: Key Highlights & Top Highlights",
            "strategy": "High-CTR Hook",
            "reason": "Broad appeal capturing casual and enthusiast audiences alike."
        }
    ]

    results = []
    for item in fallback_templates[:count]:
        results.append({
            "title": item["title"],
            "strategy": item["strategy"],
            "primary_keyword": clean_kw or subject,
            "reason": item["reason"],
            "relevance_score": 90,
            "ctr_score": 85
        })
    return results
