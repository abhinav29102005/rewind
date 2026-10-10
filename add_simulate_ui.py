import sys

path = "vscode-extension/src/extension.ts"
with open(path, "r") as f:
    content = f.read()

html_target = """  <div class="tester-box">"""
html_replacement = """  <div class="tester-box" style="margin-bottom: 24px;">
    <div class="section-title">
      <span>🎬</span>
      <span>Presentation Demo Scenarios</span>
    </div>
    <p style="font-size: 13px; opacity: 0.7; margin: 0 0 10px 0;">
      Click below to instantly simulate an AI attempting a destructive action:
    </p>
    <div class="input-row" style="gap: 12px; display: flex;">
      <button class="btn btn-sec" style="color: var(--accent-red);" onclick="simulateAction('DROP TABLE users CASCADE')">Simulate: Drop Database Table</button>
      <button class="btn btn-sec" style="color: var(--accent-amber);" onclick="simulateAction('rm -rf demo/')">Simulate: Wipe Demo Folder</button>
    </div>
  </div>

  <div class="tester-box">"""

script_target = """    function refreshDashboard() {"""
script_replacement = """    function simulateAction(cmd) {
      vscode.postMessage({ command: 'simulateAction', commandText: cmd });
    }

    function refreshDashboard() {"""

handler_target = """            } else if (msg.command === "testPolicy") {"""
handler_replacement = """            } else if (msg.command === "simulateAction") {
                try {
                    await fetch("http://127.0.0.1:8787/api/v1/approvals/simulate", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ command: msg.commandText || "rm -rf /" })
                    });
                    updateApprovals(false);
                } catch (e) {
                    vscode.window.showErrorMessage("Failed to simulate action. Is Rewind running?");
                }
            } else if (msg.command === "testPolicy") {"""

if html_target in content and script_target in content and handler_target in content:
    content = content.replace(html_target, html_replacement)
    content = content.replace(script_target, script_replacement)
    content = content.replace(handler_target, handler_replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success")
else:
    print("Target not found")
