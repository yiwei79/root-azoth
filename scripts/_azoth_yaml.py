"""Shared YAML-fence parser for Azoth markdown files.

Several Azoth markdown files (TRUST_HOSTS.md, the policy docs) embed
machine-readable YAML blocks between HTML-comment fence markers:

    <!-- name:start -->
    key: value
    <!-- name:end -->

This module exposes a single helper that extracts and parses the block,
returning the parsed object. It is used by both the manifest check
(scripts/hermes_manifest_check.py) and the trust-host contract test
(tests/test_trust_hosts_contract.py) so the two callers can't drift.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def parse_fenced_yaml(text: str, *, name: str) -> dict[str, Any]:
    """Extract and parse the YAML block between <!-- name:start --> and <!-- name:end -->.

    Raises AssertionError if the fences are missing or the block is empty.
    Raises yaml.YAMLError if the block does not parse.
    """
    start_marker = f"<!-- {name}:start -->"
    end_marker = f"<!-- {name}:end -->"
    start = text.find(start_marker)
    end = text.find(end_marker)
    assert start >= 0, f"missing {start_marker} fence"
    assert end > start, f"missing {end_marker} fence after start"
    block = text[start + len(start_marker) : end].strip()
    assert block, f"{name} fence block is empty"
    loaded = yaml.safe_load(block)
    assert isinstance(loaded, dict), f"{name} fence block must parse to a dict"
    return loaded


def load_fenced_yaml_file(path: Path, *, name: str) -> dict[str, Any]:
    """Read the file at `path` and parse its named YAML fence."""
    return parse_fenced_yaml(path.read_text(encoding="utf-8"), name=name)
