# Getting Started with Rewind

Rewind is an **enforced approval and undo layer for AI agents**. It intercepts shell commands, SQL queries, Docker calls, cloud actions, and file mutations, classifying each operation by risk:

* **Safe** (`ls`, `git status`, `SELECT`): Executes immediately with zero human friction.
* **Reversible** (`UPDATE`, file edits, `git commit`): Captures an atomic snapshot before execution, enabling instant one-click rollback.
* **Irreversible** (`DROP TABLE`, `rm -rf`, `aws s3 rb`): Physically halted by the proxy until cryptographically approved by authorized humans.

---

## 5-Minute Quickstart

### 1. Installation

Install Rewind using `pip` or `uv`:

```bash
uv pip install rewind-guard
# or with development dependencies:
uv pip install -e ".[dev]"
```

Verify the installation:

```bash
rewind --version
```

### 2. Initialize Configuration

Generate a default `rewind.yaml` file:

```bash
rewind config show > rewind.yaml
```

Inspect the configuration:
```yaml
version: 1
mode: enforce
default_risk: irreversible
policies:
  packs:
    - filesystem
    - postgresql
    - git
    - aws_s3
    - docker
control_plane:
  listen_host: "127.0.0.1"
  listen_port: 8765
```

### 3. Start the Control Plane & MCP Server

Start the Rewind service (runs both the MCP server and team dashboard):

```bash
rewind start
```

Access the Web Dashboard at `http://127.0.0.1:8765`.

### 4. Create an Admin User

In a separate terminal, bootstrap your team credentials:

```bash
rewind admin create-user --username alice --role admin
```

You can now log into the Web Dashboard to review live sessions, pending approvals, notifications, and tamper-evident audit logs.

### 5. Running the Agent Safety Benchmark

Rewind includes an adversarial safety benchmark that tests against tool discovery attacks, scoped deletes, misleading justifications, prompt injection, and credential replay:

```bash
# Run all benchmark scenarios across targets (none, cooperative, rewind)
rewind bench run-all --target all

# View the generated markdown report
cat benchmark/results/results.md
```

---

## Next Steps

* [System Architecture](architecture.md): Learn how the Shell Proxy, Policy Engine, and MCP Server work together.
* [Configuration Reference](config.md): Explore all configuration settings in `rewind.yaml`.
* [Policy Pack Authoring](policy_packs.md): Write declarative YAML rules for custom databases and internal tools.
* [Plugin Authoring](plugins.md): Extend Rewind with custom Python classifiers and snapshot backends.
* [Threat Model & Limitations](threat_model.md): Understand the security boundaries and fail-closed guarantees.
