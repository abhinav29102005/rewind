# Threat Model & Limitations

A rigorous guardrail layer must clearly document what it protects, what it does not protect, and what assumptions must hold for guarantees to remain valid.

---

## 1. Protected Threats

Rewind is designed to defend against:

1. **Reckless Agent Execution**: Accidental destructive commands executed by autonomous agents (e.g., `DELETE FROM table;`, `DROP DATABASE;`, `rm -rf /`, `docker system prune -a`).
2. **Prompt Injection & Tool Abuse**: Attackers injecting malicious instructions into agent context (via untrusted documents, issues, or web scraping) that command the agent to delete backups, tamper with configurations, or escalate privileges.
3. **Misleading Stated Justifications**: Agents supplying deceptive `reason` fields (e.g. claiming "Routine backup maintenance" while running `DROP TABLE`) are evaluated purely on the AST/tokens of the actual payload, completely ignoring agent explanations.
4. **Approval Code Replay & Tampering**:
   * One-time approval codes are cryptographically bound to the SHA-256 hash of the exact tool call parameters. If parameters change, the code is invalid.
   * Single-use OTPs expire and cannot be replayed.
   * Session initiators cannot vote on their own actions (Separation of Duties).
5. **Silent State Tampering**:
   * All decisions and system events are appended to a SHA-256 hash-chained audit ledger ($H_i = \text{SHA256}(H_{i-1} \parallel \text{entry}_i)$). Any modification, deletion, or reordering of historical records breaks cryptographic verification.

---

## 2. Mandatory Trust Assumptions

For Rewind's security guarantees to hold, the host environment must enforce the following boundaries:

1. **No Direct Credentials**: The AI agent **must not** possess direct API credentials, database passwords, or AWS keys. All tool calls must route through the Rewind MCP Server or Shell Proxy, which injects credentials only after approval.
2. **No Out-of-Band Network Access**: The agent sandbox must block direct egress to protected databases and cloud APIs. If an agent can reach the database port directly without going through Rewind's proxy, Rewind cannot enforce policy.
3. **Configuration & Code Immutability**:
   * The `rewind.yaml` configuration file and policy packs **must not be writable** by the agent process.
   * Session and CLI overlays are strictly **tighten-only**; any relaxation requires administrative privileges and an audit reason.
4. **Trusted Approver Channels**:
   * Approver identity is trusted via authenticated sessions and API tokens.
   * One-time approval codes are never transmitted to shared communication channels (e.g. Slack/Discord channels) where untrusted agents or unauthorized observers could read them.

---

## 3. Known Limitations & Non-Goals

1. **In-Process Python Plugins**: Plugins run in-process without memory or capability sandboxing. Plugins are considered trusted extensions. Malicious plugins could compromise the host runtime.
2. **Policy Incompleteness & Novel Destruction**:
   * Policy packs classify known patterns. Novel or obscure destructive operations not matched by policy fall back to `default_risk` (`irreversible`).
   * Over-classification can lead to human approval fatigue.
3. **Latency of Consensus (N-of-M)**:
   * Multi-human voting requires out-of-band communication and introduces latency. If notification channels fail or approvers are unavailable, the action remains **held or denied**. Rewind never fails open to avoid blocking workflows.
4. **Data Exfiltration / Passive Leaks**:
   * Rewind is an **execution gatekeeper and rollback layer**, not an outbound DLP (Data Loss Prevention) filter. While read actions (`SELECT`, `cat`, `ls`) are classified as `safe`, an agent could theoretically leak sensitive read data through conversational output if sandbox network isolation is absent.
