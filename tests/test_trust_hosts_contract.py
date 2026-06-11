from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
TRUST_HOSTS_PATH = REPO_ROOT / "kernel" / "TRUST_HOSTS.md"
TRUST_HOSTS_YAML = REPO_ROOT / "kernel" / "trust_hosts.yaml"


def _parse_trust_hosts_markdown(text: str) -> dict[str, object]:
    """Pull the YAML block between the trust_hosts fence markers."""
    start = text.find("<!-- trust_hosts:start -->")
    end = text.find("<!-- trust_hosts:end -->")
    assert start >= 0 and end > start, "TRUST_HOSTS.md must contain trust_hosts:start/end fences"
    block = text[start + len("<!-- trust_hosts:start -->"):end].strip()
    return yaml.safe_load(block)


def test_trust_hosts_md_exists_with_required_fences() -> None:
    assert TRUST_HOSTS_PATH.is_file(), "kernel/TRUST_HOSTS.md is missing"


def test_trust_hosts_yaml_block_is_parseable() -> None:
    payload = _parse_trust_hosts_markdown(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "trust_bearing_hosts" in payload
    assert "best_effort_mirrors" in payload


def test_trust_bearing_hosts_are_exactly_three() -> None:
    payload = _parse_trust_hosts_markdown(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    hosts = sorted(str(h) for h in payload["trust_bearing_hosts"])
    assert hosts == ["codex", "hermes", "opencode"], (
        "Trust-bearing hosts must be exactly Codex + Hermes + OpenCode."
    )


def test_best_effort_mirrors_include_four_remaining_platforms() -> None:
    payload = _parse_trust_hosts_markdown(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    mirrors = sorted(str(m) for m in payload["best_effort_mirrors"])
    # 6 hosts total; 3 trust-bearing + 3 best-effort mirrors
    assert mirrors == ["antigravity", "claude_code", "copilot", "cursor", "gemini"], (
        "Best-effort mirrors must include antigravity, claude_code, copilot, cursor, gemini."
    )


def test_runtime_guards_listed_are_filenames_only() -> None:
    payload = _parse_trust_hosts_markdown(TRUST_HOSTS_PATH.read_text(encoding="utf-8"))
    guards = payload.get("runtime_guards", {}).get("trust_bearing") or []
    assert isinstance(guards, list)
    assert len(guards) >= 4, "Must list at least 4 friction-event guards"
    for g in guards:
        assert isinstance(g, str)
        assert g.startswith("scripts/check_fd_"), f"Guard name {g!r} must follow scripts/check_fd_*.py"
