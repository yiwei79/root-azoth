# Orchestrator as Default Pipeline Entry (P1-013)

## Summary

P1-013 makes Azoth's pipeline entry behavior explicit rather than heuristic. The **Orchestrator** (`agents/tier1-core/orchestrator.agent.md`) is the canonical session-level pipeline owner for all platform surfaces. The **Architect** is a spawned design/review subagent invoked by the Orchestrator via BL-011.

## Role Split

| Role | Responsibility | Invocation |
|------|---------------|-----------|
| Orchestrator | Session-level pipeline owner; Declaration ownership; gate management; subagent routing; BL-012 handoffs | Default entry via `agent: orchestrator` on pipeline commands, plus Codex `azoth-*` command-wrapper skills |
| Architect | Spawned design/review subagent; architecture briefs; review disposition | Spawned by Orchestrator via BL-011 (`Agent(subagent_type=architect)`) |

The Architect returns findings to the Orchestrator. The Orchestrator is always the continuing speaker; the Architect is never the final speaker after returning.

## Platform Binding

### Copilot / OpenCode

Pipeline commands (`.claude/commands/auto.md`, `deliver.md`, `deliver-full.md`) carry `agent: orchestrator` in their frontmatter. `scripts/azoth-deploy.py` propagates this field to:

- `.github/prompts/auto.prompt.md`, `deliver.prompt.md`, `deliver-full.prompt.md` (Copilot)
- `.opencode/commands/auto.md`, `deliver.md`, `deliver-full.md` (OpenCode)

When Copilot or OpenCode loads a prompt/command with `agent: orchestrator`, the orchestrator agent file (`.claude/agents/orchestrator.md`) governs the session.

### Codex

Codex does not document repo-defined custom slash-command registration. `scripts/azoth-deploy.py` therefore projects canonical Azoth command docs into discoverable Codex wrapper skills under `.agents/skills/azoth-*`, each with `agents/openai.yaml` UI metadata so `/skills` exposes entries such as `/auto`, `/deliver`, `/next`, and `/start`.

Codex entry has two layers:

- **Primary**: use `/skills` or `$azoth-auto`, `$azoth-deliver`, `$azoth-next`, etc.
- **Fallback**: literal `/auto`-style prompt text is routed by `.codex/hooks/user_prompt_submit_router.py` when the matching `.claude/commands/<name>.md` exists, but governed flows are redirected back toward the staged `$azoth-*` entry path rather than treated as permission to continue inline.

The orchestrator remains the session-level pipeline owner in Codex, but parity is **skill-routed** and **hook-soft**: `.codex/config.toml`, `.codex/hooks.json`, and `.codex/agents/orchestrator.toml` provide strong workflow guidance, while non-Bash tool enforcement remains behavioral rather than Claude-style mechanical interception. For governed tokens such as `/deliver-full`, the Codex adapter now fails closed at the instruction layer: if staged delegation is unavailable, the expected behavior is to stop after the Declaration and ask the human whether to authorize delegation, adjust the pipeline, or switch platforms.

### Claude Code

The orchestrator agent is deployed to `.claude/agents/orchestrator.md` by `azoth-deploy.py`. Claude Code hard binding via `.claude/settings.json` is deferred to a follow-on slice. Current behavior: Claude Code's main session reads the agent file when an explicit `agent:` field is present in the command.

### Drift Detection

Five tests in `tests/test_azoth_deploy.py` enforce the orchestrator binding contract:

| Test | What it checks |
|------|---------------|
| `test_transform_command_copilot_preserves_orchestrator_agent_field` | Unit: transform function passes through `agent: orchestrator` |
| `test_copilot_pipeline_prompts_have_orchestrator_agent_binding` | Deployed: `.github/prompts/` have `agent: orchestrator` |
| `test_opencode_pipeline_commands_have_orchestrator_agent_binding` | Deployed: `.opencode/commands/` have `agent: orchestrator` |
| `test_orchestrator_claude_agent_deployed_with_required_body_sections` | Deployed: `.claude/agents/orchestrator.md` has all 7 required sections |
| `test_deployed_copilot_prompts_match_transform_with_orchestrator` | Parity: deployed pipeline prompts match `transform_command_copilot` output |

Run `python scripts/azoth-deploy.py` to regenerate deployed surfaces after any source change.

Codex command-surface parity is covered separately by deploy drift tests for generated wrapper skills and metadata, including `test_deployed_codex_command_skill_wrappers_match_transform`.

## Why Test-Based Drift Detection Is Sufficient

`scripts/azoth-deploy.py` is the **sole write path** for all generated outputs. This means:

1. Any manual edit to a generated file is caught by the parity tests (`T5`, `test_deployed_copilot_prompts_match_transform`, `test_deployed_opencode_commands_match_transform`).
2. Any missing `agent:` binding is caught by `T2` and `T3`.
3. Any incomplete orchestrator body is caught by `T4`.
4. No separate drift YAML artifact is needed — the test suite is the drift record.

## Decision Rationale

- **Option A (dedicated orchestrator)** was selected over reusing architect as the main-session agent because the roles have different continuation semantics: orchestrators are the continuing speaker, architects are spawned and return.
- **Copilot/OpenCode binding** is additive (`agent:` field in frontmatter) — no existing behavior is broken if the runtime ignores an unknown field.
- **Claude Code hard binding** was initially deferred because `.claude/settings.json` mutation affects all sessions globally. P1-013 superseded this deferral by closing the enforcement gap via the CLAUDE.md instruction surface (rule 10) rather than platform config mutation.

## Deferred Work

- **Claude Code main-session hard binding via `.claude/settings.json`**: superseded by P1-013. The instruction-surface approach (CLAUDE.md rule 10 + Copilot instructions "Default agent persona" section) closes the main-session enforcement gap without `.claude/settings.json` mutation. Hard binding via a platform `defaultAgent` key remains an option if the platform adds stable support for it in future.
- Copilot agent runtime binding behavior in production is unverified — additive field, no action needed in this slice.

## References

- `agents/tier1-core/orchestrator.agent.md` — orchestrator contract
- `agents/tier1-core/architect.agent.md` — architect role boundary (§ Role Boundary (P1-013))
- `scripts/azoth-deploy.py` — deployment pipeline
- `tests/test_azoth_deploy.py` — drift tests (T1–T5)
- `kernel/GOVERNANCE.md` §5 — Default Posture (D26)
- Decision refs: D21, D23, D46
