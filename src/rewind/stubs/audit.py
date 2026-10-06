"""In-memory append-only audit log with a working SHA-256 hash chain."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from typing import Any

GENESIS = "0" * 64


def _entry_hash(prev: str, body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + canonical).encode("utf-8")).hexdigest()


class StubAuditLog:
    """Implements :class:`rewind.contracts.AuditLog` in memory."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def append(
        self,
        event_type: str,
        data: dict[str, Any],
        actor: str | None = None,
        session_id: str | None = None,
    ) -> str:
        with self._lock:
            prev = self._entries[-1]["hash"] if self._entries else GENESIS
            body = {
                "seq": len(self._entries) + 1,
                "event_type": event_type,
                "data": json.loads(json.dumps(data, default=str)),
                "actor": actor,
                "session_id": session_id,
                "ts": datetime.now(UTC).isoformat(),
            }
            h = _entry_hash(prev, body)
            self._entries.append({**body, "prev": prev, "hash": h})
            return h

    def verify(self) -> tuple[bool, str | None]:
        with self._lock:
            prev = GENESIS
            for e in self._entries:
                body = {k: e[k] for k in ("seq", "event_type", "data", "actor", "session_id", "ts")}
                if e["prev"] != prev or _entry_hash(prev, body) != e["hash"]:
                    return False, str(e["seq"])
                prev = e["hash"]
            return True, None

    def query(self, **filters: Any) -> list[dict[str, Any]]:
        with self._lock:
            out = []
            for e in self._entries:
                if all(e.get(k) == v for k, v in filters.items()):
                    out.append(dict(e))
            return out

    # Test helper: simulate tampering.
    def _tamper(self, index: int, data: dict[str, Any]) -> None:
        self._entries[index]["data"] = data
