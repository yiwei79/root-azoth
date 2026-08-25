# Codex Platform Guide

> How to use Azoth in Codex without falling back into the old noisy hook-first flow.

## Summary

- Codex is a **co-primary** Azoth host alongside Claude Code.
- Codex is **calm-by-default**: the default adapter keeps only the narrow `UserPromptSubmit` compatibility hook.
- Codex now also supports an opt-in **`azoth-seamless`** permission profile for repo-local low-friction work.
- Tracked Codex adapter artifacts now include calm defaults plus tracked companion surfaces for `seamless` and `verbose`; local activation still happens through `/hookmode`.
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
- During longer reasoning or tool-use work, emit a brief public work-state cue: one short sentence naming the current action or decision. Do not try to dump private chain-of-thought.
- Use hierarchy on purpose: a brief orienting sentence, then bullets or a compact table only when they genuinely improve scanning.
- For end-of-work communication, start with a direct outcome sentence, then use 2-4 short titled sections or labeled lines only when they improve reading speed.
- Separate the scoped task outcome from session or admin state. If the work is done but closeout or approval remains, say that explicitly up front.
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

## Why Claude Can Feel Different

Part of the Claude interaction style people notice is **host behavior**, not only prompt text.

- Claude surfaces configurable communication styles and summarized thinking in the product.
- Codex now exposes two relevant product controls of its own:
  - `/personality` in the app, CLI, and IDE extension
  - `Settings > General > Follow-up behavior` in the app for more live steering while work is in progress

Recommended Codex setup when you want the closest Azoth-hosted approximation to the
"brief progress cue + easy final summary" feel:

- Choose the more conversational / empathetic Codex personality if you want a warmer collaborator style.
- Enable Follow-up behavior when you want more live interaction during longer-running work.
- Keep the Azoth Codex communication layer enabled so repo-local summaries still separate
  task outcome from session/admin state and preserve terse machine-facing artifacts.

This layered model matters: Azoth can shape the repo-local communication contract, but it
should not pretend to expose hidden reasoning or reimplement product-level UI affordances.

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

Optional local verbose hook overlay:

```bash
python3 scripts/codex_hooks_mode.py set verbose
python3 scripts/codex_hooks_mode.py set verbo
```

Opt-in seamless permission profile:

```bash
python3 scripts/codex_hooks_mode.py set seamless
python3 scripts/codex_hooks_mode.py status
```

Return to the calm default with:

```bash
python3 scripts/codex_hooks_mode.py set calm
python3 scripts/codex_hooks_mode.py status
```

`verbose` is diagnostic-only. It is not the canonical Codex operating model and not evidence of successful Codex parity.

`verbose` is a hook overlay, not a full operating-mode replacement. It preserves the current permission profile, so a workspace can be `calm + verbose` or `seamless + verbose`.

`azoth-seamless` is the repo-local "safe but lower-friction" option:

- keeps `sandbox_mode = "workspace-write"`
- keeps network disabled
- switches to `approval_policy = "untrusted"`
- loads `.codex/rules/azoth-seamless.star` so a narrow allowlist of trusted Azoth/Git inspection commands runs without repeated prompts
- still prompts or forbids higher-risk commands; it is not full-access and it does not relax Azoth gates

The seamless rules are intentionally narrow. Example: read-only `git status`, `git diff`, `git show`, and `python3 scripts/check_gates.py` are trusted; mutating Git commands, shell wrappers, closeout, and destructive patterns still stop for approval or fail closed. Plain `git branch` is **not** auto-allowed because it can create refs; only explicitly read-only forms such as `git branch --list` and `git branch --show-current` are trusted.

Tracked Codex adapter artifacts:

- `.codex/config.toml` keeps the calm repo default
- `.codex/config.seamless.toml` is the tracked seamless companion
- `.codex/hooks.json` keeps the calm repo default
- `.codex/hooks.verbose.json` is the tracked verbose companion

`python3 scripts/azoth-deploy.py` refreshes those tracked artifacts. If you want a local opt-in after deploy, re-run `python3 scripts/codex_hooks_mode.py set seamless` or `... set verbose`.

## Execpolicy Verification

Use Codex's local execpolicy checker to inspect the generated seamless rules:

```bash
codex execpolicy check --rules .codex/rules/azoth-seamless.star git status
codex execpolicy check --rules .codex/rules/azoth-seamless.star git commit -m test
codex execpolicy check --rules .codex/rules/azoth-seamless.star rm -rf tmp
```

Expected decisions:

- `git status` → `allow`
- `git commit -m test` → `prompt`
- `rm -rf tmp` → `forbidden`

## Governance

- Codex still uses the same shared `.azoth/*` state and gate semantics as Claude Code.
- Governed work still requires valid scope/pipeline gates.
- If the effective route requires staged governed execution and staged delegation is unavailable, Codex must **fail closed** instead of continuing inline.
- Literal slash tokens are advisory compatibility input only; they do not authorize skipping the governed loop.
- Managed `requirements.toml` policy and `guardian_subagent` review remain phase-2 enterprise follow-ons, not part of the repo-local seamless profile.

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
