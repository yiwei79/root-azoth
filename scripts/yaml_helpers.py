#!/usr/bin/env python3
"""
yaml_helpers.py - Shared safe YAML helpers for hot Azoth scripts.

Uses PyYAML's C-backed SafeLoader when available, with the pure-Python
SafeLoader as a compatibility fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def safe_load_yaml(text: str) -> Any:
    """Load YAML text with the fastest available safe loader."""
    return yaml.load(text, Loader=YAML_SAFE_LOADER)


def safe_load_yaml_path(path: Path) -> Any:
    """Load a YAML file using UTF-8 text and the shared safe loader."""
    return safe_load_yaml(path.read_text(encoding="utf-8"))
