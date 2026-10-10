import json

with open("package.json", "r") as f:
    data = json.load(f)

data["version"] = "0.1.3"

with open("package.json", "w") as f:
    json.dump(data, f, indent=2)
