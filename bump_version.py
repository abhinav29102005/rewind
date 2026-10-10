import json

path = "vscode-extension/package.json"
with open(path, "r") as f:
    data = json.load(f)

data["version"] = "0.1.4"

with open(path, "w") as f:
    json.dump(data, f, indent=2)

print("Bumped to 0.1.4")
