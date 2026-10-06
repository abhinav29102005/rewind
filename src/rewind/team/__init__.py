"""Rewind team features: auth, store, RBAC, shared approval queues, sessions, and notifications."""

from __future__ import annotations

from .approvals import ApprovalError, ApprovalQueueManager
from .auth import (
    AuthError,
    CsrfManager,
    LoginRateLimiter,
    SessionCookieManager,
    generate_api_token,
    hash_password,
    hash_token,
    verify_password,
)
from .models import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalVote,
    NotificationLogEntry,
    Role,
    Session,
    User,
    VoteDecision,
)
from .rbac import PermissionDenied, check_permission, has_permission, requires
from .sessions import SessionManager
from .store import TeamStore

__all__ = [
    "ApprovalError",
    "ApprovalQueueManager",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalVote",
    "AuthError",
    "CsrfManager",
    "LoginRateLimiter",
    "NotificationLogEntry",
    "PermissionDenied",
    "Role",
    "Session",
    "SessionCookieManager",
    "SessionManager",
    "TeamStore",
    "User",
    "VoteDecision",
    "check_permission",
    "generate_api_token",
    "has_permission",
    "hash_password",
    "hash_token",
    "requires",
    "verify_password",
]
