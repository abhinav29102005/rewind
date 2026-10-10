import sys

path = "vscode-extension/src/extension.ts"
with open(path, "r") as f:
    content = f.read()

target1 = """      <button class="btn btn-sec" style="color: var(--accent-red);" onclick="simulateAction('DROP TABLE users CASCADE')">Simulate: Drop Database Table</button>
      <button class="btn btn-sec" style="color: var(--accent-amber);" onclick="simulateAction('rm -rf demo/')">Simulate: Wipe Demo Folder</button>
    </div>"""

replacement1 = """      <button class="btn btn-sec" style="color: var(--accent-red);" onclick="simulateAction('DROP TABLE users CASCADE')">Simulate: Drop Database Table</button>
      <button class="btn btn-sec" style="color: var(--accent-amber);" onclick="simulateAction('rm -rf demo/')">Simulate: Wipe Demo Folder</button>
      <button class="btn btn-sec" style="color: var(--accent-green);" onclick="resetDemo()">Reset Demo Files</button>
    </div>"""

target2 = """    function simulateAction(cmd) {
      vscode.postMessage({ command: 'simulateAction', commandText: cmd });
    }"""

replacement2 = """    function simulateAction(cmd) {
      vscode.postMessage({ command: 'simulateAction', commandText: cmd });
    }
    
    function resetDemo() {
      vscode.postMessage({ command: 'resetDemo' });
    }"""

target3 = """            } else if (msg.command === "simulateAction") {"""

replacement3 = """            } else if (msg.command === "resetDemo") {
                try {
                    await fetch("http://127.0.0.1:8787/api/v1/demo/reset", {
                        method: "POST"
                    });
                    vscode.window.showInformationMessage("Demo files reset to original state!");
                } catch (e) {
                    vscode.window.showErrorMessage("Failed to reset demo. Is Rewind running?");
                }
            } else if (msg.command === "simulateAction") {"""

if target1 in content and target2 in content and target3 in content:
    content = content.replace(target1, replacement1)
    content = content.replace(target2, replacement2)
    content = content.replace(target3, replacement3)
    with open(path, "w") as f:
        f.write(content)
    print("Success")
else:
    print("Target not found")
    print("t1", target1 in content)
    print("t2", target2 in content)
    print("t3", target3 in content)
