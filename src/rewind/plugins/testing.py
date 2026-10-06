"""Plugin conformance test kit for plugin authors."""

from __future__ import annotations

from datetime import datetime

from ..contracts import (
    ActionRequest,
    ApprovalChannel,
    Classification,
    Classifier,
    NotificationEvent,
    NotificationEventType,
    RiskClass,
    SnapshotBackend,
)


def assert_classifier_conformance(classifier: Classifier) -> None:
    """Verifies that a classifier conforms to the Classifier protocol and contracts."""
    assert hasattr(classifier, "name") and isinstance(classifier.name, str)
    assert hasattr(classifier, "supports") and callable(classifier.supports)
    assert hasattr(classifier, "classify") and callable(classifier.classify)

    sample_action = ActionRequest(
        id="test_action",
        agent_id="test_agent",
        tool="sql",
        operation="exec",
        payload={"statement": "SELECT 1"},
        created_at=datetime.now(),
    )

    supported = classifier.supports(sample_action)
    assert isinstance(supported, bool)

    if supported:
        res = classifier.classify(sample_action)
        assert isinstance(res, Classification)
        assert isinstance(res.risk, RiskClass)
        assert isinstance(res.reasons, list)


def assert_snapshot_backend_conformance(backend: SnapshotBackend) -> None:
    """Verifies that a snapshot backend conforms to the SnapshotBackend protocol."""
    assert hasattr(backend, "name") and isinstance(backend.name, str)
    assert hasattr(backend, "supports") and callable(backend.supports)
    assert hasattr(backend, "capture") and callable(backend.capture)
    assert hasattr(backend, "preview_restore") and callable(backend.preview_restore)
    assert hasattr(backend, "restore") and callable(backend.restore)

    sample_action = ActionRequest(
        id="test_action",
        agent_id="test_agent",
        tool="fs",
        operation="exec",
        payload={"command": "touch sample.txt"},
        created_at=datetime.now(),
    )

    if backend.supports(sample_action):
        snap_id = backend.capture(sample_action)
        assert isinstance(snap_id, str)
        preview = backend.preview_restore(snap_id)
        assert isinstance(preview, dict)
        restore_res = backend.restore(snap_id, force=False)
        assert isinstance(restore_res, dict)


def assert_approval_channel_conformance(channel: ApprovalChannel) -> None:
    """Verifies that an approval channel conforms to the ApprovalChannel protocol."""
    assert hasattr(channel, "name") and isinstance(channel.name, str)
    assert hasattr(channel, "notify") and callable(channel.notify)

    event = NotificationEvent(
        id="evt_test",
        type=NotificationEventType.APPROVAL_REQUESTED,
        created_at=datetime.now(),
        summary="Action requires approval",
        action_id="act_123",
        risk=RiskClass.IRREVERSIBLE,
    )

    # Must not raise exceptions
    channel.notify(event)
