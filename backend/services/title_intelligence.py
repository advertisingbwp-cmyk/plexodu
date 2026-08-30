import os
import re
import json
import requests

try:
    from app.core.config import settings
except ImportError:
    settings = None

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]


def get_groq_key():
    if settings and getattr(settings, 'GROQ_API_KEY', None):
        return settings.GROQ_API_KEY
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
    Generates realistic, high-CTR, trending YouTube titles based on real search intent,
    live YouTube autocomplete queries, and creator best practices.
    """
    keyword = (keyword or "").strip()
    topic = (topic or "").strip()
    description = (description or "").strip()
    video_type = (video_type or "").strip()
    target_audience = (target_audience or "").strip()
    tags = tags or []
    related_queries = related_queries or []
    top_video_titles = top_video_titles or []

    # Clean inputs
    clean_kw = re.sub(r'[#@\(\)\[\]]', '', keyword).strip()
    clean_topic = re.sub(r'[#@\(\)\[\]]', '', topic).strip()

    # Determine primary subject
    primary_subject = clean_topic or clean_kw or (tags[0] if tags else "YouTube Video")
    primary_kw = clean_kw or (clean_topic.split()[0] if clean_topic else "Video")

    # Fetch live autocomplete suggestions if empty
    if not related_queries and clean_kw:
        related_queries = _fetch_autocomplete(clean_kw)

    # Check for Groq API Key
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
            # Supplement if partial
            needed = count - len(ai_titles)
            fb = _generate_contextual_fallback(clean_kw, clean_topic, description, related_queries, count=needed)
            return (ai_titles + fb)[:count]

    # Deterministic high-CTR creator fallback
    return _generate_contextual_fallback(
        clean_kw=clean_kw,
        clean_topic=clean_topic,
        description=description,
        related_queries=related_queries,
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
            if len(data) > 1 and isinstance(data[1], list):
                return [s.strip() for s in data[1] if s.strip() and s.strip().lower() != query.lower()][:8]
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
    """Calls Groq AI to generate realistic, trending YouTube titles that real creators use."""
    context_lines = []
    if clean_kw:
        context_lines.append(f"Target Keyword: '{clean_kw}'")
    if clean_topic:
        context_lines.append(f"Specific Video Topic / Angle: '{clean_topic}'")
    if related_queries:
        context_lines.append(f"Live YouTube Autocomplete Searches: {', '.join(related_queries[:6])}")
    if top_video_titles:
        context_lines.append(f"Top Ranking YouTube Videos in Niche: {', '.join(top_video_titles[:3])}")
    if description:
        context_lines.append(f"Content Summary: '{description[:200]}'")
    if video_type:
        context_lines.append(f"Video Format: '{video_type}'")

    context_str = "\n".join(context_lines)

    system_prompt = (
        "You are an elite YouTube Creator Title Consultant and SEO Strategist. "
        "Your job is to generate REALISTIC, HIGH-CTR, TRENDING YouTube titles that real successful creators use to rank in search and get millions of clicks in this specific niche.\n\n"
        "GUIDELINES FOR TITLE REALISM & QUALITY:\n"
        "1. Sound like a REAL successful YouTuber in that specific niche, NOT a robotic AI.\n"
        "   - For Gaming (e.g. PUBG, Free Fire, GTA): Use authentic creator hooks (e.g. 1v4 clutch gameplay, new update hidden features, best zero-recoil sensitivity, conqueror rank push, pro tips).\n"
        "   - For Tech/Coding (e.g. Python, React): Use practical creator hooks (e.g. complete roadmap, building a real app, beginner mistakes to avoid, 2026 guide).\n"
        "   - For Sports/Cricket (e.g. Cricket, Football): Use tactical, match-analysis, or skill hooks (e.g. match analysis, bowling/batting masterclass, turning point breakdown).\n"
        "   - For Vlogs/Productivity/Finance: Use genuine value and curiosity hooks.\n"
        "2. Leverage the provided 'Live YouTube Autocomplete Searches' to make titles match exactly what viewers are actively searching.\n"
        "3. DO NOT output repetitive formulas like 'Keyword Explained: Key Concepts' or 'Everything You Need to Know About...'.\n"
        "4. DO NOT use cheap spam words: No 'You Won't Believe', No 'Nobody Tells You', No 'Secret Tips to Blow Up'.\n"
        "5. Keep titles between 45–68 characters for mobile viewport clarity.\n"
        "6. Provide distinct strategic angles (e.g. Search Intent, High-CTR Hook, Pro Guide / Masterclass, Trending Update / Breakdown).\n\n"
        "Return ONLY a JSON array of objects with keys:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"(string - the realistic, engaging YouTube title)\",\n"
        "    \"strategy\": \"(string, e.g. Search Intent, High-CTR Hook, Pro Guide, Trending Analysis)\",\n"
        "    \"primary_keyword\": \"(string)\",\n"
        "    \"reason\": \"(string - why this title works for YouTube search & click-through)\",\n"
        "    \"relevance_score\": (number 85-98),\n"
        "    \"ctr_score\": (number 80-96)\n"
        "  }\n"
        "]"
    )

    user_prompt = (
        f"Generate {count} top-tier, realistic YouTube title ideas for this creator:\n\n"
        f"{context_str}\n\n"
        "Output ONLY the raw JSON array. No markdown, no introductory text."
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
            "temperature": 0.55,
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
                                if any(banned in title_text.lower() for banned in ["nobody tells you", "blow up with", "you won't believe"]):
                                    continue
                                validated.append({
                                    "title": title_text,
                                    "strategy": item.get("strategy") or "Search Intent",
                                    "primary_keyword": item.get("primary_keyword") or clean_kw or primary_subject,
                                    "reason": item.get("reason") or "High search alignment and natural creator engagement.",
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
    description: str,
    related_queries: list,
    count: int
) -> list:
    """
    Intelligent creator fallback that creates natural, trending YouTube titles
    tailored by niche detection (Gaming, Tech, Sports, Creator) instead of robotic templates.
    """
    subject = clean_topic or clean_kw or "YouTube Video"
    subject_title = subject.title()
    kw_title = clean_kw.title() if clean_kw else subject_title
    kw_lower = clean_kw.lower()

    # Niche Detection
    is_gaming = any(g in kw_lower for g in ["pubg", "pub g", "free fire", "freefire", "game", "gaming", "gta", "minecraft", "valorant", "cod", "fortnite"])
    is_coding = any(c in kw_lower for c in ["python", "javascript", "react", "html", "css", "django", "flask", "ai", "coding", "programming", "sql"])
    is_sports = any(s in kw_lower for s in ["cricket", "football", "soccer", "messi", "ronaldo", "batting", "bowling", "ipl", "match"])

    # Clean queries to use
    q1 = related_queries[0].title() if (related_queries and len(related_queries) > 0) else ""
    q2 = related_queries[1].title() if (related_queries and len(related_queries) > 1) else ""

    if clean_topic and clean_topic.lower() != clean_kw.lower():
        # User gave explicit topic (e.g. "Pakistan vs India match analysis")
        fallback_templates = [
            {
                "title": f"{subject_title} (Full Match Analysis & Key Moments)",
                "strategy": "Trending Analysis",
                "reason": "Directly targets high-interest viewer demand with clear, analytical framing."
            },
            {
                "title": f"{subject_title}: 5 Crucial Turning Points You Missed",
                "strategy": "High-CTR Hook",
                "reason": "Strong curiosity hook focusing on specific match observations."
            },
            {
                "title": f"{subject_title} — Complete Breakdown & Post-Match Review",
                "strategy": "Search Intent",
                "reason": "Captures post-event search traffic seeking full breakdowns."
            },
            {
                "title": f"Why This Happened: {subject_title} In-Depth Look",
                "strategy": "Curiosity / Inquiry",
                "reason": "Encourages discussion and high viewer retention."
            }
        ]
    elif is_gaming:
        # Gaming Niche: PUBG, Free Fire, etc.
        game_name = "PUBG Mobile" if ("pubg" in kw_lower or "pub g" in kw_lower) else ("Free Fire" if "free" in kw_lower else subject_title)
        fallback_templates = [
            {
                "title": f"{game_name}: Top 5 Pro Settings & Sensitivity for Zero Recoil",
                "strategy": "Pro Guide",
                "reason": "High-volume search demand for control and gameplay optimization."
            },
            {
                "title": f"1v4 Clutch Gameplay & Conqueror Rank Push in {game_name}",
                "strategy": "High-CTR Gameplay",
                "reason": "Appeals directly to competitive action fans with high-intent gameplay hooks."
            },
            {
                "title": f"{game_name} New Update: Top Hidden Features & Gameplay Changes",
                "strategy": "Trending Update",
                "reason": "Captures surge in searches for latest game patch and meta shifts."
            },
            {
                "title": f"How to Win Every Solo vs Squad in {game_name} (Pro Tips)",
                "strategy": "Tactical Guide",
                "reason": "Practical survival and combat tips that drive high watch time."
            }
        ]
    elif is_coding:
        # Tech / Coding Niche
        lang = subject_title
        fallback_templates = [
            {
                "title": f"{lang} Complete Roadmap 2026: What You Actually Need to Learn",
                "strategy": "Career Roadmap",
                "reason": "Consistent high search volume from beginners and upskilling developers."
            },
            {
                "title": f"Build a Real Full-Stack Project with {lang} in 1 Hour",
                "strategy": "Hands-On Project",
                "reason": "Project-based tutorials have the highest click-through and completion rates."
            },
            {
                "title": f"10 Common {lang} Mistakes Beginners Make (And How to Fix Them)",
                "strategy": "Problem-Solution",
                "reason": "Addresses real developer pain points with immediate utility."
            },
            {
                "title": f"{lang} Crash Course for Beginners: From Zero to Pro",
                "strategy": "Search Intent",
                "reason": "Top evergreen search keyword alignment for programming tutorials."
            }
        ]
    elif is_sports:
        # Sports / Cricket Niche
        fallback_templates = [
            {
                "title": f"{subject_title}: Tactical Breakdown, Key Strategies & Match Review",
                "strategy": "Match Analysis",
                "reason": "Engages sports fans looking for in-depth technical discussion."
            },
            {
                "title": f"Mastering {subject_title}: Essential Techniques for Better Performance",
                "strategy": "Training Masterclass",
                "reason": "High intent for skill improvement and athletic development."
            },
            {
                "title": f"{subject_title} Explained: Rules, Strategies & What Makes It Great",
                "strategy": "Search Intent",
                "reason": "Clean overview matching general search audience."
            },
            {
                "title": f"Top 5 Moments & Game-Changing Plays in {subject_title}",
                "strategy": "Highlights Breakdown",
                "reason": "High-energy hook targeting enthusiast and casual fans alike."
            }
        ]
    else:
        # General / Autocomplete-grounded creator titles
        sub_q = f" ({q1})" if q1 else ""
        fallback_templates = [
            {
                "title": f"{subject_title}{sub_q}: Complete Guide & Pro Insights (2026)",
                "strategy": "Search Intent",
                "reason": "Anchored directly in current YouTube user search interest."
            },
            {
                "title": f"Everything You Need to Know About {subject_title} (Key Breakdown)",
                "strategy": "Comprehensive Overview",
                "reason": "Clear value proposition for viewers researching this topic."
            },
            {
                "title": f"Top 5 Things You Should Know Before Starting {subject_title}",
                "strategy": "High-CTR Hook",
                "reason": "Curiosity and preparation hook driving high initial click rates."
            },
            {
                "title": f"{subject_title} Explained: Key Trends, Tips & Practical Advice",
                "strategy": "Practical Guide",
                "reason": "Balanced informational title with strong search discoverability."
            }
        ]

    results = []
    for item in fallback_templates[:count]:
        results.append({
            "title": item["title"],
            "strategy": item["strategy"],
            "primary_keyword": clean_kw or subject,
            "reason": item["reason"],
            "relevance_score": 92,
            "ctr_score": 88
        })
    return results
