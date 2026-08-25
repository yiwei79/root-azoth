from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    (ROOT / "kernel" / "templates" / "public-scripts").is_dir(),
    reason="public-script templates are exercised after product extraction",
)
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from personal_knowledge_review import build_review_packet  # noqa: E402
from test_public_personal_knowledge_recall import _approved_root  # noqa: E402


def test_review_reports_manifest_approved_card_without_writes(tmp_path: Path) -> None:
    personal_root = _approved_root(tmp_path)

    packet = build_review_packet(personal_root, as_of=date(2026, 8, 25))

    assert packet["summary"] == {
        "total_cards": 1,
        "current_cards": 1,
        "review_due_cards": 0,
        "requires_operator_review": False,
        "overall_status": "current",
    }
    assert packet["no_write_contract"] == {
        "writes_personal_root": False,
        "reads_raw_memory_or_inbox": False,
        "imports_unreviewed_sources": False,
    }
    assert "body" not in str(packet)
