import json
from datetime import datetime, timezone
import pathlib
import subprocess

repo_root = pathlib.Path("/Users/yiwei/GithubRepos/root-azoth")

# W1: write episode
episodes_path = repo_root / ".azoth" / "memory" / "episodes.jsonl"
episodes = []
with open(episodes_path, "r") as f:
    for line in f:
        if line.strip():
            episodes.append(json.loads(line))
last_num = 0
for ep in episodes:
    try:
        if ep["id"].startswith("ep-"):
            last_num = max(last_num, int(ep["id"].split("-")[1]))
    except ValueError:
        pass

new_id = f"ep-{last_num + 1:03d}"
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

new_ep = {
    "id": new_id,
    "timestamp": timestamp,
    "session_id": "2026-04-11-p1-003",
    "type": "success",
    "goal": "Pipeline composition linter execution / P1-003",
    "summary": "Implemented P1-003: extracted the dictionary-based pipeline schema validator from tests into standalone CLI scripts/pipeline_lint.py. Tests and test presets were updated to import the script. Workflows and developer preflight docs were updated.",
    "lessons": ["Extracting existing Python validation logic is cleaner than relying on external JSON schema libraries when native test checks are robust."],
    "tags": ["pipeline-linter", "P1-003", "CLI-extraction", "CI-integration"],
    "reinforcement_count": 0,
    "m2_candidate": False,
    "context": {
        "files_changed": [
            "scripts/pipeline_lint.py",
            "tests/test_pipeline_schema.py",
            "tests/test_pipeline_presets.py",
            ".github/workflows/ci.yml",
            "docs/AZOTH_ARCHITECTURE.md"
        ]
    }
}

with open(episodes_path, "a") as f:
    f.write(json.dumps(new_ep) + "\n")

print(f"W1: Appeared episode {new_id} to {episodes_path}")

# W2: close out scope gate
gate_path = repo_root / ".azoth" / "scope-gate.json"
gate_data = {}
if gate_path.exists():
    with open(gate_path, "r") as f:
        gate_data = json.load(f)
gate_data["approved"] = False
gate_data["closed_at"] = timestamp
with open(gate_path, "w") as f:
    json.dump(gate_data, f, indent=2)

print(f"W2: scope gate closed at {gate_path}")

# azoth.yaml update episodes length
az_path = repo_root / "azoth.yaml"
if az_path.exists():
    with open(az_path, "r") as f:
        az_lines = f.readlines()
    with open(az_path, "w") as f:
        for line in az_lines:
            if line.startswith("  episodes: "):
                f.write(f"  episodes: {len(episodes) + 1}\n")
            else:
                f.write(line)

print("W2b: azoth.yaml episode count updated")

# W4: version bump
print("W4: Running version-bump.py...")
subprocess.run(["python3", "scripts/version-bump.py", "--patch"], cwd=repo_root, check=True)

orient_path = repo_root / ".azoth" / "session-orientation.txt"
if orient_path.exists():
    orient_path.unlink()
    print("W4: Removed session-orientation.txt")
else:
    print("W4: session-orientation.txt not found (skipped)")
