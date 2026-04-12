"""
P1-014 backlog closure tests.

Verifies that the Antigravity bootstrap adapter delivery is recorded as complete
in the backlog, and that the core acceptance criteria hold structurally.
"""
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).parent.parent
BACKLOG_PATH = REPO_ROOT / ".azoth" / "backlog.yaml"
SKILL_PATH = REPO_ROOT / ".agents" / "skills" / "azoth-operating-model" / "SKILL.md"
RULE_PATH = REPO_ROOT / ".agents" / "rules" / "azoth-core.md"


def _load_backlog() -> dict:
    with open(BACKLOG_PATH) as f:
        return yaml.safe_load(f)


def _find_item(backlog: dict, item_id: str) -> Optional[dict]:
    return next(
        (i for i in backlog.get("items", []) if i["id"] == item_id), None
    )


def test_p1014_status_is_complete() -> None:
    """P1-014 must be marked complete after delivery."""
    backlog = _load_backlog()
    item = _find_item(backlog, "P1-014")
    assert item is not None, "P1-014 not found in backlog"
    assert item["status"] == "complete", (
        f"Expected status 'complete', got '{item['status']}'"
    )


def test_p1014_completed_date_present() -> None:
    """P1-014 must have a completed_date field set to the delivery date."""
    backlog = _load_backlog()
    item = _find_item(backlog, "P1-014")
    assert item is not None, "P1-014 not found in backlog"
    assert "completed_date" in item, "completed_date field missing from P1-014"
    assert item["completed_date"], "completed_date must not be empty"


def test_p1015_unblocked_by_p1014_complete() -> None:
    """P1-015 is blocked_by P1-014; with P1-014 complete, P1-015 becomes unblocked."""
    backlog = _load_backlog()
    p1014 = _find_item(backlog, "P1-014")
    p1015 = _find_item(backlog, "P1-015")
    assert p1014 is not None, "P1-014 not found"
    assert p1015 is not None, "P1-015 not found"
    assert "P1-014" in (p1015.get("blocked_by") or []), (
        "P1-015 should list P1-014 in blocked_by"
    )
    assert p1014["status"] == "complete", (
        "P1-014 must be complete for P1-015 to be considered unblocked"
    )


def test_azoth_operating_model_skill_references_azoth_state() -> None:
    """AC4: Skill must reference .azoth/ as authoritative state and address scope/boundary."""
    content = SKILL_PATH.read_text()
    assert ".azoth/" in content, (
        "Operating model skill must reference .azoth/ as the authoritative state layer (AC4)"
    )
    assert "scope" in content.lower(), (
        "Operating model skill must address scope discipline (AC4)"
    )
    assert "boundary" in content.lower() or "bootstrap" in content.lower(), (
        "Operating model skill must address platform-boundary guidance (AC4)"
    )


def test_azoth_core_rule_refuses_governed_work() -> None:
    """AC5: Always-on rule must explicitly refuse kernel/M1/governed work."""
    content = RULE_PATH.read_text()
    assert "kernel" in content.lower(), (
        "azoth-core.md must reference kernel boundary (AC5)"
    )
    assert "M1" in content or "governed" in content.lower(), (
        "azoth-core.md must refuse governed M1 work (AC5)"
    )
    assert "stop" in content.lower() or "redirect" in content.lower(), (
        "azoth-core.md must instruct agent to stop or redirect for out-of-scope work (AC5)"
    )
