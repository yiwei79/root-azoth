from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from personal_knowledge_review import build_review_packet  # noqa: E402
from test_personal_knowledge_recall import _write_personal_root  # noqa: E402


def test_review_packet_reports_current_session_start_cards_without_body(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    packet = build_review_packet(
        personal_root,
        as_of=date(2026, 5, 3),
    )

    assert packet["packet_type"] == "personal_knowledge_review"
    assert packet["summary"] == {
        "total_cards": 4,
        "current_cards": 4,
        "review_due_cards": 0,
        "requires_operator_review": False,
        "overall_status": "current",
    }
    assert [card["card_id"] for card in packet["cards"]] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
        "kb-root-azoth-004",
    ]
    assert packet["due_cards"] == []
    assert "body" not in str(packet)
    assert packet["no_write_contract"] == {
        "writes_personal_root": False,
        "reads_raw_memory_or_inbox": False,
        "imports_unreviewed_sources": False,
    }


def test_review_packet_makes_due_cards_actionable(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    packet = build_review_packet(
        personal_root,
        as_of=date(2026, 6, 1),
    )

    assert packet["summary"] == {
        "total_cards": 4,
        "current_cards": 0,
        "review_due_cards": 4,
        "requires_operator_review": True,
        "overall_status": "review_due",
    }
    assert [card["card_id"] for card in packet["due_cards"]] == [
        "kb-root-azoth-001",
        "kb-root-azoth-002",
        "kb-root-azoth-003",
        "kb-root-azoth-004",
    ]
    assert {card["review_reason"] for card in packet["due_cards"]} == {
        "card review_after date has passed"
    }
    assert "approved personal-knowledge review lane" in packet["next_safe_action"]
    assert "kb-root-azoth-004" in packet["next_safe_action"]


def test_review_cli_outputs_json_and_can_fail_on_due(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    ok = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_knowledge_review.py"),
            "--personal-root",
            str(personal_root),
            "--as-of",
            "2026-05-03",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    due = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_knowledge_review.py"),
            "--personal-root",
            str(personal_root),
            "--as-of",
            "2026-06-01",
            "--fail-on-due",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["summary"]["overall_status"] == "current"
    assert due.returncode == 2
    assert json.loads(due.stdout)["summary"]["overall_status"] == "review_due"


def test_review_cli_requires_json(tmp_path: Path) -> None:
    personal_root = _write_personal_root(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "personal_knowledge_review.py"),
            "--personal-root",
            str(personal_root),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires --json" in result.stderr
