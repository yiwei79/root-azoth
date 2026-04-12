"""v0.2.0 roadmap task specs carry decision_ref aligned with roadmap.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ROADMAP = REPO / ".azoth" / "roadmap.yaml"
SPECS_DIR = REPO / ".azoth" / "roadmap-specs" / "v0.2.0"


def _find_task(road: dict, tid: str) -> dict | None:
    """Find a task by id in any v0.2.0-pN version tasks/completed_tasks, or initiatives (by task_ref)."""
    for block in road["versions"]:
        bid = block.get("id", "")
        if bid.startswith("v0.2.0-p"):
            all_tasks = (block.get("tasks") or []) + (block.get("completed_tasks") or [])
            for t in all_tasks:
                if t.get("id") == tid:
                    return t
    for ini in road.get("initiatives") or []:
        if ini.get("task_ref") == tid or ini.get("id") == tid:
            return ini
    return None


def test_v020_spec_files_have_decision_ref() -> None:
    for path in sorted(SPECS_DIR.glob("P*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "decision_ref" in data, f"{path.name} missing decision_ref"
        assert isinstance(data["decision_ref"], list), f"{path.name} decision_ref not a list"


def test_v020_roadmap_tasks_match_spec_decision_ref() -> None:
    road = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))
    for tid in (
        "P5-006",
        "P1-001",
        "P1-002",
        "P1-003",
        "P1-004",
        "P1-005",
        "P1-006",
        "P1-007",
        "P1-008",
        "P1-009",
        "P1-010",
        "P1-011",
        "P1-012",
        "P1-013",
    ):
        task = _find_task(road, tid)
        assert task is not None, (
            f"roadmap missing task {tid} "
            "(not found in active version tasks or initiatives task_ref)"
        )
        spec_path = SPECS_DIR / f"{tid}.yaml"
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        assert spec["decision_ref"] == task.get("decision_ref"), (
            f"{tid}: spec decision_ref {spec['decision_ref']!r} != "
            f"roadmap {task.get('decision_ref')!r}"
        )
