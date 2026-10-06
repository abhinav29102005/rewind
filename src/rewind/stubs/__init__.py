"""Stubs for Phase 0/1 modules so Phase 2/3 work is not blocked.

These implement the protocols in :mod:`rewind.contracts`. Contract tests in
``tests/contracts`` run against both these stubs and the real adapters.
"""

from __future__ import annotations

from .approval_codes import StubApprovalCodes
from .audit import StubAuditLog
from .broker import StubTokenBroker
from .classifier import StubBaseClassifier
from .snapshot import StubSnapshotBackend

__all__ = [
    "StubApprovalCodes",
    "StubAuditLog",
    "StubBaseClassifier",
    "StubSnapshotBackend",
    "StubTokenBroker",
]
