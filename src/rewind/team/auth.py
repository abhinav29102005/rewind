"""Authentication, password hashing, API tokens, and session security."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


class AuthError(Exception):
    """Authentication or token validation error."""


def hash_password(password: str) -> str:
    """Hash password using argon2id."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify password hash using argon2id."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, Exception):
        return False


def generate_api_token() -> tuple[str, str]:
    """Generates (raw_token, token_hash). Store hash only."""
    raw = "rwt_" + secrets.token_hex(24)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, token_hash


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class SessionCookieManager:
    """Manages signed session cookies for web UI."""

    def __init__(self, secret_key: bytes | None = None, max_age_hours: float = 8.0) -> None:
        self.secret = secret_key or secrets.token_bytes(32)
        self.max_age_seconds = int(max_age_hours * 3600)

    def create_cookie_value(self, user_id: str) -> str:
        nonce = secrets.token_hex(16)
        ts = int(time.time())
        data = f"{user_id}:{ts}:{nonce}"
        sig = hmac.new(self.secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{data}:{sig}"

    def verify_cookie_value(self, cookie: str) -> str | None:
        try:
            parts = cookie.split(":")
            if len(parts) != 4:
                return None
            user_id, ts_str, nonce, sig = parts
            ts = int(ts_str)
            if time.time() - ts > self.max_age_seconds:
                return None
            data = f"{user_id}:{ts_str}:{nonce}"
            expected_sig = hmac.new(self.secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            return user_id
        except Exception:
            return None


class LoginRateLimiter:
    """Simple sliding-window rate limiter for login attempts."""

    def __init__(self, max_per_minute: int = 10) -> None:
        self.max_per_minute = max_per_minute
        self._attempts: dict[str, list[float]] = {}

    def is_rate_limited(self, identifier: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        history = [t for t in self._attempts.get(identifier, []) if t > window_start]
        self._attempts[identifier] = history
        return len(history) >= self.max_per_minute

    def record_attempt(self, identifier: str) -> None:
        now = time.time()
        history = self._attempts.setdefault(identifier, [])
        history.append(now)


class CsrfManager:
    """CSRF token generator and validator."""

    def __init__(self, secret: bytes | None = None) -> None:
        self.secret = secret or secrets.token_bytes(32)

    def create_token(self, user_id: str) -> str:
        nonce = secrets.token_hex(16)
        ts = int(time.time())
        data = f"{user_id}:{ts}:{nonce}"
        sig = hmac.new(self.secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{data}:{sig}"

    def verify_token(self, token: str, user_id: str, max_age_seconds: int = 3600) -> bool:
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False
            tok_uid, ts_str, nonce, sig = parts
            if tok_uid != user_id:
                return False
            ts = int(ts_str)
            if time.time() - ts > max_age_seconds:
                return False
            data = f"{tok_uid}:{ts_str}:{nonce}"
            expected_sig = hmac.new(self.secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False
