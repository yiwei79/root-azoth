from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from personal_harness_daily_flow import run_daily_flow  # noqa: E402
from test_cockpit_bootstrap_verify import _write_cockpit_bootstrap_fixture  # noqa: E402
from test_personal_knowledge_recall import _card, _write_yaml  # noqa: E402


def _write_memory_fixture(repo: Path) -> None:
    memory_dir = repo / ".azoth" / "memory"
    memory_dir.mkdir(parents=True)
    episode = {
        "id": "ep-463",
        "timestamp": "2026-05-01T00:00:00Z",
        "type": "pattern",
        "goal": "Verify context before project work",
        "summary": "Run-ledger clobber taught fail-closed write claims.",
        "lessons": ["Keep write claims explicit before autonomous work."],
        "tags": ["context", "write-claim"],
        "reinforcement_count": 1,
        "context": {},
    }
    (memory_dir / "episodes.jsonl").write_text(json.dumps(episode) + "\n", encoding="utf-8")
    (memory_dir / "patterns.yaml").write_text(
        yaml.safe_dump({"patterns": []}, sort_keys=False),
        encoding="utf-8",
    )


def _write_personal_cards(personal_root: Path) -> None:
    card_dir = personal_root / ".azoth" / "knowledge" / "cards" / "root-azoth"
    for index in range(1, 6):
        card_id = f"kb-root-azoth-00{index}"
        _write_yaml(card_dir / f"{card_id}.yaml", _card(card_id))


def test_daily_flow_verifies_cockpit_readback_and_context_packet(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_memory_fixture(tmp_path)

    report = run_daily_flow(
        cockpit_root=cockpit,
        repo_root=tmp_path,
        project_id="ras-or-ray",
        goal="Verify context before project work",
        requested_actions=("focused_verification",),
        query_tags=("context",),
        as_of="2026-05-03T00:00:00Z",
    )

    assert report["packet_type"] == "personal_harness_daily_flow"
    assert report["ok"] is True
    assert report["cockpit"]["project_id"] == "ras-or-ray"
    assert report["cockpit"]["selected_mode"] == "assisted"
    assert report["cockpit"]["menu_has_context_command"] is True
    assert report["cockpit"]["personal_knowledge_root"] == ""
    assert report["context_packet"]["context_view"]["harness_profile"] == "assisted"
    assert report["context_packet"]["context_view"]["route_capsule"]["route_state"] == "assist"
    assert report["context_packet"]["context_view"]["project_context"] == {
        "project": "ras-or-ray",
        "selected_mode": "assisted",
        "freshness": "current",
        "receipt_ref": ".azoth/projects/handoffs/t-049-ras-or-ray-2026-05-01.yaml",
    }
    assert report["context_packet"]["context_view"]["memory_context"][0]["id"] == "ep-463"
    assert report["context_packet"]["context_view"]["personal_context"] == []
    assert report["personal_knowledge_review"]["summary"]["overall_status"] == "skipped"
    assert {check["status"] for check in report["checks"]} == {"pass"}
    assert report["no_write_contract"] == {
        "cockpit_repo_mutated": False,
        "project_repo_mutated": False,
        "project_context_imported": False,
    }


def test_daily_flow_auto_loads_cockpit_personal_knowledge(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_memory_fixture(tmp_path)
    _write_personal_cards(cockpit)

    report = run_daily_flow(
        cockpit_root=cockpit,
        repo_root=tmp_path,
        project_id="ras-or-ray",
        goal="Verify context before project work",
        requested_actions=("focused_verification",),
        query_tags=("context",),
        as_of="2026-05-03T00:00:00Z",
    )

    assert report["ok"] is True
    assert report["cockpit"]["personal_knowledge_root"] == str(cockpit)
    personal_context = report["context_packet"]["context_view"]["personal_context"]
    review = report["personal_knowledge_review"]
    assert [item["card_id"] for item in personal_context] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
    ]
    assert review["summary"]["overall_status"] == "current"
    assert review["summary"]["total_cards"] == 4
    assert review["due_cards"] == []
    assert any(
        check["id"] == "personal_context_loaded" and check["status"] == "pass"
        for check in report["checks"]
    )
    assert any(
        check["id"] == "personal_context_freshness" and check["status"] == "pass"
        for check in report["checks"]
    )


def test_daily_flow_warns_when_personal_knowledge_needs_review(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_memory_fixture(tmp_path)
    _write_personal_cards(cockpit)

    report = run_daily_flow(
        cockpit_root=cockpit,
        repo_root=tmp_path,
        project_id="ras-or-ray",
        goal="Verify context before project work",
        requested_actions=("focused_verification",),
        query_tags=("context",),
        as_of="2026-06-01T00:00:00Z",
    )

    assert report["ok"] is True
    assert report["context_packet"]["warnings"] == [
        "personal knowledge review due: kb-root-azoth-001, kb-root-azoth-002, "
        "kb-root-azoth-003, kb-root-azoth-004"
    ]
    assert report["personal_knowledge_review"]["summary"] == {
        "total_cards": 4,
        "current_cards": 0,
        "review_due_cards": 4,
        "requires_operator_review": True,
        "overall_status": "review_due",
    }
    assert [card["card_id"] for card in report["personal_knowledge_review"]["due_cards"]] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
        "kb-root-azoth-004",
    ]
    assert any(
        check["id"] == "personal_context_freshness"
        and check["status"] == "warn"
        and "kb-root-azoth-001" in check["summary"]
        and "kb-root-azoth-004" in check["summary"]
        for check in report["checks"]
    )


def test_daily_flow_fails_closed_when_cockpit_mode_disagrees_with_route(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_memory_fixture(tmp_path)
    index_path = cockpit / ".azoth" / "projects" / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["projects"][0]["selected_mode"] = "guide"
    index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

    report = run_daily_flow(
        cockpit_root=cockpit,
        repo_root=tmp_path,
        project_id="ras-or-ray",
        goal="Verify context before project work",
        requested_actions=("focused_verification",),
        query_tags=("context",),
        as_of="2026-05-03T00:00:00Z",
    )

    assert report["ok"] is False
    assert any(check["id"] == "mode_consistency" and check["status"] == "fail" for check in report["checks"])


def test_daily_flow_cli_outputs_json(tmp_path: Path) -> None:
    cockpit = _write_cockpit_bootstrap_fixture(tmp_path / "yiwei-azoth-cockpit")
    _write_memory_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_harness_daily_flow.py"),
            "--cockpit-root",
            str(cockpit),
            "--repo-root",
            str(tmp_path),
            "--project",
            "ras-or-ray",
            "--goal",
            "Verify context before project work",
            "--action",
            "focused_verification",
            "--tag",
            "context",
            "--as-of",
            "2026-05-03T00:00:00Z",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["packet_type"] == "personal_harness_daily_flow"
    assert report["ok"] is True
