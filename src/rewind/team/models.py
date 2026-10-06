"""Pydantic and data models for Phase 3 team features."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    ADMIN = "admin"
    APPROVER = "approver"
    VIEWER = "viewer"


class User(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    username: str
    role: Role
    active: bool = True
    created_at: datetime


class ApiToken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    token_hash: str
    label: str | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    started_by: str
    policy_profile: str = "default"
    started_at: datetime
    ended_at: datetime | None = None
    end_reason: str | None = None


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    action_id: str
    session_id: str | None = None
    action_hash: str
    mode: str = "any_one"  # "any_one" | "n_of_m"
    required: int = 1
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None


class VoteDecision(StrEnum):
    APPROVE = "approve"
    DENY = "deny"


class ApprovalVote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    request_id: str
    approver_id: str
    decision: VoteDecision
    action_hash: str
    voted_at: datetime


class NotificationLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event_type: str
    channel: str
    request_id: str | None = None
    status: str
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime
