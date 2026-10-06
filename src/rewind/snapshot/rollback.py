"""
Rollback Orchestration.

Coordinates rollback across multiple snapshot backends (git, database)
to provide one-command restore functionality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .database import DatabaseSnapshotter
    from .git import GitSnapshotter

logger = logging.getLogger(__name__)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    snapshot_id: str
    restored_files: bool = False
    restored_database: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "snapshot_id": self.snapshot_id,
            "restored_files": self.restored_files,
            "restored_database": self.restored_database,
            "errors": self.errors,
        }


class RollbackOrchestrator:
    """
    Coordinates rollback across file and database snapshot backends.

    Provides a single `rollback(snapshot_id)` method that restores
    both files and databases from a combined snapshot.
    """

    def __init__(
        self,
        git_snapshotter: GitSnapshotter | None = None,
        db_snapshotter: DatabaseSnapshotter | None = None,
    ) -> None:
        self._git = git_snapshotter
        self._db = db_snapshotter
        # Links file snapshots to database snapshots for combined rollback
        self._linked: dict[str, str] = {}  # file_snapshot_id -> db_snapshot_id

    def link_snapshots(self, file_snapshot_id: str, db_snapshot_id: str) -> None:
        """Link a file snapshot to a database snapshot for combined rollback."""
        self._linked[file_snapshot_id] = db_snapshot_id

    def rollback(
        self,
        snapshot_id: str,
        connection_string: str | None = None,
    ) -> RollbackResult:
        """
        Rollback to a snapshot. Handles both file and database restores.

        Args:
            snapshot_id: The snapshot ID to rollback to (file or database)
            connection_string: PostgreSQL connection string (if restoring a PG database)
        """
        result = RollbackResult(success=True, snapshot_id=snapshot_id)

        # Try file rollback
        if self._git:
            git_snapshot = self._git.get_snapshot(snapshot_id)
            if git_snapshot:
                try:
                    self._git.rollback(snapshot_id)
                    result.restored_files = True
                except Exception as e:
                    result.errors.append(f"File rollback failed: {e}")
                    result.success = False

        # Check for linked database snapshot
        linked_db_id = self._linked.get(snapshot_id)
        if linked_db_id and self._db:
            db_snapshot = self._db.get_snapshot(linked_db_id)
            if db_snapshot:
                try:
                    if db_snapshot.db_type == "sqlite":
                        self._db.restore_sqlite(linked_db_id)
                        result.restored_database = True
                    elif db_snapshot.db_type == "postgresql" and connection_string:
                        self._db.restore_postgresql(linked_db_id, connection_string)
                        result.restored_database = True
                    else:
                        result.errors.append(
                            f"Cannot restore {db_snapshot.db_type}: missing connection info"
                        )
                except Exception as e:
                    result.errors.append(f"Database rollback failed: {e}")
                    result.success = False

        # Try direct database rollback
        if self._db and not result.restored_database:
            db_snapshot = self._db.get_snapshot(snapshot_id)
            if db_snapshot:
                try:
                    if db_snapshot.db_type == "sqlite":
                        self._db.restore_sqlite(snapshot_id)
                        result.restored_database = True
                    elif db_snapshot.db_type == "postgresql" and connection_string:
                        self._db.restore_postgresql(snapshot_id, connection_string)
                        result.restored_database = True
                except Exception as e:
                    result.errors.append(f"Database rollback failed: {e}")
                    result.success = False

        if result.restored_files or result.restored_database:
            logger.info("Rollback completed: %s", result.to_dict())
        else:
            result.success = False
            result.errors.append(f"No snapshot found for ID: {snapshot_id}")
            logger.error("Rollback failed: no matching snapshot found for %s", snapshot_id)

        return result
