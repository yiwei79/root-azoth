"""P1-006: session-closeout W2 names session-state handoff path."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CLOSEOUT = REPO / ".claude" / "commands" / "session-closeout.md"
CONTRACT = REPO / "commands" / "session-closeout" / "command.yaml"
CANONICAL_BODY = REPO / "commands" / "session-closeout" / "body.md"
ARCHITECTURE = REPO / "docs" / "AZOTH_ARCHITECTURE.md"


def test_w2_mentions_session_state_path() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert ".azoth/session-state.md" in text


def test_closeout_mentions_governed_final_delivery_approval_dependency() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")
    assert ".azoth/final-delivery-approvals.jsonl" in text
    assert "human final-delivery approval" in text


def test_session_closeout_contract_uses_canonical_body_source() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["body"] == {
        "mode": "canonical_markdown",
        "source_path": "commands/session-closeout/body.md",
    }
    assert contract["execution"]["kind"] == "closeout"


def test_canonical_closeout_body_documents_semantics_payload_and_w3_default() -> None:
    text = CANONICAL_BODY.read_text(encoding="utf-8")
    assert "--semantics-file" in text
    assert "\"schema_version\": 1" in text
    assert "\"mode\": \"defer\"" in text
    assert "saved `next_step` checkpoint" in text


def test_architecture_matches_always_fire_version_bump_rule() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "final step always calls `version-bump.py --patch`" in text
    assert "after\n  confirming at least one artifact was written this session" not in text
