"""
Scoped Capability Tokens.

Issues short-lived, scoped tokens to agents. Tokens carry only the
permissions needed for the current task and expire after use or timeout.
The agent receives these tokens instead of raw production credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TokenScope(Enum):
    """Scope of capabilities a token can grant."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class CapabilityToken:
    """A short-lived, scoped capability token."""

    token_id: str
    credential_name: str  # Which vault credential this token is scoped to
    scopes: list[TokenScope]
    expires_at: float
    max_uses: int  # 0 = unlimited
    created_at: float = field(default_factory=time.time)
    use_count: int = 0
    revoked: bool = False

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        return self.max_uses > 0 and self.use_count >= self.max_uses

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired and not self.is_exhausted

    def has_scope(self, scope: TokenScope) -> bool:
        return scope in self.scopes

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "credential_name": self.credential_name,
            "scopes": [s.value for s in self.scopes],
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "is_valid": self.is_valid,
        }


class TokenManager:
    """
    Manages capability tokens: issue, validate, use, revoke.

    Uses HMAC-SHA256 for token signing to prevent forgery.
    """

    def __init__(self, secret_key: str | None = None) -> None:
        self._secret = (secret_key or secrets.token_hex(32)).encode()
        self._tokens: dict[str, CapabilityToken] = {}

    def issue(
        self,
        credential_name: str,
        scopes: list[TokenScope],
        ttl_seconds: int = 300,
        max_uses: int = 1,
    ) -> CapabilityToken:
        """
        Issue a new capability token.

        Args:
            credential_name: Name of the credential in the vault
            scopes: List of permitted scopes
            ttl_seconds: Time-to-live in seconds (default 5 minutes)
            max_uses: Maximum number of uses (default 1, single-use)
        """
        token_id = self._generate_token_id(credential_name)
        token = CapabilityToken(
            token_id=token_id,
            credential_name=credential_name,
            scopes=scopes,
            expires_at=time.time() + ttl_seconds,
            max_uses=max_uses,
        )
        self._tokens[token_id] = token
        logger.info(
            "Token issued: %s (cred=%s, scopes=%s, ttl=%ds, max_uses=%d)",
            token_id[:16],
            credential_name,
            [s.value for s in scopes],
            ttl_seconds,
            max_uses,
        )
        return token

    def validate(self, token_id: str, required_scope: TokenScope | None = None) -> CapabilityToken:
        """
        Validate a token and optionally check scope.
        Raises ValueError if invalid.
        """
        token = self._tokens.get(token_id)
        if token is None:
            raise ValueError(f"Unknown token: {token_id[:16]}...")

        if token.revoked:
            raise ValueError(f"Token {token_id[:16]}... has been revoked")

        if token.is_expired:
            raise ValueError(f"Token {token_id[:16]}... has expired")

        if token.is_exhausted:
            raise ValueError(f"Token {token_id[:16]}... has exhausted its uses")

        if required_scope and not token.has_scope(required_scope):
            raise ValueError(
                f"Token {token_id[:16]}... lacks required scope: {required_scope.value}"
            )

        return token

    def use(self, token_id: str, required_scope: TokenScope | None = None) -> CapabilityToken:
        """Validate and consume one use of the token."""
        token = self.validate(token_id, required_scope)
        token.use_count += 1
        logger.debug("Token used: %s (use %d/%d)", token_id[:16], token.use_count, token.max_uses)
        return token

    def revoke(self, token_id: str) -> None:
        """Immediately revoke a token."""
        token = self._tokens.get(token_id)
        if token:
            token.revoked = True
            logger.info("Token revoked: %s", token_id[:16])

    def revoke_all(self, credential_name: str | None = None) -> int:
        """Revoke all tokens, or all tokens for a specific credential."""
        count = 0
        for token in self._tokens.values():
            if (credential_name is None or token.credential_name == credential_name) and not token.revoked:
                    token.revoked = True
                    count += 1
        logger.info("Revoked %d tokens (filter=%s)", count, credential_name or "all")
        return count

    def cleanup_expired(self) -> int:
        """Remove expired and fully-used tokens from memory."""
        to_remove = [
            tid for tid, t in self._tokens.items() if not t.is_valid
        ]
        for tid in to_remove:
            del self._tokens[tid]
        return len(to_remove)

    def _generate_token_id(self, credential_name: str) -> str:
        """Generate a signed, unique token ID."""
        nonce = secrets.token_hex(16)
        payload = f"{credential_name}:{nonce}:{time.time()}"
        signature = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return f"rwt_{nonce}_{signature[:16]}"

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tokens.values() if t.is_valid)
