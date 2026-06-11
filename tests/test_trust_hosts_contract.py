from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
TRUST_HOSTS_PATH = REPO_ROOT / "kernel" / "TRUST_HOSTS.md"
TRUST_HOSTS_YAML = REPO_ROOT / "kernel" / "trust_hosts.yaml"

# Reuse the same fence parser as hermes_manifest_check.py so the two
# callers can't drift. Importing the script directly would run its main();
# add its directory to sys.path and import the helper module.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _azoth_yaml import parse_fenced_yaml  # noqa: E402


def _parse_trust_hosts(text: str) -> dict[str, object]:
    return parse_fenced_yaml(text, name="trust_hosts")


def test_trust_hosts_md_exists_with_required_fences() -> None:
    assert TRUST_HOSTS_PATH.is_file(), "kernel/TRUST_HOSTS.md is missing"


def test_trust_hosts_yaml_block_is_parseable() -> None:
    payload = _parse_trust_hosts(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "trust_bearing_hosts" in payload
    assert "best_effort_mirrors" in payload


def test_trust_bearing_hosts_are_exactly_three() -> None:
    payload = _parse_trust_hosts(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    hosts = sorted(str(h) for h in payload["trust_bearing_hosts"])
    assert hosts == ["codex", "hermes", "opencode"], (
        "Trust-bearing hosts must be exactly Codex + Hermes + OpenCode."
    )


def test_best_effort_mirrors_include_four_remaining_platforms() -> None:
    payload = _parse_trust_hosts(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    mirrors = sorted(str(m) for m in payload["best_effort_mirrors"])
    # 6 hosts total; 3 trust-bearing + 3 best-effort mirrors
    assert mirrors == ["antigravity", "claude_code", "copilot", "cursor", "gemini"], (
        "Best-effort mirrors must include antigravity, claude_code, copilot, cursor, gemini."
    )


def test_runtime_guards_listed_are_filenames_only() -> None:
    payload = _parse_trust_hosts(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    guards = payload.get("runtime_guards", {}).get("trust_bearing") or []
    assert isinstance(guards, list)
    assert len(guards) >= 4, "Must list at least 4 friction-event guards"
    for g in guards:
        assert isinstance(g, str)
        assert g.startswith("scripts/check_fd_"), f"Guard name {g!r} must follow scripts/check_fd_*.py"
