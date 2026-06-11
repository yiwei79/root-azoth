# Azoth Trust Hosts

> Layer 0 file — kernel-level. Changes only via human-approved promotion (D51, D55).

This file is the single source of truth for which AI coding hosts Azoth treats as
**trust-bearing** (mechanical gate enforcement) versus **best-effort mirrors**
(instructional / advisory only). The trust posture is the opposite of a peer
matrix: trust-bearing hosts share the kernel checksum and run the runtime
guards; best-effort mirrors do not.

The trust-host decision (D55) commits Azoth to three trust-bearing hosts:
**Codex, Hermes, OpenCode**. The remaining five platforms ship as best-effort
mirrors with explicit "instructional, not mechanical" labels.

<!-- trust_hosts:start -->
trust_bearing_hosts:
  - hermes        # ~/.hermes/profiles/azoth-personal-cockpit/ — primary; profile-level kernel + memory + skills
  - codex         # .codex/hooks.json + developer_instructions — secondary; command + skill-routed
  - opencode      # .opencode/ — secondary; plugin permission: deny mirrors Trust Contract posture

best_effort_mirrors:
  - claude_code   # Hook layer is real (PreToolUse), but kernel is per-repo, not per-profile
  - antigravity   # GEMINI.md + .agents/rules/; instruction-only, no PreToolUse
  - copilot       # .github/ files; depends on user invoking slash commands
  - cursor        # .cursor/rules/*.mdc; behavioral enforcement only
  - gemini        # .gemini/ + GEMINI.md; instruction-first

downgrade_warning: |
  Best-effort mirrors do NOT enforce the kernel. They document it.
  If the kernel changes, mirror behavior may diverge silently.
  Drift check (`scripts/hermes_manifest_check.py`) runs in CI on trust-bearing hosts
  and in best-effort warning mode on the others.

runtime_guards:
  trust_bearing:
    - scripts/check_fd_003_subagent_isolation.py
    - scripts/check_fd_004_hydration_scope.py
    - scripts/check_fd_005_completion_semantics.py
    - scripts/check_fd_008_subagent_contract.py
  best_effort:
    - none (mirrors document the guards; they do not run them)
<!-- trust_hosts:end -->

## Why exactly three

The 2026-05-01 meta-research concluded that harness assumptions age as models
improve, and that prompt walls do not survive real load. The right answer is
to commit to the hosts where the gate layer is **mechanical** and run the
runtime guards there as subprocesses. The other five platforms either lack a
hook layer, lack an enforcement surface, or have advisory-only rule files.

Adding a fourth trust-bearing host requires an explicit amendment to this
file with rationale, evidence of mechanical enforcement, and a runtime guard
integration plan. Removing one is allowed but must be justified.

## Operator-installation evidence (2026-06-11)

- **Hermes**: `~/.hermes/profiles/azoth-personal-cockpit/` — active profile, session DB present.
- **Codex**: installed at `/Users/yiwei/.npm-global/bin/codex` (symlink to
  `@openai/codex/bin/codex.js`); verified by Hermes-visible shim at
  `~/.hermes/profiles/azoth-personal-cockpit/bin/codex`. Version 0.131.0.
- **OpenCode**: installed at `/Users/yiwei/.opencode/bin/opencode` (Mach-O
  arm64 native binary); verified by Hermes-visible shim at
  `~/.hermes/profiles/azoth-personal-cockpit/bin/opencode`. Version 1.14.33.

If any host is moved or removed, update the shim layer first, then update
this file in the same change.
