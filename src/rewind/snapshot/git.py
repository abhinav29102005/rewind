"""
Git-based filesystem snapshots.

Creates automatic git commits in a shadow repository before any
reversible or irreversible action, enabling preview and rollback.
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    """Record of a snapshot (checkpoint) taken before a risky operation."""

    snapshot_id: str
    action_summary: str
    created_at: float = field(default_factory=time.time)
    commit_hash: str = ""
    path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "action_summary": self.action_summary,
            "created_at": self.created_at,
            "commit_hash": self.commit_hash,
            "path": self.path,
        }


class GitSnapshotError(Exception):
    """Raised when a git snapshot operation fails."""


class GitSnapshotter:
    """
    Takes git-based snapshots of a directory before risky operations.

    Uses a shadow git repo (can be the project's own repo or a separate one)
    to create commits that serve as checkpoints.
    """

    def __init__(self, working_dir: Path | str) -> None:
        self._working_dir = Path(working_dir).resolve()
        self._snapshots: dict[str, Snapshot] = {}

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a git command in the working directory."""
        cmd = ["git", "-C", str(self._working_dir)] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise GitSnapshotError(f"Git command timed out: {' '.join(cmd)}") from e

    def is_git_repo(self) -> bool:
        """Check if the working directory is a git repo."""
        result = self._run_git("rev-parse", "--is-inside-work-tree")
        return result.returncode == 0

    def init_if_needed(self) -> bool:
        """Initialize a git repo if one doesn't exist. Returns True if created."""
        if self.is_git_repo():
            return False
        result = self._run_git("init")
        if result.returncode != 0:
            raise GitSnapshotError(f"Failed to init git repo: {result.stderr}")
        logger.info("Initialized git repo at %s", self._working_dir)
        return True

    def create_snapshot(self, action_summary: str) -> Snapshot:
        """
        Create a snapshot (git commit) of the current state.

        Stages all changes and creates a commit with a descriptive message.
        Returns a Snapshot with the commit hash.
        """
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"

        # Stage all changes
        self._run_git("add", "-A")

        # Check if there are changes to commit
        status = self._run_git("status", "--porcelain")
        if not status.stdout.strip():
            # Nothing to commit — take a snapshot of the current HEAD
            head = self._run_git("rev-parse", "HEAD")
            commit_hash = head.stdout.strip() if head.returncode == 0 else "none"
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                action_summary=action_summary,
                commit_hash=commit_hash,
                path=str(self._working_dir),
                metadata={"type": "no-change"},
            )
            self._snapshots[snapshot_id] = snapshot
            logger.info("Snapshot %s: no changes (HEAD=%s)", snapshot_id, commit_hash[:8])
            return snapshot

        # Create the commit
        commit_msg = f"[rewind snapshot] {snapshot_id}: {action_summary}"
        result = self._run_git("commit", "-m", commit_msg, "--allow-empty")
        if result.returncode != 0:
            raise GitSnapshotError(f"Failed to create snapshot commit: {result.stderr}")

        # Get the commit hash
        head = self._run_git("rev-parse", "HEAD")
        commit_hash = head.stdout.strip()

        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            action_summary=action_summary,
            commit_hash=commit_hash,
            path=str(self._working_dir),
        )
        self._snapshots[snapshot_id] = snapshot
        logger.info("Snapshot created: %s (commit=%s)", snapshot_id, commit_hash[:8])
        return snapshot

    def get_diff(self, snapshot_id: str) -> str:
        """Get the diff between a snapshot and the current state."""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise GitSnapshotError(f"Unknown snapshot: {snapshot_id}")

        if not snapshot.commit_hash or snapshot.commit_hash == "none":
            return "(no changes recorded)"

        result = self._run_git("diff", snapshot.commit_hash, "HEAD")
        return result.stdout if result.returncode == 0 else f"(diff failed: {result.stderr})"

    def rollback(self, snapshot_id: str) -> bool:
        """
        Rollback to a snapshot.

        Uses `git checkout` to restore the working directory to the snapshot state.
        Creates a new commit recording the rollback.
        """
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise GitSnapshotError(f"Unknown snapshot: {snapshot_id}")

        if not snapshot.commit_hash or snapshot.commit_hash == "none":
            logger.warning("Cannot rollback to snapshot %s: no commit hash", snapshot_id)
            return False

        # Checkout the snapshot commit's tree
        result = self._run_git("checkout", snapshot.commit_hash, "--", ".")
        if result.returncode != 0:
            raise GitSnapshotError(f"Rollback failed: {result.stderr}")

        # Commit the rollback
        rollback_msg = f"[rewind rollback] restored to {snapshot_id} ({snapshot.commit_hash[:8]})"
        self._run_git("add", "-A")
        self._run_git("commit", "-m", rollback_msg, "--allow-empty")

        logger.info("Rolled back to snapshot %s (commit=%s)", snapshot_id, snapshot.commit_hash[:8])
        return True

    def list_snapshots(self) -> list[Snapshot]:
        """List all recorded snapshots, newest first."""
        return sorted(self._snapshots.values(), key=lambda s: s.created_at, reverse=True)

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        return self._snapshots.get(snapshot_id)
