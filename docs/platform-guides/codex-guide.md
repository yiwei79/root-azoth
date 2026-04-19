# Codex Platform Guide

> How to use Azoth in Codex without falling back into the old noisy hook-first flow.

## Summary

- Codex is a **co-primary** Azoth host alongside Claude Code.
- Codex is **calm-by-default**: the default adapter keeps only the narrow `UserPromptSubmit` compatibility hook.
- `$azoth-start` is the **canonical daily entry surface** in Codex.
- Compatibility wrappers like `$azoth-auto` and literal slash tokens still work, but they normalize back through the same calm-flow controller.
- Generated Codex wrappers resolve from `commands/<name>/command.yaml`; some command bodies still bridge through `.claude/commands/*.md` while `legacy_claude_markdown` remains live.

## Human-Facing Output

Codex intentionally uses a **richer human-facing presentation layer** than the shared
BL-051 baseline. This is a Codex-first follow-on, not a platform-wide rewrite.

What counts as **human-facing** output in Codex:

- summaries after discovery or implementation
- approvals, declarations, and decision framing shown to the human
- plans, tradeoff explanations, and “what happens next” guidance

What counts as **operational / machine-facing** output:

- BL-011 spawn payloads
- BL-012 stage summaries
- gate files and gate-validation state
- evaluator scorecards and schema-bound YAML/JSON/TOML artifacts

Codex guidance for human-facing output:

- Prefer short titled sections over long paragraph walls.
- Use hierarchy on purpose: a brief orienting sentence, then bullets or a compact table only when they genuinely improve scanning.
- Use **selective** emojis as navigational markers, not decoration.
- Use tables for comparisons, options, gate state, and pipeline declarations only when they stay visually narrow in the chat column.
- If a table would overflow, wrap badly, or introduce horizontal scrolling, switch to bullets, labeled lines, or a short contrastive comparison instead.
- Keep the user’s long-term goal visible: restate the goal, make scope boundaries legible, and offer only the nearest helpful next step.

Codex guidance for operational output:

- Keep it terse, plain, and parseable.
- Do not add decorative formatting to machine-oriented artifacts.
- Do not let richer presentation bleed into gates, handoffs, or schema-bound records.

This split is deliberate: Codex should feel more scannable and supportive in human chat
without weakening Azoth’s deterministic pipeline artifacts or silently changing the
shared Claude/Copilot/OpenCode/Gemini house style.

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
