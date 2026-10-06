# Policy Pack Authoring Guide

Policy packs are declarative YAML files that define how Rewind classifies agent actions. Rewind ships with five core packs (`filesystem`, `postgresql`, `git`, `aws_s3`, and `docker`), and you can author custom packs for your organization's internal tools and databases.

---

## 1. Anatomy of a Policy Pack

Create a YAML file under `policies/` (e.g. `policies/my_service.yaml`):

```yaml
name: my_service
version: "1.0.0"
description: "Guardrails for internal customer service tools"
author: "Security Team"

rules:
  # Safe rules
  - id: my_service_read_status
    risk: safe
    tool: my_service
    match:
      operation: get_status
    reason: "Status checks are read-only and idempotent."

  # Reversible rules
  - id: my_service_update_email
    risk: reversible
    tool: my_service
    match:
      operation: update_user_email
    reason: "Email updates can be reverted from audit history."

  # Irreversible rules
  - id: my_service_delete_tenant
    risk: irreversible
    tool: my_service
    match:
      operation: delete_tenant
    reason: "Tenant deletion causes permanent data loss."
```

---

## 2. Matcher Types & Criteria

A rule's `match` block supports several criteria depending on the tool:

### SQL Matching
For SQL tools (`postgresql`, `sqlite`, `mysql`):

```yaml
rules:
  - id: pg_unscoped_delete
    risk: irreversible
    tool: sql
    match:
      dialect: postgres
      statement_types: ["DELETE"]
      requires_where: true # Triggers if WHERE is absent or WHERE 1=1
    reason: "Unscoped DELETE removes all table records without filtering."

  - id: pg_drop_table
    risk: irreversible
    tool: sql
    match:
      statement_types: ["DROP"]
    reason: "DROP TABLE irreversibly destroys table schema and data."
```

### Shell & Filesystem Matching
For shell commands (`sh`, `bash`, `exec`, `terminal`):

```yaml
rules:
  - id: fs_recursive_remove
    risk: irreversible
    tool: shell
    match:
      commands: ["rm", "shred", "srm"]
      flags: ["-r", "-rf", "-R", "--recursive"]
      paths: ["/", "/etc", "/var", "/home", "~"]
    reason: "Recursive file deletion removes entire directories."
```

### Generic Tool Matching
For custom MCP tools and APIs:

```yaml
rules:
  - id: k8s_delete_namespace
    risk: irreversible
    tool: kubernetes
    match:
      operation: "delete"
      resource: "namespace"
    reason: "Deleting a namespace cascades to all contained workloads."
```

---

## 3. Precedence & Evaluation Order

When multiple rules match an action:

1. **Explicit Overrides**: Overrides in `rewind.yaml` (`policies.overrides`) take top priority.
2. **Strictness Precedence**: If multiple pack rules match, Rewind selects the **strictest** classification (`irreversible` > `reversible` > `safe`).
3. **Default Fallback**: If no rules match, Rewind assigns the `default_risk` configured in `rewind.yaml` (default: `irreversible`).

---

## 4. Testing Your Policy Pack

Use Rewind's CLI to test policy classifications without executing actions:

```bash
# List all active packs
rewind policy list

# Test classification for an arbitrary action
rewind policy test --tool sql --op query --payload '{"query": "DROP TABLE users;"}'
```

Every policy pack should include a comprehensive table-driven test suite with at least 25 test cases covering:
- Standard safe operations
- Standard reversible mutations
- High-risk operations
- Known evasion vectors (quotes, comments, whitespace, subqueries, aliases)
