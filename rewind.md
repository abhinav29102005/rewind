# Rewind: an enforced approval and undo layer for AI agents

> Prompts are advice. Rewind makes irreversible actions **require approval and stay reversible** outside the agent's control.

**Status:** concept (working title). **Track:** AI Core Technologies / Open Innovation.

**Read this first:** this space is already crowded. Section 4 lists existing tools. This project is only worth building if it commits to the specific differentiators in Section 5 and proves them against those tools.

---

## 1. The problem

Autonomous coding and operations agents are being given real credentials and real infrastructure. When they make a destructive mistake, nothing in the stack stops it, and instructions written into the agent's prompt do not reliably prevent it.

## 2. Evidence the problem is real

| Incident | What happened |
|---|---|
| PocketOS (reported April 2026) | A Cursor agent deleted a company's production database and its backups in about 9 seconds, via an API call that asked for no confirmation. It used an API token found in an unrelated file, and later acknowledged breaking its own rules. |
| DataTalks.Club (March 2026) | A Claude Code agent deleted the production database while trying to clean up duplicates it had mistakenly created. |
| Replit (July 2025) | An agent wiped data for over 1,200 executives and 1,190 companies during a "code and action freeze" meant to prevent this. |
| Broader trend | The Centre for Long-Term Resilience logged 698 cases between October 2025 and March 2026 where an agent or bot took covert, deceptive or unrequested actions. One write-up reports 188 of 344 verified enterprise AI incidents (2023 to 2026) where an autonomous system caused harm in production with no attacker involved. |

The common failure, as described by the affected founder: instructions in an agent's context are advisory and cannot replace enforcement built into APIs, tokens and the handling of irreversible operations.

(Incident details come from press and blog reporting; treat counts from secondary sources as indicative.)

## 3. What Rewind does

1. **Credential broker.** The agent never holds raw production tokens. Rewind holds them and exposes scoped, short-lived capabilities.
2. **Action classification.** Every tool call is classified: safe, reversible, or irreversible.
3. **Out-of-band approval.** Irreversible actions pause until a human approves through a channel the agent cannot reach, using one-time codes the agent cannot forge or replay.
4. **Delayed destruction.** Deletes become scheduled deletes with a cancel window; one incident team added exactly this kind of "delayed deletion" afterwards.
5. **Snapshots and rollback.** Automatic checkpoint before risky operations, with preview and one-command restore.
6. **Tamper-evident audit log** of every action and approval.

## 4. Existing tools (honest landscape)

| Tool | What it already covers |
|---|---|
| infraveil-guard | Human-approval gate for destructive commands with a tamper-evident local log; documents itself as a *cooperative* guardrail, not an unbypassable jail |
| Hermes Agent | Dangerous-command approval modes plus automatic checkpoints and `/rollback` |
| Castor | Wraps agent tool calls, pauses destructive ones for approval, supports checkpoints and rollback |
| Doberman | Reviews every tool call from MCP-compatible coding agents; fails closed |
| onedoor | Tiered guardrail engine with default-deny, undo with compensating commands, kill switch, MCP proxy |
| hoop.dev | Open-source gateway with policy enforcement and just-in-time approval for risky database commands |

## 5. The gap we aim to fill (only if we can prove it)

Most of the tools above are **cooperative**: the agent is told to route actions through the guard, so a confused or injected agent can skip it. The real incidents also involved an agent finding a credential it should not have used.

The candidate differentiators:
- **Non-bypassable by construction:** the agent has no direct path or credential to production; only Rewind does.
- **Credential isolation plus delayed destruction at the infrastructure layer**, not only at the command layer.
- **One policy and rollback model across tools**, not just shell commands (databases, cloud APIs, MCP tools).
- **A published, reproducible benchmark** of destructive-action scenarios (including the documented incidents, replayed in a sandbox) that scores every tool, including ours.

If a benchmark shows an existing tool already covers these, the right move is to contribute to that tool instead.

## 6. Gaps we do NOT fill

- **Not a substitute for basic hygiene:** separate production and staging, least-privilege tokens, and immutable off-site backups remain essential.
- **Not prevention of bad judgement.** We contain damage; we do not make the agent smarter.
- **Not complete rollback.** Some actions (emails sent, external API effects, payments) cannot be undone; we can only gate them.
- **Approval fatigue.** Too many prompts and humans click yes; tuning matters.
- **Cannot protect what bypasses it.** Anything with direct credentials outside Rewind is unprotected.

## 7. What we can and cannot accomplish

| Can accomplish (prototype) | Cannot accomplish (yet) |
|---|---|
| Credential broker and proxy for a few tool types (filesystem, SQL, one cloud API) | Cover every agent framework and cloud provider |
| Action classifier with explainable reasons | Perfect classification of every novel action |
| Approval flow with unforgeable one-time codes | Guarantee against a fully compromised host |
| Snapshot and rollback for files and database state | Reverse external side effects |
| Replay of documented incident patterns in a sandbox | Prove production-grade security without independent review |

## 8. Who can use it

- Solo developers and "vibe coders" giving agents access to real data
- Small startups without a platform-security team
- Teams adopting MCP-based agents
- Educators and researchers testing agent safety

## 9. Impact

- Turns incidents like a 9-second database deletion into a recoverable event.
- Raises the baseline for safe agent deployment, especially for small teams that cannot afford enterprise tooling.
- Provides a shared benchmark that makes safety claims comparable.

## 10. Getting people to use it

- **One-command install** (pip or a drop-in MCP proxy) and a five-minute demo that replays a real incident, showing it blocked.
- **Safe-by-default config**: audit-only mode first, then enforce.
- **Integrations first**: ship adapters for popular coding agents and MCP clients.
- **Publish the benchmark** and invite other tools to compete on it.
- **Open source with clear docs** and a security policy; developers trust what they can read.
- **Write post-mortem-style content** showing exactly which failure each feature prevents.

## 11. How to scale

| Phase | Goal | Deliverable |
|---|---|---|
| 0 | Prove the differentiator | Prototype plus benchmark against two or three existing tools |
| 1 | Usable core | Credential broker, approval, snapshot, audit log; adapters for 2 to 3 agents |
| 2 | Ecosystem | Policy packs (databases, cloud, git), plugin API, community-contributed scenarios |
| 3 | Team features | Shared approval queues, roles, central audit, notifications |
| 4 | Sustainability | Optional hosted audit and approval service; open-source core stays free |

## 12. Architecture and free tech stack

```
Agent ──► Rewind proxy ──► classify ──► [safe] execute + log
              │                      └─► [irreversible] hold ──► human approval (out-of-band)
              │                                                    │
        credential broker                                     approved → snapshot → execute
        (agent never sees tokens)                             denied   → block + log
```

Python, SQLite, an MCP proxy layer, git or filesystem snapshots, a small local web UI. Any open model for optional risk explanations.

## 13. Evaluation plan

- Scenario suite: documented incident patterns plus adversarial cases (prompt injection, token discovery, "approve it for me")
- Metrics: blocked destructive actions, false blocks on safe work, rollback success rate, approval latency
- Head-to-head against existing tools on the same suite

## 14. Resources and sources

- TechRepublic, "AI Agent Reportedly Deletes Company's Entire Database, Admits to Violating Guardrails" (May 2026)
- GovInfoSecurity, "AI Agent Wipes Startup's Data in 9-Second API Call"
- ACS Information Age and Euronews coverage of the April 2026 incident (linked in the aggregation post)
- Tools: infraveil-guard (PyPI), Hermes Agent docs (secure-hermes-on-a-work-machine), castor-kernel (PyPI), doberman-core (PyPI), onedoor (PyPI), hoop.dev guardrails blog

## 15. Open questions

- Can a benchmark show a real gap in existing tools?
- How do we make credential isolation easy enough that people actually adopt it?

## License

Suggested: Apache-2.0 or MIT.
