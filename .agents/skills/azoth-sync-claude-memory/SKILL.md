---
name: azoth-sync-claude-memory
description: Replay deferred W3 Claude-memory mirroring from repo-local Azoth state.
  Use when Codex closeout left `.azoth/claude-memory-sync-pending.json` or when the
  user wants to refresh Claude memory after running with broader host write access.
---

Use this skill as the Codex-visible entrypoint for replaying deferred Claude memory mirroring.

Codex does not register repository-defined helper scripts in its built-in `/` command picker.
This skill is the explicit Codex-native equivalent of running `python3 scripts/sync_claude_memory.py`.

Execution contract:
- Read `.azoth/claude-memory-sync-pending.json` when present to understand the deferred W3 state.
- Run `python3 scripts/sync_claude_memory.py`.
- If the host still blocks writes to `~/.claude/.../memory/`, report that the sync remains deferred and ask for broader host write access.
- Treat `.azoth/` state as authoritative; do not mutate W1/W2/W4 closeout records beyond marking the pending artifact synced after a successful replay.

Command metadata:
- Script path: `scripts/sync_claude_memory.py`
- Pending artifact: `.azoth/claude-memory-sync-pending.json`
- Description: Replay deferred W3 Claude-memory mirroring from repo-local Azoth state
