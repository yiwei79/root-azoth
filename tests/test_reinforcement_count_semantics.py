"""P1-006 AC-1 + schema-drift: reinforcement_count increment rule and mirror parity."""

from __future__ import annotations

import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_MD = REPO / "skills" / "remember" / "SKILL.md"

CLOSEOUT_MIRRORS = [
    pytest.param(
        REPO / ".claude" / "commands" / "session-closeout.md",
        id="claude",
    ),
    pytest.param(
        REPO / ".github" / "prompts" / "session-closeout.prompt.md",
        id="github",
    ),
    pytest.param(
        REPO / ".opencode" / "commands" / "session-closeout.md",
        id="opencode",
    ),
    pytest.param(
        REPO / ".agents" / "workflows" / "session-closeout.md",
        id="agents",
    ),
    pytest.param(
        REPO / ".gemini" / "commands" / "session-closeout.toml",
        id="gemini",
    ),
]


def test_skill_md_documents_when_to_increment_reinforcement_count() -> None:
    """AC-1: SKILL.md must contain a 'When to increment' rule for reinforcement_count."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "When to increment" in text, (
        "skills/remember/SKILL.md is missing the 'When to increment' section "
        "for reinforcement_count. Add a '### When to increment reinforcement_count' "
        "subsection under the Episode Schema."
    )


@pytest.mark.parametrize("mirror_path", CLOSEOUT_MIRRORS)
def test_closeout_mirror_episode_template_includes_reinforcement_count(
    mirror_path: Path,
) -> None:
    """Schema drift: each closeout mirror's episode JSON template must include reinforcement_count."""
    text = mirror_path.read_text(encoding="utf-8")
    assert "reinforcement_count" in text, (
        f"{mirror_path.relative_to(REPO)} episode template is missing 'reinforcement_count'. "
        "Add '\"reinforcement_count\": 0' to the episode JSON block in step 4."
    )
