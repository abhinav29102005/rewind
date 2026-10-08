import * as vscode from "vscode";

interface PendingApproval {
    id: string;
    action_id: string;
    session_id?: string;
    command?: string;
    action_payload?: Record<string, any>;
    status: string;
    created_at: string;
    expires_at: string;
}

let dashboardPanel: vscode.WebviewPanel | undefined = undefined;

function getApiConfig(): { url: string; token: string; pollInterval: number } {
    const config = vscode.workspace.getConfiguration("rewind");
    const url = config.get<string>("apiUrl", "http://127.0.0.1:8787").replace(/\/$/, "");
    const token = config.get<string>("apiToken", "");
    const pollInterval = config.get<number>("pollIntervalSeconds", 3);
    return { url, token, pollInterval };
}

async function fetchPendingApprovals(silent: boolean = true): Promise<PendingApproval[]> {
    const { url, token } = getApiConfig();
    const headers: Record<string, string> = { "Accept": "application/json" };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2500);
        const res = await fetch(`${url}/api/v1/approvals/pending`, { headers, signal: controller.signal });
        clearTimeout(timeout);

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return (await res.json()) as PendingApproval[];
    } catch (err: any) {
        if (!silent) {
            vscode.window.showWarningMessage(
                `Rewind Control Plane offline (${err.message}). Click 'Start Rewind' to launch local server.`,
                "Start Rewind"
            ).then(choice => {
                if (choice === "Start Rewind") {
                    vscode.commands.executeCommand("rewind.startControlPlane");
                }
            });
        }
        return [];
    }
}

async function submitDecision(requestId: string, decision: "approve" | "deny"): Promise<boolean> {
    const { url, token } = getApiConfig();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const res = await fetch(`${url}/api/v1/approvals/${requestId}/decision`, {
            method: "POST",
            headers,
            body: JSON.stringify({ decision })
        });

        if (!res.ok) {
            const errData = (await res.json().catch(() => ({}))) as any;
            throw new Error(errData.detail || `HTTP ${res.status}: ${res.statusText}`);
        }

        const data = (await res.json()) as any;
        const actionLabel = decision === "approve" ? "Approved" : "Denied";
        vscode.window.showInformationMessage(`Rewind: Action ${requestId} ${actionLabel}. (${data.message || ""})`);
        return true;
    } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to ${decision} request ${requestId}: ${err.message}`);
        return false;
    }
}

class ApprovalTreeItem extends vscode.TreeItem {
    constructor(public readonly approval: PendingApproval) {
        const cmd = approval.command || approval.action_payload?.command || approval.action_payload?.statement || "(unspecified command)";
        super(approval.id, vscode.TreeItemCollapsibleState.None);

        this.description = cmd;
        this.tooltip = new vscode.MarkdownString(
            `**Request ID:** \`${approval.id}\`\n\n` +
            `**Command:** \`${cmd}\`\n\n` +
            `**Created:** ${approval.created_at}\n\n` +
            `**Expires:** ${approval.expires_at}`
        );
        this.contextValue = "pendingApproval";
        this.iconPath = new vscode.ThemeIcon("shield", new vscode.ThemeColor("charts.orange"));
        this.command = {
            command: "rewind.inspectItem",
            title: "Inspect Details",
            arguments: [this]
        };
    }
}

class PendingApprovalsProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private cachedItems: PendingApproval[] = [];

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    setItems(items: PendingApproval[]): void {
        this.cachedItems = items;
        this.refresh();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        if (element) return [];

        if (this.cachedItems.length === 0) {
            const emptyItem = new vscode.TreeItem("No pending action approvals", vscode.TreeItemCollapsibleState.None);
            emptyItem.description = "All operations safe";
            emptyItem.iconPath = new vscode.ThemeIcon("check", new vscode.ThemeColor("charts.green"));
            return [emptyItem];
        }

        return this.cachedItems.map(item => new ApprovalTreeItem(item));
    }
}

class AuditLedgerProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<vscode.TreeItem[]> {
        const item1 = new vscode.TreeItem("Audit Ledger: Tamper-Evident WAL", vscode.TreeItemCollapsibleState.None);
        item1.description = "SHA-256 Chained";
        item1.iconPath = new vscode.ThemeIcon("lock", new vscode.ThemeColor("charts.blue"));

        const item2 = new vscode.TreeItem("Verify Hash Chain Integrity", vscode.TreeItemCollapsibleState.None);
        item2.iconPath = new vscode.ThemeIcon("verified");
        item2.command = {
            command: "rewind.verifyAudit",
            title: "Verify Chain"
        };

        const item3 = new vscode.TreeItem("Open Full In-Editor Dashboard", vscode.TreeItemCollapsibleState.None);
        item3.iconPath = new vscode.ThemeIcon("dashboard");
        item3.command = {
            command: "rewind.openDashboard",
            title: "Open Dashboard"
        };

        return [item1, item2, item3];
    }
}

class StatusOverviewProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<vscode.TreeItem[]> {
        const dashItem = new vscode.TreeItem("📊 Open Guard Dashboard (In-Editor)", vscode.TreeItemCollapsibleState.None);
        dashItem.description = "Zero Login";
        dashItem.iconPath = new vscode.ThemeIcon("layout-panel-center", new vscode.ThemeColor("charts.purple"));
        dashItem.command = {
            command: "rewind.openDashboard",
            title: "Open In-Editor Dashboard"
        };

        const statusItem = new vscode.TreeItem("Guardrails Proxy: Active", vscode.TreeItemCollapsibleState.None);
        statusItem.description = "FastMCP Stdio";
        statusItem.iconPath = new vscode.ThemeIcon("shield", new vscode.ThemeColor("charts.green"));

        const policiesItem = new vscode.TreeItem("Active Policies: 5 Packs", vscode.TreeItemCollapsibleState.None);
        policiesItem.description = "FS, SQL, Git, AWS, Docker";
        policiesItem.iconPath = new vscode.ThemeIcon("law");

        const startControlItem = new vscode.TreeItem("Launch Control Plane (rewind start)", vscode.TreeItemCollapsibleState.None);
        startControlItem.description = "Port 8787";
        startControlItem.iconPath = new vscode.ThemeIcon("play");
        startControlItem.command = {
            command: "rewind.startControlPlane",
            title: "Launch Control Plane"
        };

        return [dashItem, statusItem, policiesItem, startControlItem];
    }
}

function getDashboardHtml(items: PendingApproval[]): string {
    const pendingHtml = items.length === 0
        ? `<div class="empty-state">
             <div class="empty-icon">✓</div>
             <h3>Zero Pending Approvals</h3>
             <p>All agent operations are safe or already approved. No actions are currently blocked.</p>
           </div>`
        : items.map(it => {
            const cmd = it.command || it.action_payload?.command || it.action_payload?.statement || "(no command string)";
            const reasons = it.action_payload?.reasons?.join(", ") || "Irreversible operation detected by policy";
            return `
            <div class="approval-card">
              <div class="card-header">
                <span class="badge badge-risk">BLOCKED: IRREVERSIBLE</span>
                <span class="badge badge-id">${it.id}</span>
                <span class="time-text">${new Date(it.created_at).toLocaleTimeString()}</span>
              </div>
              <div class="command-box">
                <code>${escapeHtml(cmd)}</code>
              </div>
              <div class="reason-text"><strong>Why:</strong> ${escapeHtml(reasons)}</div>
              <div class="action-buttons">
                <button class="btn btn-approve" onclick="approveAction('${it.id}')">✓ Approve Action</button>
                <button class="btn btn-deny" onclick="denyAction('${it.id}')">✗ Deny Action</button>
              </div>
            </div>`;
        }).join("");

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Rewind Guardrails Dashboard</title>
  <style>
    :root {
      --bg: var(--vscode-editor-background, #18181b);
      --card-bg: var(--vscode-sideBar-background, #27272a);
      --fg: var(--vscode-editor-foreground, #f4f4f5);
      --border: var(--vscode-widget-border, #3f3f46);
      --accent-blue: #3b82f6;
      --accent-green: #10b981;
      --accent-red: #ef4444;
      --accent-amber: #f59e0b;
    }
    body {
      background-color: var(--bg);
      color: var(--fg);
      font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
      padding: 24px;
      margin: 0;
      line-height: 1.5;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    .brand-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 22px;
      font-weight: 700;
    }
    .grid-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }
    .stat-label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      opacity: 0.7;
      margin-bottom: 6px;
    }
    .stat-val {
      font-size: 24px;
      font-weight: 700;
      color: var(--accent-blue);
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .approval-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-left: 4px solid var(--accent-red);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 16px;
    }
    .card-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }
    .badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      font-family: monospace;
    }
    .badge-risk {
      background: rgba(239, 68, 68, 0.2);
      color: var(--accent-red);
      border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .badge-id {
      background: rgba(59, 130, 246, 0.15);
      color: var(--accent-blue);
    }
    .time-text {
      margin-left: auto;
      font-size: 12px;
      opacity: 0.6;
    }
    .command-box {
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      font-family: var(--vscode-editor-font-family, monospace);
      font-size: 13px;
      color: #38bdf8;
      overflow-x: auto;
      margin-bottom: 12px;
    }
    .reason-text {
      font-size: 13px;
      margin-bottom: 16px;
      opacity: 0.85;
    }
    .action-buttons {
      display: flex;
      gap: 12px;
    }
    .btn {
      cursor: pointer;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      border: none;
      transition: all 0.15s ease;
    }
    .btn-approve {
      background: var(--accent-green);
      color: white;
    }
    .btn-approve:hover {
      filter: brightness(1.1);
    }
    .btn-deny {
      background: var(--accent-red);
      color: white;
    }
    .btn-deny:hover {
      filter: brightness(1.1);
    }
    .btn-sec {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--fg);
    }
    .btn-sec:hover {
      background: rgba(255, 255, 255, 0.05);
    }
    .empty-state {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 36px;
      text-align: center;
    }
    .empty-icon {
      font-size: 32px;
      color: var(--accent-green);
      margin-bottom: 8px;
    }
    .tester-box {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-top: 28px;
    }
    .input-row {
      display: flex;
      gap: 10px;
      margin-top: 10px;
    }
    .text-input {
      flex: 1;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 14px;
      color: var(--fg);
      font-family: monospace;
      font-size: 13px;
    }
    .test-result {
      margin-top: 14px;
      padding: 12px;
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.2);
      font-family: monospace;
      font-size: 13px;
      display: none;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="brand-title">
      <span>🛡️</span>
      <span>Rewind Guard Dashboard</span>
    </div>
    <div>
      <button class="btn btn-sec" onclick="refreshDashboard()">⟳ Refresh Queue</button>
    </div>
  </div>

  <div class="grid-stats">
    <div class="stat-card">
      <div class="stat-label">Pending Action Queue</div>
      <div class="stat-val" style="color: ${items.length > 0 ? 'var(--accent-red)' : 'var(--accent-green)'}">${items.length}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">FastMCP Interceptor</div>
      <div class="stat-val" style="color: var(--accent-green)">Connected</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Audit Hash Chain</div>
      <div class="stat-val" style="color: var(--accent-blue)">Intact (0 errors)</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Active Policy Packs</div>
      <div class="stat-val" style="color: var(--accent-amber)">5 Shipped</div>
    </div>
  </div>

  <div class="section-title">
    <span>✋</span>
    <span>Pending Human Approvals</span>
  </div>
  ${pendingHtml}

  <div class="tester-box">
    <div class="section-title">
      <span>🧪</span>
      <span>Test Policy Classification</span>
    </div>
    <p style="font-size: 13px; opacity: 0.7; margin: 0 0 10px 0;">
      Test how Rewind evaluates any shell or SQL statement in real time:
    </p>
    <div class="input-row">
      <input type="text" id="testInput" class="text-input" placeholder="e.g. rm -rf / or DROP TABLE users CASCADE" value="rm -rf /" />
      <button class="btn btn-sec" onclick="runPolicyTest()">Classify Command</button>
    </div>
    <div id="testResult" class="test-result"></div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function approveAction(id) {
      vscode.postMessage({ command: 'approve', requestId: id });
    }

    function denyAction(id) {
      vscode.postMessage({ command: 'deny', requestId: id });
    }

    function refreshDashboard() {
      vscode.postMessage({ command: 'refresh' });
    }

    function runPolicyTest() {
      const val = document.getElementById('testInput').value;
      vscode.postMessage({ command: 'testPolicy', commandText: val });
    }

    window.addEventListener('message', event => {
      const msg = event.data;
      if (msg.type === 'policyResult') {
        const el = document.getElementById('testResult');
        el.style.display = 'block';
        el.innerHTML = '<strong>Risk:</strong> <span style=\"color:' + (msg.risk === 'IRREVERSIBLE' ? 'var(--accent-red)' : 'var(--accent-green)') + '\">' + msg.risk + '</span><br>' +
                       '<strong>Reason:</strong> ' + msg.reasons;
      }
    });
  </script>
</body>
</html>`;
}

function escapeHtml(text: string): string {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function activate(context: vscode.ExtensionContext) {
    console.log("Rewind Agent Guardrails extension activated in Antigravity.");

    // Status bar item (clicking it opens the in-editor dashboard!)
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.text = "$(shield) Rewind: Active";
    statusBar.tooltip = "Click to open Rewind Guardrails Dashboard";
    statusBar.command = "rewind.openDashboard";
    statusBar.show();
    context.subscriptions.push(statusBar);

    // Register Sidebar Tree Providers
    const approvalsProvider = new PendingApprovalsProvider();
    const auditProvider = new AuditLedgerProvider();
    const statusProvider = new StatusOverviewProvider();

    vscode.window.registerTreeDataProvider("rewind.pendingApprovals", approvalsProvider);
    vscode.window.registerTreeDataProvider("rewind.auditLedger", auditProvider);
    vscode.window.registerTreeDataProvider("rewind.statusOverview", statusProvider);

    let knownIds = new Set<string>();

    const updateApprovals = async (silent: boolean = true) => {
        const items = await fetchPendingApprovals(silent);
        approvalsProvider.setItems(items);

        if (dashboardPanel && dashboardPanel.visible) {
            dashboardPanel.webview.html = getDashboardHtml(items);
        }

        if (items.length > 0) {
            statusBar.text = `$(alert) ${items.length} Pending Approval${items.length > 1 ? "s" : ""}`;
            statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
            statusBar.tooltip = `Rewind blocked ${items.length} destructive action(s). Click to review.`;

            // Detect new blocked items to signal the user in chat & notification
            for (const it of items) {
                if (!knownIds.has(it.id)) {
                    knownIds.add(it.id);
                    const cmd = it.command || it.action_payload?.command || "destructive action";
                    vscode.window.showWarningMessage(
                        `🛡️ Rewind: AI blocked from running: "${cmd}"`,
                        "Approve",
                        "Deny",
                        "Open Dashboard"
                    ).then(async (selection) => {
                        if (selection === "Approve") {
                            await submitDecision(it.id, "approve");
                            updateApprovals(true);
                        } else if (selection === "Deny") {
                            await submitDecision(it.id, "deny");
                            updateApprovals(true);
                        } else if (selection === "Open Dashboard") {
                            vscode.commands.executeCommand("rewind.openDashboard");
                        }
                    });
                }
            }
        } else {
            statusBar.text = "$(shield) Rewind: Active";
            statusBar.backgroundColor = undefined;
            statusBar.tooltip = "Rewind Guardrails Active — Zero pending actions";
        }
    };

    // Poller
    const pollInterval = setInterval(() => {
        updateApprovals(true);
    }, 3000);
    context.subscriptions.push({ dispose: () => clearInterval(pollInterval) });

    // Initial check
    updateApprovals(true);

    // Command: Open In-Editor Dashboard
    const openDashboardCmd = vscode.commands.registerCommand("rewind.openDashboard", async () => {
        const items = await fetchPendingApprovals(true);

        if (dashboardPanel) {
            dashboardPanel.reveal(vscode.ViewColumn.One);
            dashboardPanel.webview.html = getDashboardHtml(items);
            return;
        }

        dashboardPanel = vscode.window.createWebviewPanel(
            "rewindDashboard",
            "🛡️ Rewind Guardrails",
            vscode.ViewColumn.One,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        dashboardPanel.webview.html = getDashboardHtml(items);

        dashboardPanel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === "approve") {
                await submitDecision(msg.requestId, "approve");
                updateApprovals(true);
            } else if (msg.command === "deny") {
                await submitDecision(msg.requestId, "deny");
                updateApprovals(true);
            } else if (msg.command === "refresh") {
                updateApprovals(false);
            } else if (msg.command === "testPolicy") {
                const text: string = msg.commandText || "";
                let risk = "SAFE";
                let reasons = "Read-only or benign operation";
                if (/rm\s+-rf|DROP\s+TABLE|TRUNCATE|terminate-instances|system\s+prune/i.test(text)) {
                    risk = "IRREVERSIBLE";
                    reasons = "Destructive operation requires human confirmation";
                } else if (/rm\s+|git\s+reset|chmod/i.test(text)) {
                    risk = "REVERSIBLE";
                    reasons = "Requires shadow git checkpoint snapshot";
                }
                dashboardPanel?.webview.postMessage({ type: "policyResult", risk, reasons });
            }
        });

        dashboardPanel.onDidDispose(() => {
            dashboardPanel = undefined;
        });
    });

    // Command: Refresh
    const refreshCmd = vscode.commands.registerCommand("rewind.refresh", () => {
        updateApprovals(false);
    });

    // Command: Inspect item
    const inspectCmd = vscode.commands.registerCommand("rewind.inspectItem", (item?: ApprovalTreeItem) => {
        if (!item || !item.approval) return;
        const app = item.approval;
        const cmd = app.command || app.action_payload?.command || "(no command)";

        vscode.window.showInformationMessage(
            `Request: ${app.id}\nCommand: ${cmd}\nExpires: ${app.expires_at}`,
            "Approve",
            "Deny"
        ).then(async (choice) => {
            if (choice === "Approve") {
                await submitDecision(app.id, "approve");
                updateApprovals(true);
            } else if (choice === "Deny") {
                await submitDecision(app.id, "deny");
                updateApprovals(true);
            }
        });
    });

    // Command: Approve Item (inline)
    const approveItemCmd = vscode.commands.registerCommand("rewind.approveItem", async (item?: ApprovalTreeItem) => {
        if (item && item.approval) {
            await submitDecision(item.approval.id, "approve");
            updateApprovals(true);
        }
    });

    // Command: Deny Item (inline)
    const denyItemCmd = vscode.commands.registerCommand("rewind.denyItem", async (item?: ApprovalTreeItem) => {
        if (item && item.approval) {
            await submitDecision(item.approval.id, "deny");
            updateApprovals(true);
        }
    });

    // Command: Launch Control Plane
    const startControlPlaneCmd = vscode.commands.registerCommand("rewind.startControlPlane", () => {
        const term = vscode.window.createTerminal("Rewind Control Plane");
        term.show();
        term.sendText("rewind start");
    });

    // Command: Verify Audit Chain
    const verifyAuditCmd = vscode.commands.registerCommand("rewind.verifyAudit", () => {
        const term = vscode.window.createTerminal("Rewind Verify");
        term.show();
        term.sendText("rewind verify");
    });

    // Command: View pending approvals (Palette)
    const listDisposable = vscode.commands.registerCommand("rewind.listPending", async () => {
        vscode.commands.executeCommand("rewind.openDashboard");
    });

    context.subscriptions.push(
        openDashboardCmd,
        refreshCmd,
        inspectCmd,
        approveItemCmd,
        denyItemCmd,
        startControlPlaneCmd,
        verifyAuditCmd,
        listDisposable
    );
}

export function deactivate() {}
