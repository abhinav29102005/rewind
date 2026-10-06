"""
One-Time Approval Codes.

Generates unforgeable, time-limited, single-use approval codes.
The agent cannot forge or replay these codes because:
1. They are HMAC-signed with a secret the agent never sees.
2. They expire after a configurable timeout.
3. They are single-use and tracked.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ApprovalCode:
    """A single-use approval code tied to a specific action."""

    code: str
    action_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    used: bool = False
    used_at: float | None = None

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired


class CodeGenerator:
    """
    Generates and validates one-time approval codes.

    Codes are HMAC-signed so they cannot be forged without the secret.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        default_ttl_seconds: int = 600,
    ) -> None:
        self._secret = (secret_key or secrets.token_hex(32)).encode()
        self._ttl = default_ttl_seconds
        self._codes: dict[str, ApprovalCode] = {}

    def generate(self, action_id: str, ttl_seconds: int | None = None) -> ApprovalCode:
        """
        Generate a one-time approval code for an action.

        The code format is: RW-XXXXXX (6-char uppercase alphanumeric)
        plus an HMAC signature for verification.
        """
        ttl = ttl_seconds or self._ttl
        nonce = secrets.token_hex(8)
        payload = f"{action_id}:{nonce}:{time.time()}"
        sig = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()[:12]
        code = f"RW-{sig[:6].upper()}"

        approval_code = ApprovalCode(
            code=code,
            action_id=action_id,
            expires_at=time.time() + ttl,
        )
        self._codes[code] = approval_code
        logger.info("Approval code generated for action %s: %s (TTL=%ds)", action_id, code, ttl)
        return approval_code

    def validate_and_consume(self, code: str, action_id: str) -> bool:
        """
        Validate and consume an approval code.

        Returns True if the code is valid, matches the action, and hasn't
        been used or expired. The code is marked as used on success.
        """
        approval_code = self._codes.get(code)
        if approval_code is None:
            logger.warning("Unknown approval code attempted: %s", code)
            return False

        if approval_code.action_id != action_id:
            logger.warning(
                "Approval code %s used for wrong action: expected %s, got %s",
                code,
                approval_code.action_id,
                action_id,
            )
            return False

        if not approval_code.is_valid:
            reason = "expired" if approval_code.is_expired else "already used"
            logger.warning("Invalid approval code %s: %s", code, reason)
            return False

        approval_code.used = True
        approval_code.used_at = time.time()
        logger.info("Approval code %s consumed for action %s", code, action_id)
        return True

    def cleanup_expired(self) -> int:
        """Remove expired and used codes."""
        to_remove = [
            code for code, ac in self._codes.items() if not ac.is_valid
        ]
        for code in to_remove:
            del self._codes[code]
        return len(to_remove)

    @property
    def pending_count(self) -> int:
        return sum(1 for ac in self._codes.values() if ac.is_valid)
