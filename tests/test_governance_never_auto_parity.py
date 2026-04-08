"""
BL-025: kernel/GOVERNANCE.md §5 Never-Auto (D26) must match UNIVERSAL_NEVER_AUTO
in scripts/azoth-deploy.py (OpenCode permission merge).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_GOVERNANCE = _REPO / "kernel" / "GOVERNANCE.md"
_SCRIPT = _REPO / "scripts" / "azoth-deploy.py"
_spec = importlib.util.spec_from_file_location("azoth_deploy", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
UNIVERSAL_NEVER_AUTO = _mod.UNIVERSAL_NEVER_AUTO


def _extract_never_auto_bullets(md: str) -> list[str]:
    """Lines under ### Never-Auto (Always Require Human Signal) until next ### or ##."""
    lines = md.splitlines()
    in_block = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "### Never-Auto (Always Require Human Signal)":
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if line.startswith("---"):
            break
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
    return out


def test_governance_never_auto_matches_universal_never_auto() -> None:
    text = _GOVERNANCE.read_text(encoding="utf-8")
    extracted = _extract_never_auto_bullets(text)
    assert extracted, "GOVERNANCE.md Never-Auto subsection missing or empty"
    assert extracted == list(UNIVERSAL_NEVER_AUTO), (
        f"GOVERNANCE Never-Auto bullets {extracted!r} != "
        f"UNIVERSAL_NEVER_AUTO {list(UNIVERSAL_NEVER_AUTO)!r}"
    )

