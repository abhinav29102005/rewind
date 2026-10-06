# Configuration Reference (`rewind.yaml`)

This configuration reference is **automatically generated** from Rewind's Pydantic v2 schemas (`rewind.config.models`).

Rewind validates configuration strictly using `extra='forbid'`. Unknown keys or schema violations cause Rewind to **fail closed** immediately.

## Top-Level Schema

### RewindConfig

Root configuration file structure for `rewind.yaml`.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `version` | `Literal[1]` | `1` |  |
| `mode` | `Literal['audit_only', 'enforce']` | `"enforce"` |  |
| `data_dir` | `Path` | `data` |  |
| `policies` | `PoliciesConfig` | `packs=['filesystem', 'postgresql', 'git', 'aws_s3', 'docker'] paths=[] overrides=[]` |  |
| `approval` | `ApprovalConfig` | `default=ApprovalPolicy(mode='any_one', n=1, timeout_minutes=15, eligible_roles=['approver', 'admin'], veto=True, separation_of_duties=True) by_risk={}` |  |
| `snapshots` | `SnapshotsConfig` | `retention_hours=72 backend_priority=['git', 'sqlite', 'pg_dump']` |  |
| `notifications` | `NotificationsConfig` | `channels=[] max_attempts=5 dedupe_window_seconds=300` |  |
| `plugins` | `PluginsConfig` | `enabled=[] classifier_timeout_seconds=2.0` |  |
| `sessions` | `SessionsConfig` | `max_duration_hours=8 idle_timeout_minutes=60 profiles={'default': PolicyOverlay(mode=None, escalate_reversible=False, rule_overrides=[], approval={}, override_reason=None), 'strict': PolicyOverlay(mode='enforce', escalate_reversible=True, rule_overrides=[], approval={<RiskClass.IRREVERSIBLE: 'irreversible'>: ApprovalPolicyPatch(mode='n_of_m', n=2, timeout_minutes=None, eligible_roles=None, veto=None, separation_of_duties=None)}, override_reason=None)}` |  |
| `control_plane` | `ControlPlaneConfig` | `host='127.0.0.1' port=8787 public_url=None login_rate_limit_per_minute=10 web_session_hours=8` |  |
| `security` | `SecurityConfig` | `agent_os_user=None` |  |
| `audit` | `AuditConfig` | `redact_payload_fields=['password', 'token', 'secret', 'authorization', 'api_key']` |  |
| `escalate_reversible` | `bool` | `False` |  |

## Policy Configuration

### PoliciesConfig

Configures policy pack loading and individual rule overrides.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `packs` | `list[str]` | `['filesystem', 'postgresql', 'git', 'aws_s3', 'docker']` |  |
| `paths` | `list[Path]` | `[]` |  |
| `overrides` | `list[RuleOverride]` | `[]` |  |

### RuleOverride

Specifies per-rule risk overrides with mandatory audit justification.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `rule_id` | `str` | **required** |  |
| `risk` | `RiskClass` | **required** |  |
| `override_reason` | `str \| None` | `None` |  |

## Approval Policies

### ApprovalConfig

Configures approval behavior per risk classification.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `default` | `ApprovalPolicy` | `mode='any_one' n=1 timeout_minutes=15 eligible_roles=['approver', 'admin'] veto=True separation_of_duties=True` |  |
| `by_risk` | `dict[RiskClass, ApprovalPolicyPatch]` | `{}` |  |

### ApprovalPolicy

Fine-grained consensus requirements (any-one vs. N-of-M, timeout, eligible roles, veto).

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `Literal['any_one', 'n_of_m']` | `"any_one"` |  |
| `n` | `int` | `1` |  |
| `timeout_minutes` | `int` | `15` |  |
| `eligible_roles` | `list[Literal['approver', 'admin']]` | `['approver', 'admin']` |  |
| `veto` | `bool` | `True` |  |
| `separation_of_duties` | `bool` | `True` |  |

### ApprovalPolicyPatch

Partial approval policy overrides layered on top of defaults.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `Literal['any_one', 'n_of_m'] \| None` | `None` |  |
| `n` | `int \| None` | `None` |  |
| `timeout_minutes` | `int \| None` | `None` |  |
| `eligible_roles` | `list[Literal['approver', 'admin']] \| None` | `None` |  |
| `veto` | `bool \| None` | `None` |  |
| `separation_of_duties` | `bool \| None` | `None` |  |

## Session Controls

### SessionsConfig

Configures session lifetimes and tighten-only security profiles.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_duration_hours` | `float` | `8` |  |
| `idle_timeout_minutes` | `int` | `60` |  |
| `profiles` | `dict[str, PolicyOverlay]` | `{'default': PolicyOverlay(mode=None, escalate_reversible=False, rule_overrides=[], approval={}, override_reason=None), 'strict': PolicyOverlay(mode='enforce', escalate_reversible=True, rule_overrides=[], approval={<RiskClass.IRREVERSIBLE: 'irreversible'>: ApprovalPolicyPatch(mode='n_of_m', n=2, timeout_minutes=None, eligible_roles=None, veto=None, separation_of_duties=None)}, override_reason=None)}` |  |

### PolicyOverlay

Tighten-only security profile constraints applied to sessions.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `Literal['audit_only', 'enforce'] \| None` | `None` |  |
| `escalate_reversible` | `bool` | `False` |  |
| `rule_overrides` | `list[RuleOverride]` | `[]` |  |
| `approval` | `dict[RiskClass, ApprovalPolicyPatch]` | `{}` |  |
| `override_reason` | `str \| None` | `None` |  |

## Snapshots

### SnapshotsConfig

State snapshot capture and rollback retention settings.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `retention_hours` | `int` | `72` |  |
| `backend_priority` | `list[str]` | `['git', 'sqlite', 'pg_dump']` |  |

## Audit Logging

### AuditConfig

Cryptographic tamper-evident hash-chained audit ledger settings.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `redact_payload_fields` | `list[str]` | `['password', 'token', 'secret', 'authorization', 'api_key']` |  |

## Notifications

### NotificationsConfig

Notification dispatcher and outgoing communication channels.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `channels` | `list[Annotated[rewind.config.models.SlackChannelConfig \| rewind.config.models.DiscordChannelConfig \| rewind.config.models.WebhookChannelConfig \| rewind.config.models.EmailChannelConfig, FieldInfo(annotation=NoneType, required=True, discriminator='type')]]` | `[]` |  |
| `max_attempts` | `int` | `5` |  |
| `dedupe_window_seconds` | `int` | `300` |  |

### WebhookChannelConfig

HMAC-SHA256 signed HTTP webhook endpoints (`X-Rewind-Signature`).

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str \| None` | `None` |  |
| `events` | `list[Literal['*', 'approval_requested', 'approval_decided', 'action_blocked', 'deletion_pending', 'session_started', 'session_ended', 'config_changed', 'audit_chain_failure']]` | `['*']` |  |
| `rate_limit_per_minute` | `int` | `30` |  |
| `digest_low_severity` | `bool` | `False` |  |
| `direct` | `bool` | `False` |  |
| `type` | `Literal['webhook']` | **required** |  |
| `url_env` | `str` | **required** |  |
| `secret_env` | `str` | **required** |  |

### SlackChannelConfig

Slack Block Kit webhook integration.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str \| None` | `None` |  |
| `events` | `list[Literal['*', 'approval_requested', 'approval_decided', 'action_blocked', 'deletion_pending', 'session_started', 'session_ended', 'config_changed', 'audit_chain_failure']]` | `['*']` |  |
| `rate_limit_per_minute` | `int` | `30` |  |
| `digest_low_severity` | `bool` | `False` |  |
| `direct` | `bool` | `False` |  |
| `type` | `Literal['slack']` | **required** |  |
| `webhook_url_env` | `str` | **required** |  |

### DiscordChannelConfig

Discord embed webhook integration.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str \| None` | `None` |  |
| `events` | `list[Literal['*', 'approval_requested', 'approval_decided', 'action_blocked', 'deletion_pending', 'session_started', 'session_ended', 'config_changed', 'audit_chain_failure']]` | `['*']` |  |
| `rate_limit_per_minute` | `int` | `30` |  |
| `digest_low_severity` | `bool` | `False` |  |
| `direct` | `bool` | `False` |  |
| `type` | `Literal['discord']` | **required** |  |
| `webhook_url_env` | `str` | **required** |  |

### EmailChannelConfig

Direct SMTP email notifications.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str \| None` | `None` |  |
| `events` | `list[Literal['*', 'approval_requested', 'approval_decided', 'action_blocked', 'deletion_pending', 'session_started', 'session_ended', 'config_changed', 'audit_chain_failure']]` | `['*']` |  |
| `rate_limit_per_minute` | `int` | `30` |  |
| `digest_low_severity` | `bool` | `False` |  |
| `direct` | `bool` | `False` |  |
| `type` | `Literal['email']` | **required** |  |
| `smtp_host` | `str` | **required** |  |
| `smtp_port` | `int` | `587` |  |
| `starttls` | `bool` | `True` |  |
| `from_addr` | `str` | **required** |  |
| `to_addrs_env` | `str` | **required** |  |
| `username_env` | `Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[MaxLen(max_length=128), _PydanticGeneralMetadata(pattern='^[A-Z_][A-Z0-9_]*$')])] \| None` | `None` |  |
| `password_env` | `Annotated[str, FieldInfo(annotation=NoneType, required=True, metadata=[MaxLen(max_length=128), _PydanticGeneralMetadata(pattern='^[A-Z_][A-Z0-9_]*$')])] \| None` | `None` |  |

## Control Plane Dashboard

### ControlPlaneConfig

Web UI and local HTTP server settings for human approval queue.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `host` | `str` | `"127.0.0.1"` |  |
| `port` | `int` | `8787` |  |
| `public_url` | `str \| None` | `None` |  |
| `login_rate_limit_per_minute` | `int` | `10` |  |
| `web_session_hours` | `float` | `8` |  |

## Plugins

### PluginsConfig

Plugin loading and isolation settings.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled` | `list[str]` | `[]` |  |
| `classifier_timeout_seconds` | `float` | `2.0` |  |
