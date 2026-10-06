from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rewind.config import ConfigError, PolicyOverlay, apply_overlay, config_hash, load_config
from rewind.config.models import ApprovalPolicyPatch, RewindConfig, RuleOverride
from rewind.contracts import RiskClass

if TYPE_CHECKING:
    from pathlib import Path

EXAMPLE = """
version: 1
mode: enforce
data_dir: ./data
policies:
  packs: [filesystem, postgresql, git, aws_s3, docker]
  paths: [./policies]
  overrides:
    - rule_id: pg-delete-scoped
      risk: irreversible
approval:
  default: { mode: any_one, timeout_minutes: 15 }
  by_risk:
    irreversible: { mode: n_of_m, n: 2, eligible_roles: [approver, admin] }
snapshots:
  retention_hours: 72
  backend_priority: [git, sqlite, pg_dump]
notifications:
  channels:
    - { type: slack, webhook_url_env: REWIND_SLACK_WEBHOOK, events: [approval_requested, action_blocked] }
    - { type: webhook, url_env: REWIND_AUDIT_WEBHOOK, secret_env: REWIND_WEBHOOK_SECRET, events: ["*"] }
plugins:
  enabled: []
"""


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "rewind.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_example_config_loads(tmp_path: Path) -> None:
    cfg = load_config(write(tmp_path, EXAMPLE), env={})
    assert cfg.mode == "enforce"
    irr = cfg.approval.for_risk(RiskClass.IRREVERSIBLE)
    assert irr.mode == "n_of_m" and irr.n == 2 and irr.timeout_minutes == 15
    assert cfg.approval.for_risk(RiskClass.REVERSIBLE).mode == "any_one"


def test_defaults_are_fail_closed(tmp_path: Path) -> None:
    cfg = load_config(env={}, search_dir=tmp_path)
    assert cfg.mode == "enforce"
    assert cfg.control_plane.host == "127.0.0.1"


@pytest.mark.parametrize(
    "bad",
    [
        "mode: permissive\n",
        "version: 2\n",
        "unknown_key: 1\n",
        "approval: { default: { mode: any_one, n: 3 } }\n",
        "approval: { default: { mode: n_of_m, n: 1 } }\n",
        "approval: { default: { eligible_roles: [viewer] } }\n",
        "approval: { default: { timeout_minutes: 0 } }\n",
        "notifications: { channels: [ { type: slack, webhook_url: 'https://hooks.slack.com/x' } ] }\n",
        "notifications: { channels: [ { type: slack, webhook_url_env: 'lower-case' } ] }\n",
        "notifications: { channels: [ { type: sms, number_env: X } ] }\n",
        "notifications: { channels: [ { type: slack, webhook_url_env: X, events: [nope] } ] }\n",
        "policies: { overrides: [ { rule_id: a, risk: irreversible }, { rule_id: a, risk: safe } ] }\n",
        "policies: { overrides: [ { rule_id: a, risk: dangerous } ] }\n",
        "- just\n- a list\n",
        "mode: [unclosed\n",
    ],
)
def test_invalid_config_refuses(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ConfigError) as ei:
        load_config(write(tmp_path, bad), env={})
    assert str(ei.value)  # exact, non-empty error


def test_missing_explicit_file_refuses(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(tmp_path / "nope.yaml", env={})


def test_env_cannot_relax_mode(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="audit_only"):
        load_config(write(tmp_path, "mode: enforce\n"), env={"REWIND_MODE": "audit_only"})


def test_env_can_tighten_mode(tmp_path: Path) -> None:
    cfg = load_config(write(tmp_path, "mode: audit_only\n"), env={"REWIND_MODE": "enforce"})
    assert cfg.mode == "enforce"


def test_env_invalid_value_refuses(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="environment"):
        load_config(write(tmp_path, ""), env={"REWIND_CONTROL_PLANE_PORT": "notaport"})


def test_overlay_tighten_allowed_for_anyone() -> None:
    base = RewindConfig()
    ov = PolicyOverlay(
        escalate_reversible=True,
        approval={RiskClass.IRREVERSIBLE: ApprovalPolicyPatch(mode="n_of_m", n=3)},
    )
    new = apply_overlay(base, ov, actor_role="approver")
    assert new.escalate_reversible
    assert new.approval.for_risk(RiskClass.IRREVERSIBLE).n == 3


@pytest.mark.parametrize(
    "ov",
    [
        PolicyOverlay(mode="audit_only"),
        PolicyOverlay(approval={RiskClass.SAFE: ApprovalPolicyPatch(timeout_minutes=120)}),
        PolicyOverlay(approval={RiskClass.SAFE: ApprovalPolicyPatch(veto=False)}),
        PolicyOverlay(approval={RiskClass.SAFE: ApprovalPolicyPatch(separation_of_duties=False)}),
    ],
)
def test_overlay_relax_refused_for_non_admin(ov: PolicyOverlay) -> None:
    with pytest.raises(ConfigError, match="only tighten"):
        apply_overlay(RewindConfig(), ov, actor_role="approver")


def test_overlay_relax_admin_needs_reason() -> None:
    with pytest.raises(ConfigError, match="override_reason"):
        apply_overlay(RewindConfig(), PolicyOverlay(mode="audit_only"), actor_role="admin")
    new = apply_overlay(
        RewindConfig(),
        PolicyOverlay(mode="audit_only", override_reason="incident drill, ticket OPS-1"),
        actor_role="admin",
    )
    assert new.mode == "audit_only"


def test_rule_override_relax_detected_against_pack() -> None:
    ov = PolicyOverlay(rule_overrides=[RuleOverride(rule_id="pg-drop", risk=RiskClass.SAFE)])
    with pytest.raises(ConfigError):
        apply_overlay(
            RewindConfig(), ov, actor_role="approver",
            pack_rule_risk={"pg-drop": RiskClass.IRREVERSIBLE},
        )


def test_n_of_m_downgrade_is_relaxation() -> None:
    base = apply_overlay(
        RewindConfig(),
        PolicyOverlay(approval={RiskClass.IRREVERSIBLE: ApprovalPolicyPatch(mode="n_of_m", n=2)}),
        actor_role="approver",
    )
    with pytest.raises(ConfigError):
        apply_overlay(
            base,
            PolicyOverlay(approval={RiskClass.IRREVERSIBLE: ApprovalPolicyPatch(mode="any_one", n=1)}),
            actor_role="approver",
        )


def test_config_hash_stable_and_sensitive() -> None:
    a, b = RewindConfig(), RewindConfig()
    assert config_hash(a) == config_hash(b)
    c = RewindConfig(mode="audit_only")
    assert config_hash(a) != config_hash(c)


def test_strict_profile_is_builtin_and_tightening() -> None:
    cfg = RewindConfig()
    strict = cfg.sessions.profiles["strict"]
    new = apply_overlay(cfg, strict, actor_role="approver")
    assert new.escalate_reversible
    assert new.approval.for_risk(RiskClass.IRREVERSIBLE).mode == "n_of_m"
