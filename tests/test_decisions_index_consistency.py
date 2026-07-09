from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DECISIONS_INDEX = ROOT / "docs" / "DECISIONS_INDEX.md"
DECISION_ROW_RE = re.compile(r"^\| D(\d+) \|", re.MULTILINE)


def _decision_numbers() -> list[int]:
    text = DECISIONS_INDEX.read_text(encoding="utf-8")
    return [int(match.group(1)) for match in DECISION_ROW_RE.finditer(text)]


def test_decision_count_references_match_decisions_index() -> None:
    numbers = _decision_numbers()
    assert numbers, "docs/DECISIONS_INDEX.md must contain D-number rows"
    count = len(numbers)
    highest = max(numbers)
    expected_range = f"D1–D{highest}"
    expected_count = f"{count} decisions"

    index_text = DECISIONS_INDEX.read_text(encoding="utf-8")
    assert expected_range in index_text
    assert f"| **Total** | **{count}** |" in index_text

    for rel in (
        "CLAUDE.md",
        "GEMINI.md",
        "kernel/templates/platform-adapters/gemini/GEMINI.md.template",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert expected_count in text, f"{rel} must mention {expected_count}"
