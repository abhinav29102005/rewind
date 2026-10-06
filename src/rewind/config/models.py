"""Pydantic schema for ``rewind.yaml``.

Every model forbids unknown keys so typos fail loudly instead of silently
falling back to a default. Secrets are referenced by environment variable name
(``*_env`` fields) and never stored in the file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..contracts import NotificationEventType, RiskClass

EnvVarName = Annotated[str, Field(pattern=r"^[A-Z_][A-Z0-9_]*$", max_length=128)]
RuleId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$", max_length=128)]
ApproverRole = Literal["approver", "admin"]  # viewers can never be eligible approvers


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuleOverride(_Strict):
    rule_id: RuleId
    risk: RiskClass
    override_reason: str | None = Field(default=None, min_length=8, max_length=500)


class PoliciesConfig(_Strict):
    packs: list[str] = Field(
        default_factory=lambda: ["filesystem", "postgresql", "git", "aws_s3", "docker"]
    )
    paths: list[Path] = Field(default_factory=list)
    overrides: list[RuleOverride] = Field(default_factory=list)

    @field_validator("overrides")
    @classmethod
    def _unique_overrides(cls, v: list[RuleOverride]) -> list[RuleOverride]:
        ids = [o.rule_id for o in v]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate overrides for rule ids: {sorted(dupes)}")
        return v


def _default_eligible_roles() -> list[ApproverRole]:
    return ["approver", "admin"]


class ApprovalPolicy(_Strict):
    """Fully-resolved approval policy for one risk class."""

    mode: Literal["any_one", "n_of_m"] = "any_one"
    n: int = Field(default=1, ge=1, le=20)
    timeout_minutes: int = Field(default=15, ge=1, le=24 * 60)
    eligible_roles: list[ApproverRole] = Field(default_factory=_default_eligible_roles)
    veto: bool = True  # a single eligible deny denies the request
    separation_of_duties: bool = True  # session starter's vote never counts

    @model_validator(mode="after")
    def _check(self) -> ApprovalPolicy:
        if self.mode == "any_one" and self.n != 1:
            raise ValueError("approval mode 'any_one' requires n == 1 (use 'n_of_m' for n > 1)")
        if self.mode == "n_of_m" and self.n < 2:
            raise ValueError("approval mode 'n_of_m' requires n >= 2")
        if not self.eligible_roles:
            raise ValueError("eligible_roles must not be empty")
        return self


class ApprovalPolicyPatch(_Strict):
    """Partial approval policy merged on top of ``approval.default``."""

    mode: Literal["any_one", "n_of_m"] | None = None
    n: int | None = Field(default=None, ge=1, le=20)
    timeout_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    eligible_roles: list[ApproverRole] | None = None
    veto: bool | None = None
    separation_of_duties: bool | None = None


class ApprovalConfig(_Strict):
    default: ApprovalPolicy = Field(default_factory=ApprovalPolicy)
    by_risk: dict[RiskClass, ApprovalPolicyPatch] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_resolved(self) -> ApprovalConfig:
        for risk in self.by_risk:
            self.for_risk(risk)  # raises if the merged policy is invalid
        return self

    def for_risk(self, risk: RiskClass) -> ApprovalPolicy:
        patch = self.by_risk.get(risk)
        if patch is None:
            return self.default
        merged = self.default.model_dump()
        merged.update({k: v for k, v in patch.model_dump().items() if v is not None})
        if patch.mode == "n_of_m" and patch.n is None and merged["n"] < 2:
            merged["n"] = 2  # DECISION: n_of_m without n means 2-of-M (the minimum).
        return ApprovalPolicy.model_validate(merged)


class SnapshotsConfig(_Strict):
    retention_hours: int = Field(default=72, ge=1, le=24 * 365)
    backend_priority: list[str] = Field(default_factory=lambda: ["git", "sqlite", "pg_dump"])


EventFilter = Literal[
    "*",
    "approval_requested",
    "approval_decided",
    "action_blocked",
    "deletion_pending",
    "session_started",
    "session_ended",
    "config_changed",
    "audit_chain_failure",
]
assert set(EventFilter.__args__) - {"*"} == {e.value for e in NotificationEventType}  # type: ignore[attr-defined]


def _default_events() -> list[EventFilter]:
    return ["*"]


class _ChannelBase(_Strict):
    name: str | None = Field(default=None, max_length=64)
    events: list[EventFilter] = Field(default_factory=_default_events)
    rate_limit_per_minute: int = Field(default=30, ge=1, le=10_000)
    digest_low_severity: bool = False
    # Shared channels never receive one-time codes. Only a channel explicitly
    # marked direct (per-user delivery) may carry recipient-addressed events.
    direct: bool = False


class SlackChannelConfig(_ChannelBase):
    type: Literal["slack"]
    webhook_url_env: EnvVarName


class DiscordChannelConfig(_ChannelBase):
    type: Literal["discord"]
    webhook_url_env: EnvVarName


class WebhookChannelConfig(_ChannelBase):
    type: Literal["webhook"]
    url_env: EnvVarName
    secret_env: EnvVarName


class EmailChannelConfig(_ChannelBase):
    type: Literal["email"]
    smtp_host: str
    smtp_port: int = Field(default=587, ge=1, le=65535)
    starttls: bool = True
    from_addr: str
    to_addrs_env: EnvVarName
    username_env: EnvVarName | None = None
    password_env: EnvVarName | None = None


ChannelConfig = Annotated[
    SlackChannelConfig | DiscordChannelConfig | WebhookChannelConfig | EmailChannelConfig,
    Field(discriminator="type"),
]


class NotificationsConfig(_Strict):
    channels: list[ChannelConfig] = Field(default_factory=list)
    max_attempts: int = Field(default=5, ge=1, le=20)
    dedupe_window_seconds: int = Field(default=300, ge=0, le=86_400)


class PluginsConfig(_Strict):
    enabled: list[str] = Field(default_factory=list)
    classifier_timeout_seconds: float = Field(default=2.0, gt=0, le=30)


class PolicyOverlay(_Strict):
    """A tighten-only bundle of overrides (session profiles, CLI flags).

    Relaxing changes require the admin role and ``override_reason``.
    """

    mode: Literal["audit_only", "enforce"] | None = None
    escalate_reversible: bool = False  # treat every reversible action as irreversible
    rule_overrides: list[RuleOverride] = Field(default_factory=list)
    approval: dict[RiskClass, ApprovalPolicyPatch] = Field(default_factory=dict)
    override_reason: str | None = Field(default=None, min_length=8, max_length=500)


def _builtin_profiles() -> dict[str, PolicyOverlay]:
    return {
        "default": PolicyOverlay(),
        "strict": PolicyOverlay(
            mode="enforce",
            escalate_reversible=True,
            approval={RiskClass.IRREVERSIBLE: ApprovalPolicyPatch(mode="n_of_m", n=2)},
        ),
    }


class SessionsConfig(_Strict):
    max_duration_hours: float = Field(default=8, gt=0, le=24 * 7)
    idle_timeout_minutes: int = Field(default=60, ge=1, le=24 * 60)
    profiles: dict[str, PolicyOverlay] = Field(default_factory=_builtin_profiles)

    @field_validator("profiles")
    @classmethod
    def _keep_builtins(cls, v: dict[str, PolicyOverlay]) -> dict[str, PolicyOverlay]:
        merged = _builtin_profiles()
        merged.update(v)
        return merged


class ControlPlaneConfig(_Strict):
    host: str = "127.0.0.1"  # loopback by default; never expose on the agent network
    port: int = Field(default=8787, ge=1, le=65535)
    public_url: str | None = None  # used for links in notifications
    login_rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    web_session_hours: float = Field(default=8, gt=0, le=72)


class SecurityConfig(_Strict):
    agent_os_user: str | None = None  # used by the startup permission check (POSIX)


class AuditConfig(_Strict):
    redact_payload_fields: list[str] = Field(
        default_factory=lambda: ["password", "token", "secret", "authorization", "api_key"]
    )


class RewindConfig(_Strict):
    version: Literal[1] = 1
    mode: Literal["audit_only", "enforce"] = "enforce"
    data_dir: Path = Path("./data")
    policies: PoliciesConfig = Field(default_factory=PoliciesConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    snapshots: SnapshotsConfig = Field(default_factory=SnapshotsConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    sessions: SessionsConfig = Field(default_factory=SessionsConfig)
    control_plane: ControlPlaneConfig = Field(default_factory=ControlPlaneConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    # Set by apply_overlay; part of the effective config, not normally in YAML.
    escalate_reversible: bool = False
