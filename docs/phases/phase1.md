# Phase 1: Usable Core

**Goal:** A working system that a developer can install and use with a real agent.

## Overview

Phase 1 focuses on building the core components required to run Rewind as a functional guardrail for AI agents. This includes managing credentials, classifying actions, handling the approval flow, and taking snapshots for rollback.

## Key Components

1.  **Credential Broker (`rewind.broker`):**
    *   `Vault`: An encrypted local store for production credentials. (Completed)
    *   `TokenManager`: Issues and validates short-lived, scoped capability tokens (HMAC-signed) to agents. (Completed)

2.  **Action Classification (`rewind.classifier`):**
    *   `ClassificationEngine`: Orchestrates multiple classifiers. (Completed)
    *   `RuleClassifier`: Classifies actions based on pattern matching (regex) against built-in or custom policy rules. (Completed)

3.  **Approval Flow (`rewind.approval`):**
    *   `CodeGenerator`: Generates one-time, time-limited approval codes. (Completed)
    *   `ApprovalQueue`: Manages pending requests and handles timeouts. (Completed)
    *   *Pending:* Local Web UI for humans to approve/deny actions.

4.  **Snapshot & Rollback (`rewind.snapshot`):**
    *   `GitSnapshotter`: Takes git-based filesystem snapshots. (Completed)
    *   `DatabaseSnapshotter`: Takes database snapshots (SQLite, PostgreSQL). (Completed)
    *   `RollbackOrchestrator`: Coordinates rollback across multiple backends. (Completed)

5.  **Audit Log (`rewind.audit`):**
    *   `AuditLog`: Append-only SQLite log. (Completed)
    *   `chain`: Hash-chain verification for tamper detection. (Completed)

6.  **Agent Adapters (`rewind.proxy`):**
    *   `ShellProxy`: Wraps and intercepts shell commands. (Completed)
    *   `MCPProxy`: Drop-in MCP server adapter. (Completed)

## Next Steps

*   Implement the local Web UI for the `ApprovalQueue`.
*   Integrate the `Snapshotter` classes fully into the proxy flow (i.e., actually take the snapshot when an action is classified as `REVERSIBLE`).
*   Complete the CLI implementation (especially the `rollback` and `demo` commands).
