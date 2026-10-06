<p align="center">
  <h1 align="center">🔄 Rewind</h1>
  <p align="center">
    <strong>An enforced approval and undo layer for AI agents</strong>
  </p>
  <p align="center">
    Prompts are advice. Rewind makes irreversible actions <b>require approval and stay reversible</b> — outside the agent's control.
  </p>
  <p align="center">
    <a href="#quickstart">Quickstart</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#benchmark">Benchmark</a> •
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

> **Status:** Concept / Early Development  
> **License:** Apache-2.0 (proposed)

## The Problem

Autonomous AI agents (Cursor, Claude Code, Replit Agent, etc.) are routinely given real credentials and real infrastructure access. When they make a destructive mistake — and [they do](#why-this-matters) — nothing in the stack stops them. Instructions in the agent's prompt are **advisory**, not enforceable.

### Why This Matters

| Incident | What Happened |
|---|---|
| **PocketOS** (Apr 2026) | A Cursor agent deleted a production database and its backups in ~9 seconds, using an API token found in an unrelated file. |
| **DataTalks.Club** (Mar 2026) | A Claude Code agent deleted the production database while trying to clean up duplicates it had mistakenly created. |
| **Replit** (Jul 2025) | An agent wiped data for 1,200+ executives and 1,190 companies during a "code and action freeze" meant to prevent this. |

The Centre for Long-Term Resilience logged **698 cases** (Oct 2025 – Mar 2026) of agents taking covert, deceptive, or unrequested actions.

## How It Works

```
Agent ──► Rewind Proxy ──► Classify ──► [safe]         → execute + log
              │                     └──► [reversible]   → snapshot → execute + log
              │                     └──► [irreversible] → hold ──► human approval (out-of-band)
              │                                                        │
        Credential Broker                                   approved → snapshot → execute
        (agent never sees tokens)                           denied   → block + log
```

The agent **never** holds raw production credentials. Rewind sits between the agent and your infrastructure, holding tokens and exposing scoped, short-lived capabilities. A confused or prompt-injected agent literally cannot bypass what it cannot reach.

## Features

| Feature | Description |
|---|---|
| 🔐 **Credential Broker** | Agent never sees raw production tokens. Rewind holds them and exposes scoped, short-lived capabilities. |
| 🏷️ **Action Classification** | Every tool call is classified as `safe`, `reversible`, or `irreversible` with explainable reasons. |
| ✋ **Out-of-Band Approval** | Irreversible actions pause until a human approves through a channel the agent cannot reach, using unforgeable one-time codes. |
| ⏳ **Delayed Destruction** | Deletes become scheduled deletes with a configurable cancel window. |
| 📸 **Snapshots & Rollback** | Automatic checkpoints before risky operations. Preview diffs and one-command restore. |
| 📋 **Tamper-Evident Audit Log** | Cryptographically chained log of every action, approval, and rollback. |

## What Makes Rewind Different

Most existing guardrail tools are **cooperative** — the agent is told to route actions through the guard, so a confused or injected agent can skip it. Rewind's differentiators:

- **Non-bypassable by construction** — the agent has no direct path or credential to production
- **Credential isolation + delayed destruction at the infrastructure layer**, not only at the command layer
- **One policy and rollback model across tools** — databases, cloud APIs, MCP tools, filesystems
- **A published, reproducible benchmark** of destructive-action scenarios to score every tool, including ours

## Quickstart

> ⚠️ **Coming soon** — the project is in early development.

```bash
# Install (planned)
pip install rewind-guard

# Or use as a drop-in MCP proxy
rewind proxy --config rewind.yaml

# Run the incident-replay demo
rewind demo --scenario pocketos
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Storage | SQLite (audit log, state) |
| Proxy | MCP-compatible proxy layer |
| Snapshots | Git / filesystem-level snapshots |
| UI | Local web dashboard |
| AI (optional) | Any open model for risk explanations |

## Honest Landscape

We acknowledge the existing tools in this space and commit to benchmarking against them:

| Tool | Overlap |
|---|---|
| infraveil-guard | Approval gate + tamper-evident log (cooperative) |
| Hermes Agent | Approval modes + checkpoints + rollback |
| Castor | Tool-call wrapping, approval, checkpoints |
| Doberman | Fail-closed tool-call review for MCP agents |
| onedoor | Default-deny, undo, kill switch, MCP proxy |
| hoop.dev | Policy enforcement + JIT approval for DB commands |

> **If benchmarking shows an existing tool already covers our differentiators, the right move is to contribute to that tool instead.**

## Who Is This For

- 🧑‍💻 Solo developers and "vibe coders" giving agents access to real data
- 🚀 Small startups without a platform-security team
- 🔌 Teams adopting MCP-based agents
- 🎓 Educators and researchers testing agent safety

## What Rewind Does NOT Do

- **Not a substitute for basic hygiene** — separate prod/staging, least-privilege tokens, and off-site backups remain essential
- **Not prevention of bad judgement** — we contain damage; we don't make the agent smarter
- **Not complete rollback** — emails sent, external API effects, and payments cannot be undone; we can only gate them
- **Cannot protect what bypasses it** — anything with direct credentials outside Rewind is unprotected

## Benchmark

The evaluation suite (planned) will include:

- **Incident replays** — documented real-world incidents reproduced in a sandbox
- **Adversarial scenarios** — prompt injection, token discovery, "approve it for me" attacks
- **Metrics** — blocked destructive actions, false blocks on safe work, rollback success rate, approval latency
- **Head-to-head** comparisons against existing tools on the same suite

## Contributing

We welcome contributions! Whether it's adding new tool adapters, scenario definitions for the benchmark, or improving the core proxy — see the [Development Plan](PLAN.md) for the roadmap and where help is most needed.

```bash
git clone https://github.com/your-org/rewind.git
cd rewind
# Setup instructions coming soon
```

## License

Apache-2.0 (proposed)

---

<p align="center">
  <i>Turning 9-second database deletions into recoverable events.</i>
</p>
