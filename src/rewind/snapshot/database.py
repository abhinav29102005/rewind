"""
Database snapshot and rollback.

Supports SQLite (via .backup()) and PostgreSQL (via pg_dump/pg_restore).
Creates pre-action backups and enables one-command restore.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DBSnapshot:
    """Record of a database snapshot."""

    snapshot_id: str
    db_type: str  # "sqlite" or "postgresql"
    source: str   # file path or connection string (sanitized)
    backup_path: str
    created_at: float = field(default_factory=time.time)
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "db_type": self.db_type,
            "source": self.source,
            "backup_path": self.backup_path,
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
        }


class DBSnapshotError(Exception):
    """Raised when a database snapshot operation fails."""


class DatabaseSnapshotter:
    """
    Creates and manages database snapshots for rollback.

    Supports SQLite (built-in) and PostgreSQL (requires pg_dump/pg_restore).
    """

    def __init__(self, backup_dir: Path | str = ".rewind/db_snapshots") -> None:
        self._backup_dir = Path(backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: dict[str, DBSnapshot] = {}

    def snapshot_sqlite(self, db_path: Path | str, action_summary: str = "") -> DBSnapshot:
        """
        Create a snapshot of a SQLite database using the backup API.

        This is safe even while the database is being written to.
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise DBSnapshotError(f"SQLite database not found: {db_path}")

        snapshot_id = f"dbsnap_{uuid.uuid4().hex[:12]}"
        backup_path = self._backup_dir / f"{snapshot_id}_{db_path.name}"

        try:
            source_conn = sqlite3.connect(str(db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            source_conn.backup(backup_conn)
            backup_conn.close()
            source_conn.close()
        except sqlite3.Error as e:
            raise DBSnapshotError(f"SQLite backup failed: {e}") from e

        size = backup_path.stat().st_size

        snapshot = DBSnapshot(
            snapshot_id=snapshot_id,
            db_type="sqlite",
            source=str(db_path),
            backup_path=str(backup_path),
            size_bytes=size,
            metadata={"action_summary": action_summary},
        )
        self._snapshots[snapshot_id] = snapshot
        logger.info(
            "SQLite snapshot created: %s (%s, %d bytes)",
            snapshot_id,
            db_path.name,
            size,
        )
        return snapshot

    def snapshot_postgresql(
        self,
        connection_string: str,
        db_name: str,
        action_summary: str = "",
    ) -> DBSnapshot:
        """
        Create a snapshot of a PostgreSQL database using pg_dump.

        Requires pg_dump to be available on PATH.
        """
        snapshot_id = f"dbsnap_{uuid.uuid4().hex[:12]}"
        backup_path = self._backup_dir / f"{snapshot_id}_{db_name}.sql"

        try:
            result = subprocess.run(
                ["pg_dump", "--dbname", connection_string, "-f", str(backup_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise DBSnapshotError(f"pg_dump failed: {result.stderr}")
        except FileNotFoundError:
            raise DBSnapshotError("pg_dump not found on PATH") from None
        except subprocess.TimeoutExpired as e:
            raise DBSnapshotError("pg_dump timed out") from e

        size = backup_path.stat().st_size
        # Sanitize connection string for logging (remove password)
        safe_source = db_name

        snapshot = DBSnapshot(
            snapshot_id=snapshot_id,
            db_type="postgresql",
            source=safe_source,
            backup_path=str(backup_path),
            size_bytes=size,
            metadata={"action_summary": action_summary},
        )
        self._snapshots[snapshot_id] = snapshot
        logger.info("PostgreSQL snapshot created: %s (%s, %d bytes)", snapshot_id, db_name, size)
        return snapshot

    def restore_sqlite(self, snapshot_id: str) -> bool:
        """Restore a SQLite database from a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise DBSnapshotError(f"Unknown snapshot: {snapshot_id}")
        if snapshot.db_type != "sqlite":
            raise DBSnapshotError(f"Snapshot {snapshot_id} is not a SQLite snapshot")

        backup_path = Path(snapshot.backup_path)
        target_path = Path(snapshot.source)

        if not backup_path.exists():
            raise DBSnapshotError(f"Backup file missing: {backup_path}")

        shutil.copy2(str(backup_path), str(target_path))
        logger.info("SQLite restored from snapshot %s to %s", snapshot_id, target_path)
        return True

    def restore_postgresql(self, snapshot_id: str, connection_string: str) -> bool:
        """Restore a PostgreSQL database from a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise DBSnapshotError(f"Unknown snapshot: {snapshot_id}")
        if snapshot.db_type != "postgresql":
            raise DBSnapshotError(f"Snapshot {snapshot_id} is not a PostgreSQL snapshot")

        backup_path = Path(snapshot.backup_path)
        if not backup_path.exists():
            raise DBSnapshotError(f"Backup file missing: {backup_path}")

        try:
            result = subprocess.run(
                ["psql", "--dbname", connection_string, "-f", str(backup_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise DBSnapshotError(f"psql restore failed: {result.stderr}")
        except FileNotFoundError:
            raise DBSnapshotError("psql not found on PATH") from None

        logger.info("PostgreSQL restored from snapshot %s", snapshot_id)
        return True

    def list_snapshots(self) -> list[DBSnapshot]:
        """List all database snapshots, newest first."""
        return sorted(self._snapshots.values(), key=lambda s: s.created_at, reverse=True)

    def get_snapshot(self, snapshot_id: str) -> DBSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def cleanup(self, max_age_seconds: int = 86400 * 7) -> int:
        """Remove snapshots older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        to_remove = [
            sid for sid, s in self._snapshots.items() if s.created_at < cutoff
        ]
        for sid in to_remove:
            snapshot = self._snapshots.pop(sid)
            backup = Path(snapshot.backup_path)
            if backup.exists():
                backup.unlink()
        return len(to_remove)
