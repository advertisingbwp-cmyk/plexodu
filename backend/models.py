from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="Creator")
    login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    email_verified = db.Column(db.Boolean, default=True)
    credits = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Trend(db.Model):
    __tablename__ = "trends"
    trend_id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(20), nullable=False)  # YouTube / TikTok
    total_views = db.Column(db.BigInteger, default=0)
    growth_rate = db.Column(db.Float, default=0.0)
    virality_score = db.Column(db.Float, default=0.0)
    peak_date = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
    recorded_date = db.Column(db.Date, default=datetime.utcnow)


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
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    format = db.Column(db.String(10), default="PDF")
    file_path = db.Column(db.String(255))
    gen_date = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)   # e.g. LOGIN, SEARCH, EXPORT_PDF, EXPORT_CSV, CHAT
    details = db.Column(db.Text, nullable=True)          # extra context (keyword, platform …)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class RewardTransaction(db.Model):
    __tablename__ = "reward_transactions"
    id = db.Column(db.Integer, primary_key=True)
    reward_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False)  # "welcome_bonus", "rewarded_ad_ssv", "admin_grant"
    session_id = db.Column(db.String(128), nullable=True)
    reward_type = db.Column(db.String(50), nullable=False)  # "WELCOME_CREDIT", "REWARDED_AD", "SPONSOR_PASS"
    credit_amount = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="PENDING")  # PENDING, COMPLETED, REJECTED, EXPIRED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    verification_data = db.Column(db.Text, nullable=True)

