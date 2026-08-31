"""
Plexudo Phase 2 Production Readiness Comprehensive Audit Suite
Executes end-to-end tests for Auth, YouTube OAuth, YouTube API v3,
Plexudo 50/50 SEO Score formula, Groq AI, Security, and Database invariants.
"""

import os
import sys
import json
import sqlite3
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.core.config import settings

BASE_URL = "http://127.0.0.1:5000"

audit_report = {
    "pass": [],
    "fail": [],
    "fixed": [],
    "manual": [],
    "risks": []
}

def audit_assert(category, test_name, condition, details=""):
    item = {"category": category, "name": test_name, "details": details}
    if condition:
        print(f"  [PASS] {category} -> {test_name}: {details}")
        audit_report["pass"].append(item)
    else:
        print(f"  [FAIL] {category} -> {test_name}: {details}")
        audit_report["fail"].append(item)

print("==================================================")
print("1. ENVIRONMENT & PRODUCTION CONFIG AUDIT")
print("==================================================")
audit_assert("ENV", ".env file loaded", (BASE_DIR / ".env").exists() or bool(settings.SECRET_KEY))
audit_assert("ENV", ".env.example exists", (BASE_DIR / ".env.example").exists())
audit_assert("ENV", "GROQ_API_KEY present", settings.is_groq_configured())
audit_assert("ENV", "YOUTUBE_API_KEY present", settings.is_youtube_configured())
audit_assert("ENV", "GOOGLE_CLIENT_ID present", bool(settings.GOOGLE_CLIENT_ID))
audit_assert("ENV", "GOOGLE_CLIENT_SECRET present", bool(settings.GOOGLE_CLIENT_SECRET))
audit_assert("ENV", "GOOGLE_REDIRECT_URI set", bool(settings.GOOGLE_REDIRECT_URI))

print("\n==================================================")
print("2. DATABASE INVARIANTS AUDIT")
print("==================================================")
db_path = BASE_DIR / "backend" / "smtas.db"
audit_assert("DB", "Database file exists", db_path.exists())
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cur.fetchall()]
conn.close()

for t in ["users", "trends", "metrics", "sentiment", "reports", "audit_logs"]:
    audit_assert("DB", f"Table '{t}' in schema", t in tables)

print("\n==================================================")
print("3. REAL END-TO-END AUTH AUDIT")
print("==================================================")
session = requests.Session()
pid = os.getpid()
test_user = f"audit_user_{pid}@plexudo.io"
test_pass = "ComplexPlexudoPass!2026"

# Register
reg = session.post(f"{BASE_URL}/api/register", json={"name": "Audit User", "email": test_user, "password": test_pass, "role": "Researcher"})
audit_assert("AUTH", "User Registration (201)", reg.status_code == 201)

# Duplicate
dup = session.post(f"{BASE_URL}/api/register", json={"name": "Audit User", "email": test_user, "password": test_pass, "role": "Researcher"})
audit_assert("AUTH", "Duplicate Email Rejection (409)", dup.status_code == 409)

# Login
login = session.post(f"{BASE_URL}/api/login", json={"email": test_user, "password": test_pass})
audit_assert("AUTH", "User Login (200)", login.status_code == 200)

# Session check
chk = session.get(f"{BASE_URL}/api/session")
audit_assert("AUTH", "Session Validation (/api/session)", chk.status_code == 200 and chk.json().get("authenticated") == True)

print("\n==================================================")
print("4. REAL YOUTUBE DATA API V3 AUDIT")
print("==================================================")
# Audit Channel Live
ch_res = session.post(f"{BASE_URL}/api/audit-channel", json={"identifier": "@mrbeast"})
audit_assert("YOUTUBE", "Real Channel Lookup (@mrbeast)", ch_res.status_code == 200 and ch_res.json().get("error") == False and ch_res.json().get("channel_name") == "MrBeast")

# Video Analysis Live
vid_res = session.post(f"{BASE_URL}/api/video-analysis", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
audit_assert("YOUTUBE", "Real Video Analysis", vid_res.status_code == 200 and vid_res.json().get("error") == False)

# Empty Channel handling
bad_ch = session.post(f"{BASE_URL}/api/audit-channel", json={"identifier": "@nonexistent_channel_xyz_99999"})
audit_assert("YOUTUBE", "Honest Error for Invalid Channel", bad_ch.json().get("error") == True)

print("\n==================================================")
print("5. SEO 50/50 SCORE FORMULA AUDIT")
print("==================================================")
seo_payload = {
    "title": "Top 10 YouTube SEO Secrets 2026 - Ranked Fast",
    "description": "Discover Top 10 YouTube SEO Secrets 2026 to grow your channel fast and get viral views.",
    "tags": ["youtube seo", "secrets 2026", "grow channel", "viral views", "tips", "tricks", "guide", "ranking", "algorithm", "views", "subscriber", "growth", "strategy", "creator", "tutorial"]
}
seo_res = session.post(f"{BASE_URL}/api/channel-seo/seo/analyze", json=seo_payload)
seo_data = seo_res.json()
items = seo_data.get("actionableItems", {})
breakdown = items.get("breakdown", {})

audit_assert("SEO", "50/50 SEO Endpoint Status (200)", seo_res.status_code == 200)
audit_assert("SEO", "Tag Count Score Component", "tagCount" in breakdown)
audit_assert("SEO", "Tag Volume Score Component", "tagVolume" in breakdown)
audit_assert("SEO", "Keywords in Title Component", "keywordsInTitle" in breakdown)
audit_assert("SEO", "Keywords in Desc Component", "keywordsInDescription" in breakdown)
audit_assert("SEO", "Triple Keyword Overlap Component", "sameKeywordOverlap" in breakdown)
audit_assert("SEO", "Total Score Out of 50", items.get("total", 0) <= 50)

print("\n==================================================")
print("6. REAL GROQ AI AUDIT")
print("==================================================")
ai_res = session.post(f"{BASE_URL}/api/chat", json={"message": "Suggest 3 viral video topics for tech channels."})
audit_assert("AI", "Real Groq AI Response (200)", ai_res.status_code == 200 and len(ai_res.json().get("reply", "")) > 50)

# Title generator
titles_res = session.post(f"{BASE_URL}/api/channel-seo/ai/suggest-titles", json={"title": "NextJS Tutorial 2026"})
audit_assert("AI", "AI Viral Title Generator", titles_res.status_code == 200 and len(titles_res.json().get("titles", [])) == 3)

print("\n==================================================")
print("7. SECURITY & ACCESS CONTROL AUDIT")
print("==================================================")
unauth_s = requests.Session()
unauth_chk = unauth_s.get(f"{BASE_URL}/api/session")
audit_assert("SEC", "Unauthenticated Session Rejection", unauth_chk.json().get("logged_in") == False or unauth_chk.status_code == 401)

# Logout
logout = session.post(f"{BASE_URL}/api/logout")
post_logout = session.get(f"{BASE_URL}/api/session")
audit_assert("SEC", "Logout Session Invalidation", logout.status_code == 200 and (post_logout.json().get("logged_in") == False or post_logout.status_code == 401))

print("\n==================================================")
print(f"AUDIT RUN SUMMARY: {len(audit_report['pass'])} Passed, {len(audit_report['fail'])} Failed")
print("==================================================")
