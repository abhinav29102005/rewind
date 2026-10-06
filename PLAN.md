# Rewind — Development Plan

> A phased roadmap for building an enforced approval and undo layer for AI agents.

---

## Guiding Principles

1. **Prove before building** — validate the differentiator with a benchmark before investing in features.
2. **Ship early, scope small** — each phase delivers a usable, testable artifact.
3. **Honest evaluation** — if an existing tool covers our gaps, contribute upstream instead.
4. **Safe defaults** — audit-only mode first, enforcement second.

---

## Phase 0 — Prove the Differentiator

**Goal:** Demonstrate that credential isolation + non-bypassable approval fills a real gap that cooperative guardrails do not.

**Duration:** 2–3 weeks

### Deliverables

| # | Task | Details | Exit Criteria |
|---|---|---|---|
| 0.1 | **Project scaffold** | Python package structure, `pyproject.toml`, dev tooling (ruff, pytest, mypy), CI skeleton | `pip install -e .` works, linter and tests pass (zero tests is fine) |
| 0.2 | **Incident replay sandbox** | Docker Compose environment simulating the PocketOS scenario: a fake database, a leaked API token in a file, and a scripted "agent" that finds and uses it | Scripted agent successfully destroys the sandbox database in <10 seconds |
| 0.3 | **Minimal Rewind proxy** | Intercept the destructive call, block it, log it. No approval flow yet — just a hard block on classified-irreversible actions | Same scripted agent run with Rewind proxy: destructive call is blocked, logged, sandbox survives |
| 0.4 | **Benchmark v0** | Run the same scenario against 2–3 existing tools (infraveil-guard, Castor, onedoor). Document: does the cooperative tool stop the agent when the agent doesn't use it? | Written comparison table with pass/fail per tool per scenario |
| 0.5 | **Decision gate** | Review benchmark results. If an existing tool passes all scenarios, pivot to contributing to that tool. | Go/no-go decision documented |

### Milestone: Benchmark report published, go/no-go decision made.

---

## Phase 1 — Usable Core

**Goal:** A working system that a developer can install and use with a real agent.

**Duration:** 4–6 weeks

### 1A — Credential Broker

| # | Task | Details |
|---|---|---|
| 1A.1 | **Credential vault** | Encrypted local store (SQLite + `cryptography` library) for production tokens. Agent process has no read access to the vault file. |
| 1A.2 | **Scoped capability tokens** | Rewind issues short-lived, scoped tokens to the agent. Tokens carry only the permissions needed for the current task and expire after use or timeout. |
| 1A.3 | **Token revocation** | Immediate revocation on: approval denial, session end, or anomaly detection. |

### 1B — Action Classification Engine

| # | Task | Details |
|---|---|---|
| 1B.1 | **Rule-based classifier** | Pattern matching on tool calls: `DROP`, `DELETE`, `rm -rf`, destructive API verbs. Classifies as `safe` / `reversible` / `irreversible`. |
| 1B.2 | **Plugin classifier interface** | Abstract base class so adapters can provide tool-specific classification (e.g., a Postgres adapter knows `TRUNCATE` is irreversible). |
| 1B.3 | **Explanation output** | Each classification includes a human-readable reason string (e.g., "SQL statement contains DROP TABLE on a production-flagged database"). |
| 1B.4 | **Optional LLM classifier** | For ambiguous actions, optionally call a local/open model to assess risk. Fail-safe: if the model is uncertain, classify as irreversible. |

### 1C — Approval Flow

| # | Task | Details |
|---|---|---|
| 1C.1 | **Out-of-band approval channel** | Local web UI served on a separate port. Agent process has no access to this port. |
| 1C.2 | **One-time approval codes** | HMAC-based, time-limited, single-use codes. Agent cannot forge or replay. |
| 1C.3 | **Approval queue** | Pending actions shown with: tool call details, classification reason, associated snapshot ID, approve/deny buttons. |
| 1C.4 | **Timeout policy** | Configurable auto-deny after N minutes of no response. |

### 1D — Snapshot & Rollback

| # | Task | Details |
|---|---|---|
| 1D.1 | **Filesystem snapshots** | Git-based: auto-commit to a shadow repo before any reversible/irreversible action. |
| 1D.2 | **Database snapshots** | `pg_dump` / SQLite `.backup()` before destructive DB operations. |
| 1D.3 | **Diff preview** | Show what changed since the last snapshot (file diffs, DB schema/row diffs). |
| 1D.4 | **One-command rollback** | `rewind rollback <snapshot-id>` restores files and/or database state. |

### 1E — Audit Log

| # | Task | Details |
|---|---|---|
| 1E.1 | **Append-only SQLite log** | Every event: action received, classification, approval request/response, execution result, rollback. |
| 1E.2 | **Hash chain** | Each log entry includes a SHA-256 hash of the previous entry. Tamper detection on startup. |
| 1E.3 | **Log viewer** | CLI command `rewind log` and web UI tab showing the full audit trail. |

### 1F — Agent Adapters (pick 2–3)

| # | Task | Details |
|---|---|---|
| 1F.1 | **MCP proxy adapter** | Drop-in MCP server that wraps any downstream MCP tool server. Transparent to the agent. |
| 1F.2 | **CLI wrapper adapter** | `rewind exec -- <command>` that intercepts shell commands. |
| 1F.3 | **Python SDK adapter** | Decorator / context manager for Python-based agents: `with rewind.guard():` |

### Milestone: A developer can `pip install rewind-guard`, configure credentials, and run their MCP agent through Rewind with approval and rollback working.

---

## Phase 2 — Ecosystem & Policy Packs

**Goal:** Broad coverage of common tools, community-contributed scenarios, and a plugin API.

**Duration:** 4–6 weeks

| # | Task | Details |
|---|---|---|
| 2.1 | **Policy packs** | Pre-built classification rules for: PostgreSQL, MySQL, AWS S3, AWS IAM, GCP, Git (force-push, branch-delete), Docker, Kubernetes. Shipped as YAML/JSON config files. |
| 2.2 | **Plugin API** | Formal plugin interface: custom classifiers, custom snapshot backends, custom approval channels (Slack, email, SMS). |
| 2.3 | **Benchmark v1** | Expanded scenario suite: 10+ scenarios including adversarial (prompt injection, privilege escalation, social engineering for approval). Head-to-head against all tools from Section 4. |
| 2.4 | **Community scenario format** | YAML schema for defining destructive-action test scenarios. CLI command to run a scenario: `rewind bench run <scenario.yaml>`. |
| 2.5 | **Configuration system** | `rewind.yaml` with: global policies, per-tool overrides, approval channel config, snapshot retention, auto-deny timeout. |
| 2.6 | **Documentation site** | mkdocs or similar: getting started, configuration reference, adapter guides, scenario authoring guide, architecture deep-dive. |

### Milestone: Policy packs for 5+ tool types. Plugin API stable. Benchmark v1 published.

---

## Phase 3 — Team Features

**Goal:** Multi-user support for teams and organizations.

**Duration:** 4–6 weeks

| # | Task | Details |
|---|---|---|
| 3.1 | **Shared approval queues** | Multiple team members can approve/deny actions. Configurable: any-one-approves vs. N-of-M approval. |
| 3.2 | **Role-based access** | Roles: admin (configure policies), approver (approve/deny), viewer (read audit log). |
| 3.3 | **Notifications** | Slack, Discord, email, and webhook notifications for pending approvals and blocked actions. |
| 3.4 | **Central audit dashboard** | Aggregated view across all team members' agent sessions. Filter by agent, user, action type, time range. |
| 3.5 | **Session management** | Named sessions with per-session policies. `rewind session start --policy strict` |

### Milestone: A 3–5 person team can share an approval queue with role-based access and a central audit view.

---

## Phase 4 — Sustainability

**Goal:** Long-term viability through optional hosted services while keeping the core open-source and free.

**Duration:** Ongoing

| # | Task | Details |
|---|---|---|
| 4.1 | **Hosted audit service** | Optional cloud storage for audit logs with long-term retention, search, and compliance exports. |
| 4.2 | **Hosted approval service** | Optional managed approval channel with mobile push notifications and SSO. |
| 4.3 | **Enterprise features** | SAML/OIDC SSO, audit log export to SIEM, compliance reports. |
| 4.4 | **Open-source sustainability** | Core remains Apache-2.0. Hosted services fund development. Contributor guide, security policy, responsible disclosure process. |

### Milestone: Sustainable project with clear open-core boundary.

---

## Project Structure (Target)

```
rewind/
├── pyproject.toml
├── README.md
├── PLAN.md
├── rewind.md                    # Original concept doc
├── rewind.yaml.example          # Example configuration
├── src/
│   └── rewind/
│       ├── __init__.py
│       ├── cli.py               # CLI entry point
│       ├── proxy/
│       │   ├── __init__.py
│       │   ├── mcp.py           # MCP proxy adapter
│       │   └── shell.py         # Shell command wrapper
│       ├── broker/
│       │   ├── __init__.py
│       │   ├── vault.py         # Credential storage
│       │   └── tokens.py        # Scoped capability tokens
│       ├── classifier/
│       │   ├── __init__.py
│       │   ├── engine.py        # Classification engine
│       │   ├── rules.py         # Rule-based classifier
│       │   └── llm.py           # Optional LLM classifier
│       ├── approval/
│       │   ├── __init__.py
│       │   ├── codes.py         # One-time approval codes
│       │   ├── queue.py         # Approval queue
│       │   └── web.py           # Local approval web UI
│       ├── snapshot/
│       │   ├── __init__.py
│       │   ├── git.py           # Git-based file snapshots
│       │   ├── database.py      # Database snapshots
│       │   └── rollback.py      # Rollback orchestration
│       ├── audit/
│       │   ├── __init__.py
│       │   ├── log.py           # Append-only audit log
│       │   └── chain.py         # Hash chain verification
│       └── plugins/
│           ├── __init__.py
│           └── base.py          # Plugin interface
├── policies/
│   ├── postgresql.yaml
│   ├── mysql.yaml
│   ├── aws_s3.yaml
│   └── filesystem.yaml
├── benchmark/
│   ├── scenarios/
│   │   ├── pocketos_replay.yaml
│   │   ├── datatalks_replay.yaml
│   │   └── prompt_injection.yaml
│   ├── runner.py
│   └── report.py
├── tests/
│   ├── test_classifier.py
│   ├── test_broker.py
│   ├── test_approval.py
│   ├── test_snapshot.py
│   └── test_audit.py
├── docker/
│   └── docker-compose.yaml      # Sandbox environment
└── docs/
    ├── getting-started.md
    ├── configuration.md
    ├── adapters.md
    └── architecture.md
```

---

## Key Decisions to Make

| Decision | Options | Recommendation |
|---|---|---|
| **Package name** | `rewind-guard`, `rewind-ai`, `rewindctl` | `rewind-guard` (clear, available on PyPI — verify) |
| **MCP protocol version** | Latest stable | Pin to a specific version, test against it |
| **Snapshot backend** | Git, filesystem copy, ZFS/Btrfs, LVM | Git for Phase 1 (universally available), optional advanced backends in Phase 2 |
| **Approval channel** | Local web UI, CLI prompt, Slack, email | Local web UI for Phase 1 (zero external deps), plugins for others in Phase 2 |
| **Database support** | SQLite-only vs. Postgres/MySQL | SQLite for Rewind's own storage; snapshot/rollback adapters for Postgres + SQLite targets in Phase 1 |
| **License** | Apache-2.0, MIT | Apache-2.0 (patent protection for contributors) |

---

## Success Metrics

| Metric | Phase 0 | Phase 1 | Phase 2 |
|---|---|---|---|
| Benchmark scenarios | 3 | 5 | 10+ |
| Destructive actions blocked | 100% of known patterns | 100% of known + classifier coverage | 100% + adversarial |
| False block rate | Not measured | <5% on safe operations | <2% |
| Rollback success rate | N/A | >95% for files + SQLite | >95% for all supported backends |
| Install-to-first-block time | N/A | <5 minutes | <5 minutes |
| Tools benchmarked against | 2–3 | 3–4 | All from Section 4 |

---

## Open Questions (from concept doc)

1. **Can a benchmark show a real gap in existing tools?** → Phase 0 answers this.
2. **How do we make credential isolation easy enough that people actually adopt it?** → Phase 1 UX focus.
3. **Name collision?** → Need to verify `rewind` / `rewind-guard` availability on PyPI.
4. **MCP ecosystem maturity** — is the protocol stable enough to build a proxy against?

---

*Last updated: 2026-10-06*
