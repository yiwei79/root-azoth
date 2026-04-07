# Azoth Session State — Cross-IDE Handoff Capsule
# Written by /session-closeout. Read by .cursor/rules/azoth-memory.mdc on Cursor session start.
# Schema:
#   state: empty | active
#   last_ide: cursor | claude-code
#   timestamp: ISO 8601
#   active_task: BL-XXX title or free-form description
#   active_files: list of files actively being modified
#   pending_decisions: open questions or decisions awaiting input
#   approved_scope: one-line summary of the approved scope card
#   next_action: concrete first step to resume work

state: empty
last_ide: cursor
timestamp: 2026-04-08T23:50:00Z
active_task: ""
active_files: []
pending_decisions: []
approved_scope: ""
next_action: "Run /next for a new scope card (e.g. P5-005 or P5-006). Optional: /intake for inbox queue."
