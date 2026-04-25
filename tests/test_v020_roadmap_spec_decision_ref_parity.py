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
        "T-015",
        "T-016",
        "T-017",
        "T-025",
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


def test_codex_model_selection_shipped_continuity() -> None:
    road = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))
    backlog = yaml.safe_load(BACKLOG.read_text(encoding="utf-8"))
    proposal = yaml.safe_load(
        (REPO / ".azoth" / "proposals" / "codex-intelligent-model-selection.yaml").read_text(
            encoding="utf-8"
        )
    )

    p3 = next(block for block in road["versions"] if block.get("id") == "v0.2.0-p3")
    active_tasks = {item["id"]: item for item in p3.get("tasks") or []}
    completed_tasks = {item["id"]: item for item in p3.get("completed_tasks") or []}

    assert "T-017" not in active_tasks, "Shipped T-017 must not remain in the live p3 task list."
    assert "T-015" in completed_tasks, "v0.2.0-p3 should retain T-015 as completed history."
    assert "T-016" in completed_tasks, "v0.2.0-p3 should retain T-016 as completed history."
    assert "T-017" in completed_tasks, "v0.2.0-p3 should preserve T-017 as shipped history."
    assert "T-025" in completed_tasks, "v0.2.0-p3 should preserve T-025 as shipped history."
    assert completed_tasks["T-015"].get("decision_ref") == ["D19", "D21", "D23", "D46", "D52"]
    assert completed_tasks["T-016"].get("decision_ref") == ["D19", "D46", "D50", "D52"]
    assert completed_tasks["T-017"].get("decision_ref") == ["D19", "D21", "D23", "D46", "D52"]

    backlog_t015 = _find_backlog_item(backlog, "T-015")
    backlog_t017 = _find_backlog_item(backlog, "T-017")
    backlog_t025 = _find_backlog_item(backlog, "T-025")
    assert backlog_t015 is not None, "T-015 must exist in backlog.yaml as the restored seed row."
    assert backlog_t017 is not None, "T-017 must exist in backlog.yaml as the shipped selector-policy row."
    assert backlog_t025 is not None, "T-025 must exist in backlog.yaml as the runtime resolver row."
    assert backlog_t015.get("status") == "complete"
    assert backlog_t015.get("roadmap_ref") == "T-015"
    assert backlog_t017.get("status") == "complete"
    assert backlog_t017.get("initiative_ref") == "INI-PLT-006"
    assert backlog_t017.get("roadmap_ref") == "T-017"
    assert backlog_t025.get("status") == "complete"
    assert backlog_t025.get("initiative_ref") == "INI-PLT-006"
    assert backlog_t025.get("roadmap_ref") == "T-025"

    initiatives = {item["id"]: item for item in road.get("initiatives") or []}
    plt006 = initiatives["INI-PLT-006"]
    assert plt006.get("task_ref") is None, (
        "INI-PLT-006 should not point at completed T-017 as if it were still live work."
    )
    t017_slice = next(item for item in plt006.get("slices") or [] if item.get("task_ref") == "T-017")
    assert t017_slice.get("status") == "complete"
    assert t017_slice.get("role") == "historical"
    t025_slice = next(item for item in plt006.get("slices") or [] if item.get("task_ref") == "T-025")
    assert t025_slice.get("status") == "complete"
    assert t025_slice.get("role") == "historical"

    shipped_follow_on = proposal["details"]["shipped_follow_on"]
    assert shipped_follow_on["backlog_id"] == "T-017"
    assert "shipped the selector-policy and task-definition lane" in shipped_follow_on["note"]
    next_follow_on = proposal["details"]["next_follow_on"]
    assert next_follow_on["backlog_id"] == "T-025"
    assert "runtime bridge follow-on" in next_follow_on["note"]


def test_codex_permissions_follow_on_history_is_preserved() -> None:
    backlog = yaml.safe_load(BACKLOG.read_text(encoding="utf-8"))

    backlog_t016 = _find_backlog_item(backlog, "T-016")
    assert backlog_t016 is not None, "T-016 must exist in backlog.yaml."
    assert backlog_t016.get("status") == "complete"


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
    assert ppl001.get("phase") is None
    assert ppl001.get("task_ref") is None
    assert ppl001.get("spec_ref") is None
    slices = ppl001.get("slices") or []
    assert [item.get("task_ref") for item in slices] == ["T-005", "T-006"]
    assert all(item.get("status") == "complete" for item in slices)
    assert all(item.get("role") == "historical" for item in slices)
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
    # The evidence-grounding rollout is complete, so the initiative should now be
    # historical-only rather than scheduled against a stale slice alias.
    assert evi001.get("phase") is None
    assert evi001.get("task_ref") is None
    assert evi001.get("spec_ref") is None
    assert slices[0]["role"] == "historical"
    assert slices[0]["status"] == "complete"
    assert slices[1]["role"] == "historical"
    assert slices[1]["status"] == "complete"
    assert slices[2]["role"] == "historical"
    assert slices[2]["status"] == "complete"


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
