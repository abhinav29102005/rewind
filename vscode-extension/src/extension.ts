import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
    console.log("Rewind VS Code extension activated.");

    let approveDisposable = vscode.commands.registerCommand("rewind.approve", async () => {
        // In a real implementation, this would fetch from the ApprovalQueue HTTP server
        const request = await vscode.window.showInputBox({
            prompt: "Enter Request ID to Approve",
            placeHolder: "REQ-XXXX-YYYY"
        });
        
        if (request) {
            vscode.window.showInformationMessage(`Approved Rewind action: ${request}`);
            // Send approval HTTP request here
        }
    });

    let denyDisposable = vscode.commands.registerCommand("rewind.deny", async () => {
        const request = await vscode.window.showInputBox({
            prompt: "Enter Request ID to Deny",
            placeHolder: "REQ-XXXX-YYYY"
        });
        
        if (request) {
            vscode.window.showWarningMessage(`Denied Rewind action: ${request}`);
            // Send deny HTTP request here
        }
    });

    context.subscriptions.push(approveDisposable, denyDisposable);
}

export function deactivate() {}
