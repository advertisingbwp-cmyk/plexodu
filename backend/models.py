from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


def utc_today():
    return datetime.now(timezone.utc).date()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    role = db.Column(db.String(30), default="Creator")
    avatar_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)


class Trend(db.Model):
    __tablename__ = "trends"
    trend_id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(20), nullable=False)  # YouTube / TikTok
    total_views = db.Column(db.BigInteger, default=0)
    growth_rate = db.Column(db.Float, default=0.0)
    virality_score = db.Column(db.Float, default=0.0)
    peak_date = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now)

    # Phase 8 — Trend Intelligence Engine additions
    first_seen_at = db.Column(db.DateTime, default=utc_now)
    last_seen_at = db.Column(db.DateTime, default=utc_now)
    scan_count = db.Column(db.Integer, default=1)
    current_trend_score = db.Column(db.Float, nullable=True)
    current_direction = db.Column(db.String(20), default="STABLE")
    current_confidence = db.Column(db.String(20), default="Low")
    current_velocity = db.Column(db.Float, default=0.0)
    current_acceleration = db.Column(db.Float, default=0.0)

    metrics = db.relationship("Metric", backref="trend", lazy=True)
    sentiments = db.relationship("Sentiment", backref="trend", lazy=True)


class Metric(db.Model):
    __tablename__ = "metrics"
    id = db.Column(db.Integer, primary_key=True)
    trend_id = db.Column(db.Integer, db.ForeignKey("trends.trend_id"), nullable=False)
    views = db.Column(db.BigInteger, default=0)
    likes = db.Column(db.BigInteger, default=0)
    shares = db.Column(db.BigInteger, default=0)
    comments_count = db.Column(db.BigInteger, default=0)
    recorded_date = db.Column(db.Date, default=utc_today)

    # Phase 8 — Observation metadata
    captured_at = db.Column(db.DateTime, default=utc_now)
    engagement_rate = db.Column(db.Float, default=0.0)
    source = db.Column(db.String(50), default="youtube_api")


class Sentiment(db.Model):
    __tablename__ = "sentiment"
    id = db.Column(db.Integer, primary_key=True)
    trend_id = db.Column(db.Integer, db.ForeignKey("trends.trend_id"), nullable=False)
    positive_score = db.Column(db.Float, default=0.0)
    negative_score = db.Column(db.Float, default=0.0)
    neutral_score = db.Column(db.Float, default=0.0)
    dominant_sentiment = db.Column(db.String(20))
    sample_comment = db.Column(db.Text)


class Report(db.Model):
    __tablename__ = "reports"
    report_id = db.Column(db.Integer, primary_key=True)
    trend_id = db.Column(db.Integer, db.ForeignKey("trends.trend_id"), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    format = db.Column(db.String(10), default="PDF")
    file_path = db.Column(db.String(255))
    gen_date = db.Column(db.DateTime, default=utc_now)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)   # e.g. SEARCH, EXPORT_PDF, EXPORT_CSV, CHAT
    details = db.Column(db.Text, nullable=True)          # extra context (keyword, platform …)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now)




