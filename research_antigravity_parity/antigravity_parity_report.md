# Antigravity Parity Resolution Report

## The Problem

Prior to our fix, the Antigravity (Gemini IDE) workspace was functioning in a "bootstrap loop" mode. It manually hosted exactly four minimized workflows (`/auto`, `/next`, `/deliver`, and `/session-closeout`) in the `.agents/workflows/` directory.

However, the repository's native operating model holds **21 canonical commands** inside the `.claude/commands/` directory. For other platforms like OpenCode and Copilot, these canonical commands are automatically transformed and mapped via the `scripts/azoth-deploy.py` utility.

## Why it Wasn't Working

1. **Deployment Vacuum:** Antigravity was not targeted by the `azoth-deploy.py` script.
2. **Missing Files:** The IDE uses the actual presence of `.md` files in `.agents/workflows/` and `.agents/skills/` to define its slash commands and tools. Because the deploy script didn't target Antigravity, those remaining 17 workflows (such as `/eval`, `/intake`, and `/start`) literally did not exist in the `.agents/` path that the IDE evaluates.
3. **Hardcoded Sandboxing:** The initial bootstrap versions of `auto.md` and `deliver.md` manually hardcoded text refusing to process kernel files. We needed a way to provide those protections globally without overriding every canonical file.

## The Resolution

We adapted the project seamlessly by:

1. Formalizing the sandboxing boundaries into a `.md.template` (`kernel/templates/platform-adapters/antigravity/azoth-core.md.template`), turning the hardcoded warnings into a global "Always On" rule.
2. Modifying `azoth-deploy.py` to add `antigravity` to its `--platforms` loop.
3. Running `azoth-deploy.py`, which projected all 21 `.claude/commands/` into `.agents/workflows/`. The IDE now reads this population and registers them as usable slash commands natively.

## Self-Improvement Lessons

1. **Audit deploy coverage before UI diagnosis.**
   When a new platform does not expose expected commands, first check whether the platform is actually targeted by the deployment path. In this case, the missing slash commands were caused by a deployment vacuum, not by a markdown-shape problem.

2. **Treat file presence as the source of truth for file-discovered platforms.**
   Antigravity defines workflows and skills from the actual files under `.agents/workflows/` and `.agents/skills/`. A partial bootstrap is not parity; it is only a temporary subset.

3. **Use adapter projection instead of hand-maintained mirrors.**
   For serious platform support, projecting canonical `.claude/commands/` into the target platform path via `azoth-deploy.py` is more reliable than maintaining a manually reduced workflow set.

4. **Move global boundaries into adapter rules or templates.**
   Cross-cutting protections such as kernel or governed-work boundaries should live in a platform-level rule/template, not be duplicated as hardcoded caveats inside each mirrored workflow.

5. **Do not let UI errors outrank simpler structural explanations.**
   A UI error like `__store` may still be real, but it should not be treated as the primary root cause until deploy coverage and file population have been ruled out.

## What To Reuse

- New platform parity work should begin with: canonical source inventory, deploy-target coverage check, target-path population check, then runtime/UI diagnosis.
- Manual bootstrap workflows are acceptable only as a short-lived bridge while a real deploy target is being added.
- The Antigravity install and deploy path should remain a distinct initiative until the adapter is proven operational.
