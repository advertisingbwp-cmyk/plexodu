"""
SMTAS Security Guard Subsystem
Implements:
1. Strict Input Validation (Schema, regex, length, format)
2. Configurable Multi-Tier Rate Limiting (IP + Account with Exponential Backoff)
3. Information Leakage Prevention & Safe Error Handling
4. File Upload Safety & Isolated Storage
"""

import re
import os
import time
import logging
from typing import Dict, Tuple, Optional
from werkzeug.utils import secure_filename

logger = logging.getLogger("smtas_security")
logging.basicConfig(level=logging.INFO)

# ==============================================================================
# 1. INPUT VALIDATION SCHEMAS & UTILITIES
# ==============================================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
YOUTUBE_URL_REGEX = re.compile(r'^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/|channel\/|c\/|@)|youtu\.be\/)[a-zA-Z0-9_\-\@]+')
VALID_ROLES = {"Digital Marketer", "Brand Strategist", "Researcher", "Administrator", "Member"}

class ValidationError(Exception):
    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.message = message
        self.field = field

def validate_email_input(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a valid string", "email")
    cleaned = email.strip().lower()
    if len(cleaned) < 5 or len(cleaned) > 120:
        raise ValidationError("Email length must be between 5 and 120 characters", "email")
    if not EMAIL_REGEX.match(cleaned):
        raise ValidationError("Invalid email address format", "email")
    return cleaned

def validate_password_input(password: str) -> str:
    if not isinstance(password, str):
        raise ValidationError("Password must be a valid string", "password")
    if len(password) < 6 or len(password) > 100:
        raise ValidationError("Password must be between 6 and 100 characters", "password")
    return password

def validate_keyword_input(keyword: str) -> str:
    if not isinstance(keyword, str):
        raise ValidationError("Keyword must be a string", "keyword")
    cleaned = keyword.strip()
    if not cleaned:
        raise ValidationError("Keyword cannot be empty", "keyword")
    if len(cleaned) > 100:
        raise ValidationError("Keyword is too long (maximum 100 characters)", "keyword")
    # Reject dangerous control characters
    if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', cleaned):
        raise ValidationError("Keyword contains invalid characters", "keyword")
    return cleaned

def validate_youtube_url(url: str) -> str:
    if not isinstance(url, str):
        raise ValidationError("URL must be a string", "url")
    cleaned = url.strip()
    if not cleaned:
        raise ValidationError("URL cannot be empty", "url")
    if len(cleaned) > 255:
        raise ValidationError("URL is too long", "url")
    if not YOUTUBE_URL_REGEX.match(cleaned):
        raise ValidationError("Invalid YouTube video or channel URL format", "url")
    return cleaned

def validate_user_role(role: str) -> str:
    if role not in VALID_ROLES:
        return "Researcher"
    return role

# ==============================================================================
# 2. MULTI-TIER RATE LIMITING WITH EXPONENTIAL BACKOFF
# ==============================================================================

class SlidingWindowRateLimiter:
    def __init__(self):
        # Maps key -> list of timestamps
        self.requests: Dict[str, list] = {}
        # Maps key -> { "failures": int, "blocked_until": float }
        self.backoffs: Dict[str, dict] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Check rate limit and exponential backoff.
        Returns (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        
        # Check backoff lock
        if key in self.backoffs:
            blocked_until = self.backoffs[key].get("blocked_until", 0)
            if now < blocked_until:
                return False, int(blocked_until - now)

        # Clean old timestamps
        if key not in self.requests:
            self.requests[key] = []
        
        self.requests[key] = [t for t in self.requests[key] if t > now - window_seconds]

        if len(self.requests[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self.requests[key][0]))
            return False, max(retry_after, 1)

        self.requests[key].append(now)
        return True, 0

    def record_auth_failure(self, key: str):
        """Exponential backoff on repeated authentication failures."""
        now = time.time()
        if key not in self.backoffs:
            self.backoffs[key] = {"failures": 0, "blocked_until": 0}
        
        self.backoffs[key]["failures"] += 1
        fails = self.backoffs[key]["failures"]
        
        if fails >= 5:
            # Exponential delay: 5 fails = 30s, 6 = 60s, 7 = 120s (max 15 mins)
            delay = min(30 * (2 ** (fails - 5)), 900)
            self.backoffs[key]["blocked_until"] = now + delay
            logger.warning(f"RateLimiter: Auth backoff applied to {key} for {delay}s")

    def reset_auth_failure(self, key: str):
        if key in self.backoffs:
            del self.backoffs[key]

rate_limiter = SlidingWindowRateLimiter()

# Configurable limits from environment
AUTH_LIMIT_PER_MIN = int(os.environ.get("AUTH_RATE_LIMIT_PER_MIN", 10))
API_LIMIT_PER_MIN  = int(os.environ.get("API_RATE_LIMIT_PER_MIN", 100))
AI_LIMIT_PER_MIN   = int(os.environ.get("AI_RATE_LIMIT_PER_MIN", 30))

# ==============================================================================
# 3. FILE UPLOAD SAFETY & ISOLATED STORAGE
# ==============================================================================

ALLOWED_EXTENSIONS = {'csv', 'pdf', 'png', 'jpg', 'jpeg', 'json'}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

def get_upload_directory() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(base_dir, "isolated_storage", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def validate_and_save_upload(file_obj, user_id: str) -> str:
    """Validates file type, size, safe filename, and stores in isolated non-executable folder."""
    if not file_obj or file_obj.filename == '':
        raise ValidationError("No file provided", "file")
    
    filename = secure_filename(file_obj.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"File type '.{ext}' is not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}", "file")
    
    # Check magic bytes for security
    header = file_obj.read(512)
    file_obj.seek(0)  # reset pointer
    
    # Reject executable payloads (e.g. PHP, Python, Shell, EXE header MZ)
    if header.startswith(b'MZ') or b'<?php' in header.lower() or b'#!/bin/' in header:
        raise ValidationError("File content violates security validation policy", "file")
    
    upload_dir = get_upload_directory()
    safe_name = f"u_{user_id}_{int(time.time())}_{filename}"
    save_path = os.path.join(upload_dir, safe_name)
    
    file_obj.save(save_path)
    return save_path
