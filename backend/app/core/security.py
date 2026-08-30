import secrets
import hashlib
import hmac as _hmac
import base64
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from functools import lru_cache

@lru_cache()
def _get_hasher() -> PasswordHasher:
    from app.core.config import get_settings
    if get_settings().ENVIRONMENT == "test":
        # Fast profile for tests
        return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    # OWASP baseline for production
    return PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    return _get_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _get_hasher().verify(password_hash, password)
    except Exception:
        return False


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe random token (32 bytes)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a token. Only this hash is stored, never the raw token."""
    return hashlib.sha256(token.encode()).hexdigest()


def _get_fernet_key() -> bytes:
    """
    Derive a valid 32-byte URL-safe base64 Fernet key from TOKEN_ENCRYPTION_KEY env var.
    Uses SHA-256 to ensure any arbitrary secret key string is deterministically mapped
    to exactly 32 raw bytes and base64-urlsafe-encoded.
    """
    from app.core.config import get_settings
    raw = get_settings().TOKEN_ENCRYPTION_KEY.encode("utf-8")
    try:
        if len(raw) == 44 and len(base64.urlsafe_b64decode(raw)) == 32:
            return raw
    except Exception:
        pass
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_bytes(data: bytes) -> bytes:
    return Fernet(_get_fernet_key()).encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return Fernet(_get_fernet_key()).decrypt(data)


def generate_csrf_token(session_id: str) -> str:
    """HMAC-SHA256 of the session ID, keyed with CSRF_SECRET."""
    from app.core.config import get_settings
    key = get_settings().CSRF_SECRET.encode()
    msg = str(session_id).encode()
    return _hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_csrf_token(token: str, session_id: str) -> bool:
    expected = generate_csrf_token(session_id)
    return _hmac.compare_digest(token, expected)
