# Host Trust Matrix

> Authoritative per-host enforcement table. See `kernel/TRUST_HOSTS.md` for the
> trust-bearing / best-effort decision (D55) and `docs/HERMES_SUBSTRATE.md` for
> the substrate mapping (D56).

## Per-host enforcement

| Host | Trust tier | Enforcement layer | Drift check | Runtime guards |
|---|---|---|---|---|
| **Hermes** | Trust-bearing (primary) | `~/.hermes/profiles/<panel>/` profile state + AGENTS.md shim + `delegate_task` isolation | Yes (daily `cronjob azoth-kernel-drift-check` watchdog + `scripts/hermes_manifest_check.py`) | Yes (via `scripts/azoth_guards.py` subprocess before scope complete) |
| **Codex** | Trust-bearing (secondary) | `.codex/hooks.json` (narrow compatibility hook) + `.codex/agents/*.toml` + `developer_instructions` | Yes (kernel checksum shared) | Yes (via `scripts/azoth_guards.py` invoked by orchestrator) |
| **OpenCode** | Trust-bearing (secondary) | `.opencode/` plugin permission: deny mirrors Trust Contract posture | Yes (when runtime present) | Yes (via `scripts/azoth_guards.py` invoked by orchestrator) |
| Claude Code | Best-effort mirror | `.claude/settings.json` PreToolUse hooks (real, but kernel is per-repo) | Warning only | Best-effort (orchestrator may or may not invoke) |
| Cursor | Best-effort mirror | `.cursor/rules/*.mdc` (instructional only, no hook execution) | None | None |
| Copilot | Best-effort mirror | `.github/` files (slash-command-driven; user must invoke) | None | None |
| Gemini CLI | Best-effort mirror | `GEMINI.md` + `.gemini/settings.json` (instruction-first) | None | None |
| Antigravity | Best-effort mirror | `.agents/rules/*.md` (instruction-only) | None | None |

## Why exactly three trust-bearing hosts

The 2026-05-01 meta-research concluded that harness assumptions age as models
improve, and that prompt walls do not survive real load. The right answer is
to commit to hosts where the gate layer is **mechanical** and run the runtime
guards there as subprocesses.

Concretely:

- **Hermes** has a profile isolation primitive (separate `~/.hermes/profiles/<panel>/` per authority plane), the cross-profile write guard, `delegate_task` for true subagent isolation, `session_search` for FTS5-backed episodic recall, and the `memory` tool for human-approved semantic memory. The kernel lives in the profile; projects reference it via AGENTS.md shim.
- **Codex** has `.codex/hooks.json` (mechanical hook layer) + `.codex/agents/*.toml` (declarative agent definitions) + `developer_instructions` (system-prompt layer). 1,471 LOC of control-plane code in `scripts/codex_control_plane.py`, `codex_hooks_mode.py`, `codex_model_selector.py` already implements the harness commitment.
- **OpenCode** has a plugin system with `permission: deny` semantics that can mirror Trust Contract posture declaratively.

The other five platforms either lack a hook layer (Cursor, Copilot, Gemini,
Antigravity) or have a hook layer but no enforcement surface that runs against
the kernel (Claude Code has PreToolUse but the kernel is per-repo, not per-
profile, so manifest drift is unobservable from the hook).

## Migration note

A consumer project that wants trust-bearing behavior must:

1. Be operated from one of the three trust-bearing hosts.
2. Reference the kernel via AGENTS.md (read-only pointer).
3. Run `python3 scripts/hermes_manifest_check.py` before any session that
   touches governed state.
4. Use `scripts/azoth_guards.py` before marking any scope complete.

If the operator is on a best-effort mirror host, the kernel is documented
but not enforced. Drift detection runs in CI on trust-bearing hosts and in
best-effort warning mode on mirrors.

## Adding a fourth trust-bearing host

Requires an explicit amendment to `kernel/TRUST_HOSTS.md` with:

1. Mechanical evidence (hook layer / permission system / structural guard).
2. Integration plan for the runtime guards (D57) as subprocesses.
3. Operator-install evidence (absolute path to binary, version, smoke test).
4. Hermes-visible shim if the host CLI is not on the operator's PATH.

Removing a trust-bearing host requires an explicit amendment documenting the
regression (e.g., "Codex CLI no longer installed on operator workstation,
downgrading to best-effort mirror").

## Cross-host coordination

A change to the kernel affects all three trust-bearing hosts and all five
mirrors. The expected flow on a kernel change:

1. Workshop edits kernel file in `root-azoth`.
2. Refresh `.azoth/kernel-checksums.sha256`.
3. Run `python3 scripts/hermes_manifest_check.py` to confirm invariants hold.
4. Run `python3 scripts/azoth-deploy.py` to regenerate adapter mirrors.
5. Public `azoth` repo re-extracts via `scripts/azoth_extract_product.py`.
6. Personal cockpit pulls the new public release.

The daily `azoth-kernel-drift-check` cronjob verifies the kernel checksum
match on the trust-bearing host schedule (06:00 local) and surfaces drift
to the operator if any invariant fails.
