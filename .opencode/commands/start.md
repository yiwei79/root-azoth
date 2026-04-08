---
description: Session welcome dashboard — orient, then route to your next action
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

2. **Read the user's selection and route accordingly**

   | Input | Action |
   |-------|--------|
   | `resume` | Scope gate is already active — proceed directly with the approved goal |
   | `next` | Run `/next` to open a scope card for the next priority task |
   | `intake` | Run `/intake` to process queued insights from `.azoth/inbox/` |
   | `promote` | Run `/promote` to review M2→M1 promotion candidates |
   | `eval` | Run `/eval` — quality gate (**0.85** baseline); **escalates to `/eval-swarm`** when workflow/content triggers multi-branch or high-stakes review (see `eval.md`) |
   | `<custom goal>` | Pass the goal to `/auto` — the auto-pipeline router selects the right preset |

3. **If the dashboard script is missing or errors**, fall back to manual orientation:
   - Read `azoth.yaml` for version/phase/layer status
   - Read `.azoth/backlog.yaml` for pending work
   - Check `.azoth/scope-gate.json` for active scope
   - Then offer the same routing options above

## Notes

- `/start` is orientation only — it does not write files or open a scope gate
- **Claude Code:** When `hooks.SessionStart` is configured in `.claude/settings.json` (P5-007), the welcome script runs on session `startup` and `resume`. Output is injected once into context **and** mirrored to **`.azoth/session-orientation.txt`**. Use **`Read`** on that file only when showing **verbatim plain** orientation in chat; avoid redundant reads otherwise. **Bash** `welcome.py` (Rich) is fine for the designed UI — output may be **collapsed** in the IDE; **expand** to see the full menu. **See `CLAUDE.md` core rule 9.**
- **Cursor:** SessionStart hooks do not run. For the **full Rich UI**, run `python3 scripts/welcome.py` in the **integrated terminal** (Terminal panel). **Bash** in chat also works—**expand** output if collapsed. Plain text: **`Read`** `.azoth/session-orientation.txt` or `welcome.py --plain`. See `CLAUDE.md` rules 8–9.
- The `resume` option appears only when a non-expired scope gate exists
- If no scope gate exists, `/next` is the normal first step
