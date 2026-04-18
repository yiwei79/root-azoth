# Codex Platform Guide

> How to use Azoth in Codex without falling back into the old noisy hook-first flow.

## Summary

- Codex is a **co-primary** Azoth host alongside Claude Code.
- Codex is **calm-by-default**: the default adapter keeps only the narrow `UserPromptSubmit` compatibility hook.
- `$azoth-start` is the **canonical daily entry surface** in Codex.
- Compatibility wrappers like `$azoth-auto` and literal slash tokens still work, but they normalize back through the same calm-flow controller.
- Generated Codex wrappers resolve from `commands/<name>/command.yaml`; some command bodies still bridge through `.claude/commands/*.md` while `legacy_claude_markdown` remains live.

## Daily Flow

Use these as the default Codex entries:

```text
$azoth-start
$azoth-start next
$azoth-start closeout
$azoth-start pipeline_command=auto <goal>
$azoth-start pipeline_command=deliver <goal>
$azoth-start pipeline_command=deliver-full <goal>
```

Compatibility surfaces:

- `/start`, `/next`, `/auto`, `/deliver`, `/deliver-full`
- `$azoth-auto`, `$azoth-deliver`, `$azoth-deliver-full`, `$azoth-session-closeout`

Those compatibility routes are not separate daily workflows. They normalize into the same start-centered control plane and must preserve the effective `pipeline_command`.

## Hooks And Noise

Default Codex behavior keeps only:

- `UserPromptSubmit` in `.codex/hooks.json`

Why:

- Codex surfaces hook activity prominently in the UI.
- Azoth uses the default hook profile only for compatibility routing.
- Broader automation is available, but not enabled by default because it degrades the Codex UX.

Optional local verbose mode:

```bash
python3 scripts/codex_hooks_mode.py set verbose
python3 scripts/codex_hooks_mode.py set verbo
```

Return to the calm default with:

```bash
python3 scripts/codex_hooks_mode.py set calm
python3 scripts/codex_hooks_mode.py status
```

`verbose` is diagnostic-only. It is not the canonical Codex operating model and not evidence of successful Codex parity.

## Governance

- Codex still uses the same shared `.azoth/*` state and gate semantics as Claude Code.
- Governed work still requires valid scope/pipeline gates.
- If the effective route requires staged governed execution and staged delegation is unavailable, Codex must **fail closed** instead of continuing inline.
- Literal slash tokens are advisory compatibility input only; they do not authorize skipping the governed loop.

## Closeout

Codex closeout keeps repo-local state authoritative:

- W1, W2, and W4 under `.azoth/` are the shared contract
- `.azoth/session-state.md` is the repo-local W2 handoff artifact
- W3 is **best-effort/deferred by default** in Codex
- W3 must never block W4

Canonical daily closeout:

```text
$azoth-start closeout
```

Direct wrapper:

```text
$azoth-session-closeout
```

Literal `/session-closeout` remains a compatibility fallback.
