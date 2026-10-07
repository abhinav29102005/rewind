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

function getApiConfig(): { url: string; token: string } {
    const config = vscode.workspace.getConfiguration("rewind");
    const url = config.get<string>("apiUrl", "http://127.0.0.1:8787").replace(/\/$/, "");
    const token = config.get<string>("apiToken", "");
    return { url, token };
}

async function fetchPendingApprovals(): Promise<PendingApproval[]> {
    const { url, token } = getApiConfig();
    const headers: Record<string, string> = {
        "Accept": "application/json"
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const res = await fetch(`${url}/api/v1/approvals/pending`, { headers });
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return (await res.json()) as PendingApproval[];
    } catch (err: any) {
        vscode.window.showErrorMessage(`Rewind API connection failed: ${err.message}. Is 'rewind start' running?`);
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

export function activate(context: vscode.ExtensionContext) {
    console.log("Rewind Agent Guardrails extension activated.");

    // Status bar item
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.text = "$(shield) Rewind Guard";
    statusBar.tooltip = "Click to view pending Rewind approvals";
    statusBar.command = "rewind.listPending";
    statusBar.show();
    context.subscriptions.push(statusBar);

    // Command: View pending approvals
    let listDisposable = vscode.commands.registerCommand("rewind.listPending", async () => {
        const pending = await fetchPendingApprovals();
        if (pending.length === 0) {
            vscode.window.showInformationMessage("Rewind: Zero pending approvals in the action queue.");
            return;
        }

        const items: vscode.QuickPickItem[] = pending.map((req) => {
            const cmd = req.command || req.action_payload?.command || "(no command)";
            return {
                label: `$(shield) ${req.id}`,
                description: cmd,
                detail: `Session: ${req.session_id || "standalone"} | Created: ${req.created_at}`
            };
        });

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: `Select an action to inspect or approve (${pending.length} pending)`
        });

        if (selected) {
            const reqId = selected.label.replace("$(shield) ", "");
            const choice = await vscode.window.showQuickPick(
                [
                    { label: "$(check) Approve", description: `Authorize execution of ${reqId}` },
                    { label: "$(x) Deny", description: `Veto and cancel ${reqId}` }
                ],
                { placeHolder: `Action for ${reqId}: ${selected.description}` }
            );

            if (choice) {
                const decision = choice.label.includes("Approve") ? "approve" : "deny";
                await submitDecision(reqId, decision);
            }
        }
    });

    // Command: Approve
    let approveDisposable = vscode.commands.registerCommand("rewind.approve", async () => {
        const pending = await fetchPendingApprovals();
        let targetId: string | undefined;

        if (pending.length > 0) {
            const items = pending.map((req) => ({
                label: req.id,
                description: req.command || req.action_payload?.command || "(no command)"
            }));
            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: "Select a request to approve"
            });
            targetId = selected?.label;
        } else {
            targetId = await vscode.window.showInputBox({
                prompt: "Enter Request ID to Approve",
                placeHolder: "apr_XXXXXXXXXXXX"
            });
        }

        if (targetId) {
            await submitDecision(targetId, "approve");
        }
    });

    // Command: Deny
    let denyDisposable = vscode.commands.registerCommand("rewind.deny", async () => {
        const pending = await fetchPendingApprovals();
        let targetId: string | undefined;

        if (pending.length > 0) {
            const items = pending.map((req) => ({
                label: req.id,
                description: req.command || req.action_payload?.command || "(no command)"
            }));
            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: "Select a request to deny"
            });
            targetId = selected?.label;
        } else {
            targetId = await vscode.window.showInputBox({
                prompt: "Enter Request ID to Deny",
                placeHolder: "apr_XXXXXXXXXXXX"
            });
        }

        if (targetId) {
            await submitDecision(targetId, "deny");
        }
    });

    context.subscriptions.push(listDisposable, approveDisposable, denyDisposable);
}

export function deactivate() {}
