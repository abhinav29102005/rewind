"""
Rewind CLI entry point.

Provides commands for:
- rewind exec -- <command>     : Run a command through the proxy
- rewind log                   : View the audit log
- rewind verify                : Verify the audit log hash chain
- rewind rollback <id>         : Rollback to a snapshot
- rewind vault list            : List stored credentials
- rewind start                 : Start the web control plane
- rewind bench run <file>      : Run benchmark scenario(s)
- rewind bench run-all         : Run all benchmark scenarios
- rewind session start/end/list: Manage team sessions
- rewind admin create/list     : Manage administrative users
- rewind policy list/test      : Inspect and test policy rules
- rewind plugin list           : List discovered plugins
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .approval.queue import ApprovalQueue
from .audit.log import AuditLog, EventType
from .classifier.engine import ClassificationEngine
from .classifier.rules import RuleClassifier
from .config.defaults import builtin_policy_dir
from .config.loader import ConfigError, check_file_permissions, config_hash, load_config
from .contracts import ActionRequest, RiskClass
from .policy.engine import PolicyClassifier
from .policy.pack import load_packs
from .proxy.shell import ShellProxy

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="rewind")
def main() -> None:
    """Rewind - An enforced approval and undo layer for AI agents."""
    pass


@main.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--timeout", default=60, help="Command timeout in seconds")
@click.option("--audit-db", default="rewind_audit.db", help="Path to audit database")
def exec_cmd(command: tuple[str, ...], timeout: int, audit_db: str) -> None:
    """Execute a command through the Rewind proxy."""
    cmd_str = " ".join(command)

    audit_log = AuditLog(db_path=audit_db)
    classifier = ClassificationEngine()
    classifier.add_classifier(RuleClassifier())
    queue = ApprovalQueue()

    proxy = ShellProxy(
        classifier=classifier,
        audit_log=audit_log,
        approval_queue=queue,
    )

    result = proxy.execute(cmd_str, timeout=timeout)

    if result.status == "executed":
        console.print(f"[green][OK][/green] Command executed (risk: {result.risk})")
        if result.stdout:
            console.print(result.stdout, end="")
        if result.stderr:
            console.print(f"[yellow]{result.stderr}[/yellow]", end="")
        sys.exit(result.exit_code or 0)

    elif result.status == "blocked":
        console.print(
            Panel(
                f"[red bold][BLOCKED] BLOCKED[/red bold]\n\n"
                f"Command: [cyan]{cmd_str}[/cyan]\n"
                f"Risk: [red]{result.risk}[/red]\n"
                f"Action ID: {result.action_id}\n"
                f"Approval Request: {result.approval_request_id or 'N/A'}",
                title="Rewind - Action Blocked",
                border_style="red",
            )
        )
        sys.exit(1)

    audit_log.close()


@main.command()
@click.option("--audit-db", default="rewind_audit.db", help="Path to audit database")
@click.option("--limit", default=20, help="Number of events to show")
@click.option("--type", "event_type", default=None, help="Filter by event type")
def log(audit_db: str, limit: int, event_type: str | None) -> None:
    """View the audit log."""
    audit_log = AuditLog(db_path=audit_db)

    et = EventType(event_type) if event_type else None
    events = audit_log.get_events(event_type=et, limit=limit)

    if not events:
        console.print("[dim]No audit events found.[/dim]")
        return

    table = Table(title="Audit Log", show_lines=True)
    table.add_column("ID", style="dim", width=6)
    table.add_column("Type", style="cyan", width=22)
    table.add_column("Timestamp", width=20)
    table.add_column("Details", width=60)
    table.add_column("Chain", style="dim", width=12)

    import datetime

    for event in events:
        ts = datetime.datetime.fromtimestamp(event.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        details = json.dumps(event.data, default=str)[:80]
        table.add_row(
            str(event.event_id),
            event.event_type.value,
            ts,
            details,
            event.chain_hash[:12] + "...",
        )

    console.print(table)
    console.print(f"\n[dim]Total events: {audit_log.count}[/dim]")
    audit_log.close()


@main.command()
@click.option("--audit-db", default="rewind_audit.db", help="Path to audit database")
def verify(audit_db: str) -> None:
    """Verify the audit log hash chain integrity."""
    audit_log = AuditLog(db_path=audit_db)
    is_valid, last_verified = audit_log.verify_chain()

    if is_valid:
        console.print(
            f"[green][OK] Chain verified:[/green] {last_verified} entries, all intact."
        )
    else:
        console.print(
            f"[red][FAIL] Chain BROKEN[/red] at entry {last_verified + 1}. "
            f"The audit log may have been tampered with."
        )
        sys.exit(1)

    audit_log.close()


@main.command()
@click.argument("snapshot_id")
def rollback(snapshot_id: str) -> None:
    """Rollback filesystem state to a snapshot checkpoint."""
    from .snapshot.git import GitSnapshotError, GitSnapshotter

    snapshotter = GitSnapshotter(Path.cwd())
    try:
        ok = snapshotter.rollback(snapshot_id)
        if ok:
            console.print(f"[green bold][OK] Successfully rolled back to snapshot {snapshot_id}[/green bold]")
        else:
            console.print(f"[red bold][FAIL] Could not rollback to snapshot {snapshot_id}[/red bold]")
    except GitSnapshotError as e:
        console.print(f"[red bold][ERROR] Rollback failed:[/red bold] {e}")


@main.group()
def vault() -> None:
    """Manage the credential vault."""
    pass


@vault.command(name="list")
def vault_list() -> None:
    """List stored credentials (names and types only)."""
    from .broker.vault import Vault

    v = Vault()
    try:
        v.initialize()
    except Exception as e:
        console.print(f"[red]Failed to open vault: {e}[/red]")
        return

    creds = v.list_credentials()
    if not creds:
        console.print("[dim]No credentials stored.[/dim]")
        return

    table = Table(title="Credential Vault")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")

    for cred in creds:
        table.add_row(cred["name"], cred["type"])

    console.print(table)


# =============================================================================
# Control Plane Server Command
# =============================================================================
@main.command()
@click.option("--config", "config_file", default=None, help="Path to rewind.yaml")
@click.option("--port", default=None, type=int, help="Port to bind control plane")
def start(config_file: str | None, port: int | None) -> None:
    """Start the Rewind control plane web UI and API."""
    try:
        cfg = load_config(config_file)
    except ConfigError as e:
        console.print(f"[red bold]Refusing to start:[/red bold] {e}")
        sys.exit(1)

    # Permission check
    paths_to_check = [Path("rewind.yaml"), builtin_policy_dir(), cfg.data_dir]
    warnings = check_file_permissions(paths_to_check, cfg.security.agent_os_user)
    for w in warnings:
        console.print(f"[yellow][WARNING] Security warning:[/yellow] {w}")

    h = config_hash(cfg)
    console.print(f"[green][OK] Effective config hash:[/green] {h[:16]}...")
    if cfg.mode == "audit_only":
        console.print(Panel("[yellow bold][WARNING] AUDIT-ONLY MODE ACTIVE: Blocking is disabled.[/yellow bold]"))

    bind_port = port or cfg.control_plane.port
    console.print(f"[cyan][START] Starting Control Plane on http://{cfg.control_plane.host}:{bind_port}[/cyan]")

    import uvicorn

    from .audit.log import AuditLog
    from .team.store import TeamStore
    from .web.team_app import create_team_app

    data_dir = cfg.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    store = TeamStore(data_dir / "team.db")
    audit_log = AuditLog(data_dir / "audit.db")
    app = create_team_app(store, cfg, audit_log=audit_log)

    uvicorn.run(app, host=cfg.control_plane.host, port=bind_port, log_level="info")


# =============================================================================
# Benchmark Commands
# =============================================================================
@main.group()
def bench() -> None:
    """Run and report benchmark scenarios."""
    pass


@bench.command(name="run")
@click.argument("scenario_file")
@click.option("--target", default="rewind", type=click.Choice(["rewind", "cooperative", "none", "all"]))
def bench_run(scenario_file: str, target: str) -> None:
    """Run a single benchmark scenario file."""
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner()
    res = runner.run_scenario(scenario_file, target=target)

    console.print(Panel(f"Scenario: [cyan]{res['name']}[/cyan] ({res['scenario']})"))
    table = Table(title="Target Results")
    table.add_column("Target", style="bold")
    table.add_column("Destructive Prevented")
    table.add_column("Data Loss (Rows)")
    table.add_column("Duration")

    for t_name, t_data in res["targets"].items():
        blocked = "[green]Yes[/green]" if t_data.get("destructive_prevented") else "[red]No[/red]"
        loss = str(t_data.get("data_loss_rows", 0))
        table.add_row(t_name, blocked, loss, f"{t_data.get('duration_ms')}ms")

    console.print(table)


@bench.command(name="run-all")
@click.option("--target", default="all", type=click.Choice(["rewind", "cooperative", "none", "all"]))
@click.option("--scenarios-dir", default="benchmark/scenarios", help="Scenarios folder")
@click.option("--output-dir", default="benchmark/results", help="Results folder")
def bench_run_all(target: str, scenarios_dir: str, output_dir: str) -> None:
    """Run all benchmark scenarios and generate report."""
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner()
    results = runner.run_all(scenarios_dir, target=target)
    json_p, md_p = runner.generate_report(results, output_dir)

    console.print(f"[green][OK] Completed {len(results)} scenarios.[/green]")
    console.print(f"Report written to: [cyan]{md_p}[/cyan]")


# =============================================================================
# Team Sessions Commands
# =============================================================================
@main.group()
def session() -> None:
    """Manage team sessions."""
    pass


@session.command(name="start")
@click.option("--name", required=True, help="Session name")
@click.option("--policy", "policy_profile", default="default", help="Policy profile (default | strict)")
@click.option("--user", "user_identifier", default="alice", help="Username or ID starting session")
@click.option("--db", default="data/team.db", help="Path to team database")
def session_start(name: str, policy_profile: str, user_identifier: str, db: str) -> None:
    """Start a new agent session."""
    from .team.models import Role
    from .team.sessions import SessionManager
    from .team.store import TeamStore

    store = TeamStore(db)
    cfg = load_config()
    mgr = SessionManager(store, cfg)

    # Resolve user
    user = store.get_user(user_identifier)
    if not user:
        res = store.get_user_by_username(user_identifier)
        if res:
            user = res[0]
    if not user:
        # Fallback to first active admin or create default
        for u in store.list_users():
            if u.role == Role.ADMIN and u.active:
                user = u
                break
    if not user:
        user = store.create_user("usr_admin", "admin", "cli_default", Role.ADMIN)

    sess, eff_cfg = mgr.start_session(name, user, profile_name=policy_profile)
    console.print(f"[green][OK] Started session:[/green] {sess.id} (profile: {sess.policy_profile})")


@session.command(name="list")
@click.option("--db", default="data/team.db", help="Path to team database")
def session_list(db: str) -> None:
    """List sessions."""
    from .team.store import TeamStore

    store = TeamStore(db)
    sessions = store.list_sessions()

    table = Table(title="Sessions")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Profile")
    table.add_column("Status")

    for s in sessions:
        status = "[dim]Ended[/dim]" if s.ended_at else "[green]Active[/green]"
        table.add_row(s.id, s.name, s.policy_profile, status)

    console.print(table)


@session.command(name="end")
@click.argument("session_id")
@click.option("--db", default="data/team.db", help="Path to team database")
def session_end(session_id: str, db: str) -> None:
    """End a session."""
    from .team.sessions import SessionManager
    from .team.store import TeamStore

    store = TeamStore(db)
    cfg = load_config()
    mgr = SessionManager(store, cfg)
    mgr.end_session(session_id, reason="cli_command")
    console.print(f"[yellow]Session {session_id} ended.[/yellow]")


# =============================================================================
# Admin User Commands
# =============================================================================
@main.group()
def admin() -> None:
    """Administrative management."""
    pass


@admin.command(name="create")
@click.option("--username", required=True, help="Username")
@click.option("--role", default="admin", type=click.Choice(["admin", "approver", "viewer"]))
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--db", default="data/team.db", help="Path to team database")
def admin_create(username: str, role: str, password: str, db: str) -> None:
    """Create a user locally."""
    from .team.auth import hash_password
    from .team.models import Role
    from .team.store import TeamStore

    store = TeamStore(db)
    uid = "usr_" + uuid.uuid4().hex[:10]
    u = store.create_user(uid, username, hash_password(password), Role(role))
    console.print(f"[green][OK] User {u.username} created with role {u.role.value} (ID: {u.id})[/green]")


admin.add_command(admin_create, name="create-user")


@admin.command(name="list-users")
@click.option("--db", default="data/team.db", help="Path to team database")
def admin_list_users(db: str) -> None:
    """List registered users."""
    from .team.store import TeamStore

    store = TeamStore(db)
    users = store.list_users()

    table = Table(title="Users")
    table.add_column("ID")
    table.add_column("Username")
    table.add_column("Role")
    table.add_column("Active")

    for u in users:
        table.add_row(u.id, u.username, u.role.value, str(u.active))

    console.print(table)


# =============================================================================
# Policy Commands
# =============================================================================
@main.group()
def policy() -> None:
    """Policy packs and rule inspection."""
    pass


@policy.command(name="list")
def policy_list() -> None:
    """List loaded policy packs."""
    packs = load_packs(
        ["filesystem", "postgresql", "git", "aws_s3", "docker"],
        [builtin_policy_dir()],
    )
    table = Table(title="Shipped Policy Packs")
    table.add_column("Pack", style="bold")
    table.add_column("Tool")
    table.add_column("Rules")
    table.add_column("Default Risk")

    for p in packs:
        table.add_row(p.pack, p.tool, str(len(p.rules)), p.default_risk.value)

    console.print(table)


@policy.command(
    name="test",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("statement", nargs=-1)
@click.option("--tool", default="sql", type=click.Choice(["sql", "fs", "shell", "git", "docker", "aws_s3", "k8s"]))
@click.option("--op", "--operation", "operation", default="exec", help="Operation name")
@click.option("--payload", default=None, help="JSON or YAML payload string")
@click.pass_context
def policy_test(
    ctx: click.Context,
    statement: tuple[str, ...],
    tool: str,
    operation: str,
    payload: str | None,
) -> None:
    """Test classification of a statement or command."""
    packs = load_packs(
        ["filesystem", "postgresql", "git", "aws_s3", "docker"],
        [builtin_policy_dir()],
    )
    classifier = PolicyClassifier(packs)

    payload_dict: dict[str, Any] = {}
    import yaml

    all_tokens = list(statement) + list(ctx.args)

    if payload:
        candidate_payload = (payload + " " + " ".join(all_tokens)).strip() if all_tokens else payload
        try:
            parsed = yaml.safe_load(candidate_payload)
            if isinstance(parsed, dict):
                payload_dict = parsed
            else:
                parsed_single = yaml.safe_load(payload)
                if isinstance(parsed_single, dict):
                    payload_dict = parsed_single
        except Exception:
            try:
                parsed_single = yaml.safe_load(payload)
                if isinstance(parsed_single, dict):
                    payload_dict = parsed_single
            except Exception as e:
                console.print(f"[red]Error parsing --payload: {e}[/red]")
                return

    if not payload_dict and all_tokens:
        stmt_str = " ".join(all_tokens)
        payload_dict["statement"] = stmt_str
        payload_dict["command"] = stmt_str
        payload_dict["query"] = stmt_str

    if not payload_dict:
        console.print("[red]Please provide a statement argument or --payload string.[/red]")
        return

    actual_tool = "fs" if tool == "shell" else tool

    act = ActionRequest(
        id="test_act",
        agent_id="cli",
        tool=actual_tool,
        operation=operation,
        payload=payload_dict,
        created_at=__import__("datetime").datetime.now(),
    )
    res = classifier.classify(act)
    color = "green" if res.risk == RiskClass.SAFE else ("yellow" if res.risk == RiskClass.REVERSIBLE else "red")
    console.print(f"Risk: [{color} bold]{res.risk.value.upper()}[/{color} bold]")
    console.print(f"Reasons: {', '.join(res.reasons) if res.reasons else 'None'}")
    console.print(f"Rules fired: {', '.join(res.rule_ids) if res.rule_ids else 'None'}")


# =============================================================================
# Plugin Commands
# =============================================================================
@main.group()
def plugin() -> None:
    """Plugin inspection."""
    pass


@plugin.command(name="list")
def plugin_list() -> None:
    """List discovered plugins."""
    from .plugins.loader import list_installed_plugins

    plugins = list_installed_plugins()
    if not plugins:
        console.print("[dim]No third-party plugins discovered in python entry points.[/dim]")
        return

    table = Table(title="Installed Plugins")
    table.add_column("Name")
    table.add_column("Kind")
    table.add_column("Version")
    table.add_column("Rewind API")

    for p in plugins:
        table.add_row(p.name, p.kind.value, p.version, p.rewind_api_version)

    console.print(table)



# =============================================================================
# Integrate / Connect Commands
# =============================================================================
@main.command(name="integrate")
@click.option("--agent", type=click.Choice(["antigravity", "vscode", "claude", "cursor", "windsurf", "zed", "roo", "all"]), help="Target agent to configure")
@click.option("--config", "config_path", type=click.Path(), help="Inject Rewind into a custom JSON config path")
@click.option("--print-json", is_flag=True, help="Print MCP configuration snippet to stdout")
def integrate_cmd(agent: str | None, config_path: str | None, print_json: bool) -> None:
    """Incorporate Rewind MCP guardrails into Claude, Cursor, Windsurf, Zed, or any client."""
    import shutil
    import subprocess
    from pathlib import Path

    repo_dir = Path(__file__).resolve().parent.parent.parent
    uv_bin = shutil.which("uv") or "uv"

    mcp_snippet = {
        "mcpServers": {
            "rewind-guard": {
                "command": uv_bin,
                "args": ["--directory", str(repo_dir), "run", "rewind-mcp"]
            }
        }
    }

    if print_json:
        console.print(json.dumps(mcp_snippet, indent=2))
        return

    script_path = repo_dir / "scripts" / "setup-agent.sh"
    if script_path.exists():
        args = [str(script_path)]
        if agent:
            args.extend(["--agent", agent])
        if config_path:
            args.extend(["--config", config_path])
        subprocess.run(args)
    else:
        console.print(Panel(json.dumps(mcp_snippet, indent=2), title="Add to your Agent's MCP Config"))


if __name__ == "__main__":
    main()
