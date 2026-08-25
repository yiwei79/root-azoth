# Azoth repo-local execpolicy for Codex `approval_policy = "untrusted"`.
# Keep this narrowly scoped: allow only high-frequency, low-risk commands that
# are already bounded by workspace sandboxing or repo-local read semantics.

# Read-only Git inspection.
prefix_rule(pattern=["git", "status"], justification="Read-only repo status inspection.")
prefix_rule(
    pattern=["git", "diff", "--no-index"],
    decision="prompt",
    justification="Cross-tree diff mode is broader than normal repo inspection.",
)
prefix_rule(pattern=["git", "diff"], justification="Read-only diff inspection.")
prefix_rule(pattern=["git", "show"], justification="Read-only object inspection.")
prefix_rule(pattern=["git", "log"], justification="Read-only history inspection.")
prefix_rule(
    pattern=["git", "branch", ["--list", "--show-current"]],
    justification="Read-only branch inspection forms only.",
)

# Azoth read-only verification and dashboard scripts.
prefix_rule(
    pattern=["python3", "scripts/check_gates.py"],
    justification="Repo-local gate validation without mutation.",
)
prefix_rule(
    pattern=["python3", "scripts/welcome.py"],
    justification="Repo-local dashboard rendering without mutation.",
)
prefix_rule(
    pattern=["python3", "scripts/roadmap_dashboard.py"],
    justification="Repo-local roadmap dashboard rendering without mutation.",
)
prefix_rule(
    pattern=["python3", "scripts/codex_hooks_mode.py", "status"],
    justification="Read-only Codex mode status inspection.",
)
prefix_rule(
    pattern=["python3", "scripts/azoth-deploy.py", "--check"],
    justification="Read-only deploy parity verification.",
)

# High-blast-radius shell entry points and mutating Git paths should always prompt.
prefix_rule(pattern=["bash"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["sh"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["zsh"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["/bin/bash"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["/bin/sh"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["/bin/zsh"], decision="prompt", justification="Shell wrappers can hide broad side effects.")
prefix_rule(pattern=["git", "add"], decision="prompt", justification="Stages mutable repo state.")
prefix_rule(pattern=["git", "commit"], decision="prompt", justification="Creates mutable history.")
prefix_rule(pattern=["git", "push"], decision="prompt", justification="Publishes mutable history.")
prefix_rule(pattern=["git", "cherry-pick"], decision="prompt", justification="Replays mutable history.")
prefix_rule(pattern=["git", "rebase"], decision="prompt", justification="Rewrites history.")
prefix_rule(pattern=["git", "merge"], decision="prompt", justification="Mutates branch history.")
prefix_rule(pattern=["git", "branch", "-d"], decision="prompt", justification="Deletes a branch ref.")
prefix_rule(pattern=["git", "branch", "-D"], decision="prompt", justification="Force deletes a branch ref.")
prefix_rule(
    pattern=["python3", "scripts/do_closeout.py"],
    decision="prompt",
    justification="Writes Azoth closeout state.",
)
prefix_rule(
    pattern=["python3", "scripts/worktree_sync.py"],
    decision="prompt",
    justification="Mutates worktrees and integration state.",
)

# Explicitly forbid destructive patterns that Azoth should never normalize as smooth-path defaults.
prefix_rule(
    pattern=["rm", "-rf"],
    decision="forbidden",
    justification="Recursive destructive deletion is outside Azoth seamless mode.",
)
prefix_rule(
    pattern=["git", "reset", "--hard"],
    decision="forbidden",
    justification="Hard reset discards state outside Azoth seamless mode.",
)
