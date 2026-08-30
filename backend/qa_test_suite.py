"""
SMTAS / Plexudo - End-to-End QA Test Suite
Tests Environment, Database, Authentication, Public Routes, Tools, Security, and API Endpoints.
"""

import sys
import os
import requests
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.core.config import settings

BASE_URL = "http://127.0.0.1:5000"

results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "bugs": []
}

def log_test(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name}: {status} {details}")
    else:
        results["failed"] += 1
        print(f"  [FAIL] {name}: {status} {details}")
        results["bugs"].append(f"{name}: {details}")

print("==================================================")
print("1. ENVIRONMENT & CONFIGURATION QA")
print("==================================================")
log_test("Config File Loaded", settings.model_config.get("env_file") is not None, f"({settings.model_config.get('env_file')})")
log_test("GROQ_API_KEY Configured", settings.is_groq_configured())
log_test("GOOGLE_CLIENT_ID Configured", bool(settings.GOOGLE_CLIENT_ID))
log_test("GOOGLE_CLIENT_SECRET Configured", bool(settings.GOOGLE_CLIENT_SECRET))
log_test("YOUTUBE_API_KEY Configured", settings.is_youtube_configured())
log_test("GROQ_MODEL Configured", bool(settings.GROQ_MODEL), f"({settings.GROQ_MODEL})")
log_test("GOOGLE_REDIRECT_URI Configured", bool(settings.GOOGLE_REDIRECT_URI))

print("\n==================================================")
print("2. DATABASE VERIFICATION QA")
print("==================================================")
db_path = BASE_DIR / "backend" / "smtas.db"
if db_path.exists():
    log_test("SQLite Database File Exists", True, f"({db_path})")
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        expected_tables = ["users", "trends", "metrics", "sentiment", "reports", "audit_logs"]
        for t in expected_tables:
            log_test(f"Table '{t}' Exists", t in tables)
    except Exception as e:
        log_test("Database Query", False, str(e))
else:
    log_test("SQLite Database File Exists", False)

print("\n==================================================")
print("3. PUBLIC WEBSITE & ASSET ROUTES QA")
print("==================================================")
public_routes = [
    ("/", 200, "Home / Landing Page"),
    ("/dashboard.html", 200, "Dashboard App"),
    ("/robots.txt", 200, "robots.txt"),
    ("/sitemap.xml", 200, "sitemap.xml"),
    ("/favicon.svg", 200, "favicon.svg"),
    ("/css/style.css", 200, "Main CSS Bundle"),
    ("/js/login.js", 200, "Auth JS Bundle"),
    ("/js/dashboard.js", 200, "Dashboard JS Bundle"),
]

for route, expected_code, desc in public_routes:
    try:
        res = requests.get(f"{BASE_URL}{route}", timeout=5)
        passed = (res.status_code == expected_code)
        log_test(f"Route {route} ({desc})", passed, f"Status: {res.status_code}")
    except Exception as e:
        log_test(f"Route {route} ({desc})", False, f"Exception: {type(e).__name__}")

print("\n==================================================")
print("4. AUTHENTICATION FLOW REAL TEST QA")
print("==================================================")
session = requests.Session()
test_email = f"qa_test_user_{os.getpid()}@example.com"
test_password = "SecurePassword123!"
test_name = "QA Automation User"

# Test 1: Register New User
try:
    reg_res = session.post(
        f"{BASE_URL}/api/register",
        json={"name": test_name, "email": test_email, "password": test_password, "role": "Researcher"},
        timeout=5
    )
    reg_passed = (reg_res.status_code == 201)
    log_test("User Registration Flow", reg_passed, f"Status: {reg_res.status_code}")
except Exception as e:
    log_test("User Registration Flow", False, str(e))

# Test 2: Duplicate Email Rejection
try:
    dup_res = session.post(
        f"{BASE_URL}/api/register",
        json={"name": test_name, "email": test_email, "password": test_password, "role": "Researcher"},
        timeout=5
    )
    dup_passed = (dup_res.status_code == 409)
    log_test("Duplicate Email Rejection", dup_passed, f"Status: {dup_res.status_code}")
except Exception as e:
    log_test("Duplicate Email Rejection", False, str(e))

# Test 3: Login with Correct Password
try:
    login_res = session.post(
        f"{BASE_URL}/api/login",
        json={"email": test_email, "password": test_password},
        timeout=5
    )
    login_passed = (login_res.status_code == 200)
    log_test("User Login Flow", login_passed, f"Status: {login_res.status_code}")
except Exception as e:
    log_test("User Login Flow", False, str(e))

# Test 4: Protected Session Endpoint
try:
    session_res = session.get(f"{BASE_URL}/api/session", timeout=5)
    session_passed = (session_res.status_code == 200 and session_res.json().get("user", {}).get("email") == test_email)
    log_test("Protected /api/session Validation", session_passed, f"Status: {session_res.status_code}")
except Exception as e:
    log_test("Protected /api/session Validation", False, str(e))

print("\n==================================================")
print("5. CORE ANALYTICS TOOLS & API ENDPOINTS QA")
print("==================================================")

# Tool 1: YouTube Trend Search
try:
    search_res = session.post(f"{BASE_URL}/api/search", json={"keyword": "FreeFire"}, timeout=15)
    search_data = search_res.json()
    search_passed = (search_res.status_code == 200 and "trend_id" in search_data)
    log_test("Tool: Trend Search (/api/search)", search_passed, f"Status: {search_res.status_code}")
except Exception as e:
    log_test("Tool: Trend Search (/api/search)", False, str(e))

# Tool 2: Video Analysis
try:
    vid_res = session.post(
        f"{BASE_URL}/api/video-analysis",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        timeout=15
    )
    vid_data = vid_res.json()
    vid_passed = (vid_res.status_code == 200 and "analysis" in vid_data)
    log_test("Tool: Video Analysis (/api/video-analysis)", vid_passed, f"Status: {vid_res.status_code}")
except Exception as e:
    log_test("Tool: Video Analysis (/api/video-analysis)", False, str(e))

# Tool 3: Competitor Channel Audit
try:
    audit_res = session.post(
        f"{BASE_URL}/api/audit-channel",
        json={"identifier": "@mrbeast"},
        timeout=15
    )
    audit_data = audit_res.json()
    audit_passed = (audit_res.status_code == 200 and "channel" in audit_data)
    log_test("Tool: Competitor Channel Audit (/api/audit-channel)", audit_passed, f"Status: {audit_res.status_code}")
except Exception as e:
    log_test("Tool: Competitor Channel Audit (/api/audit-channel)", False, str(e))

# Tool 4: SEO 50/50 Scoring Engine
try:
    seo_res = session.post(
        f"{BASE_URL}/api/channel-seo/seo/analyze",
        json={
            "title": "74 Kills FAMAS + MP40 Pro Gameplay | FreeFire",
            "description": "Full pro FreeFire gameplay guide with top headshot tips and tricks.",
            "tags": ["freefire", "gameplay", "famas", "mp40", "headshot"]
        },
        timeout=10
    )
    seo_passed = (seo_res.status_code == 200 and "actionableItems" in seo_res.json())
    score_total = seo_res.json().get("actionableItems", {}).get("total", 0) if seo_passed else 0
    log_test("Tool: 50/50 SEO Scoring (/api/channel-seo/seo/analyze)", seo_passed, f"Score: {score_total}/50")
except Exception as e:
    log_test("Tool: 50/50 SEO Scoring (/api/channel-seo/seo/analyze)", False, str(e))

# Tool 5: AI Title Generator
try:
    titles_res = session.post(
        f"{BASE_URL}/api/channel-seo/ai/suggest-titles",
        json={
            "title": "FreeFire Secret Tricks",
            "description": "Best pro settings",
            "tags": ["freefire", "tricks"]
        },
        timeout=15
    )
    titles_passed = (titles_res.status_code == 200 and "titles" in titles_res.json())
    log_test("Tool: AI Title Generator (/api/channel-seo/ai/suggest-titles)", titles_passed, f"Status: {titles_res.status_code}")
except Exception as e:
    log_test("Tool: AI Title Generator (/api/channel-seo/ai/suggest-titles)", False, str(e))

# Tool 6: History & Logs
try:
    hist_res = session.get(f"{BASE_URL}/api/trends", timeout=5)
    hist_passed = (hist_res.status_code == 200 and "trends" in hist_res.json())
    log_test("Search Trends History API (/api/trends)", hist_passed, f"Status: {hist_res.status_code}")
except Exception as e:
    log_test("Search Trends History API (/api/trends)", False, str(e))

try:
    audit_log_res = session.get(f"{BASE_URL}/api/audit-log", timeout=5)
    audit_log_passed = (audit_log_res.status_code == 200 and "logs" in audit_log_res.json())
    log_test("Audit Logs API (/api/audit-log)", audit_log_passed, f"Status: {audit_log_res.status_code}")
except Exception as e:
    log_test("Audit Logs API (/api/audit-log)", False, str(e))

print("\n==================================================")
print("6. SECURITY & UNAUTHENTICATED ACCESS QA")
print("==================================================")
unauth_session = requests.Session()
try:
    unauth_res = unauth_session.get(f"{BASE_URL}/api/session", timeout=5)
    unauth_passed = (unauth_res.status_code == 401 or unauth_res.json().get("logged_in") == False)
    log_test("Unauthenticated /api/session Rejection (401/False)", unauth_passed, f"Status: {unauth_res.status_code}")
except Exception as e:
    log_test("Unauthenticated /api/session Rejection (401/False)", False, str(e))

try:
    logout_res = session.post(f"{BASE_URL}/api/logout", timeout=5)
    post_logout_session = session.get(f"{BASE_URL}/api/session", timeout=5)
    logout_passed = (logout_res.status_code == 200 and (post_logout_session.status_code == 401 or post_logout_session.json().get("logged_in") == False))
    log_test("User Logout & Session Revocation Flow", logout_passed, f"Status: {logout_res.status_code}")
except Exception as e:
    log_test("User Logout & Session Revocation Flow", False, str(e))

print("\n==================================================")
print(f"QA TEST RUN COMPLETE: {results['passed']} Passed, {results['failed']} Failed")
print("==================================================")
