"""Comprehensive tests for Team features: Auth, Store, RBAC, Approvals, Sessions, Notifications."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from rewind.config.models import RewindConfig
from rewind.contracts import ActionRequest, NotificationEvent, NotificationEventType, RiskClass
from rewind.stubs.audit import StubAuditLog
from rewind.stubs.broker import StubTokenBroker
from rewind.team import (
    ApprovalError,
    ApprovalQueueManager,
    ApprovalStatus,
    CsrfManager,
    PermissionDenied,
    Role,
    SessionCookieManager,
    SessionManager,
    TeamStore,
    User,
    VoteDecision,
    check_permission,
    generate_api_token,
    has_permission,
    hash_password,
    verify_password,
)
from rewind.team.notify import escape_untrusted


@pytest.fixture
def store():
    s = TeamStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def sample_users(store: TeamStore):
    admin = store.create_user("u_admin", "admin_user", hash_password("admin_pass"), Role.ADMIN)
    app1 = store.create_user("u_app1", "approver_1", hash_password("app1_pass"), Role.APPROVER)
    app2 = store.create_user("u_app2", "approver_2", hash_password("app2_pass"), Role.APPROVER)
    viewer = store.create_user("u_view", "viewer_user", hash_password("view_pass"), Role.VIEWER)
    return {"admin": admin, "app1": app1, "app2": app2, "viewer": viewer}


# -----------------------------------------------------------------------------
# 1. Auth & Password & Token Tests
# -----------------------------------------------------------------------------
def test_password_hashing():
    pw = "SuperSecurePassword123!"
    h = hash_password(pw)
    assert h != pw
    assert verify_password(h, pw) is True
    assert verify_password(h, "WrongPassword") is False


def test_api_tokens(store: TeamStore, sample_users):
    raw, h = generate_api_token()
    assert raw.startswith("rwt_")
    store.create_api_token("tok_1", sample_users["app1"].id, h, label="dev")

    user = store.get_user_by_token_hash(h)
    assert user is not None
    assert user.id == sample_users["app1"].id

    # Wrong token hash
    assert store.get_user_by_token_hash("wrong_hash") is None


def test_session_cookie_tampering():
    mgr = SessionCookieManager(max_age_hours=1.0)
    cookie = mgr.create_cookie_value("user_123")
    assert mgr.verify_cookie_value(cookie) == "user_123"

    # Tampered user id
    tampered = cookie.replace("user_123", "user_999")
    assert mgr.verify_cookie_value(tampered) is None

    # Tampered signature
    bad_sig = cookie[:-4] + "ffff"
    assert mgr.verify_cookie_value(bad_sig) is None


def test_csrf_token():
    csrf = CsrfManager()
    token = csrf.create_token("user_123")
    assert csrf.verify_token(token, "user_123") is True
    assert csrf.verify_token(token, "user_other") is False


# -----------------------------------------------------------------------------
# 2. RBAC Permissions Matrix
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "role, permission, expected",
    [
        (Role.ADMIN, "view", True),
        (Role.ADMIN, "approve", True),
        (Role.ADMIN, "session", True),
        (Role.ADMIN, "policy", True),
        (Role.ADMIN, "manage_users", True),
        (Role.ADMIN, "rollback", True),
        (Role.APPROVER, "view", True),
        (Role.APPROVER, "approve", True),
        (Role.APPROVER, "session", True),
        (Role.APPROVER, "policy", False),
        (Role.APPROVER, "manage_users", False),
        (Role.APPROVER, "rollback", True),
        (Role.VIEWER, "view", True),
        (Role.VIEWER, "approve", False),
        (Role.VIEWER, "session", False),
        (Role.VIEWER, "policy", False),
        (Role.VIEWER, "manage_users", False),
        (Role.VIEWER, "rollback", False),
    ],
)
def test_rbac_matrix(role: Role, permission: str, expected: bool):
    assert has_permission(role, permission) is expected
    u = User(id="test", username="test", role=role, active=True, created_at=datetime.now())
    if expected:
        check_permission(u, permission)  # does not raise
    else:
        with pytest.raises(PermissionDenied):
            check_permission(u, permission)


# -----------------------------------------------------------------------------
# 3. Shared Approval Queues (any-one & N-of-M, action hash binding, SoD, expiry)
# -----------------------------------------------------------------------------
def make_action(action_id: str = "act_1", session_id: str | None = None) -> ActionRequest:
    return ActionRequest(
        id=action_id,
        session_id=session_id,
        agent_id="agent_1",
        tool="sql",
        operation="exec",
        payload={"statement": "DROP TABLE users"},
        created_at=datetime.now(),
    )


def test_approval_any_one_mode(store: TeamStore, sample_users):
    audit = StubAuditLog()
    mgr = ApprovalQueueManager(store, audit_log=audit)
    act = make_action("act_any")
    req = mgr.create_request(act, mode="any_one", required=1, expires_at=datetime.now() + timedelta(minutes=15))

    status, _ = mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act)
    assert status == ApprovalStatus.APPROVED


def test_approval_n_of_m_consensus(store: TeamStore, sample_users):
    mgr = ApprovalQueueManager(store)
    act = make_action("act_nofm")
    req = mgr.create_request(act, mode="n_of_m", required=2, expires_at=datetime.now() + timedelta(minutes=15))

    # First vote from approver 1: leaves request pending
    status1, _ = mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act)
    assert status1 == ApprovalStatus.PENDING

    # Second vote from approver 2: reaches consensus and approves
    status2, _ = mgr.vote(req.id, sample_users["app2"], VoteDecision.APPROVE, act)
    assert status2 == ApprovalStatus.APPROVED


def test_approval_duplicate_voter_rejected(store: TeamStore, sample_users):
    mgr = ApprovalQueueManager(store)
    act = make_action("act_dupe")
    req = mgr.create_request(act, mode="n_of_m", required=2, expires_at=datetime.now() + timedelta(minutes=15))

    mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act)
    with pytest.raises(ApprovalError, match="already voted"):
        mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act)


def test_approval_action_hash_binding(store: TeamStore, sample_users):
    mgr = ApprovalQueueManager(store)
    act = make_action("act_bound")
    req = mgr.create_request(act, mode="any_one", required=1, expires_at=datetime.now() + timedelta(minutes=15))

    # Modifying the action payload must cause vote rejection!
    tampered_act = ActionRequest(
        id=act.id,
        session_id=act.session_id,
        agent_id=act.agent_id,
        tool="sql",
        operation="exec",
        payload={"statement": "DROP TABLE different_table"},
        created_at=act.created_at,
    )
    with pytest.raises(ApprovalError, match="modified"):
        mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, tampered_act)


def test_separation_of_duties(store: TeamStore, sample_users):
    sess_mgr = SessionManager(store, RewindConfig())
    session, _ = sess_mgr.start_session("test_sess", sample_users["app1"])

    mgr = ApprovalQueueManager(store)
    act = make_action("act_sod", session_id=session.id)
    req = mgr.create_request(act, mode="any_one", required=1, expires_at=datetime.now() + timedelta(minutes=15))

    # Initiator approver_1 tries to vote on own session action: rejected!
    with pytest.raises(ApprovalError, match="Separation of duties"):
        mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act, separation_of_duties=True)

    # Different approver (approver_2) is allowed to vote
    status, _ = mgr.vote(req.id, sample_users["app2"], VoteDecision.APPROVE, act, separation_of_duties=True)
    assert status == ApprovalStatus.APPROVED


def test_approval_veto_on_deny(store: TeamStore, sample_users):
    mgr = ApprovalQueueManager(store)
    act = make_action("act_veto")
    req = mgr.create_request(act, mode="n_of_m", required=2, expires_at=datetime.now() + timedelta(minutes=15))

    # One approver denies: veto immediately marks request denied
    status, _ = mgr.vote(req.id, sample_users["app1"], VoteDecision.DENY, act, veto=True)
    assert status == ApprovalStatus.DENIED


def test_approval_expiry(store: TeamStore, sample_users):
    mgr = ApprovalQueueManager(store)
    act = make_action("act_exp")
    # Expired 5 seconds ago
    req = mgr.create_request(act, mode="any_one", required=1, expires_at=datetime.now() - timedelta(seconds=5))

    with pytest.raises(ApprovalError, match="expired"):
        mgr.vote(req.id, sample_users["app1"], VoteDecision.APPROVE, act)


# -----------------------------------------------------------------------------
# 4. Session Management & Token Revocation
# -----------------------------------------------------------------------------
def test_session_lifecycle(store: TeamStore, sample_users):
    broker = StubTokenBroker()
    audit = StubAuditLog()
    sess_mgr = SessionManager(store, RewindConfig(), token_broker=broker, audit_log=audit)

    session, eff_cfg = sess_mgr.start_session("prod_run", sample_users["app1"], profile_name="strict")
    assert session.name == "prod_run"
    assert eff_cfg.escalate_reversible is True  # strict profile escalated

    tok = broker.issue(session.id, {"read", "write"})
    assert broker.is_valid(tok) is True

    # End session
    sess_mgr.end_session(session.id, actor=sample_users["app1"], reason="work_complete")
    s_ended = store.get_session(session.id)
    assert s_ended.ended_at is not None
    # Token must be revoked immediately
    assert broker.is_valid(tok) is False


# -----------------------------------------------------------------------------
# 5. Notifications & Security
# -----------------------------------------------------------------------------
def test_no_secret_code_in_notification_payload():
    evt = NotificationEvent(
        id="evt_1",
        type=NotificationEventType.APPROVAL_REQUESTED,
        created_at=datetime.now(),
        summary="Action requires approval",
        action_id="act_1",
        risk=RiskClass.IRREVERSIBLE,
        untrusted={"sql": "DROP TABLE users; -- sneaky"},
    )
    dumped = evt.model_dump_json()
    # Must never contain approval codes
    assert "RW-" not in dumped


def test_escape_untrusted_text():
    malicious = "<script>alert('xss')</script> & DROP TABLE users;"
    escaped = escape_untrusted(malicious)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped
