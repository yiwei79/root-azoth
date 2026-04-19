# Azoth — The Universal Agentic Toolkit

> *"Be water, my friend."*

**Azoth** is a portable agentic toolkit: disciplined agents, layered memory, governed delivery pipelines, and a single human alignment point. The name comes from alchemy — Azoth is the *universal solvent*: it dissolves into any project and transforms how agents work within it.

**License:** [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) (copyright retained; commercial use by arrangement — see `LICENSE`) · **Version:** see `[azoth.yaml](azoth.yaml)`

---

## Philosophy in one minute

- **Be water** — a tiny invariant **kernel** (Layer 0), refinable **skills** and memory (Layer 1), **agent** archetypes (Layer 2), and per-goal **pipelines** (Layer 3). Shape follows the task; entropy stays bounded.
- **A-to-Z** — completeness from bootloader to delivery; patterns can promote from episode → semantic memory → procedural assets when humans approve.
- **Trust by design** — scope cards, governed routes for kernel work, and (in Claude Code) hooks that enforce gates on writes.

Full design: `[docs/AZOTH_ARCHITECTURE.md](docs/AZOTH_ARCHITECTURE.md)` (decisions, layers, sync model).

---

## This repo vs the public product


|          | **root-azoth** (this repository)                           | **azoth** (public package)                          |
| -------- | ---------------------------------------------------------- | --------------------------------------------------- |
| Role     | Private **workshop** — design, build, and test the toolkit | Deployable product **extracted** from this scaffold |
| Audience | You, maintainers, contributors                             | Anyone who clones the released artifact             |


Mechanical extraction uses `sync-config.yaml` and product profiles (see architecture **§18** three-tier model). Until you publish, treat **this** clone as the source of truth.

---

## Quickstart — develop in **root-azoth**

For people working **in this repo**:

1. **Prerequisites:** Python **3.11+**, `git`, and one co-primary host: [Claude Code](https://claude.com/claude-code) or Codex. Optional: OpenCode, Copilot, Cursor, Gemini adapters.
2. **Install Python deps** used by tooling (e.g. Rich for the welcome dashboard):
  `pip install -r requirements-dev.txt` (from repo root; or your project venv).
  This form satisfies **pip-install-guard** in Claude Code Bash.
3. **Validate:** `python3 -m pytest` and `python3 -m ruff check .` / `ruff format --check .` (same gates as **GitHub Actions** `.github/workflows/ci.yml`).
4. **After changing** canonical `.claude/commands/*.md`, `skills/*`, `agents/**`, or Codex adapter bridge files, sync platform copies:
  `python3 scripts/azoth-deploy.py`
5. **Public product extract (P4-004):** `python3 scripts/azoth_extract_product.py --validate-only` (CI smoke) or
  `python3 scripts/azoth_extract_product.py --out /tmp/azoth-dist` (full tree per `sync-config.yaml` `product_extraction`).
6. **Session entry:** In **Claude Code**, **SessionStart** injects plain orientation at open (see `CLAUDE.md` rule 9); you can still run `/start` or `python3 scripts/welcome.py` for Rich or a refresh. In **Codex**, `$azoth-start` is the canonical daily entry surface: use `$azoth-start`, `$azoth-start next`, `$azoth-start closeout`, or `$azoth-start pipeline_command=<auto|deliver|deliver-full> <goal>`. Compatibility wrappers like `$azoth-auto` and `$azoth-deliver-full`, plus literal `/start`, `/next`, `/auto`, and `/deliver-full` text, normalize back through the same calm-flow control plane; they are compatibility fallback surfaces, not native Codex slash registration. Elsewhere, run `/start` or `python3 scripts/welcome.py`, then `/next`, `/intake`, or a custom goal per the generated command surfaces.

Core contributor context lives in `**[CLAUDE.md](CLAUDE.md)`** — read it first.

---

## Quickstart — install Azoth **into another project**

You install **from** a checkout of this repo **into** a target project (not into the Azoth repo itself).

**Interactive entry (recommended):** from the repo root, run `python3 scripts/azoth_init.py` — choose **project** to install into your current directory, or **scaffold** for workshop-only next steps. Non-interactive: `python3 scripts/azoth_init.py --project -y` or `--scaffold -y`.

**Direct installers** (same behavior as project mode):

```bash
cd /path/to/your-app
bash /path/to/root-azoth/install.sh
```

The installer detects your AI toolchain (Claude Code, Codex, OpenCode, Copilot, etc.), lays down templates, and wires the bootloader. If you have not bootstrapped before, see `**[docs/DAY0_TUTORIAL.md](docs/DAY0_TUTORIAL.md)**`.

**Windows:** use `install.ps1` the same way (from PowerShell, with paths adjusted), or `python3 scripts/azoth_init.py --project -y` from a checkout of this repo.

---

## Where to go next

**Paths:** In **this** repo (root-azoth), Layer 0 lives at `**kernel/`**. In a **consumer project** after `install.sh`, the same governance text is under `**.azoth/kernel/`** — see architecture **§18** (D42).


| Need                                                  | Location                                                                                                              |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Architecture & decisions                              | `[docs/AZOTH_ARCHITECTURE.md](docs/AZOTH_ARCHITECTURE.md)`                                                            |
| Path duality (scaffold `kernel/` vs `.azoth/kernel/`) | Architecture **§18** (D42)                                                                                            |
| Boot sequence (Activate → Survey → Operate → Harden)  | `[kernel/BOOTLOADER.md](kernel/BOOTLOADER.md)` (this repo) · `**BOOTLOADER.md`** under `.azoth/kernel/` after install |
| Trust, entropy, alignment                             | `[kernel/TRUST_CONTRACT.md](kernel/TRUST_CONTRACT.md)` · or `.azoth/kernel/TRUST_CONTRACT.md` when installed          |
| Governance & memory rules                             | `[kernel/GOVERNANCE.md](kernel/GOVERNANCE.md)` · or `.azoth/kernel/GOVERNANCE.md` when installed                      |
| Sync / extraction                                     | `[scripts/azoth-sync.py](scripts/azoth-sync.py)`, `[sync-config.yaml](sync-config.yaml)`                              |


---

## Contributing

Work happens under the Azoth trust contract: bounded changes, human approval for kernel promotion, and no scope creep past an approved goal. If you add skills, agents, slash commands, or Codex adapter files, run `**python3 scripts/azoth-deploy.py**` so Codex, OpenCode, Copilot, and Cursor stay aligned.

**Pull requests:** Opening a PR loads [`.github/pull_request_template.md`](.github/pull_request_template.md) — including a **one-liner** to request **GitHub Copilot** review so findings land as **D32 inbox JSONL** (see [`kernel/GOVERNANCE.md`](kernel/GOVERNANCE.md) §7) for **`/intake`**, not ad-hoc drive-by edits. Repository Copilot context: [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

**Cursor:** For IDE-side blindspot review that **writes the same D32 contract** to `.azoth/inbox/`, use **`/review-insights`** or follow **`skills/cursor-review-insights/SKILL.md`** (see [`.cursor/rules/code-review-insights.mdc`](.cursor/rules/code-review-insights.mdc) after `azoth-deploy`).

**Slash commands** (`.claude/commands/*.md`) must declare `**azoth_effect: read | write | mixed`** in YAML frontmatter so it is obvious whether the default path can **build** (Write/Edit) or stays read-only — see `[kernel/GOVERNANCE.md](kernel/GOVERNANCE.md)`.
