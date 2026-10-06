"""Load, merge and validate configuration. Fails closed.

Precedence (lowest to highest): built-in defaults, ``rewind.yaml``,
``REWIND_*`` environment variables, per-session overrides, CLI flags.

Environment variables, session overlays and CLI flags may only *tighten*
policy. A relaxing overlay needs the admin role plus ``override_reason``
(audited by the caller).
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from ..contracts import RiskClass, risk_rank
from .models import ApprovalConfig, ApprovalPolicy, PolicyOverlay, RewindConfig

if TYPE_CHECKING:
    from collections.abc import Mapping


class ConfigError(Exception):
    """Configuration is invalid, unreadable or a disallowed relaxation."""


DEFAULT_CONFIG_NAMES = ("rewind.yaml", "rewind.yml")


def _format_validation_error(err: ValidationError, source: str) -> str:
    lines = [f"Invalid configuration in {source}:"]
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"]) or "<root>"
        lines.append(f"  - {loc}: {e['msg']}")
    return "\n".join(lines)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Cannot read config file {path}: {e.strerror or e}") from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ConfigError(f"Config file {path} is not valid YAML: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a mapping at the top level")
    return data


# Environment variables understood by the loader. Anything else starting with
# REWIND_ is ignored here (it may be a secret referenced by *_env).
_ENV_KEYS = {
    "REWIND_MODE": ("mode",),
    "REWIND_DATA_DIR": ("data_dir",),
    "REWIND_CONTROL_PLANE_HOST": ("control_plane", "host"),
    "REWIND_CONTROL_PLANE_PORT": ("control_plane", "port"),
    "REWIND_PUBLIC_URL": ("control_plane", "public_url"),
}


def _set_path(d: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cur = d
    for p in path[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[path[-1]] = value


def load_config(
    path: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cli_overlay: PolicyOverlay | None = None,
    search_dir: Path | None = None,
) -> RewindConfig:
    """Load the effective configuration, or raise :class:`ConfigError`.

    # DECISION: invalid config refuses to start in *every* mode, not just
    # enforce, because an invalid file cannot be trusted to tell us its mode.
    """
    env = os.environ if env is None else env
    source = "<defaults>"
    raw: dict[str, Any] = {}

    if path is None and env.get("REWIND_CONFIG"):
        path = env["REWIND_CONFIG"]
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file {p} does not exist")
        raw = _read_yaml(p)
        source = str(p)
    else:
        base = search_dir or Path.cwd()
        for name in DEFAULT_CONFIG_NAMES:
            if (base / name).exists():
                raw = _read_yaml(base / name)
                source = str(base / name)
                break

    try:
        file_cfg = RewindConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(_format_validation_error(e, source)) from e

    # Environment layer.
    merged = file_cfg.model_dump(mode="json")
    for key, cfg_path in _ENV_KEYS.items():
        if key in env:
            _set_path(merged, cfg_path, env[key])
    try:
        env_cfg = RewindConfig.model_validate(merged)
    except ValidationError as e:
        raise ConfigError(_format_validation_error(e, "environment variables")) from e
    if file_cfg.mode == "enforce" and env_cfg.mode == "audit_only":
        raise ConfigError(
            "REWIND_MODE=audit_only cannot relax a config file that sets mode: enforce. "
            "Change rewind.yaml instead."
        )

    if cli_overlay is not None:
        env_cfg = apply_overlay(env_cfg, cli_overlay, actor_role=None)
    return env_cfg


def _approval_relaxations(base: ApprovalPolicy, new: ApprovalPolicy, label: str) -> list[str]:
    out: list[str] = []
    if base.mode == "n_of_m" and new.mode == "any_one":
        out.append(f"{label}: approval mode n_of_m -> any_one")
    if new.n < base.n:
        out.append(f"{label}: required approvals {base.n} -> {new.n}")
    if new.timeout_minutes > base.timeout_minutes:
        out.append(f"{label}: timeout {base.timeout_minutes} -> {new.timeout_minutes} minutes")
    if base.veto and not new.veto:
        out.append(f"{label}: veto disabled")
    if base.separation_of_duties and not new.separation_of_duties:
        out.append(f"{label}: separation of duties disabled")
    added = set(new.eligible_roles) - set(base.eligible_roles)
    if added:
        out.append(f"{label}: eligible roles widened by {sorted(added)}")
    return out


def relaxations(
    base: RewindConfig,
    new: RewindConfig,
    pack_rule_risk: Mapping[str, RiskClass] | None = None,
) -> list[str]:
    """List every way ``new`` is less strict than ``base`` (empty = tighten-only)."""
    out: list[str] = []
    if base.mode == "enforce" and new.mode == "audit_only":
        out.append("mode enforce -> audit_only")
    if base.escalate_reversible and not new.escalate_reversible:
        out.append("escalate_reversible disabled")
    for risk in RiskClass:
        out += _approval_relaxations(
            base.approval.for_risk(risk), new.approval.for_risk(risk), f"approval[{risk.value}]"
        )
    base_ov = {o.rule_id: o.risk for o in base.policies.overrides}
    for o in new.policies.overrides:
        reference = base_ov.get(o.rule_id)
        if reference is None and pack_rule_risk is not None:
            reference = pack_rule_risk.get(o.rule_id)
        if reference is not None and risk_rank(o.risk) < risk_rank(reference):
            out.append(f"rule {o.rule_id}: {reference.value} -> {o.risk.value}")
    removed = set(base_ov) - {o.rule_id for o in new.policies.overrides}
    for rid in sorted(removed):
        out.append(f"rule {rid}: override removed")
    return out


def apply_overlay(
    base: RewindConfig,
    overlay: PolicyOverlay,
    *,
    actor_role: str | None,
    pack_rule_risk: Mapping[str, RiskClass] | None = None,
) -> RewindConfig:
    """Apply a session/CLI overlay. Tighten-only unless admin + override_reason."""
    data = base.model_dump(mode="json")
    if overlay.mode is not None:
        data["mode"] = overlay.mode
    if overlay.escalate_reversible:
        data["escalate_reversible"] = True

    ov = {o["rule_id"]: o for o in data["policies"]["overrides"]}
    for r in overlay.rule_overrides:
        ov[r.rule_id] = r.model_dump(mode="json")
    data["policies"]["overrides"] = list(ov.values())

    by_risk = data["approval"]["by_risk"]
    for risk, patch in overlay.approval.items():
        current = dict(by_risk.get(risk.value) or {})
        current.update({k: v for k, v in patch.model_dump(mode="json").items() if v is not None})
        by_risk[risk.value] = current
    try:
        ApprovalConfig.model_validate(data["approval"])
        new = RewindConfig.model_validate(data)
    except ValidationError as e:
        raise ConfigError(_format_validation_error(e, "overlay")) from e

    relaxed = relaxations(base, new, pack_rule_risk)
    if relaxed:
        if actor_role != "admin":
            raise ConfigError(
                "Overrides may only tighten policy. Refused relaxations: " + "; ".join(relaxed)
            )
        if not overlay.override_reason:
            raise ConfigError(
                "Relaxing policy requires override_reason. Relaxations: " + "; ".join(relaxed)
            )
    return new


def config_hash(cfg: RewindConfig) -> str:
    """Stable SHA-256 of the effective config (logged to the audit log at start)."""
    canonical = json.dumps(cfg.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_file_permissions(paths: list[Path], agent_os_user: str | None) -> list[str]:
    """Warn if config/policy/data paths are world-writable or agent-writable.

    POSIX only. On Windows, ACLs cannot be checked portably, so a single
    warning is returned telling the operator to verify ACLs manually.
    """
    warnings: list[str] = []
    if sys.platform == "win32":
        return [
            "File-permission check is not supported on Windows; verify manually that the "
            "agent's OS user cannot write rewind.yaml, policy directories or the data dir."
        ]
    agent_uid: int | None = None
    agent_gids: set[int] = set()
    if agent_os_user:
        try:
            import grp
            import pwd

            pw = pwd.getpwnam(agent_os_user)
            agent_uid = pw.pw_uid
            agent_gids = {pw.pw_gid} | {
                g.gr_gid for g in grp.getgrall() if agent_os_user in g.gr_mem
            }
        except KeyError:
            warnings.append(f"agent_os_user {agent_os_user!r} does not exist on this host")

    to_check: list[Path] = []
    for p in paths:
        if not p.exists():
            continue
        to_check.append(p)
        if p.is_dir():
            to_check.extend(p.rglob("*"))
    for p in to_check:
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_mode & stat.S_IWOTH:
            warnings.append(f"{p} is world-writable")
        if agent_uid is not None:
            if st.st_uid == agent_uid and st.st_mode & stat.S_IWUSR:
                warnings.append(f"{p} is owned and writable by agent user {agent_os_user}")
            elif st.st_gid in agent_gids and st.st_mode & stat.S_IWGRP:
                warnings.append(f"{p} is group-writable by a group of agent user {agent_os_user}")
    return warnings
