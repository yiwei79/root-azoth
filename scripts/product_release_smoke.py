#!/usr/bin/env python3
"""Repeatable T-036 product extraction and consumer-install smoke."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXTRACTOR = ROOT / "scripts" / "azoth_extract_product.py"

TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".toml"}
REDACTION_PLACEHOLDER = "{{REDACTED}}"

ABSENT_PREFIXES = (
    ".azoth/",
    ".claude/commands/",
    ".claude/hooks/",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/worktrees/",
    ".codex/hooks.mode.local",
    ".codex/permission_profile.local",
    ".git/",
    ".mypy_cache/",
    ".nox/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".tox/",
    ".venv/",
    "__pycache__/",
    "build/",
    "dist/",
    "docs/DAY0_TUTORIAL.md",
    "research_antigravity_parity/",
    "root-azoth.code-workspace",
    "tests/",
    "venv/",
    "workspace/",
)

REQUIRED_PRODUCT_PATHS = (
    "README.md",
    ".github/workflows/ci.yml",
    ".github/copilot-instructions.md",
    ".github/prompts/auto.prompt.md",
    ".github/agents/orchestrator.agent.md",
    "install.sh",
    "install.ps1",
    "scripts/azoth_release_profile.py",
    "kernel/templates/CLAUDE.md.template",
    "kernel/templates/bootloader-state.md.template",
    "kernel/templates/release-profiles/full-consumer.yaml",
    "kernel/BOOTLOADER.md",
    "kernel/GOVERNANCE.md",
    "kernel/PROMOTION_RUBRIC.md",
    "kernel/TRUST_CONTRACT.md",
)

REQUIRED_CONSUMER_PATHS = (
    "CLAUDE.md",
    "AGENTS.md",
    "azoth.yaml",
    ".github/copilot-instructions.md",
    ".github/prompts/auto.prompt.md",
    ".github/agents/orchestrator.agent.md",
    ".azoth/kernel/BOOTLOADER.md",
    ".azoth/kernel/GOVERNANCE.md",
    ".azoth/kernel/PROMOTION_RUBRIC.md",
    ".azoth/kernel/TRUST_CONTRACT.md",
    ".azoth/kernel-checksums.sha256",
    ".azoth/memory/episodes.jsonl",
    ".azoth/memory/patterns.yaml",
    "skills",
    "agents",
)

FULL_RELEASE_REFERENCE_PATHS = (
    "scripts/azoth_release_profile.py",
    "kernel/templates/release-profiles/full-consumer.yaml",
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
)

FULL_CONSUMER_RUNTIME_PATHS = (
    "commands/start/command.yaml",
    "commands/roadmap/command.yaml",
    "pipelines/full.pipeline.yaml",
    "scripts/codex_control_plane.py",
    "scripts/roadmap_dashboard.py",
    "scripts/autonomous_loop.py",
    ".agents/skills/azoth-start/SKILL.md",
    ".agents/skills/azoth-roadmap/SKILL.md",
    ".agents/skills/azoth-autonomous-auto/SKILL.md",
    ".azoth/roadmap.yaml",
    ".azoth/backlog.yaml",
    ".azoth/roadmap-specs/v0.2.0/README.md",
    ".azoth/initiative-banks/.gitkeep",
    ".azoth/design-banks/.gitkeep",
    ".azoth/autonomous-loop-state.local.yaml.example",
)

PRIVATE_RUNTIME_STATE_PATHS = (
    ".azoth/scope-gate.json",
    ".azoth/pipeline-gate.json",
    ".azoth/run-ledger.local.yaml",
    ".azoth/run-ledger.local.yaml.lock",
    ".azoth/autonomous-loop-state.local.yaml",
    ".azoth/final-delivery-approvals.jsonl",
)

PRIVATE_RUNTIME_STATE_GLOBS = (
    ".azoth/write-claim*.json",
)

PRIVATE_RUNTIME_STATE_DIRS = (
    ".azoth/telemetry",
)

FULL_RUNTIME_GITIGNORE_RULES = (
    ".azoth/scope-gate.json",
    "!.azoth/scope-gate.json.example",
    ".azoth/pipeline-gate.json",
    "!.azoth/pipeline-gate.json.example",
    ".azoth/run-ledger.local.yaml",
    "!.azoth/run-ledger.local.yaml.example",
    ".azoth/run-ledger.local.yaml.lock",
    ".azoth/autonomous-loop-state.local.yaml",
    "!.azoth/autonomous-loop-state.local.yaml.example",
    ".azoth/final-delivery-approvals.jsonl",
    ".azoth/write-claim*.json",
    ".azoth/telemetry/",
)

INSTALLED_REFERENCE_PATTERNS = (
    re.compile(r"(?<![\w./-])\.claude/commands/[A-Za-z0-9_-]+\.md"),
    re.compile(
        r"(?<![\w./-])commands/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
        r"\.(?:md|yaml|yml|json|toml)"
    ),
    re.compile(
        r"(?<![\w./-])pipelines/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
        r"\.(?:md|yaml|yml|json|toml)"
    ),
    re.compile(r"(?<![\w./-])scripts/[A-Za-z0-9_.-]+\.py"),
    re.compile(r"(?<![\w./-])\.agents/skills/azoth-[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*"),
)

INSTALLED_REFERENCE_SCAN_PREFIXES = (
    ".agents/skills/azoth-",
    ".claude/commands/",
    ".github/agents/",
    ".github/prompts/",
    "commands/",
)

INSTALLED_REFERENCE_SCAN_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
}

AZOTH_WRAPPER_MARKERS = (
    "Execution contract:",
    "Source path:",
    "Contract path:",
    "Script path:",
)


class SmokeError(RuntimeError):
    pass


def run(
    cmd: list[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    optional: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.returncode and not optional:
        joined = " ".join(cmd)
        raise SmokeError(
            f"command failed ({result.returncode}): {joined}\n"
            f"cwd: {cwd}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def load_config() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "sync-config.yaml").read_text(encoding="utf-8"))


def rel_files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def assert_required_paths(root: Path, paths: tuple[str, ...]) -> None:
    missing = [path for path in paths if not (root / path).exists()]
    if missing:
        raise SmokeError(f"missing required paths in {root}: {missing}")


def assert_full_release_references(product_root: Path) -> None:
    assert_required_paths(product_root, FULL_RELEASE_REFERENCE_PATHS)


def assert_private_runtime_state_absent(root: Path) -> None:
    leaked = [path for path in PRIVATE_RUNTIME_STATE_PATHS if (root / path).exists()]
    for pattern in PRIVATE_RUNTIME_STATE_GLOBS:
        leaked.extend(path.relative_to(root).as_posix() for path in root.glob(pattern))
    for rel_dir in PRIVATE_RUNTIME_STATE_DIRS:
        runtime_dir = root / rel_dir
        if runtime_dir.is_dir():
            leaked.extend(path.relative_to(root).as_posix() for path in runtime_dir.rglob("*"))
        elif runtime_dir.exists():
            leaked.append(rel_dir)
    if leaked:
        sample = ", ".join(sorted(leaked)[:20])
        raise SmokeError(f"private runtime state leaked into consumer install: {sample}")


def assert_full_runtime_gitignore(consumer: Path) -> None:
    gitignore = consumer / ".gitignore"
    if not gitignore.is_file():
        raise SmokeError(f"consumer install missing .gitignore: {consumer}")
    lines = {
        line.strip()
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = [rule for rule in FULL_RUNTIME_GITIGNORE_RULES if rule not in lines]
    if missing:
        raise SmokeError(f"consumer .gitignore missing Full runtime rules: {missing}")


def assert_installed_runtime_references(consumer: Path) -> None:
    missing: list[str] = []
    for path in sorted(consumer.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        source = path.relative_to(consumer).as_posix()
        if source not in INSTALLED_REFERENCE_SCAN_FILES and not source.startswith(
            INSTALLED_REFERENCE_SCAN_PREFIXES
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if source.startswith(".agents/skills/azoth-") and not any(
            marker in text for marker in AZOTH_WRAPPER_MARKERS
        ):
            continue
        for pattern in INSTALLED_REFERENCE_PATTERNS:
            for match in pattern.finditer(text):
                rel_path = match.group(0)
                if "*" in rel_path:
                    continue
                if not (consumer / rel_path).exists():
                    missing.append(f"{source} -> {rel_path}")

    if missing:
        sample = ", ".join(sorted(set(missing))[:20])
        raise SmokeError(f"consumer install references missing runtime paths: {sample}")


def assert_absent_prefixes(root: Path) -> None:
    files = rel_files(root)
    leaked: list[str] = []
    for prefix in ABSENT_PREFIXES:
        if prefix.endswith("/"):
            leaked.extend(path for path in files if path.startswith(prefix))
        elif (root / prefix).exists():
            leaked.append(prefix)
    if leaked:
        sample = ", ".join(sorted(leaked)[:20])
        raise SmokeError(f"product extract contains excluded paths: {sample}")

    local_names = {".DS_Store", "__pycache__"}
    local_hits = [path for path in files if any(part in local_names for part in path.split("/"))]
    if local_hits:
        sample = ", ".join(local_hits[:20])
        raise SmokeError(f"product extract contains local artifact names: {sample}")


def assert_sanitized(root: Path, strip_patterns: list[str]) -> None:
    effective_patterns = [
        pattern for pattern in strip_patterns if pattern and pattern != REDACTION_PLACEHOLDER
    ]
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in effective_patterns:
            if pattern in text:
                hits.append(f"{path.relative_to(root).as_posix()}:{pattern}")
    if hits:
        sample = ", ".join(hits[:20])
        raise SmokeError(f"product extract contains unsanitized source patterns: {sample}")


def assert_consumer_install(consumer: Path, *, setup_level: str | None = None) -> None:
    assert_required_paths(consumer, REQUIRED_CONSUMER_PATHS)
    manifest = yaml.safe_load((consumer / "azoth.yaml").read_text(encoding="utf-8"))
    platforms = manifest.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        raise SmokeError(f"consumer manifest platforms must be a non-empty list: {platforms!r}")
    if not all(isinstance(platform, str) and " " not in platform for platform in platforms):
        raise SmokeError(f"consumer manifest platforms must be separate strings: {platforms!r}")
    if "copilot" not in platforms:
        raise SmokeError(f"consumer manifest must include copilot: {platforms!r}")
    assert_private_runtime_state_absent(consumer)
    if setup_level == "3":
        assert_required_paths(consumer, FULL_CONSUMER_RUNTIME_PATHS)
        assert_full_runtime_gitignore(consumer)
        assert_installed_runtime_references(consumer)


def smoke_bash_install(product_root: Path, setup_level: str) -> Path:
    consumer = Path(tempfile.mkdtemp(prefix="azoth-consumer-smoke-"))
    env = {**os.environ, "AZOTH_PLATFORMS": "copilot"}
    run(
        ["bash", str(product_root / "install.sh")],
        cwd=consumer,
        input_text=f"{setup_level}\n",
        env=env,
    )
    assert_consumer_install(consumer, setup_level=setup_level)
    return consumer


def smoke_pwsh_install(product_root: Path, setup_level: str) -> tuple[str, Path | None]:
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return "skipped: pwsh/powershell not found", None
    consumer = Path(tempfile.mkdtemp(prefix="azoth-consumer-smoke-pwsh-"))
    env = {**os.environ, "AZOTH_PLATFORMS": "copilot"}
    run(
        [
            pwsh,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(product_root / "install.ps1"),
        ],
        cwd=consumer,
        input_text=f"{setup_level}\n",
        env=env,
    )
    assert_consumer_install(consumer, setup_level=setup_level)
    return "passed", consumer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Extraction staging directory. Existing contents are removed by the extractor.",
    )
    parser.add_argument("--setup-level", choices=("1", "2", "3"), default="2")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-ruff", action="store_true")
    args = parser.parse_args()

    out = args.out or Path(tempfile.mkdtemp(prefix="azoth-product-rc-smoke-"))
    out = out.resolve()

    config = load_config()
    strip_patterns = config.get("sanitize", {}).get("strip_patterns", [])
    if not isinstance(strip_patterns, list) or not all(isinstance(x, str) for x in strip_patterns):
        raise SmokeError("sanitize.strip_patterns must be a list of strings")

    run([sys.executable, str(EXTRACTOR), "--out", str(out)], cwd=ROOT)
    assert_required_paths(out, REQUIRED_PRODUCT_PATHS)
    assert_absent_prefixes(out)
    assert_sanitized(out, strip_patterns)
    if args.setup_level == "3":
        assert_full_release_references(out)

    run([sys.executable, "scripts/azoth_extract_product.py", "--validate-only"], cwd=out)
    run([sys.executable, "-c", "import yaml; yaml.safe_load(open('sync-config.yaml'))"], cwd=out)
    if not args.skip_ruff:
        run([sys.executable, "-m", "ruff", "check", "scripts/"], cwd=out)

    bash_consumer: Path | None = None
    pwsh_status = "skipped: --skip-install"
    pwsh_consumer: Path | None = None
    if not args.skip_install:
        bash_consumer = smoke_bash_install(out, args.setup_level)
        pwsh_status, pwsh_consumer = smoke_pwsh_install(out, args.setup_level)

    print("product_release_smoke: OK")
    print(f"extract: {out}")
    if bash_consumer:
        print(f"consumer_bash: {bash_consumer}")
    if pwsh_consumer:
        print(f"consumer_pwsh: {pwsh_consumer}")
    else:
        print(f"consumer_pwsh: {pwsh_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
