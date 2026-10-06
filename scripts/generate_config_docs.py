"""Generates docs/config.md from Pydantic config models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from rewind.config.models import (
    ApprovalConfig,
    ApprovalPolicy,
    ApprovalPolicyPatch,
    AuditConfig,
    ControlPlaneConfig,
    DiscordChannelConfig,
    EmailChannelConfig,
    NotificationsConfig,
    PluginsConfig,
    PoliciesConfig,
    PolicyOverlay,
    RewindConfig,
    RuleOverride,
    SessionsConfig,
    SlackChannelConfig,
    SnapshotsConfig,
    WebhookChannelConfig,
)


def _format_type(tp: Any) -> str:
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is None:
        if hasattr(tp, "__name__"):
            return tp.__name__
        return str(tp)
    if origin is list:
        return f"list[{_format_type(args[0])}]"
    if origin is dict:
        return f"dict[{_format_type(args[0])}, {_format_type(args[1])}]"
    if origin is tuple:
        return f"tuple[{', '.join(_format_type(a) for a in args)}]"
    # Union / Optional
    import types
    if origin in (types.UnionType, Any):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return f"{_format_type(non_none[0])} | None"
        return " | ".join(_format_type(a) for a in args)
    return str(tp).replace("typing.", "")


def _format_default(field: FieldInfo) -> str:
    if field.is_required():
        return "**required**"
    if field.default_factory is not None:
        try:
            val = field.default_factory()
            return f"`{val}`"
        except Exception:
            return "*(factory)*"
    if field.default is not None:
        if isinstance(field.default, str):
            return f'`"{field.default}"`'
        return f"`{field.default}`"
    return "`None`"


def _model_to_markdown(model_cls: type[BaseModel], title: str, description: str = "") -> str:
    lines = [f"### {title}", ""]
    doc = description or (model_cls.__doc__ or "").strip()
    if doc:
        lines.append(f"{doc}")
        lines.append("")
    lines.append("| Field | Type | Default | Description |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for name, field in model_cls.model_fields.items():
        type_str = _format_type(field.annotation).replace("|", "\\|")
        default_str = _format_default(field).replace("|", "\\|")
        desc = (field.description or "").strip()
        lines.append(f"| `{name}` | `{type_str}` | {default_str} | {desc} |")
    lines.append("")
    return "\n".join(lines)


def generate() -> str:
    sections = [
        "# Configuration Reference (`rewind.yaml`)",
        "",
        "This configuration reference is **automatically generated** from Rewind's Pydantic v2 schemas (`rewind.config.models`).",
        "",
        "Rewind validates configuration strictly using `extra='forbid'`. Unknown keys or schema violations cause Rewind to **fail closed** immediately.",
        "",
        "## Top-Level Schema",
        "",
        _model_to_markdown(RewindConfig, "RewindConfig", "Root configuration file structure for `rewind.yaml`."),
        "## Policy Configuration",
        "",
        _model_to_markdown(PoliciesConfig, "PoliciesConfig", "Configures policy pack loading and individual rule overrides."),
        _model_to_markdown(RuleOverride, "RuleOverride", "Specifies per-rule risk overrides with mandatory audit justification."),
        "## Approval Policies",
        "",
        _model_to_markdown(ApprovalConfig, "ApprovalConfig", "Configures approval behavior per risk classification."),
        _model_to_markdown(ApprovalPolicy, "ApprovalPolicy", "Fine-grained consensus requirements (any-one vs. N-of-M, timeout, eligible roles, veto)."),
        _model_to_markdown(ApprovalPolicyPatch, "ApprovalPolicyPatch", "Partial approval policy overrides layered on top of defaults."),
        "## Session Controls",
        "",
        _model_to_markdown(SessionsConfig, "SessionsConfig", "Configures session lifetimes and tighten-only security profiles."),
        _model_to_markdown(PolicyOverlay, "PolicyOverlay", "Tighten-only security profile constraints applied to sessions."),
        "## Snapshots",
        "",
        _model_to_markdown(SnapshotsConfig, "SnapshotsConfig", "State snapshot capture and rollback retention settings."),
        "## Audit Logging",
        "",
        _model_to_markdown(AuditConfig, "AuditConfig", "Cryptographic tamper-evident hash-chained audit ledger settings."),
        "## Notifications",
        "",
        _model_to_markdown(NotificationsConfig, "NotificationsConfig", "Notification dispatcher and outgoing communication channels."),
        _model_to_markdown(WebhookChannelConfig, "WebhookChannelConfig", "HMAC-SHA256 signed HTTP webhook endpoints (`X-Rewind-Signature`)."),
        _model_to_markdown(SlackChannelConfig, "SlackChannelConfig", "Slack Block Kit webhook integration."),
        _model_to_markdown(DiscordChannelConfig, "DiscordChannelConfig", "Discord embed webhook integration."),
        _model_to_markdown(EmailChannelConfig, "EmailChannelConfig", "Direct SMTP email notifications."),
        "## Control Plane Dashboard",
        "",
        _model_to_markdown(ControlPlaneConfig, "ControlPlaneConfig", "Web UI and local HTTP server settings for human approval queue."),
        "## Plugins",
        "",
        _model_to_markdown(PluginsConfig, "PluginsConfig", "Plugin loading and isolation settings."),
    ]
    return "\n".join(sections)


if __name__ == "__main__":
    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_file = docs_dir / "config.md"
    out_file.write_text(generate(), encoding="utf-8")
    print(f"Generated {out_file}")
