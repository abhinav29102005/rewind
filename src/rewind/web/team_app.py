"""FastAPI web application and control plane dashboard for team features."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Body, Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..contracts import ActionRequest, AuditLog
from ..stubs.audit import StubAuditLog
from ..team.approvals import ApprovalError, ApprovalQueueManager
from ..team.auth import (
    CsrfManager,
    LoginRateLimiter,
    SessionCookieManager,
    hash_password,
    verify_password,
)
from ..team.models import ApprovalStatus, Role, User, VoteDecision
from ..team.rbac import check_permission
from ..team.sessions import SessionManager

if TYPE_CHECKING:
    from ..config.models import RewindConfig
    from ..team.store import TeamStore

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_team_app(
    store: TeamStore,
    config: RewindConfig,
    audit_log: AuditLog | None = None,
    queue_manager: ApprovalQueueManager | None = None,
    session_manager: SessionManager | None = None,
) -> FastAPI:
    app = FastAPI(title="Rewind Control Plane", version="1.0.0")

    from ..audit.log import AuditLog as SqliteAuditLog
    audit = audit_log or SqliteAuditLog(Path(store.db_path).parent / "audit.db")
    queue = queue_manager or ApprovalQueueManager(store, audit_log=audit)
    sessions = session_manager or SessionManager(store, config, audit_log=audit)

    from ..team.rbac import PermissionDenied

    @app.exception_handler(PermissionDenied)
    def permission_denied_handler(request: Request, exc: PermissionDenied) -> Response:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    cookie_mgr = SessionCookieManager(max_age_hours=config.control_plane.web_session_hours)
    csrf_mgr = CsrfManager()
    rate_limiter = LoginRateLimiter(max_per_minute=config.control_plane.login_rate_limit_per_minute)

    cookie_name = "rewind_session"

    def get_current_user(request: Request) -> User | None:
        # Check Authorization header (API token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()
            import hashlib
            tok_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            user = store.get_user_by_token_hash(tok_hash)
            if user:
                return user

        # Check session cookie
        cookie_val = request.cookies.get(cookie_name)
        if cookie_val:
            user_id = cookie_mgr.verify_cookie_value(cookie_val)
            if user_id:
                return store.get_user(user_id)
        return None

    def require_user(user: User | None = Depends(get_current_user)) -> User:
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        return user

    def verify_csrf(request: Request, csrf_token: str = Form(...), user: User = Depends(require_user)) -> None:
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    # --- Routes ---

    @app.get("/", response_class=RedirectResponse)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    @app.get("/prototype", response_class=HTMLResponse)
    def prototype_page() -> HTMLResponse:
        proto_path = Path(__file__).resolve().parents[3] / "frontend-prototype" / "index.html"
        if proto_path.exists():
            return HTMLResponse(content=proto_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Prototype not found</h1>", status_code=status.HTTP_404_NOT_FOUND)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> Response:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

    @app.post("/login")
    def login(
        request: Request,
        response: Response,
        username: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        if rate_limiter.is_rate_limited(f"{client_ip}:{username}"):
            audit.append("login_rate_limited", {"ip": client_ip, "username": username})
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Too many failed login attempts. Please wait."},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        res = store.get_user_by_username(username)
        if not res or not res[1] or not verify_password(res[1], password):
            rate_limiter.record_attempt(f"{client_ip}:{username}")
            audit.append("login_failed", {"ip": client_ip, "username": username})
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Invalid username or password."},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user, _ = res
        if not user.active:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Account is inactive."},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        cookie_value = cookie_mgr.create_cookie_value(user.id)
        audit.append("login_success", {"username": username}, actor=user.id)

        redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key=cookie_name,
            value=cookie_value,
            httponly=True,
            samesite="strict",
            secure=False,  # loopback dev/test
            max_age=int(config.control_plane.web_session_hours * 3600),
        )
        return redirect

    @app.post("/logout")
    def logout(user: User = Depends(require_user)) -> RedirectResponse:
        audit.append("logout", {}, actor=user.id)
        redirect = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        redirect.delete_cookie(cookie_name)
        return redirect

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request, current_user: User | None = Depends(get_current_user)) -> Response:
        if not current_user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        csrf_token = csrf_mgr.create_token(current_user.id)
        pending = store.list_approval_requests(status=ApprovalStatus.PENDING)
        active_sessions = store.list_sessions()
        audit_events = audit.query()[-50:]
        notifications = store.list_notifications(limit=30)
        users = store.list_users() if current_user.role == Role.ADMIN else []

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "current_user": current_user,
                "csrf_token": csrf_token,
                "mode": config.mode,
                "pending_requests": pending,
                "sessions": active_sessions,
                "audit_events": audit_events,
                "notifications": notifications,
                "users": users,
                "verification_status": None,
            },
        )

    @app.post("/api/approvals/{request_id}/vote")
    def vote_approval(
        request_id: str,
        decision: str = Form(...),
        otp_code: str | None = Form(None),
        csrf_token: str = Form(...),
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "approve")
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

        req = store.get_approval_request(request_id)
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

        dummy_action = ActionRequest(
            id=req.action_id,
            session_id=req.session_id,
            agent_id="mcp-agent",
            tool="shell",
            operation="exec",
            payload=req.action_payload,
            created_at=req.created_at,
        )

        dec = VoteDecision.APPROVE if decision == "approve" else VoteDecision.DENY
        try:
            sod = getattr(getattr(config.approval, "default", None), "separation_of_duties", True)
            new_status, msg = queue.vote(
                request_id=request_id,
                approver=user,
                decision=dec,
                current_action=dummy_action,
                one_time_code=otp_code.strip() if otp_code else None,
                separation_of_duties=sod,
            )
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        except ApprovalError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # --- REST API Endpoints (for VS Code extension, CLI, and Automation) ---

    @app.get("/api/v1/approvals/pending")
    def get_pending_approvals_api(user: User = Depends(require_user)) -> list[dict[str, Any]]:
        check_permission(user, "view")
        pending = store.list_approval_requests(status=ApprovalStatus.PENDING)
        return [
            {
                "id": r.id,
                "action_id": r.action_id,
                "session_id": r.session_id,
                "command": r.action_payload.get("command", ""),
                "action_payload": r.action_payload,
                "action_hash": r.action_hash,
                "mode": r.mode,
                "required": r.required,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "expires_at": r.expires_at.isoformat(),
            }
            for r in pending
        ]

    @app.post("/api/v1/approvals/{request_id}/decision")
    def decide_approval_api(
        request_id: str,
        payload: dict[str, Any] = Body(...),
        user: User = Depends(require_user),
    ) -> dict[str, Any]:
        check_permission(user, "approve")
        req = store.get_approval_request(request_id)
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

        decision_str = str(payload.get("decision", "approve")).lower()
        dec = VoteDecision.APPROVE if decision_str == "approve" else VoteDecision.DENY
        otp = payload.get("otp_code")

        dummy_action = ActionRequest(
            id=req.action_id,
            session_id=req.session_id,
            agent_id="mcp-agent",
            tool="shell",
            operation="exec",
            payload=req.action_payload,
            created_at=req.created_at,
        )

        try:
            sod = getattr(getattr(config.approval, "default", None), "separation_of_duties", True)
            new_status, msg = queue.vote(
                request_id=request_id,
                approver=user,
                decision=dec,
                current_action=dummy_action,
                one_time_code=otp.strip() if otp else None,
                separation_of_duties=sod,
            )
            return {"request_id": request_id, "status": new_status.value, "message": msg}
        except ApprovalError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    @app.post("/api/sessions/start")
    def start_session_endpoint(
        name: str = Form(...),
        profile: str = Form("default"),
        csrf_token: str = Form(...),
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "session")
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

        sessions.start_session(name=name, user=user, profile_name=profile)
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    @app.post("/api/sessions/{session_id}/end")
    def end_session_endpoint(
        session_id: str,
        csrf_token: str = Form(...),
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "session")
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

        sessions.end_session(session_id=session_id, actor=user)
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    @app.post("/api/audit/verify")
    def verify_audit_chain(
        request: Request,
        csrf_token: str = Form(...),
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "view")
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

        is_valid, _ = audit.verify()

        csrf = csrf_mgr.create_token(user.id)
        pending = store.list_approval_requests(status=ApprovalStatus.PENDING)
        active_sessions = store.list_sessions()
        audit_events = audit.query()[-50:]
        notifications = store.list_notifications(limit=30)
        users = store.list_users() if user.role == Role.ADMIN else []

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "current_user": user,
                "csrf_token": csrf,
                "mode": config.mode,
                "pending_requests": pending,
                "sessions": active_sessions,
                "audit_events": audit_events,
                "notifications": notifications,
                "users": users,
                "verification_status": is_valid,
            },
        )

    @app.get("/api/audit/export")
    def export_audit(
        format: str = "json",  # noqa: A002
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "view")
        events = audit.query()

        # Redact sensitive fields
        redacted = []
        redact_keys = set(config.audit.redact_payload_fields)
        for e in events:
            entry = dict(e)
            if "data" in entry and isinstance(entry["data"], dict):
                d = dict(entry["data"])
                for k in list(d.keys()):
                    if any(rk in k.lower() for rk in redact_keys):
                        d[k] = "[REDACTED]"
                entry["data"] = d
            redacted.append(entry)

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["seq", "event_type", "actor", "session_id", "timestamp", "data"])
            for r in redacted:
                writer.writerow([
                    r.get("seq", ""),
                    r.get("event_type", ""),
                    r.get("actor", ""),
                    r.get("session_id", ""),
                    r.get("ts", ""),
                    json.dumps(r.get("data", {})),
                ])
            output.seek(0)
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=rewind_audit_export.csv"},
            )
        else:
            return JSONResponse(content=redacted)

    @app.post("/api/users/create")
    def create_user_endpoint(
        username: str = Form(...),
        password: str = Form(...),
        role: str = Form(...),
        csrf_token: str = Form(...),
        user: User = Depends(require_user),
    ) -> Response:
        check_permission(user, "manage_users")
        if not csrf_mgr.verify_token(csrf_token, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

        import uuid
        uid = "usr_" + uuid.uuid4().hex[:10]
        store.create_user(uid, username, hash_password(password), Role(role))
        audit.append("user_created", {"new_username": username, "new_role": role}, actor=user.id)
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    return app
