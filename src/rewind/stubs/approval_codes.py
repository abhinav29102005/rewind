"""Stub one-time approval codes.

Per-approver, per-request, single-use codes. Deterministic only when
``REWIND_DEV_MODE=1``; the benchmark runner refuses to run with dev mode on.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time


def dev_mode() -> bool:
    return os.environ.get("REWIND_DEV_MODE") == "1"


class StubApprovalCodes:
    def __init__(self, ttl_seconds: int = 900, secret: bytes | None = None) -> None:
        self._ttl = ttl_seconds
        self._secret = secret or (b"dev-secret" if dev_mode() else secrets.token_bytes(32))
        # key: (request_id, approver_id) -> (code_hash, expires_at, used)
        self._codes: dict[tuple[str, str], tuple[str, float, bool]] = {}
        self._lock = threading.Lock()

    def issue(self, request_id: str, approver_id: str) -> str:
        if dev_mode():
            code = "RW-" + hmac.new(
                self._secret, f"{request_id}:{approver_id}".encode(), hashlib.sha256
            ).hexdigest()[:8].upper()
        else:
            code = "RW-" + secrets.token_hex(4).upper()
        with self._lock:
            self._codes[(request_id, approver_id)] = (
                hashlib.sha256(code.encode()).hexdigest(),
                time.time() + self._ttl,
                False,
            )
        return code

    def consume(self, request_id: str, approver_id: str, code: str) -> bool:
        """Constant-time verify and consume; codes are bound to (request, approver)."""
        with self._lock:
            entry = self._codes.get((request_id, approver_id))
            if entry is None:
                return False
            h, exp, used = entry
            ok = hmac.compare_digest(h, hashlib.sha256(code.encode()).hexdigest())
            if not ok or used or time.time() > exp:
                return False
            self._codes[(request_id, approver_id)] = (h, exp, True)
            return True
