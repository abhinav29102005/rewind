"""Session lifecycle management and per-session policy overlays."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ..config.loader import apply_overlay
from .models import ApprovalStatus, Session, User

if TYPE_CHECKING:
    from ..config.models import RewindConfig
    from ..contracts import AuditLog, TokenBroker
    from .store import TeamStore

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages sessions, per-session policy profiles, and token revocation."""

    def __init__(
        self,
        store: TeamStore,
        base_config: RewindConfig,
        token_broker: TokenBroker | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.store = store
        self.base_config = base_config
        self.token_broker = token_broker
        self.audit_log = audit_log

    def start_session(
        self,
        name: str,
        user: User,
        profile_name: str = "default",
    ) -> tuple[Session, RewindConfig]:
        """Start a new session with validated tighten-only policy profile."""
        profile = self.base_config.sessions.profiles.get(profile_name)
        if profile is None:
            raise ValueError(f"Unknown session policy profile: {profile_name!r}")

        # Validate that profile only tightens policy
        effective_cfg = apply_overlay(
            self.base_config,
            profile,
            actor_role=user.role.value,
        )

        session_id = "ses_" + uuid.uuid4().hex[:12]
        session = self.store.create_session(
            session_id=session_id,
            name=name,
            started_by=user.id,
            policy_profile=profile_name,
        )

        if self.audit_log:
            self.audit_log.append(
                "session_started",
                {"session_id": session_id, "name": name, "profile": profile_name},
                actor=user.id,
                session_id=session_id,
            )

        return session, effective_cfg

    def end_session(self, session_id: str, actor: User | None = None, reason: str = "user_requested") -> None:
        """End a session, revoke capability tokens, cancel pending approval requests, and audit."""
        session = self.store.get_session(session_id)
        if not session or session.ended_at:
            return

        self.store.end_session(session_id, reason=reason)

        # Revoke capability tokens issued to this session
        revoked_count = 0
        if self.token_broker:
            revoked_count = self.token_broker.revoke_session(session_id)

        # Cancel any pending approval requests
        now = datetime.now().isoformat()
        with self.store._lock:
            self.store._conn.execute(
                "UPDATE approval_requests SET status = ?, decided_at = ? WHERE session_id = ? AND status = ?",
                (ApprovalStatus.DENIED.value, now, session_id, ApprovalStatus.PENDING.value),
            )
            self.store._conn.commit()

        if self.audit_log:
            self.audit_log.append(
                "session_ended",
                {"session_id": session_id, "reason": reason, "revoked_tokens": revoked_count},
                actor=actor.id if actor else None,
                session_id=session_id,
            )

    def list_sessions(self, active_only: bool = False) -> list[Session]:
        return self.store.list_sessions(active_only=active_only)
