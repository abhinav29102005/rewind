"""Stub token broker: tracks issued tokens per session and supports revocation."""

from __future__ import annotations

import secrets
import threading


class StubTokenBroker:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str | None, set[str], bool]] = {}
        self._lock = threading.Lock()

    def issue(self, session_id: str | None, scopes: set[str]) -> str:
        tok = "rwt_" + secrets.token_hex(16)
        with self._lock:
            self._tokens[tok] = (session_id, set(scopes), False)
        return tok

    def is_valid(self, token: str, scope: str | None = None) -> bool:
        with self._lock:
            entry = self._tokens.get(token)
        if entry is None:
            return False
        _, scopes, revoked = entry
        if revoked:
            return False
        return scope is None or scope in scopes

    def revoke_session(self, session_id: str) -> int:
        n = 0
        with self._lock:
            for tok, (sid, scopes, revoked) in list(self._tokens.items()):
                if sid == session_id and not revoked:
                    self._tokens[tok] = (sid, scopes, True)
                    n += 1
        return n
