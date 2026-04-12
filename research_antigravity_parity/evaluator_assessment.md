# Evaluator Assessment: Antigravity Parity Investigation

## Verdict

Conditional pass.

The current evidence is sufficient to support a practical compatibility conclusion, but not an exact Claude Code parity conclusion.

## Strengths

- The investigation is grounded in first-party Google sources rather than third-party summaries.
- Antigravity has confirmed first-party surfaces for rules, workflows, skills, permissions, MCP, browser subagents, artifact review, sandboxing, and persistent knowledge.
- The adapter plan correctly distinguishes direct mappings from approximations.
- The planner does not overclaim that existing Claude Code file surfaces will load natively.

## Material gaps

- No first-party evidence shows repo-local executable hooks comparable to Claude Code PreToolUse. This is the main non-trivial parity gap.
- No first-party evidence shows user-defined custom agent persona files comparable to Azoth's current agent archetype files.
- Knowledge Items are clearly persistent memory, but the first-party docs do not describe a repo-authoritative session handoff model equivalent to Azoth's `.azoth/` state files.

## Assessment by question

### Can Azoth likely support Antigravity as a compatible platform?

Yes, probably.

The platform primitives that matter most to Azoth are present: local workspace editing, slash workflows, skills, multi-agent orchestration, browser and terminal execution, MCP integration, permissions, and reviewable artifacts.

### Can Azoth achieve exact parity with Claude Code as-is?

No.

There is no first-party evidence that Antigravity will directly consume `CLAUDE.md`, `.claude/commands/`, `.claude/agents/`, or `.github/prompts/`, and there is no first-party evidence of programmable hook scripts equivalent to Claude Code's PreToolUse hooks.

### Can Azoth achieve practical parity with an Antigravity-specific adapter?

Yes, conditionally.

The adapter must translate:

- core instructions into rules,
- command prompts into workflows,
- skills into `.agents/skills/`,
- governance controls into permissions, strict mode, sandboxing, and workflow-level checks,
- state continuity into `.azoth/` plus optional Antigravity Knowledge Items.

## Recommendation to builder

Frame the final answer as:

- practical parity: likely yes,
- exact Claude Code parity: no,
- recommended next step: build a minimal Antigravity adapter prototype before making broader parity claims.
