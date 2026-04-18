"""v0.2.0 roadmap task specs carry decision_ref aligned with roadmap.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ROADMAP = REPO / ".azoth" / "roadmap.yaml"
BACKLOG = REPO / ".azoth" / "backlog.yaml"
SPECS_DIR = REPO / ".azoth" / "roadmap-specs" / "v0.2.0"


def _find_task(road: dict, tid: str) -> dict | None:
    """Find a task by id in any v0.2.0-pN version tasks/completed_tasks, or initiatives."""
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
        for item in ini.get("slices") or []:
            if isinstance(item, dict) and item.get("task_ref") == tid:
                return ini
    return None


def _find_backlog_item(backlog: dict, tid: str) -> dict | None:
    for item in backlog.get("items") or []:
        if item.get("id") == tid:
            return item
    return None


def test_v020_spec_files_have_decision_ref() -> None:
    for path in sorted(SPECS_DIR.glob("[PT]*.yaml")):
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
        "T-005",
        "T-008",
        "T-009",
        "T-010",
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


def test_schedulable_pipeline_initiatives_do_not_point_at_completed_seed_specs() -> None:
    road = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(BACKLOG.read_text(encoding="utf-8"))

    completed_ids: set[str] = set()
    active_p2_tasks: set[str] = set()
    for block in road["versions"]:
        bid = block.get("id", "")
        if bid.startswith("v0.2.0-p"):
            for task in block.get("completed_tasks") or []:
                completed_ids.add(str(task.get("id")))
        if bid == "v0.2.0-p2":
            for task in block.get("tasks") or []:
                active_p2_tasks.add(str(task.get("id")))

    initiatives = {item["id"]: item for item in road.get("initiatives") or []}

    ppl001 = initiatives["INI-PPL-001"]
    assert ppl001.get("task_ref") not in completed_ids, (
        "INI-PPL-001 is schedulable follow-on work and must point at a live residual task, "
        "not a completed seed task."
    )
    assert str(ppl001.get("spec_ref") or "").endswith("/T-005.yaml"), (
        "INI-PPL-001 should point at the residual T-005 spec."
    )
    backlog_t005 = _find_backlog_item(backlog, "T-005")
    assert backlog_t005 is not None, "T-005 must exist in backlog.yaml"
    assert backlog_t005.get("initiative_ref") == "INI-PPL-001", (
        "T-005 backlog row must link back to INI-PPL-001."
    )
    assert backlog_t005.get("roadmap_ref") == "T-005", (
        "T-005 backlog row must point at its roadmap task id."
    )
    assert backlog_t005.get("target_version") == "v0.2.0-p2", (
        "T-005 backlog row must target v0.2.0-p2."
    )
    assert backlog_t005.get("decision_ref") == ppl001.get("decision_ref"), (
        "T-005 backlog decision_ref must match the initiative decision_ref."
    )

    ppl002 = initiatives["INI-PPL-002"]
    assert ppl002.get("task_ref") in completed_ids, (
        "INI-PPL-002 should remain linked to its historical completed seed task "
        "until a real residual slice is minted."
    )
    assert ppl002.get("phase") is None, (
        "Historical-only initiatives should remain unscheduled until a real residual slice exists."
    )
    assert str(ppl002.get("task_ref")) not in active_p2_tasks, (
        "Historical completed seed tasks must not reappear in the active p2 task list "
        "as if they were scheduled follow-on work."
    )


def test_evidence_grounding_initiative_is_multi_dimensional_and_slice_backed() -> None:
    road = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))
    initiatives = {item["id"]: item for item in road.get("initiatives") or []}

    evi001 = initiatives["INI-EVI-001"]
    assert evi001.get("theme") == "B"
    assert evi001.get("category") == "pipeline"
    assert evi001.get("dimensions") == {
        "themes": ["B", "C", "D"],
        "categories": ["pipeline", "memory", "platform"],
        "tracks": ["research-sufficiency", "evidence-capsules", "freshness"],
    }
    slices = evi001.get("slices") or []
    assert [item.get("task_ref") for item in slices] == ["T-008", "T-009", "T-010"]
    assert slices[0]["role"] == "primary"
    assert slices[0]["status"] == "active"
    assert slices[1]["status"] == "planned"
    assert slices[2]["status"] == "planned"


def test_all_initiatives_expose_dimensions_and_slices() -> None:
    road = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))

    for initiative in road.get("initiatives") or []:
        assert "dimensions" in initiative, f"{initiative['id']} missing dimensions"
        assert "slices" in initiative, f"{initiative['id']} missing slices"
        dimensions = initiative["dimensions"]
        assert isinstance(dimensions, dict), f"{initiative['id']} dimensions must be a mapping"
        assert isinstance(dimensions.get("themes"), list), (
            f"{initiative['id']} themes must be a list"
        )
        assert isinstance(dimensions.get("categories"), list), (
            f"{initiative['id']} categories must be a list"
        )
        assert isinstance(dimensions.get("tracks"), list), (
            f"{initiative['id']} tracks must be a list"
        )
        assert isinstance(initiative["slices"], list), f"{initiative['id']} slices must be a list"
