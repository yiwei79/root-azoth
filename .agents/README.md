# Antigravity Bootstrap

This repository includes a workspace-local Antigravity bootstrap under `.agents/`.

## What Is Included

- Rules: `.agents/rules/`
- Workflows: `.agents/workflows/`
- Skills: `.agents/skills/`

Current workflow commands:

- `/next`
- `/auto <goal>`
- `/deliver <goal>`
- `/session-closeout`

Current skill:

- `azoth-operating-model`

## Exact Usage Steps

1. Open the repository root in Antigravity. The workspace root must be `root-azoth`, not its parent directory.
2. Open the Agent side panel.
3. Open the Customizations panel from the `...` menu and verify the workspace surfaces:
   - Rules should include `azoth-core`
   - Workflows should include `next`, `auto`, `deliver`, and `session-closeout`
   - Skills should include `azoth-operating-model`
4. In the agent input, type the workflow name directly, for example `/auto investigate pipeline drift`.
5. For rules, remember that rules are not commands. They live in the Rules panel and should be applied there.
6. For skills, remember that skills are not commands. The agent discovers them automatically, but you can mention the skill name explicitly if needed.

## If Workflows Do Not Show Up

1. Confirm the files are under `.agents/workflows/` in the active Antigravity workspace.
2. Reload the Antigravity workspace or restart Antigravity after adding files outside the UI.
3. Re-open the Customizations panel and check the Workflows list again.
4. Type the command manually even if you do not see a suggestion list.
5. If manual typing still does not work, create one workspace workflow from Antigravity's own UI and compare its generated file shape with the files in `.agents/workflows/`.

## Operating Boundary

- This bootstrap path is for standard infrastructure, docs, and adapter work.
- `.azoth/` remains the authoritative state layer.
- Governed M1 work, kernel work, and Claude hook parity are not part of this bootstrap.

## Deferred Next Slice

Global install and deploy integration are intentionally deferred. That future slice is tracked in roadmap as an initiative rather than active phase work.
