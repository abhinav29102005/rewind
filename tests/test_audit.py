from pathlib import Path

from rewind.audit.log import AuditEvent, AuditLog, EventType


def test_audit_log_lifecycle(tmp_path: Path) -> None:
    db_path = tmp_path / "test_audit.db"
    audit = AuditLog(db_path=db_path)

    # Log some events
    event1 = audit.log(AuditEvent(
        event_type=EventType.ACTION_RECEIVED,
        data={"cmd": "ls"}
    ))
    assert event1.event_id is not None
    assert event1.chain_hash != ""

    _ = audit.log(AuditEvent(
        event_type=EventType.ACTION_CLASSIFIED,
        data={"risk": "safe"}
    ))

    assert audit.count == 2

    # Verify chain
    is_valid, last_idx = audit.verify_chain()
    assert is_valid
    assert last_idx == 2

    # Retrieve events
    events = audit.get_events()
    assert len(events) == 2
    # Events are returned newest first
    assert events[0].event_type == EventType.ACTION_CLASSIFIED
    assert events[1].event_type == EventType.ACTION_RECEIVED

    audit.close()
