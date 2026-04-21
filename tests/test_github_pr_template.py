"""Drift guard: PR template + Copilot instructions stay present for inbox-only reviews."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "rel",
    [
        ".github/pull_request_template.md",
        ".github/copilot-instructions.md",
    ],
)
def test_pr_copilot_docs_exist(rel: str) -> None:
    path = REPO / rel
    assert path.is_file(), f"missing {path}"


def test_pull_request_template_mentions_inbox_contract() -> None:
    text = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "D32" in text
    assert ".azoth/inbox" in text
    assert "/intake" in text
    assert "Copilot" in text


def test_copilot_instructions_reference_governance_d32() -> None:
    text = (REPO / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "GOVERNANCE.md" in text
    assert "D32" in text
    assert ".azoth/inbox" in text


def test_copilot_instructions_enforce_pipeline_entry_behavior() -> None:
    text = (REPO / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    for token in ("/auto", "/dynamic-full-auto", "/deliver", "/deliver-full"):
        assert token in text, f"copilot instructions must mention explicit pipeline token {token}"
    assert "do not execute the work inline in main chat" in text
    assert "Task" in text
    assert "orchestrator" in text.lower()


def test_copilot_instructions_document_closeout_memory_mirror() -> None:
    text = (REPO / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "/session-closeout" in text
    assert ".azoth" in text
    assert "~/.claude/projects/<project-key>/memory/" in text


def test_copilot_instructions_document_memory_operation_parity() -> None:
    text = (REPO / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    for token in (
        "context-recall",
        "/remember",
        "/promote",
        ".azoth/memory/episodes.jsonl",
        ".azoth/memory/patterns.yaml",
    ):
        assert token in text, f"copilot instructions must mention {token}"


def test_copilot_instructions_template_documents_memory_operation_parity() -> None:
    text = (REPO / "kernel" / "templates" / "copilot-instructions.md.template").read_text(
        encoding="utf-8"
    )
    for token in (
        "context-recall",
        "/remember",
        "/promote",
        ".azoth/memory/episodes.jsonl",
        ".azoth/memory/patterns.yaml",
    ):
        assert token in text, f"copilot instructions template must mention {token}"
