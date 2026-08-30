import os
import re
import json
import random
import urllib.parse
import requests
from flask import Blueprint, request, jsonify, session, redirect

channel_seo_bp = Blueprint('channel_seo', __name__, url_prefix='/api/channel-seo')

from app.core.config import settings

# Store OAuth tokens in session or simple dict for demo
OAUTH_TOKENS = {}

def get_google_client_id():
    return settings.GOOGLE_CLIENT_ID or os.environ.get("GOOGLE_CLIENT_ID", "").strip()

def get_google_client_secret():
    return settings.GOOGLE_CLIENT_SECRET or os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

def get_redirect_uri():
    return (
        os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
        or settings.GOOGLE_REDIRECT_URI
        or "http://127.0.0.1:5000/api/channel-seo/auth/callback"
    )

# --------------------------------------------------------------------------
# OAuth Routes
# --------------------------------------------------------------------------
import urllib.parse

@channel_seo_bp.route('/auth/google', methods=['GET'])
def auth_google():
    client_id = get_google_client_id()
    redirect_uri = get_redirect_uri()
    encoded_redirect = urllib.parse.quote(redirect_uri, safe='')
    encoded_scope = urllib.parse.quote("openid email profile https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl", safe='')

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&client_id={client_id}&redirect_uri={encoded_redirect}&"
        f"scope={encoded_scope}&access_type=offline&prompt=consent"
    )
    return redirect(auth_url)


@channel_seo_bp.route('/auth/callback', methods=['GET'])
def auth_callback():
    code = request.args.get('code')
    if not code:
        return "Missing auth code", 400

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": get_google_client_id(),
        "client_secret": get_google_client_secret(),
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code"
    }

    resp = requests.post(token_url, data=payload)
    if resp.status_code != 200:
        return f"OAuth Error: {resp.text}", 400

    tokens = resp.json()
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')
    session['google_access_token'] = access_token
    if refresh_token:
        session['google_refresh_token'] = refresh_token
    OAUTH_TOKENS['access_token'] = access_token

    # Fetch Google User Identity and login or create user
    try:
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code == 200:
            uinfo = userinfo_resp.json()
            google_email = uinfo.get("email")
            google_name = uinfo.get("name") or "Creator"
            google_sub = uinfo.get("sub")
            google_pic = uinfo.get("picture")

            if google_email:
                from models import db, User
                user = User.query.filter_by(email=google_email).first()
                if not user:
                    # Create Plexudo user with verified Google email & 3 welcome credits
                    user = User(
                        name=google_name,
                        email=google_email,
                        password_hash="google_oauth_no_pwd",
                        role="Creator",
                        google_id=google_sub,
                        avatar_url=google_pic,
                        email_verified=True,
                        credits=3
                    )
                    db.session.add(user)
                    db.session.commit()
                else:
                    # Link Google identity
                    if google_sub and not user.google_id:
                        user.google_id = google_sub
                    if google_pic and not user.avatar_url:
                        user.avatar_url = google_pic
                    user.email_verified = True
                    db.session.commit()

                # Set authenticated session
                session["user_id"] = user.id
                session["email"] = user.email
                session["role"] = user.role
    except Exception as e:
        print(f"Google userinfo sync notice: {e}")

    return redirect('/dashboard.html?seo_auth=success#channelSeo')


@channel_seo_bp.route('/auth/status', methods=['GET'])
def auth_status():
    token = session.get('google_access_token') or OAUTH_TOKENS.get('access_token')
    return jsonify({"authenticated": bool(token)})


@channel_seo_bp.route('/auth/disconnect', methods=['POST'])
def auth_disconnect():
    session.pop('google_access_token', None)
    session.pop('google_refresh_token', None)
    OAUTH_TOKENS.clear()
    return jsonify({"success": True, "connected": False, "message": "Successfully disconnected YouTube channel."})


# --------------------------------------------------------------------------
# YouTube Video Routes
# --------------------------------------------------------------------------
@channel_seo_bp.route('/videos', methods=['GET'])
def list_videos():
    token = session.get('google_access_token') or OAUTH_TOKENS.get('access_token')

    if token:
        headers = {"Authorization": f"Bearer {token}"}
        # Fetch my channel uploads playlist
        ch_resp = requests.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true", headers=headers)
        if ch_resp.status_code == 200:
            ch_data = ch_resp.json()
            items = ch_data.get('items', [])
            if items:
                uploads_id = items[0].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
                if uploads_id:
                    pl_resp = requests.get(f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_id}&maxResults=25", headers=headers)
                    if pl_resp.status_code == 200:
                        pl_items = pl_resp.json().get('items', [])
                        videos = [{
                            "videoId": item['snippet']['resourceId']['videoId'],
                            "title": item['snippet']['title'],
                            "thumbnail": item['snippet'].get('thumbnails', {}).get('medium', {}).get('url', ''),
                            "publishedAt": item['snippet'].get('publishedAt', '')
                        } for item in pl_items]
                        if videos:
                            return jsonify({"videos": videos, "connected": True})

    return jsonify({"videos": [], "connected": bool(token)})


@channel_seo_bp.route('/videos/<video_id>', methods=['GET'])
def get_video_detail(video_id):
    token = session.get('google_access_token') or OAUTH_TOKENS.get('access_token')
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}"
    if not token and api_key:
        url += f"&key={api_key}"

    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        items = resp.json().get('items', [])
        if items:
            v = items[0]['snippet']
            return jsonify({
                "videoId": video_id,
                "title": v.get('title', ''),
                "description": v.get('description', ''),
                "tags": v.get('tags', []),
                "categoryId": v.get('categoryId', '20'),
                "thumbnail": v.get('thumbnails', {}).get('high', {}).get('url', '')
            })

    return jsonify({
        "videoId": video_id,
        "title": "Free fire Gameplay after update #freefire #freefireshorts #shorts",
        "description": "Get ready for the latest free fire new update, showcasing best free fire shorts and epic gameplay moments!",
        "tags": ["free fire", "freefire", "free fire shorts", "ff shorts", "free fire gameplay"],
        "categoryId": "20",
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    })


@channel_seo_bp.route('/videos/<video_id>', methods=['PUT'])
def update_video_detail(video_id):
    token = session.get('google_access_token') or OAUTH_TOKENS.get('access_token')
    if not token:
        return jsonify({"error": "Google YouTube OAuth connection required to update video on YouTube. Please click 'Connect YouTube Channel'!"}), 401

    data = request.json or {}
    title = data.get('title', '')
    description = data.get('description', '')
    tags = data.get('tags', [])
    category_id = data.get('categoryId', '20')

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Fetch current snippet
    get_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}"
    get_resp = requests.get(get_url, headers=headers)
    if get_resp.status_code != 200:
        return jsonify({"error": "Failed to fetch video from YouTube"}), 400

    items = get_resp.json().get('items', [])
    if not items:
        return jsonify({"error": "Video not found on YouTube"}), 404

    snippet = items[0]['snippet']
    snippet['title'] = title
    snippet['description'] = description
    snippet['tags'] = tags
    snippet['categoryId'] = category_id

    update_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet"
    body = {
        "id": video_id,
        "snippet": snippet
    }

    put_resp = requests.put(update_url, headers=headers, json=body)
    if put_resp.status_code == 200:
        return jsonify({"success": True, "message": "Successfully synced changes to live YouTube video!"})
    else:
        return jsonify({"error": f"YouTube API Error: {put_resp.text}"}), 400


# --------------------------------------------------------------------------
# SEO Scoring Route
# --------------------------------------------------------------------------
STOPWORDS = set([
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'is', 'are', 'was', 'were', 'be', 'this', 'that', 'it', 'as', 'by',
    'from', 'your', 'you', 'we', 'i', 'how', 'what', 'why', 'new'
])

def extract_keywords(text):
    if not text: return []
    words = ''.join([c if c.isalnum() or c.isspace() else ' ' for c in text.lower()]).split()
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]

@channel_seo_bp.route('/seo/analyze', methods=['POST'])
def analyze_seo():
    data = request.json or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    tags = data.get('tags', [])

    # Normalize tags
    clean_tags = []
    seen_tags = set()
    for t in tags:
        t_name = (t if isinstance(t, str) else t.get('name', '')).strip().lower()
        if t_name and t_name not in seen_tags:
            clean_tags.append(t_name)
            seen_tags.add(t_name)

    title_words = set(extract_keywords(title))
    desc_words = set(extract_keywords(description))

    # 1. Title Optimization (0-10)
    title_len = len(title)
    if title_len >= 30 and title_len <= 70 and len(title_words) >= 2:
        title_opt_score = 10
        title_opt_reason = "Title length (30-70 chars) and keyword density are optimal."
    elif title_len > 0 and len(title_words) >= 1:
        title_opt_score = 7
        title_opt_reason = "Title is present, but could be enhanced for length and clarity (aim for 40-70 chars)."
    else:
        title_opt_score = 3
        title_opt_reason = "Title is too short or missing key descriptive words."

    # 2. Description Depth & Optimization (0-10)
    desc_word_count = len(description.split())
    if desc_word_count >= 80 and len(desc_words) >= 10:
        desc_opt_score = 10
        desc_opt_reason = "Comprehensive description depth (>80 words) providing strong search engine context."
    elif desc_word_count >= 30:
        desc_opt_score = 7
        desc_opt_reason = "Good baseline description. Expanding to 100+ words will provide deeper search context."
    elif desc_word_count > 0:
        desc_opt_score = 4
        desc_opt_reason = "Description is brief. Add more context about topics covered and key takeaways."
    else:
        desc_opt_score = 0
        desc_opt_reason = "Description is empty. Add 2-3 paragraphs explaining the video."

    # 3. Tag Quality & Quantity (0-10)
    tag_count = len(clean_tags)
    if tag_count >= 8:
        tag_count_score = 10
        tag_count_reason = f"Excellent tag coverage ({tag_count} unique tags)."
    elif tag_count >= 4:
        tag_count_score = 6
        tag_count_reason = f"Moderate tag count ({tag_count} tags). Aim for 8-12 relevant tags."
    elif tag_count > 0:
        tag_count_score = 3
        tag_count_reason = f"Low tag count ({tag_count} tags). Add more topic-specific tags."
    else:
        tag_count_score = 0
        tag_count_reason = "No tags added. Add relevant keywords to help search categorization."

    # 4. Keyword Consistency (0-10)
    if clean_tags and title_words:
        kw_in_title_count = sum(1 for tag in clean_tags if any(w in title_words for w in extract_keywords(tag)))
        kw_in_title_score = min(10, max(0, round((kw_in_title_count / len(clean_tags)) * 10)))
        kw_in_title_reason = f"{kw_in_title_count} of {len(clean_tags)} tags directly match words in your title."
    else:
        kw_in_title_score = 0
        kw_in_title_reason = "Tags and title words do not currently align."

    # 5. Triple Metadata Overlap (0-10)
    if clean_tags and title_words and desc_words:
        overlap_count = sum(1 for tag in clean_tags if any(w in title_words for w in extract_keywords(tag)) and any(w in desc_words for w in extract_keywords(tag)))
        overlap_score = min(10, max(1, round((overlap_count / max(1, len(title_words))) * 10))) if overlap_count > 0 else 2
        overlap_reason = f"Found {overlap_count} core topic terms synchronized across Title, Description, and Tags."
    else:
        overlap_score = 0
        overlap_reason = "Add matching keywords across Title, Description, and Tags for full consistency."

    total_score = title_opt_score + desc_opt_score + tag_count_score + kw_in_title_score + overlap_score

    return jsonify({
        "actionableItems": {
            "total": total_score,
            "max": 50,
            "methodology": "Plexudo 50-Point SEO Audit",
            "breakdown": {
                "tagCount": {"score": title_opt_score, "max": 10, "label": "Title Optimization", "reason": title_opt_reason},
                "tagVolume": {"score": desc_opt_score, "max": 10, "label": "Description Depth", "reason": desc_opt_reason},
                "keywordsInTitle": {"score": tag_count_score, "max": 10, "label": "Tag Quality & Quantity", "reason": tag_count_reason},
                "keywordsInDescription": {"score": kw_in_title_score, "max": 10, "label": "Keyword Consistency", "reason": kw_in_title_reason},
                "sameKeywordOverlap": {"score": overlap_score, "max": 10, "label": "Triple Metadata Overlap", "reason": overlap_reason}
            }
        }
    })


# --------------------------------------------------------------------------
# AI Endpoints (Plexudo SEO Intelligence)
# --------------------------------------------------------------------------
@channel_seo_bp.route('/ai/suggest-titles', methods=['POST'])
def suggest_titles():
    from services.title_intelligence import generate_context_aware_titles

    data = request.json or {}
    title = data.get('title', '').strip()
    topic = data.get('topic', '').strip() or title
    keyword = data.get('keyword', '').strip() or title
    description = data.get('description', '').strip()
    tags = data.get('tags', [])
    video_type = data.get('video_type', '').strip()
    target_audience = data.get('target_audience', '').strip()
    count = int(data.get('count', 3))

    titles = generate_context_aware_titles(
        keyword=keyword,
        topic=topic,
        description=description,
        tags=tags,
        video_type=video_type,
        target_audience=target_audience,
        count=count
    )

    return jsonify({"titles": titles})


@channel_seo_bp.route('/ai/generate-description', methods=['POST'])
def generate_description():
    data = request.json or {}
    title = data.get('title', '').strip()
    clean_title = re.sub(r'[#@\(\)\[\]]', '', title).strip() or 'YouTube Video'
    tags = data.get('tags', [])
    tag_strings = [t if isinstance(t, str) else t.get('name', '') for t in tags]
    clean_tags = [t.strip() for t in tag_strings if t.strip()]
    tag_context = ", ".join(clean_tags[:8]) if clean_tags else clean_title

    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "").strip()

    if groq_key:
        prompt_content = (
            f"Write a natural, well-structured, professional 3-paragraph YouTube description for a video titled '{clean_title}'.\n"
            f"Key topic context and keywords: {tag_context}.\n\n"
            "Structure requirements:\n"
            "1. Paragraph 1: An engaging introduction clearly describing the topic of the video.\n"
            "2. Paragraph 2: Key takeaways, topics covered, and valuable insights viewers will learn.\n"
            "3. Paragraph 3: A friendly call to action (like, subscribe, comment feedback) naturally weaving in relevant context.\n"
            "4. End with 3-4 relevant hashtags on a new line.\n"
            "Rules: Do NOT include artificial keyword-stuffing blocks, fake timestamps, or unsupported claims."
        )

        for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "max_tokens": 700,
                        "messages": [{"role": "user", "content": prompt_content}],
                        "temperature": 0.5
                    },
                    timeout=8
                )
                if resp.status_code == 200:
                    content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        if '<think>' in content:
                            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                        return jsonify({"description": content.strip()})
            except Exception:
                continue

    # Clean, natural fallback description
    topic_kw = clean_tags[0] if clean_tags else clean_title
    fallback_desc = (
        f"Welcome to the video! Today we're exploring {clean_title}.\n\n"
        f"In this guide, we dive deep into {topic_kw}, breaking down essential strategies, helpful tips, and step-by-step insights to give you the most comprehensive understanding of the topic.\n\n"
        f"If you found this video helpful, please make sure to give it a thumbs up, leave a comment with your thoughts or questions, and subscribe for more regular content!\n\n"
        f"#{clean_title.split()[0]} #YouTubeSEO #CreatorTips"
    )
    return jsonify({"description": fallback_desc})


@channel_seo_bp.route('/ai/suggest-tags', methods=['POST'])
def suggest_tags():
    data = request.json or {}
    title = data.get('title', '').strip()
    clean_title = re.sub(r'[#@\(\)\[\]]', '', title).strip() or 'YouTube Video'
    topic_keywords = extract_keywords(clean_title)
    base_kw = " ".join(topic_keywords[:3]) if topic_keywords else clean_title.lower()

    # Step 1: Query Google/YouTube Autocomplete for real user search queries
    real_suggestions = []
    try:
        ac_res = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "ds": "yt", "q": base_kw},
            timeout=4
        )
        if ac_res.status_code == 200:
            raw_sugg = ac_res.json()[1] if len(ac_res.json()) > 1 else []
            for s in raw_sugg:
                cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
                if cleaned and len(cleaned) > 2:
                    real_suggestions.append(cleaned)
    except Exception:
        pass

    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "").strip()
    ai_tags = []

    if groq_key:
        prompt_content = (
            f"Suggest 10 relevant, non-spammy YouTube tags for a video titled '{clean_title}'.\n"
            "Rules:\n"
            "- Include primary keywords, secondary phrases, and long-tail variants.\n"
            "- Do NOT invent search volume numbers.\n"
            "- Return a JSON array of objects with keys:\n"
            "  'name': (lowercase string),\n"
            "  'relevance_tier': (one of: 'Primary', 'Long-Tail', 'Category')\n"
            "Return ONLY the JSON array. No markdown."
        )

        for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]:
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt_content}],
                        "temperature": 0.4
                    },
                    timeout=8
                )
                if resp.status_code == 200:
                    raw = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    raw_clean = raw.replace('```json', '').replace('```', '').strip()
                    if '<think>' in raw_clean:
                        raw_clean = re.sub(r'<think>.*?</think>', '', raw_clean, flags=re.DOTALL).strip()
                    tags = json.loads(raw_clean)
                    if isinstance(tags, list) and len(tags) > 0:
                        for t in tags:
                            t_name = t.get("name") if isinstance(t, dict) else str(t)
                            t_tier = t.get("relevance_tier") if isinstance(t, dict) else "Primary"
                            if t_name:
                                ai_tags.append({"name": t_name.strip().lower(), "relevance_tier": t_tier})
                        break
            except Exception:
                continue

    # Combine real YouTube search queries + AI relevance tags, deduplicate
    combined = []
    seen = set()

    for s in real_suggestions[:6]:
        if s not in seen:
            combined.append({"name": s, "relevance_tier": "YouTube Search", "source": "YouTube Autocomplete"})
            seen.add(s)

    for a in ai_tags:
        clean_name = a["name"].strip().lower()
        if clean_name not in seen:
            combined.append({"name": clean_name, "relevance_tier": a.get("relevance_tier", "Primary"), "source": "Plexudo AI"})
            seen.add(clean_name)

    if not combined:
        fallback_list = [
            base_kw,
            f"{base_kw} guide",
            f"how to {base_kw}",
            f"{base_kw} tips",
            f"best {base_kw}",
            f"{base_kw} tutorial",
            f"{base_kw} breakdown"
        ]
        for f in fallback_list:
            if f not in seen:
                combined.append({"name": f, "relevance_tier": "Topic Keyword", "source": "Plexudo Heuristic"})
                seen.add(f)

    return jsonify({"tags": combined})


@channel_seo_bp.route('/ai/find-tags', methods=['POST'])
def find_tags():
    data = request.json or {}
    keyword = (data.get('keyword') or 'trending').lower().strip()
    clean_kw = re.sub(r'[^a-zA-Z0-9\s]', '', keyword).strip() or 'trending'

    real_results = []
    seen = set()
    try:
        ac_res = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "ds": "yt", "q": clean_kw},
            timeout=4
        )
        if ac_res.status_code == 200:
            raw_sugg = ac_res.json()[1] if len(ac_res.json()) > 1 else []
            for s in raw_sugg:
                cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', s).strip().lower()
                if cleaned and cleaned not in seen:
                    real_results.append({"name": cleaned, "relevance_tier": "YouTube Search", "source": "YouTube Autocomplete"})
                    seen.add(cleaned)
    except Exception:
        pass

    if len(real_results) < 5:
        fallbacks = [
            f"{clean_kw} tips",
            f"{clean_kw} tutorial",
            f"how to {clean_kw}",
            f"best {clean_kw}",
            f"{clean_kw} explained",
            f"{clean_kw} guide"
        ]
        for f in fallbacks:
            if f not in seen:
                real_results.append({"name": f, "relevance_tier": "Long-Tail", "source": "Plexudo Heuristic"})
                seen.add(f)

    return jsonify({"tags": real_results})
