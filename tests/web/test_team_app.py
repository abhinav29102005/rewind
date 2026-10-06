"""Tests for FastAPI team web application: auth, CSRF, RBAC on endpoints, export, and chain verification."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rewind.config.models import RewindConfig
from rewind.stubs.audit import StubAuditLog
from rewind.team.auth import hash_password
from rewind.team.models import Role
from rewind.team.store import TeamStore
from rewind.web.team_app import create_team_app


@pytest.fixture
def store():
    s = TeamStore(":memory:")
    # Seed users
    s.create_user("u_admin", "admin", hash_password("admin123"), Role.ADMIN)
    s.create_user("u_app", "approver", hash_password("app123"), Role.APPROVER)
    s.create_user("u_view", "viewer", hash_password("view123"), Role.VIEWER)
    yield s
    s.close()


@pytest.fixture
def audit_log():
    audit = StubAuditLog()
    audit.append("test_event", {"secret_token": "super_secret_123", "action": "test"})
    return audit


@pytest.fixture
def client(store: TeamStore, audit_log: StubAuditLog):
    cfg = RewindConfig()
    app = create_team_app(store, cfg, audit_log=audit_log)
    return TestClient(app)


def login_client(client: TestClient, username: str, password: str) -> str:
    """Logs in and returns CSRF token from the dashboard page."""
    resp = client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    assert resp.status_code == 200
    # Extract CSRF token from the dashboard HTML
    import re
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    assert match is not None
    return match.group(1)


def test_unauthenticated_redirects_to_login(client: TestClient):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_login_invalid_password(client: TestClient):
    resp = client.post("/login", data={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.text


def test_login_success(client: TestClient):
    resp = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "rewind_session" in resp.cookies


def test_csrf_protection_on_state_changing_endpoints(client: TestClient):
    # Log in as admin
    login_client(client, "admin", "admin123")
    # Attempt to create user without CSRF token
    resp = client.post("/api/users/create", data={"username": "new_user", "password": "pw", "role": "viewer"})
    assert resp.status_code == 422  # Form field required


def test_rbac_endpoint_enforcement(client: TestClient):
    # Log in as viewer
    csrf = login_client(client, "viewer", "view123")
    # Viewer tries to create a user -> HTTP 403 Forbidden
    resp = client.post(
        "/api/users/create",
        data={"username": "hacker", "password": "pw", "role": "admin", "csrf_token": csrf},
    )
    assert resp.status_code == 403


def test_audit_export_redaction(client: TestClient):
    login_client(client, "viewer", "view123")

    # JSON export
    resp_json = client.get("/api/audit/export?format=json")
    assert resp_json.status_code == 200
    events = resp_json.json()
    assert len(events) > 0
    # Assert sensitive token was redacted
    for ev in events:
        data = ev.get("data", {})
        if "secret_token" in data:
            assert data["secret_token"] == "[REDACTED]"

    # CSV export
    resp_csv = client.get("/api/audit/export?format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "[REDACTED]" in resp_csv.text


def test_audit_verify_endpoint(client: TestClient):
    csrf = login_client(client, "viewer", "view123")
    resp = client.post("/api/audit/verify", data={"csrf_token": csrf})
    assert resp.status_code == 200
    assert "Audit log hash chain intact" in resp.text
