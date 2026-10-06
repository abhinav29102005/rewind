"""Stub snapshot backend: records calls, returns fake ids."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..contracts import ActionRequest


class StubSnapshotBackend:
    name = "stub"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def supports(self, action: ActionRequest) -> bool:
        return True

    def capture(self, action: ActionRequest) -> str:
        sid = "snap_" + uuid.uuid4().hex[:12]
        self.calls.append(("capture", action.id))
        return sid

    def preview_restore(self, snapshot_id: str) -> dict[str, Any]:
        self.calls.append(("preview_restore", snapshot_id))
        return {"snapshot_id": snapshot_id, "changes": []}

    def restore(self, snapshot_id: str, force: bool = False) -> dict[str, Any]:
        self.calls.append(("restore", snapshot_id))
        return {"snapshot_id": snapshot_id, "restored": True, "force": force}
