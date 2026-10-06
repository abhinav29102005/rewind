"""
Rewind CLI entry point.

Provides commands for:
- rewind exec -- <command>     : Run a command through the proxy
- rewind log                   : View the audit log
- rewind verify                : Verify the audit log hash chain
- rewind rollback <id>         : Rollback to a snapshot
- rewind vault list            : List stored credentials
- rewind demo --scenario <name>: Run an incident replay demo
- rewind bench run <file>      : Run a benchmark scenario
"""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .approval.queue import ApprovalQueue
from .audit.log import AuditLog, EventType
from .classifier.engine import ClassificationEngine
from .classifier.rules import RuleClassifier
from .proxy.shell import ShellProxy

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="rewind")
def main() -> None:
    """🔄 Rewind — An enforced approval and undo layer for AI agents."""
    pass


@main.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--timeout", default=60, help="Command timeout in seconds")
@click.option("--audit-db", default="rewind_audit.db", help="Path to audit database")
def exec_cmd(command: tuple[str, ...], timeout: int, audit_db: str) -> None:
    """Execute a command through the Rewind proxy."""
    cmd_str = " ".join(command)

    # Initialize pipeline
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
        console.print(f"[green]✓[/green] Command executed (risk: {result.risk})")
        if result.stdout:
            console.print(result.stdout, end="")
        if result.stderr:
            console.print(f"[yellow]{result.stderr}[/yellow]", end="")
        sys.exit(result.exit_code or 0)

    elif result.status == "blocked":
        console.print(
            Panel(
                f"[red bold]⛔ BLOCKED[/red bold]\n\n"
                f"Command: [cyan]{cmd_str}[/cyan]\n"
                f"Risk: [red]{result.risk}[/red]\n"
                f"Action ID: {result.action_id}\n"
                f"Approval Request: {result.approval_request_id or 'N/A'}",
                title="Rewind — Action Blocked",
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
            event.chain_hash[:12] + "…",
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
            f"[green]✓ Chain verified:[/green] {last_verified} entries, all intact."
        )
    else:
        console.print(
            f"[red]✗ Chain BROKEN[/red] at entry {last_verified + 1}. "
            f"The audit log may have been tampered with."
        )
        sys.exit(1)

    audit_log.close()


@main.command()
@click.argument("snapshot_id")
def rollback(snapshot_id: str) -> None:
    """Rollback to a snapshot."""
    console.print(f"[yellow]Rollback to {snapshot_id}...[/yellow]")
    # TODO: Implement full rollback orchestration
    console.print("[dim]Rollback not yet implemented in CLI. Use the Python API.[/dim]")


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


@main.command()
@click.option("--scenario", required=True, help="Scenario name to demo")
def demo(scenario: str) -> None:
    """Run an incident replay demo."""
    console.print(
        Panel(
            f"[cyan]Running demo scenario: {scenario}[/cyan]\n\n"
            f"This replays a documented incident in a sandbox\n"
            f"and shows how Rewind blocks the destructive action.",
            title="🎬 Rewind Demo",
            border_style="cyan",
        )
    )
    # TODO: Implement demo runner
    console.print("[dim]Demo scenarios coming soon. See benchmark/scenarios/[/dim]")


if __name__ == "__main__":
    main()
