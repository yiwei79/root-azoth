---
description: Session welcome dashboard — orient, then route to your next action
agent: orchestrator
---

# /start

Run at the beginning of any session to get a full project snapshot before deciding what to work on.

## Steps

1. **Run the welcome dashboard**

   Execute the Rich-based dashboard script:

   ```bash
   python scripts/welcome.py
   ```

   For the **full structured text** layout (no Rich panels; same facts in plain UTF-8 — used by the SessionStart hook). Markers: `# AZOTH_SESSION_ORIENTATION_BEGIN` / `END`. **Read** + paste verbatim only when the user wants the full snapshot in chat; otherwise rely on SessionStart injection (`CLAUDE.md` core rule 9).

   ```bash
   python scripts/welcome.py --plain
   ```

   For the **versioned roadmap** (phases v0.0.x → v0.1.0) without health/backlog panels, run:

   ```bash
   python scripts/roadmap_dashboard.py
   ```

   Or invoke **`/roadmap`**.

   The welcome dashboard shows five panels:
   - **Header** — repo · branch · date · version
   - **Phases** — P1–P6 completion status
   - **System Health** (left) — layer status, memory counts, scope gate, pipeline gate (when governed)
   - **Top Backlog** (right) — top-3 unblocked items
   - **Last Session** — most recent episode summary
   - **START** — context-sensitive routing options

1. **Surface relevant memory** (context-recall)

   Before routing, invoke `context-recall` via `skills/context-recall/SKILL.md`.
   Extract 3-5 goal tags for the current session, use the skill's scoring flow to
   surface the top 1-3 relevant M3 episodes and M2 patterns, then route with that
   context in view. See `skills/context-recall/SKILL.md` for the full scoring
   algorithm and output format.

2. **Read the user's selection and route accordingly**

   | Input | Action |
   |-------|--------|
   | `resume` | Run `/resume` — continue the active approved scope, or reopen the parked same-thread session without a second scope-approval wall. If no checkpoint exists, `/auto` remains the default and must start at Stage 0 |
   | `resume <session_id>` | Run `/resume <session_id>` — reopen that parked session directly and restore its saved pipeline checkpoint when present. If no checkpoint exists, `/auto` remains the default and must start at Stage 0 |
   | `next` | Run `/next` to open a scope card for the next priority task. If another live scope exists, stop and route to `/resume`, `/park`, or `/session-closeout` instead |
   | `intake` | Run `/intake` to process queued insights from `.azoth/inbox/` |
   | `promote` | Run `/promote` to review M2→M1 promotion candidates |
   | `eval` | Run `/eval` — quality gate (**0.85** baseline); **escalates to `/eval-swarm`** when workflow/content triggers multi-branch or high-stakes review (see `eval.md`) |
   | `roadmap` | Run `/roadmap` — D48 versioned roadmap dashboard (`scripts/roadmap_dashboard.py`) |
   | `plan` | Run `/plan` — structured autonomy / planning |
   | `remember` | Run `/remember` — quick M3 episode capture without full closeout |
   | `closeout` | Run `/session-closeout` — full W1–W4 for delivery scopes, or light closeout for an exploratory session with no scope gate. In Codex calm flow, the equivalent daily route is `$azoth-start closeout` or `$azoth-session-closeout` |
   | `<custom goal>` | Let the Codex control plane classify intent first: exploratory goals open `.azoth/session-gate.json` without a scope card, while delivery goals escalate into `/auto`. When delivery escalates from a matching exploratory session, carry that identity forward explicitly as `session_id=<existing-session>` in the routed start input. In Codex calm flow, the canonical routed forms are `$azoth-start <goal>` for exploratory sessions and `$azoth-start pipeline_command=auto [session_id=<existing-session>] <goal>` for delivery |

   **More commands:** `.claude/commands/*.md` — e.g. `/deliver`, `/deliver-full`, `/dynamic-full-auto`, `/autonomous-auto`, `/bootstrap`, `/sync`, `/test`, `/context-architect`, `/arch-proposal`, `/review-insights`, `/worktree-sync`, `/eval-swarm`.

3. **If the dashboard script is missing or errors**, fall back to manual orientation:
   - Read `azoth.yaml` for version/phase/layer status
   - Read `.azoth/backlog.yaml` for pending work
   - Check `.azoth/session-gate.json` for an active exploratory session
   - Check `.azoth/scope-gate.json` for active delivery scope
   - Then offer the same routing options above

## Notes

- `/start` is orientation only — it does not write files or open a scope gate
- In Codex, the prompt router may open `.azoth/session-gate.json` before `/start` is rendered when a freeform goal is classified as exploratory chat/research/planning work. That session is real and closable even without a scope gate.
- **Claude Code:** When `hooks.SessionStart` is configured in `.claude/settings.json` (P5-007), the welcome script runs on session `startup` and `resume`. Output is injected once into context **and** mirrored to **`.azoth/session-orientation.txt`**. Use **`Read`** on that file only when showing **verbatim plain** orientation in chat; avoid redundant reads otherwise. **Bash** `welcome.py` (Rich) is fine for the designed UI — output may be **collapsed** in the IDE; **expand** to see the full menu. **See `CLAUDE.md` core rule 9.**
- **Codex:** `$azoth-start` is the canonical daily entry surface. Use `$azoth-start`, `$azoth-start next`, `$azoth-start closeout`, or `$azoth-start pipeline_command=<auto|autonomous-auto|dynamic-full-auto|deliver|deliver-full> <goal>`. Literal `/start`, `/next`, `/auto`, `/autonomous-auto`, and `/deliver-full` text remains compatibility fallback and should normalize back through the same calm-flow path.
- **Cursor:** SessionStart hooks do not run. For the **full Rich UI**, run `python3 scripts/welcome.py` in the **integrated terminal** (Terminal panel). **Bash** in chat also works—**expand** output if collapsed. Plain text: **`Read`** `.azoth/session-orientation.txt` or `welcome.py --plain`. See `CLAUDE.md` rules 8–9.
- The `resume` option appears when a non-expired scope gate exists or the current thread has a parked `session-state.md` handoff
- If no scope gate exists, `/next` is the normal first step for delivery work; exploratory sessions may still already be open via `.azoth/session-gate.json`
