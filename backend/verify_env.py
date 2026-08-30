import sys
import os
from pathlib import Path
import requests

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.config import settings

print("=== 1. CONFIG & ENV VERIFICATION ===")
print(f"Config env file: {settings.model_config.get('env_file')}")
print(f"GROQ_API_KEY: {'FOUND' if settings.is_groq_configured() else 'MISSING'}")
print(f"GOOGLE_CLIENT_ID: {'FOUND' if bool(settings.GOOGLE_CLIENT_ID) else 'MISSING'}")
print(f"GOOGLE_CLIENT_SECRET: {'FOUND' if bool(settings.GOOGLE_CLIENT_SECRET) else 'MISSING'}")
print(f"YOUTUBE_API_KEY: {'FOUND' if settings.is_youtube_configured() else 'MISSING'}")
print(f"GROQ_MODEL: {settings.GROQ_MODEL}")
print(f"GOOGLE_REDIRECT_URI: {'FOUND' if bool(settings.GOOGLE_REDIRECT_URI) else 'MISSING'}")

print("\n=== 2. REAL YOUTUBE DATA API V3 INTEGRATION TEST ===")
try:
    yt_res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "q": "technology", "type": "video", "maxResults": 1, "key": settings.YOUTUBE_API_KEY.strip()},
        timeout=10
    )
    if yt_res.status_code == 200:
        items = yt_res.json().get("items", [])
        print(f"YouTube API Connectivity: PASS (Status 200, received {len(items)} item(s))")
    else:
        err_msg = yt_res.json().get("error", {}).get("message", "Unknown error")
        print(f"YouTube API Connectivity: FAIL (Status {yt_res.status_code}: {err_msg})")
except Exception as e:
    print(f"YouTube API Connectivity: ERROR ({type(e).__name__})")

print("\n=== 3. REAL GROQ AI API INTEGRATION TEST ===")
try:
    groq_res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}", "Content-Type": "application/json"},
        json={"model": settings.GROQ_MODEL, "messages": [{"role": "user", "content": "Ping"}], "max_tokens": 10},
        timeout=10
    )
    if groq_res.status_code == 200:
        reply = groq_res.json()["choices"][0]["message"]["content"].strip()
        print(f"Groq API Connectivity: PASS (Status 200, model response received)")
    else:
        err_msg = groq_res.json().get("error", {}).get("message", "Unknown error")
        print(f"Groq API Connectivity: FAIL (Status {groq_res.status_code}: {err_msg})")
except Exception as e:
    print(f"Groq API Connectivity: ERROR ({type(e).__name__})")

print("\n=== 4. GOOGLE OAUTH CONFIGURATION TEST ===")
if settings.is_google_oauth_configured():
    print("Google OAuth Configuration: PASS (Client ID & Client Secret LOADED)")
else:
    print("Google OAuth Configuration: FAIL (Missing Client ID or Secret)")
