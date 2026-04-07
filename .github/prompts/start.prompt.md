---
mode: agent
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

   The dashboard shows five panels:
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
   | `eval` | Run `/eval` to run a quality gate on current work |
   | `<custom goal>` | Pass the goal to `/auto` — the auto-pipeline router selects the right preset |

3. **If the dashboard script is missing or errors**, fall back to manual orientation:
   - Read `azoth.yaml` for version/phase/layer status
   - Read `.azoth/backlog.yaml` for pending work
   - Check `.azoth/scope-gate.json` for active scope
   - Then offer the same routing options above

## Notes

- `/start` is orientation only — it does not write files or open a scope gate
- The `resume` option appears only when a non-expired scope gate exists
- If no scope gate exists, `/next` is the normal first step
