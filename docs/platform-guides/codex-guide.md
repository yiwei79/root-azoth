# Codex Platform Guide

> How to use Azoth in OpenAI Codex (CLI and IDE).

## Classification

Codex is **source-compatible, hooks-capable, Bash-gated, skill-routed** (D46).

| Property | Value |
|----------|-------|
| Instruction file | `CLAUDE.md` (read as project doc) + `AGENTS.md` (AAIF standard) |
| Config | `.codex/config.toml` |
| Hooks | `.codex/hooks.json` — mechanical `SessionStart`, `UserPromptSubmit`, `Stop`, and Bash-only `PreToolUse`/`PostToolUse` |
| Agents | `.codex/agents/*.toml` (11 agents, all 4 tiers) |
| Commands | `.agents/skills/azoth-*/SKILL.md` via `/skills`; literal tokens as fallback |
| Skills | `.agents/skills/` (shared Codex/Antigravity path) |
| Sandbox | `workspace-write` — network disabled (`network_access = false`) |

## Quick Start

1. Run `python3 scripts/azoth-deploy.py` to generate all Codex surfaces.
2. Verify with `python3 scripts/azoth-deploy.py --check`.
3. In Codex, use `/skills` or type `$azoth-start` to begin a session.

## Invoking Commands

Codex does not register repository-defined slash commands in its built-in `/` picker.
Azoth commands are exposed through two layers:

| Method | Example | How it works |
|--------|---------|-------------|
| **Primary**: `/skills` or `$azoth-*` | `$azoth-auto fix login bug` | Codex loads `.agents/skills/azoth-auto/SKILL.md`, which reads `.claude/commands/auto.md` |
| **Fallback**: literal token | `/auto fix login bug` | `.codex/hooks/user_prompt_submit_router.py` injects the matching command text via `additionalContext` |

Available command wrappers (21 total): `azoth-auto`, `azoth-deliver`, `azoth-deliver-full`,
`azoth-dynamic-full-auto`, `azoth-start`, `azoth-next`, `azoth-plan`, `azoth-eval`,
`azoth-eval-swarm`, `azoth-test`, `azoth-promote`, `azoth-remember`, `azoth-intake`,
`azoth-session-closeout`, `azoth-bootstrap`, `azoth-sync`, `azoth-worktree-sync`,
`azoth-roadmap`, `azoth-review-insights`, `azoth-context-architect`, `azoth-arch-proposal`.

## Trust Contract Enforcement

Codex is **hooks-capable**, but narrower than Claude Code. Current Codex runtime
mechanically supports `SessionStart`, `UserPromptSubmit`, `Stop`, and Bash-only
`PreToolUse`/`PostToolUse`. Non-Bash `Write`/`Edit` enforcement still relies on
developer instructions and the sandbox. Enforcement therefore relies on three
complementary layers:

| Layer | Mechanism | Strength |
|-------|-----------|----------|
| `developer_instructions` | Scope-gate check, entropy ceiling, kernel immutability rules inline in `.codex/config.toml` | Behavioral — model-dependent |
| Container sandbox | `workspace-write` mode with network disabled; filesystem isolation | Mechanical — OS-level |
| Stop hook | `scripts/kernel-integrity.py` validates kernel checksums at session end | Mechanical — post-hoc |

### What is enforced

- **Scope gate**: `developer_instructions` instructs the model to read `.azoth/scope-gate.json` before any write and stop if `session_id` is missing or `expires_at` has passed.
- **Entropy ceiling**: max 10 files modified, 10 created, 0 deleted without approval, 1000 lines changed (quantified inline).
- **Kernel immutability**: `kernel/*`, `.azoth/kernel/*`, `.azoth/memory/patterns.yaml` declared as never-modify-without-approval.
- **Bash package policy**: `PreToolUse` wires `.claude/hooks/pip-install-guard.py`, so direct `pip install <package>` is mechanically blocked in Codex's current Bash hook path.
- **Co-Authored-By**: `commit_attribution = ""` in config + explicit prohibition in instructions.
- **Kernel drift**: `kernel-integrity.py` runs in the Stop hook (10s timeout) and flags any kernel file changes.

### What is NOT mechanically enforced

- **Non-Bash Write/Edit deny**: current Codex `PreToolUse` interception only emits `Bash`, not `Write`, `Edit`, MCP, or web tools. A sufficiently confused model could still bypass `developer_instructions` outside the Bash hook surface.
- **Per-path deny patterns**: no Codex equivalent to Claude Code's broad `Write`/`Edit` PreToolUse deny lattice.

## Hooks

`.codex/hooks.json` configures 5 hook types with 5 hooks:

| Hook Type | Script | Purpose | Timeout |
|-----------|--------|---------|---------|
| SessionStart | `.claude/hooks/session_start_welcome.py` | Load Azoth orientation dashboard | 120s |
| UserPromptSubmit | `.codex/hooks/user_prompt_submit_router.py` | Route literal Azoth tokens to command files | — |
| PreToolUse (Bash) | `.claude/hooks/pip-install-guard.py` | Block bare `pip install <package>` | — |
| PostToolUse (Bash) | `.claude/hooks/posttooluse_terminal_filter.py` | Filter terminal output | — |
| Stop | `scripts/kernel-integrity.py` | Validate kernel integrity at session end | 10s |

The generic Stop notification hook is intentionally omitted in Codex. It was too
chatty for the value it provided, and firing on every `Stop` event did not match
Azoth's human-gate notification policy.

### Codex Hook Protocol Rules

Codex hooks have **strict stdout requirements** that differ from Claude Code. Any hook
script wired into `.codex/hooks.json` must follow these rules:

**Rule 1 — `permissionDecision` is valid only for Bash `PreToolUse`.** Codex now
documents mechanical Bash blocking via:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "..."
  }
}
```
This is useful for narrow shell guardrails such as `pip-install-guard.py`. It does
not extend to non-Bash tool classes today.

**Rule 2 — No non-JSON stdout in Stop hooks.** Codex Stop hooks parse stdout as JSON.
Any human-readable text (emoji, status messages, print statements) causes
`"invalid stop hook JSON output"`. Use `--quiet` to suppress stdout, or ensure the
script emits valid JSON or nothing.

**Rule 3 — `additionalContext` remains the main shared injection mechanism.**
`UserPromptSubmit` and `PostToolUse` can inject context via:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "<HookType>",
    "additionalContext": "injected text"
  }
}
```
This is advisory — it adds to the model's context. In `PostToolUse`, `decision: "block"`
changes how Codex continues from the Bash result, but it does not undo the shell
side effect that already happened.

**Rule 4 — SessionStart hooks emit plain text.** SessionStart stdout becomes part of
the session context. Plain text is safe. JSON wrapping is not required.

**Rule 5 — Fail-open on malformed stdin.** If the hook receives invalid JSON on stdin,
exit 0 with empty stdout. Never crash on unexpected input.

### Hook Protocol Compatibility Matrix

| Protocol | Claude Code | Codex | Safe to share? |
|----------|-------------|-------|----------------|
| `permissionDecision: deny` in Bash `PreToolUse` | ✅ Mechanical deny | ✅ Mechanical deny | Yes, for Bash-only hooks |
| `additionalContext` injection | ✅ Works | ✅ Works | Yes |
| Plain text stdout (SessionStart) | ✅ Context | ✅ Context | Yes |
| Plain text stdout (Stop) | ✅ Ignored | ❌ Parsed as JSON | No — use `--quiet` |
| Empty stdout + exit code | ✅ Works | ✅ Works | Yes |
| JSON stdout (Stop) | ✅ Works | ✅ Works | Yes |

### Adding a New Hook to Codex

Before wiring any script into `.codex/hooks.json`:

1. Check the script's stdout output — does it print human-readable text?
2. If it is a `PreToolUse` hook, assume only `matcher: "Bash"` is live today.
3. `permissionDecision` is acceptable only for Bash `PreToolUse`; do not project that assumption onto `Write`, `Edit`, MCP, or web tools.
4. For Stop hooks: ensure the script emits valid JSON or nothing to stdout.
5. For shared scripts: add `--quiet` flag or platform detection if stdout differs.
6. After adding, run `python3 scripts/azoth-deploy.py --check` to verify sync.
7. Test in a live Codex session before committing.

## Agents

11 custom agents in `.codex/agents/*.toml`, covering all 4 tiers:

| Tier | Agents |
|------|--------|
| T1 Core | architect, builder, orchestrator, planner, reviewer |
| T2 Research | researcher, research-orchestrator |
| T3 Meta | agent-crafter, evaluator, prompt-engineer |
| T4 Utility | context-architect |

Multi-agent config: `max_threads = 6`, `max_depth = 1`.

## Sandbox Constraints

Codex runs in `workspace-write` sandbox with `network_access = false`:

- **No external fetches**: researcher waves in DFA+ cannot access URLs. Research must use pre-seeded context, local files, or be delegated to a network-capable platform.
- **Filesystem isolation**: the container provides OS-level blast radius that no other Azoth platform has — a structural advantage for trust.
- **Multi-agent**: parallel researcher/explore tasks work within the sandbox using local files only.

## DFA+ in Codex

Use `$azoth-dynamic-full-auto` or literal `/dynamic-full-auto`. Key differences from Claude Code:

1. Bash `PreToolUse`/`PostToolUse` are mechanical; non-Bash guardrails still rely on `developer_instructions`.
2. Network is disabled — Wave A researchers cannot fetch external URLs.
3. Multi-agent threads (up to 6) enable parallel local exploration.
4. Scope-gate contract is identical: validate `.azoth/scope-gate.json` before writes.
5. Stop hook runs `kernel-integrity.py` at session end.

See `skills/dynamic-full-auto/SKILL.md` § Happy path — Codex.

## Session Lifecycle

| Phase | Codex behavior |
|-------|---------------|
| **Start** | SessionStart hook runs `welcome.py`; use `$azoth-start` for routing menu |
| **Scope** | `$azoth-next` writes `.azoth/scope-gate.json`; model checks it before writes |
| **Pipeline** | Orchestrator stays in main thread; subagents via `.codex/agents/*.toml` |
| **Closeout** | `$azoth-session-closeout` writes W1/W2/W4; W3 mirror attempted, `W3 deferred` if blocked |
| **Stop** | kernel-integrity.py validates |

## Deployment

All Codex surfaces are generated by `scripts/azoth-deploy.py` from canonical sources:

```
agents/**/*.agent.md       → .codex/agents/<name>.toml
.claude/commands/*.md      → .agents/skills/azoth-<name>/SKILL.md
kernel/templates/.../codex/ → .codex/config.toml, .codex/hooks.json, .codex/hooks/user_prompt_submit_router.py
```

After changing canonical agents, commands, skills, or Codex templates:
```bash
python3 scripts/azoth-deploy.py          # regenerate
python3 scripts/azoth-deploy.py --check  # verify sync
```

## Tests

10 Codex-specific tests in `tests/test_azoth_deploy.py`:

| Test | Coverage |
|------|----------|
| `test_codex_agent_required_fields` | name, description, developer_instructions present |
| `test_codex_agent_body_preserved` | Agent body text survives transform |
| `test_codex_agent_model_optional` | Optional model field handling |
| `test_main_codex_writes_agents_skills_and_adapter` | Full deployment integration |
| `test_iter_codex_adapter_deployments_maps_templates` | Template → deployment mapping |
| `test_deploy_codex_adapter_writes_matching_content` | Deployed content matches template |
| `test_lint_codex_hooks_allows_bash_pretooluse_permission_decision_script` | Bash `PreToolUse` mechanical deny allowed in Codex lint |
| `test_lint_codex_hooks_warns_for_unsupported_pretooluse_surface` | Non-Bash `PreToolUse` matcher/handler still rejected |
| `test_deployed_codex_agents_match_transform` | Live `.codex/agents/` match transform output |
| `test_deployed_codex_skill_mirror_matches_canonical` | `.agents/skills/` match canonical skills |

## Comparison with Other Platforms

| Capability | Claude Code | Codex | Gap |
|------------|-------------|-------|-----|
| Bash deny (PreToolUse) | Mechanical | Mechanical | Bash-only in Codex today |
| Write/Edit deny (PreToolUse) | Mechanical | Behavioral | Platform limitation |
| Scope-gate enforcement | Hook binary | developer_instructions | Behavioral vs mechanical |
| Container isolation | None (host FS) | OS-level sandbox | Codex advantage |
| Slash commands | Native `/` picker | `/skills` + `$azoth-*` | Higher friction, same function |
| Multi-agent | `Agent()` / `Task` | `max_threads: 6` | Equivalent |
| Network access | Full | Disabled in workspace-write | Research delegation needed |
| Kernel integrity | PreToolUse deny | Stop hook post-hoc | Detection vs prevention |

## References

- Architecture: `docs/AZOTH_ARCHITECTURE.md` §8 (Codex parity, compatibility matrix)
- Instructions: `CLAUDE.md` rule 8 (Codex command mechanics)
- DFA+: `skills/dynamic-full-auto/SKILL.md` § Happy path — Codex
- Orchestrator binding: `docs/platform-guides/orchestrator-default-entry.md` § Codex
- Trust Contract: `kernel/TRUST_CONTRACT.md` §1–§2
- Templates: `kernel/templates/platform-adapters/codex/`
