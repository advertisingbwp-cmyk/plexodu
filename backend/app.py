"""
SMTAS - Social Media Trend Analysis System
Main Flask Application (YouTube-Only + Groq AI Subsystem)
"""

import os
import sys
import re
import csv
import io
import time
import secrets
import json
import uuid
from datetime import datetime, date, timedelta, timezone

from flask import Flask, request, jsonify, send_from_directory, send_file, Response, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))
from app.core.config import settings

from models import db, User, Trend, Metric, Sentiment, Report, AuditLog
from services.real_api import fetch_youtube_data, audit_youtube_channel, analyze_youtube_video  # LIVE YouTube Data API v3
from services.nlp_engine import analyze_sentiment
from services.trend_engine import (
    calculate_growth_rate,
    calculate_virality_index,
    calculate_engagement_rate,
    calculate_seo_score,
    classify_trend_stage,
    total_views,
)
from services.report_generator import generate_pdf_report, generate_pdf_report_buffer
from services.groq_service import chat_with_groq          # Groq AI Service (Llama 3.3 70B)

from services.security_guard import (
    rate_limiter,
    ValidationError,
    validate_keyword_input,
    validate_youtube_url,
    validate_channel_identifier,
    API_LIMIT_PER_MIN,
    AI_LIMIT_PER_MIN,
    MAX_UPLOAD_SIZE,
)

import requests as _requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

DATA_DIR = os.environ.get("DATA_DIR", "/tmp" if os.environ.get("VERCEL") else os.path.dirname(__file__))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "smtas.db")

# Plexudo operates in 100% public/no-login mode. No user caches or token files needed.
def _log_action(action: str, details: str = ""):
    """Write an entry to the audit_logs table."""
    try:
        log = AuditLog(
            user_id=None,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else "127.0.0.1",
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass



app = Flask(__name__, static_folder=None)

# ProxyFix for secure reverse-proxy deployments (e.g. Vercel, Nginx, Render)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Database Configuration (PostgreSQL with pooling when DATABASE_URL is set, SQLite fallback)
database_uri = settings.DATABASE_URL if settings.DATABASE_URL else f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
if database_uri.startswith("postgresql"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
app.secret_key = settings.SECRET_KEY
IS_PRODUCTION = settings.IS_PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION


_CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://plexudo.vercel.app,http://localhost:5000,http://127.0.0.1:5000,http://localhost:5173"
).split(",") if o.strip()]
CORS(app, supports_credentials=False, origins=_CORS_ORIGINS)
db.init_app(app)

from services.title_intelligence import generate_context_aware_titles


@app.after_request
def add_security_and_robots_headers(response):
    # Send X-Robots-Tag for private API routes
    if request.path.startswith("/api/"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response

MAX_LOGIN_ATTEMPTS = 5
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()


# --------------------------------------------------------------------------
# Global Safe Error Handlers (Zero Information Leakage)
# --------------------------------------------------------------------------
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({"error": e.message, "field": e.field}), 400


@app.errorhandler(400)
def handle_bad_request(e):
    msg = getattr(e, "description", "Malformed request payload")
    return jsonify({"error": msg}), 400


@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(413)
def handle_large_file(e):
    return jsonify({"error": "File size exceeds the 5 MB limit."}), 413


@app.errorhandler(429)
def handle_rate_limit(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429


@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Requested API resource not found"}), 404
    path = request.path.lstrip("/").lower()
    public_seo_routes = {"blog", "privacy", "terms"}
    if path in public_seo_routes or path.startswith("blog/"):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({"error": "Requested resource not found"}), 404


@app.errorhandler(Exception)
def handle_generic_exception(e):
    import traceback
    # Full traceback logged securely on server only
    app.logger.error(f"Internal Server Error: {str(e)}\n{traceback.format_exc()}")
    # Client receives generic safe message
    return jsonify({"error": "An internal system error occurred. Please try again later."}), 500


# --------------------------------------------------------------------------
# Cache Policy
# --------------------------------------------------------------------------
@app.after_request
def apply_cache_control(response):
    # Dynamic API responses should not be cached in ways that leak or cross-contaminate
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"]        = "no-cache"
        response.headers["Expires"]       = "0"
    return response


# --------------------------------------------------------------------------
# Static frontend and public SEO route serving
# --------------------------------------------------------------------------
@app.route("/")
def serve_landing():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/tools")
@app.route("/tools/")
def serve_tools_index():
    return send_from_directory(os.path.join(FRONTEND_DIR, "tools"), "index.html")


@app.route("/tools/<path:tool_name>")
def serve_standalone_tool(tool_name):
    clean_name = tool_name.replace(".html", "")
    target = os.path.join(FRONTEND_DIR, "tools", f"{clean_name}.html")
    if os.path.isfile(target):
        return send_from_directory(os.path.join(FRONTEND_DIR, "tools"), f"{clean_name}.html")
    return jsonify({"error": "Tool not found"}), 404


@app.route("/blog")
@app.route("/privacy")
@app.route("/terms")
def serve_seo_pages():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/favicon.ico")
def serve_favicon_ico():
    return send_from_directory(FRONTEND_DIR, "favicon.ico", mimetype="image/x-icon")


@app.route("/favicon.svg")
def serve_favicon_svg():
    return send_from_directory(FRONTEND_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.route("/favicon.png")
@app.route("/apple-touch-icon.png")
def serve_favicon_png():
    return send_from_directory(FRONTEND_DIR, "favicon.png", mimetype="image/png")


@app.route("/<path:path>")
def serve_static_or_public(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)

    clean_path = path.strip("/").lower()
    if clean_path == "tools":
        return send_from_directory(os.path.join(FRONTEND_DIR, "tools"), "index.html")
    if clean_path.startswith("tools/"):
        tool_sub = clean_path[len("tools/"):].replace(".html", "")
        tool_file = os.path.join(FRONTEND_DIR, "tools", f"{tool_sub}.html")
        if os.path.isfile(tool_file):
            return send_from_directory(os.path.join(FRONTEND_DIR, "tools"), f"{tool_sub}.html")

    seo_routes = {"blog", "privacy", "terms"}
    if clean_path in seo_routes or clean_path.startswith("blog"):
        return send_from_directory(FRONTEND_DIR, "index.html")

    return jsonify({"error": "Requested resource not found"}), 404



# --------------------------------------------------------------------------
# YouTube Data Acquisition + Sentiment + Scoring
# --------------------------------------------------------------------------
@app.route("/api/search", methods=["POST"])
def search_trend():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"search_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds."}), 429

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Missing payload"}), 400

    keyword = validate_keyword_input(data.get("keyword", ""))

    results = {}
    search_result = _process_platform(keyword, "YouTube", fetch_youtube_data)
    results["YouTube"] = search_result

    if search_result.get("error"):
        if search_result.get("status") == 429 or search_result.get("quota_exceeded"):
            return jsonify({
                "error": search_result.get("message", "YouTube API daily quota reached. Please try again later."),
                "quota_exceeded": True
            }), 429

    _log_action("SEARCH", f"keyword={keyword} platform=YouTube")
    return jsonify({"keyword": keyword, "results": results})



def _process_platform(keyword, platform_name, fetch_fn):
    try:
        raw = fetch_fn(keyword)
    except Exception as e:
        app.logger.error(f"Error fetching {platform_name} data: {e}")
        return {"error": True, "message": f"Could not fetch {platform_name} data. Please try again later.", "status": 500}

    if raw.get("status") != 200:
        return {
            "error": True,
            "message": raw.get("error", f"{platform_name} API request failed."),
            "status": raw.get("status"),
            "quota_exceeded": raw.get("quota_exceeded", False)
        }

    growth_rate = calculate_growth_rate(raw["daily_metrics"])
    virality = calculate_virality_index(raw["daily_metrics"])
    engagement = calculate_engagement_rate(raw["daily_metrics"])
    seo_analysis = calculate_seo_score(raw["daily_metrics"], keyword)
    stage = classify_trend_stage(growth_rate)
    views_sum = total_views(raw["daily_metrics"])

    sentiment_result = analyze_sentiment(raw["comments"])

    # Generate YouTube Tags & Context-Aware Title Ideas
    related_list = raw.get("related_keywords", [])
    youtube_tags = [keyword] + [r for r in related_list if r.lower() != keyword.lower()]
    hashtag_list = [f"#{t.replace(' ', '')}" for t in youtube_tags[:6]]

    top_v_title = raw.get("title", "")
    top_video_titles = [top_v_title] if top_v_title else []

    title_objs = generate_context_aware_titles(
        keyword=keyword,
        topic="",
        related_queries=related_list,
        top_video_titles=top_video_titles,
        count=4
    )
    seo_title_ideas = [t["title"] for t in title_objs]

    trend = Trend(
        keyword=keyword,
        platform=platform_name,
        total_views=views_sum,
        growth_rate=growth_rate,
        virality_score=virality,
        peak_date=datetime.now(timezone.utc),
        created_by=None,
    )
    db.session.add(trend)
    db.session.flush()

    for day in raw["daily_metrics"]:
        db.session.add(Metric(
            trend_id=trend.trend_id,
            views=day["views"],
            likes=day["likes"],
            shares=day["shares"],
            comments_count=day["comments_count"],
            recorded_date=datetime.strptime(day["date"], "%Y-%m-%d").date(),
        ))

    db.session.add(Sentiment(
        trend_id=trend.trend_id,
        positive_score=sentiment_result["positive_score"],
        negative_score=sentiment_result["negative_score"],
        neutral_score=sentiment_result["neutral_score"],
        dominant_sentiment=sentiment_result["dominant_sentiment"],
        sample_comment=sentiment_result["sample_comment"],
    ))
    db.session.commit()

    return {
        "trend_id": trend.trend_id,
        "keyword": keyword,
        "platform": platform_name,
        "total_views": views_sum,
        "growth_rate": growth_rate,
        "virality_score": virality,
        "engagement_rate": engagement,
        "seo_analysis": seo_analysis,
        "stage": stage,
        "daily_metrics": raw["daily_metrics"],
        "sentiment": sentiment_result,
        "related_keywords": related_list,
        "youtube_tags": youtube_tags[:10],
        "youtube_hashtags": hashtag_list,
        "seo_title_ideas": seo_title_ideas,
    }


# --------------------------------------------------------------------------
# History / Listing
# --------------------------------------------------------------------------
@app.route("/api/trends", methods=["GET"])
def list_trends():
    trends = Trend.query.order_by(Trend.timestamp.desc()).limit(50).all()

    output = []
    for t in trends:
        sentiment = Sentiment.query.filter_by(trend_id=t.trend_id).first()
        growth = t.growth_rate
        output.append({
            "trend_id": t.trend_id,
            "keyword": t.keyword,
            "platform": t.platform,
            "total_views": t.total_views,
            "growth_rate": growth,
            "virality_score": t.virality_score,
            "timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M"),
            "dominant_sentiment": sentiment.dominant_sentiment if sentiment else "n/a",
        })
    return jsonify({"trends": output})


# --------------------------------------------------------------------------
# Keyword Comparison Endpoint (Compares multiple YouTube searches)
# --------------------------------------------------------------------------
@app.route("/api/compare-keywords", methods=["GET", "POST"])
def compare_keywords():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"compare_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds."}), 429

    ids = []
    if request.method == "POST" and request.is_json:
        data = request.get_json(silent=True) or {}
        raw_ids = data.get("ids", [])
        if isinstance(raw_ids, list):
            for i in raw_ids:
                try:
                    ids.append(int(i))
                except (ValueError, TypeError):
                    pass

    ids_param = request.args.get("ids", "")
    if ids_param:
        try:
            ids.extend([int(i) for i in ids_param.split(",") if i.strip()])
        except ValueError:
            pass

    if ids:
        trends = Trend.query.filter(Trend.trend_id.in_(ids)).all()
    else:
        # Default: latest 6 unique keywords
        trends = Trend.query.order_by(Trend.timestamp.desc()).limit(6).all()

    comparison_data = []
    for t in trends:
        metrics = Metric.query.filter_by(trend_id=t.trend_id).order_by(Metric.recorded_date).all()
        sentiment = Sentiment.query.filter_by(trend_id=t.trend_id).first()

        growth = t.growth_rate
        virality = t.virality_score
        if metrics and len(metrics) >= 2:
            d_metrics = [{"views": m.views, "likes": m.likes, "shares": m.shares, "comments_count": m.comments_count} for m in metrics]
            growth = calculate_growth_rate(d_metrics)
            virality = calculate_virality_index(d_metrics)

        comparison_data.append({
            "trend_id": t.trend_id,
            "keyword": t.keyword,
            "total_views": t.total_views,
            "growth_rate": growth,
            "virality_score": virality,
            "stage": classify_trend_stage(growth),
            "dominant_sentiment": sentiment.dominant_sentiment if sentiment else "n/a",
            "daily_metrics": [{"date": m.recorded_date.strftime("%Y-%m-%d"), "views": m.views} for m in metrics]
        })

    return jsonify({"comparison": comparison_data})


# --------------------------------------------------------------------------
# Report Generators — PDF & CSV
# --------------------------------------------------------------------------
@app.route("/api/report/<int:trend_id>", methods=["GET", "POST"])
def generate_report(trend_id):
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"report_ip_{client_ip}", 30, 60)
    if not allowed:
        return jsonify({"error": f"Report rate limit exceeded. Please wait {retry_after} seconds."}), 429

    trend = Trend.query.filter_by(trend_id=trend_id).first()
    if not trend:
        return jsonify({"error": "Trend report not found"}), 404

    try:
        sentiment = Sentiment.query.filter_by(trend_id=trend_id).first()
        sentiment_dict = {
            "positive_score": sentiment.positive_score,
            "negative_score": sentiment.negative_score,
            "neutral_score": sentiment.neutral_score,
            "dominant_sentiment": sentiment.dominant_sentiment,
        } if sentiment else {"positive_score": 0, "negative_score": 0, "neutral_score": 0, "dominant_sentiment": "n/a"}

        trend_dict = {
            "keyword": trend.keyword,
            "platform": trend.platform,
            "total_views": trend.total_views,
        }
        stage = classify_trend_stage(trend.growth_rate)

        user_email = "anonymous_creator@plexudo.com"

        filename, buffer = generate_pdf_report_buffer(
            trend_dict, sentiment_dict, trend.growth_rate, trend.virality_score, stage, user_email
        )

        report = Report(trend_id=trend_id, generated_by=None, format="PDF", file_path=f"memory://{filename}")
        db.session.add(report)
        db.session.commit()
        _log_action("EXPORT_PDF", f"trend_id={trend_id} keyword={trend.keyword}")

        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        app.logger.error(f"Failed to generate PDF report: {e}")
        return jsonify({"error": "Failed to generate report"}), 500


@app.route("/api/export-csv/<int:trend_id>", methods=["GET"])
def export_csv(trend_id):
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"export_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Export rate limit exceeded. Please wait {retry_after} seconds."}), 429

    trend = Trend.query.filter_by(trend_id=trend_id).first()
    if not trend:
        return jsonify({"error": "Trend report not found"}), 404

    sentiment = Sentiment.query.filter_by(trend_id=trend_id).first()
    metrics = Metric.query.filter_by(trend_id=trend_id).order_by(Metric.recorded_date).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SMTAS - YouTube Trend Analysis CSV Export"])
    writer.writerow(["Generated By", "anonymous_creator@plexudo.com"])
    writer.writerow(["Generated On", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    writer.writerow([])

    writer.writerow(["Keyword", "Platform", "Total Views", "Growth Rate (%)", "Virality Score", "Trend Stage", "Timestamp"])
    stage = classify_trend_stage(trend.growth_rate)
    writer.writerow([
        trend.keyword, trend.platform, trend.total_views,
        trend.growth_rate, trend.virality_score, stage,
        trend.timestamp.strftime("%Y-%m-%d %H:%M")
    ])
    writer.writerow([])

    if sentiment:
        writer.writerow(["Sentiment Analysis"])
        writer.writerow(["Positive (%)", "Negative (%)", "Neutral (%)", "Dominant"])
        writer.writerow([
            sentiment.positive_score, sentiment.negative_score,
            sentiment.neutral_score, sentiment.dominant_sentiment
        ])
        writer.writerow([])

    writer.writerow(["Daily Metrics"])
    writer.writerow(["Date", "Views", "Likes", "Shares", "Comments"])
    for m in metrics:
        writer.writerow([m.recorded_date, m.views, m.likes, m.shares, m.comments_count])

    csv_data = output.getvalue()
    output.close()

    _log_action("EXPORT_CSV", f"trend_id={trend_id} keyword={trend.keyword}")

    filename = f"smtas_{trend.keyword.replace(' ', '_')}_YouTube.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# --------------------------------------------------------------------------
# Groq AI Chat
# --------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def ai_chat():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"ai_ip_{client_ip}", AI_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"AI request limit reached. Please wait {retry_after} seconds."}), 429

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Message payload is required"}), 400

    message = data.get("message", "").strip()
    trend_context = data.get("context", None)
    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    if len(message) > 1000:
        return jsonify({"error": "Message exceeds maximum length (1,000 characters)"}), 400

    result = chat_with_groq(message, trend_context, history=history)
    _log_action("CHAT", f"msg_preview={message[:80]}")
    return jsonify(result)


# --------------------------------------------------------------------------
# YouTube Keyword Suggestions (Autocomplete)
# --------------------------------------------------------------------------
_SUGGEST_CACHE = {}
_SUGGEST_CACHE_TTL = 900  # 15 minutes


@app.route("/api/suggest", methods=["GET"])
def keyword_suggest():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"suggest_ip_{client_ip}", API_LIMIT_PER_MIN * 2, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds.", "suggestions": []}), 429

    query = request.args.get("q", "").strip()
    if not query or len(query) < 2 or len(query) > 100:
        return jsonify({"suggestions": []})

    # Reject invalid control characters
    if re.search(r'[\x00-\x1F<>]', query):
        return jsonify({"suggestions": []})

    cache_key = query.lower()
    cached = _SUGGEST_CACHE.get(cache_key)
    if cached:
        ts, data = cached
        if time.time() - ts < _SUGGEST_CACHE_TTL:
            return jsonify({"suggestions": data})

    suggestions = []

    if YOUTUBE_API_KEY:
        try:
            res = _requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": 8,
                    "order": "viewCount",
                    "key": YOUTUBE_API_KEY,
                },
                timeout=5,
            )
            if res.status_code == 200:
                items = res.json().get("items", [])
                seen = set()
                for item in items:
                    title = item["snippet"].get("title", "")
                    words = title.split()
                    phrase = " ".join(words[:4]).strip()
                    if phrase and phrase.lower() not in seen and query.lower() in phrase.lower():
                        suggestions.append(phrase)
                        seen.add(phrase.lower())
                    if len(title) <= 50 and title.lower() not in seen:
                        suggestions.append(title)
                        seen.add(title.lower())
        except Exception:
            pass

    if len(suggestions) < 5:
        try:
            gs_res = _requests.get(
                "https://suggestqueries.google.com/complete/search",
                params={"client": "firefox", "ds": "yt", "q": query},
                timeout=5,
            )
            if gs_res.status_code == 200:
                raw = gs_res.json()
                google_suggs = raw[1] if len(raw) > 1 else []
                for s in google_suggs[:8]:
                    if s not in suggestions:
                        suggestions.append(s)
        except Exception:
            pass

    final_suggestions = suggestions[:10]
    _SUGGEST_CACHE[cache_key] = (time.time(), final_suggestions)
    return jsonify({"suggestions": final_suggestions})


# --------------------------------------------------------------------------
# Channel / URL Audit Endpoint
# --------------------------------------------------------------------------
@app.route("/api/audit-channel", methods=["POST"])
def audit_channel():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"audit_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds."}), 429

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Missing payload"}), 400

    raw_identifier = data.get("identifier", "")
    identifier = validate_channel_identifier(raw_identifier)

    is_handle = identifier.startswith("@") or ("/" not in identifier and not identifier.startswith("http"))
    result    = audit_youtube_channel(identifier, is_handle=is_handle)

    _log_action("AUDIT_CHANNEL", f"identifier={identifier}")
    return jsonify(result)


# --------------------------------------------------------------------------
# YouTube Video Analysis Endpoint
# --------------------------------------------------------------------------
@app.route("/api/video-analysis", methods=["POST"])
def video_analysis():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"video_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds."}), 429

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Missing payload"}), 400

    raw_url = data.get("url", "").strip()
    url = validate_youtube_url(raw_url)

    result = analyze_youtube_video(url)


    if result.get("error"):
        _log_action("VIDEO_ANALYSIS_ERROR", f"url={url} err={result.get('message','')}")
        return jsonify(result), 400

    # Run NLP sentiment
    sentiment = analyze_sentiment(result["comments"])

    # Virality & growth scores
    growth_rate   = calculate_growth_rate(result["daily_metrics"])
    virality      = calculate_virality_index(result["daily_metrics"])
    engagement    = calculate_engagement_rate(result["daily_metrics"])
    seo_analysis  = calculate_seo_score(result["daily_metrics"], result["title"])
    stage         = classify_trend_stage(growth_rate)

    _log_action("VIDEO_ANALYSIS", f"video_id={result['video_id']} title={result['title'][:60]}")

    return jsonify({
        **result,
        "sentiment":     sentiment,
        "growth_rate":   growth_rate,
        "virality_score": virality,
        "engagement_rate": engagement,
        "seo_analysis":  seo_analysis,
        "stage":         stage,
    })


# --------------------------------------------------------------------------
# Audit Log endpoint
# --------------------------------------------------------------------------
@app.route("/api/audit-log", methods=["GET"])
def get_audit_log():
    client_ip = request.remote_addr or "127.0.0.1"
    allowed, retry_after = rate_limiter.is_allowed(f"audit_log_ip_{client_ip}", API_LIMIT_PER_MIN, 60)
    if not allowed:
        return jsonify({"error": f"Rate limit exceeded. Please wait {retry_after} seconds."}), 429

    logs = (
        AuditLog.query
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    output = []
    for log in logs:
        output.append({
            "id": log.id,
            "action": log.action,
            "details": log.details or "",
            "ip_address": log.ip_address or "—",
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return jsonify({"logs": output})


# --------------------------------------------------------------------------
# App bootstrap
# --------------------------------------------------------------------------
def create_tables():
    with app.app_context():
        db.create_all()
        try:
            from migrate_db import run_migration
            run_migration(db.engine)
        except Exception as e:
            app.logger.warning(f"Database migration notice: {e}")
        # NOTE: No default accounts are seeded. All user accounts must be
        # created through the normal registration flow or via environment
        # variable-controlled seed scripts in controlled deployment pipelines.


create_tables()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print(f"SMTAS YouTube-Only backend running at http://127.0.0.1:{port}")
    app.run(debug=debug_mode, host="0.0.0.0", port=port, threaded=True)
