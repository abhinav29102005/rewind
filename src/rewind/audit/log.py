"""
Append-only tamper-evident audit log.

Stores every event (action received, classification, approval, execution,
rollback) in a SQLite database with a SHA-256 hash chain for tamper detection.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from . import chain

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of audit events."""

    ACTION_RECEIVED = "action_received"
    ACTION_CLASSIFIED = "action_classified"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    SNAPSHOT_CREATED = "snapshot_created"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CHAIN_VERIFIED = "chain_verified"
    CHAIN_BROKEN = "chain_broken"


@dataclass
class AuditEvent:
    """A single audit log event."""

    event_type: EventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: int | None = None
    chain_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }


_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT    NOT NULL,
    timestamp   REAL    NOT NULL,
    data_json   TEXT    NOT NULL,
    data_hash   TEXT    NOT NULL,
    prev_hash   TEXT    NOT NULL,
    chain_hash  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
"""


class AuditLog:
    """
    Append-only, tamper-evident audit log backed by SQLite.

    Every entry is chained via SHA-256 hashes. The chain can be verified
    at any time to detect tampering.
    """

    def __init__(self, db_path: Path | str = "rewind_audit.db") -> None:
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Load the chain hash of the last entry, or genesis if empty."""
        row = self._conn.execute(
            "SELECT chain_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else chain.GENESIS_HASH

    def log(self, event: AuditEvent) -> AuditEvent:
        """Append an event to the audit log. Returns the event with id and chain_hash set."""
        data_dict = event.to_dict()
        entry = chain.create_entry(
            index=self._get_next_index(),
            data=data_dict,
            prev_hash=self._last_hash,
        )

        self._conn.execute(
            """INSERT INTO audit_log (event_type, timestamp, data_json, data_hash, prev_hash, chain_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event.event_type.value,
                event.timestamp,
                json.dumps(data_dict, default=str),
                entry.data_hash,
                entry.prev_hash,
                entry.chain_hash,
            ),
        )
        self._conn.commit()

        event.event_id = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        event.chain_hash = entry.chain_hash
        self._last_hash = entry.chain_hash

        logger.debug("Audit event logged: [%s] %s", event.event_type.value, entry.chain_hash[:16])
        return event

    def _get_next_index(self) -> int:
        row = self._conn.execute("SELECT MAX(id) FROM audit_log").fetchone()
        return (row[0] or 0) + 1

    def verify_chain(self) -> tuple[bool, int]:
        """
        Verify the entire hash chain.
        Returns (is_valid, last_verified_index).
        """
        rows = self._conn.execute(
            "SELECT id, event_type, timestamp, data_json, data_hash, prev_hash, chain_hash "
            "FROM audit_log ORDER BY id"
        ).fetchall()

        if not rows:
            return True, 0

        prev_hash = chain.GENESIS_HASH
        last_verified = 0

        for row in rows:
            entry_id, event_type, timestamp, data_json, data_hash, expected_prev, chain_hash = row
            data_dict = json.loads(data_json)

            entry = chain.ChainEntry(
                index=entry_id,
                data_hash=data_hash,
                prev_hash=expected_prev,
                chain_hash=chain_hash,
            )

            if not chain.verify_entry(entry, data_dict, prev_hash):
                logger.error("Chain verification FAILED at entry %d", entry_id)
                return False, last_verified

            prev_hash = chain_hash
            last_verified = entry_id

        logger.info("Chain verification passed: %d entries verified", last_verified)
        return True, last_verified

    def get_events(
        self,
        event_type: EventType | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with optional filters."""
        query = "SELECT id, event_type, timestamp, data_json, chain_hash FROM audit_log WHERE 1=1"
        params: list[Any] = []

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type.value)
        if since is not None:
            query += " AND timestamp >= ?"
            params.append(since)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        events = []
        for row in rows:
            evt = AuditEvent(
                event_type=EventType(row[1]),
                data=json.loads(row[3]),
                timestamp=row[2],
                event_id=row[0],
                chain_hash=row[4],
            )
            events.append(evt)
        return events

    @property
    def count(self) -> int:
        """Total number of entries in the audit log."""
        row = self._conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
