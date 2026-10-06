# Phase 0: Prove the Differentiator

**Goal:** Demonstrate that credential isolation + non-bypassable approval fills a real gap that cooperative guardrails do not.

## Overview

The purpose of Phase 0 is to validate the core assumption of Rewind: that cooperative guardrails are insufficient against an agent that discovers real credentials, and that an out-of-band proxy provides necessary protection.

If this phase proves that an existing tool already provides this protection, the project should pivot to contributing to that tool.

## Key Deliverables

1.  **Project Scaffold:** The basic Python package structure, linting, and testing setup. (Completed)
2.  **Incident Replay Sandbox:** A reproducible environment (e.g., Docker Compose) that simulates the "PocketOS" incident where an agent finds a leaked API token and uses it to drop a database.
3.  **Minimal Rewind Proxy:** A basic implementation of the `ShellProxy` and `MCPProxy` that can intercept tool calls, classify them using `RuleClassifier`, block destructive actions, and log the results to the `AuditLog`. (Completed)
4.  **Benchmark v0:** The initial benchmark suite containing adversarial scenarios to test Rewind against existing tools. (Scenarios drafted)

## Next Steps

*   Implement the Docker Compose sandbox (`docker/docker-compose.yaml`) for the PocketOS replay.
*   Create a script to run the benchmark scenarios against the sandbox (`benchmark/runner.py`).
*   Evaluate Rewind's minimal proxy against the scenarios to ensure it blocks the destructive actions.
