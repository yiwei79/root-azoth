---
description: "Show the next priority task from the roadmap and suggest how to proceed"
---

# /next — What Should I Work On?

Read the development roadmap and surface the highest-priority actionable task.

## Steps

1. **Load roadmap**: Read `.azoth/roadmap.yaml`
2. **Identify current phase**: Check `current_phase` and `current_phase_title`
3. **Find next task**: From `tasks`, find the first entry where:
   - `status` is `pending` or `in_progress`
   - `blocked_by` is null or all blockers are complete
4. **Surface context**: For the selected task:
   - Show task ID, title, priority
   - Show related architecture decision(s) from `decision_ref`
   - Look up the decision in `docs/DECISIONS_INDEX.md` for context
   - Check if prior episodes in `.azoth/memory/episodes.jsonl` relate to this task
5. **Suggest approach**: Based on the task description and decision context, propose:
   - First step to take
   - Estimated scope (files, complexity)
   - Whether a `/plan` should be run first

## Output Format

```
📋 Phase {N}: {phase_title}
🎯 Next: [{task_id}] {task_title} (Priority {priority})
📐 Decision: {decision_ref} — {decision_summary}
💡 Suggested first step: {suggestion}
```

## Rules

- If all tasks in current phase are complete, congratulate and show Phase N+1 preview
- If a task is blocked, show the blocker and suggest working on the next unblocked task
- If roadmap.yaml is missing, suggest running `/bootstrap` to initialize
- Never auto-start work — present the suggestion and wait for human signal
