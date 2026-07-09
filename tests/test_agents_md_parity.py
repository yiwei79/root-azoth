from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSHOP_AGENTS = REPO_ROOT / "AGENTS.md"

# Workshop wording (canonical)
CANONICAL_PHRASE = "per scope-gated session"


def test_workshop_agents_md_uses_scope_gated_wording() -> None:
    text = WORKSHOP_AGENTS.read_text(encoding="utf-8")
    assert CANONICAL_PHRASE in text, (
        "Workshop AGENTS.md regressed: must reference scope-gated sessions, not per-session"
    )


def test_no_per_session_entropy_wording_remains() -> None:
    """Catch the original drift: 'per session' that is NOT followed by 'scope-gated'."""
    text = WORKSHOP_AGENTS.read_text(encoding="utf-8")
    # Match 'per session' that is NOT followed by 'scope-gated'
    bad = re.findall(r"per session(?! scope-gated)", text)
    assert not bad, f"Stale 'per session' wording in AGENTS.md: {bad}"


def test_trust_hosts_section_present() -> None:
    text = WORKSHOP_AGENTS.read_text(encoding="utf-8")
    # The workshop AGENTS.md should reference the trust-bearing hosts decision
    # in some form (text or pointer to kernel/TRUST_HOSTS.md).
    has_pointer = "TRUST_HOSTS.md" in text or "trust-bearing" in text.lower()
    assert has_pointer, "AGENTS.md should reference the trust-bearing hosts decision (D55)"


def test_claude_code_platform_row_does_not_claim_missing_skills_dir() -> None:
    text = WORKSHOP_AGENTS.read_text(encoding="utf-8")
    assert "`.claude/skills/`" not in text, (
        "AGENTS.md must not advertise .claude/skills/ when that directory is not generated"
    )
