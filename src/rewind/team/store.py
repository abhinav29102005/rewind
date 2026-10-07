"""SQLite storage and schema migrations for team features."""

from __future__ import annotations

import contextlib
import json

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalVote,
    NotificationLogEntry,
    Role,
    Session,
    User,
    VoteDecision,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  role TEXT NOT NULL CHECK (role IN ('admin','approver','viewer')),
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL,
  label TEXT,
  expires_at TEXT,
  revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  started_by TEXT NOT NULL REFERENCES users(id),
  policy_profile TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  end_reason TEXT
);

CREATE TABLE IF NOT EXISTS approval_requests (
  id TEXT PRIMARY KEY,
  action_id TEXT NOT NULL,
  session_id TEXT REFERENCES sessions(id),
  action_hash TEXT NOT NULL,
  mode TEXT NOT NULL,
  required INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  decided_at TEXT,
  action_payload TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS approval_votes (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL REFERENCES approval_requests(id),
  approver_id TEXT NOT NULL REFERENCES users(id),
  decision TEXT NOT NULL CHECK (decision IN ('approve','deny')),
  action_hash TEXT NOT NULL,
  voted_at TEXT NOT NULL,
  UNIQUE (request_id, approver_id)
);

CREATE TABLE IF NOT EXISTS notification_log (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  channel TEXT NOT NULL,
  request_id TEXT,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_approval_requests_session ON approval_requests(session_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created ON approval_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_created ON notification_log(created_at);
"""


class TeamStore:
    """Manages SQLite storage for team data in WAL mode."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            with contextlib.suppress(sqlite3.OperationalError):
                self._conn.execute("ALTER TABLE approval_requests ADD COLUMN action_payload TEXT DEFAULT '{}'")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Users ---
    def create_user(self, user_id: str, username: str, password_hash: str | None, role: Role) -> User:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO users (id, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (user_id, username, password_hash, role.value, now),
            )
            self._conn.commit()
        return User(id=user_id, username=username, role=role, active=True, created_at=datetime.fromisoformat(now))

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return User(
                id=row["id"],
                username=row["username"],
                role=Role(row["role"]),
                active=bool(row["active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def get_user_by_username(self, username: str) -> tuple[User, str | None] | None:
        """Returns (User, password_hash) or None."""
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if not row:
                return None
            user = User(
                id=row["id"],
                username=row["username"],
                role=Role(row["role"]),
                active=bool(row["active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            return user, row["password_hash"]

    def list_users(self) -> list[User]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
            return [
                User(
                    id=r["id"],
                    username=r["username"],
                    role=Role(r["role"]),
                    active=bool(r["active"]),
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]

    # --- API Tokens ---
    def create_api_token(self, token_id: str, user_id: str, token_hash: str, label: str | None = None, expires_at: datetime | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO api_tokens (id, user_id, token_hash, label, expires_at) VALUES (?, ?, ?, ?, ?)",
                (token_id, user_id, token_hash, label, expires_at.isoformat() if expires_at else None),
            )
            self._conn.commit()

    def get_user_by_token_hash(self, token_hash: str) -> User | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT u.* FROM users u
                   JOIN api_tokens t ON u.id = t.user_id
                   WHERE t.token_hash = ? AND t.revoked_at IS NULL
                   AND (t.expires_at IS NULL OR t.expires_at > ?)
                   AND u.active = 1""",
                (token_hash, datetime.now().isoformat()),
            ).fetchone()
            if not row:
                return None
            return User(
                id=row["id"],
                username=row["username"],
                role=Role(row["role"]),
                active=bool(row["active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    # --- Sessions ---
    def create_session(self, session_id: str, name: str, started_by: str, policy_profile: str = "default") -> Session:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions (id, name, started_by, policy_profile, started_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, name, started_by, policy_profile, now),
            )
            self._conn.commit()
        return Session(
            id=session_id,
            name=name,
            started_by=started_by,
            policy_profile=policy_profile,
            started_at=datetime.fromisoformat(now),
        )

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return Session(
                id=row["id"],
                name=row["name"],
                started_by=row["started_by"],
                policy_profile=row["policy_profile"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                end_reason=row["end_reason"],
            )

    def list_sessions(self, active_only: bool = False) -> list[Session]:
        with self._lock:
            query = "SELECT * FROM sessions"
            if active_only:
                query += " WHERE ended_at IS NULL"
            query += " ORDER BY started_at DESC"
            rows = self._conn.execute(query).fetchall()
            return [
                Session(
                    id=r["id"],
                    name=r["name"],
                    started_by=r["started_by"],
                    policy_profile=r["policy_profile"],
                    started_at=datetime.fromisoformat(r["started_at"]),
                    ended_at=datetime.fromisoformat(r["ended_at"]) if r["ended_at"] else None,
                    end_reason=r["end_reason"],
                )
                for r in rows
            ]

    def end_session(self, session_id: str, reason: str = "user_requested") -> None:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ?, end_reason = ? WHERE id = ? AND ended_at IS NULL",
                (now, reason, session_id),
            )
            self._conn.commit()

    # --- Approval Requests & Votes ---
    def create_approval_request(
        self,
        request_id: str,
        action_id: str,
        session_id: str | None,
        action_hash: str,
        mode: str,
        required: int,
        expires_at: datetime,
        action_payload: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        now = datetime.now().isoformat()
        exp = expires_at.isoformat()
        payload_dict = action_payload or {}
        payload_json = json.dumps(payload_dict, default=str)
        with self._lock:
            self._conn.execute(
                """INSERT INTO approval_requests
                   (id, action_id, session_id, action_hash, mode, required, status, created_at, expires_at, action_payload)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (request_id, action_id, session_id, action_hash, mode, required, ApprovalStatus.PENDING.value, now, exp, payload_json),
            )
            self._conn.commit()
        return ApprovalRequest(
            id=request_id,
            action_id=action_id,
            session_id=session_id,
            action_hash=action_hash,
            mode=mode,
            required=required,
            status=ApprovalStatus.PENDING,
            created_at=datetime.fromisoformat(now),
            expires_at=expires_at,
            action_payload=payload_dict,
        )

    def _parse_payload(self, val: Any) -> dict[str, Any]:
        if not val:
            return {}
        try:
            return json.loads(val) if isinstance(val, str) else dict(val)
        except Exception:
            return {}

    def get_approval_request(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
            if not row:
                return None
            keys = row.keys()
            payload = self._parse_payload(row["action_payload"]) if "action_payload" in keys else {}
            return ApprovalRequest(
                id=row["id"],
                action_id=row["action_id"],
                session_id=row["session_id"],
                action_hash=row["action_hash"],
                mode=row["mode"],
                required=row["required"],
                status=ApprovalStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]),
                decided_at=datetime.fromisoformat(row["decided_at"]) if row["decided_at"] else None,
                action_payload=payload,
            )

    def list_approval_requests(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        with self._lock:
            query = "SELECT * FROM approval_requests"
            params: list[Any] = []
            if status:
                query += " WHERE status = ?"
                params.append(status.value)
            query += " ORDER BY created_at DESC"
            rows = self._conn.execute(query, params).fetchall()
            return [
                ApprovalRequest(
                    id=r["id"],
                    action_id=r["action_id"],
                    session_id=r["session_id"],
                    action_hash=r["action_hash"],
                    mode=r["mode"],
                    required=r["required"],
                    status=ApprovalStatus(r["status"]),
                    created_at=datetime.fromisoformat(r["created_at"]),
                    expires_at=datetime.fromisoformat(r["expires_at"]),
                    decided_at=datetime.fromisoformat(r["decided_at"]) if r["decided_at"] else None,
                )
                for r in rows
            ]

    def get_votes_for_request(self, request_id: str) -> list[ApprovalVote]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM approval_votes WHERE request_id = ? ORDER BY voted_at ASC",
                (request_id,),
            ).fetchall()
            return [
                ApprovalVote(
                    id=r["id"],
                    request_id=r["request_id"],
                    approver_id=r["approver_id"],
                    decision=VoteDecision(r["decision"]),
                    action_hash=r["action_hash"],
                    voted_at=datetime.fromisoformat(r["voted_at"]),
                )
                for r in rows
            ]

    # --- Notification Log ---
    def log_notification(
        self,
        entry_id: str,
        event_type: str,
        channel: str,
        request_id: str | None,
        status: str,
        last_error: str | None = None,
    ) -> None:
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                """INSERT INTO notification_log (id, event_type, channel, request_id, status, attempts, last_error, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (entry_id, event_type, channel, request_id, status, last_error, now),
            )
            self._conn.commit()

    def list_notifications(self, limit: int = 50) -> list[NotificationLogEntry]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notification_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                NotificationLogEntry(
                    id=r["id"],
                    event_type=r["event_type"],
                    channel=r["channel"],
                    request_id=r["request_id"],
                    status=r["status"],
                    attempts=r["attempts"],
                    last_error=r["last_error"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]
