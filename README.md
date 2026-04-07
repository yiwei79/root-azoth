# Azoth — The Universal Agentic Toolkit

> *"Be water, my friend."*

**Azoth** is a portable agentic toolkit: disciplined agents, layered memory, governed delivery pipelines, and a single human alignment point. The name comes from alchemy — Azoth is the *universal solvent*: it dissolves into any project and transforms how agents work within it.

**License:** MIT · **Version:** see [`azoth.yaml`](azoth.yaml)

---

## Philosophy in one minute

- **Be water** — a tiny invariant **kernel** (Layer 0), refinable **skills** and memory (Layer 1), **agent** archetypes (Layer 2), and per-goal **pipelines** (Layer 3). Shape follows the task; entropy stays bounded.
- **A-to-Z** — completeness from bootloader to delivery; patterns can promote from episode → semantic memory → procedural assets when humans approve.
- **Trust by design** — scope cards, governed routes for kernel work, and (in Claude Code) hooks that enforce gates on writes.

Full design: [`docs/AZOTH_ARCHITECTURE.md`](docs/AZOTH_ARCHITECTURE.md) (decisions, layers, sync model).

---

## This repo vs the public product

| | **root-azoth** (this repository) | **azoth** (public package) |
|--|-----------------------------------|----------------------------|
| Role | Private **workshop** — design, build, and test the toolkit | Deployable product **extracted** from this scaffold |
| Audience | You, maintainers, contributors | Anyone who clones the released artifact |

Mechanical extraction uses `sync-config.yaml` and product profiles (see architecture **§18** three-tier model). Until you publish, treat **this** clone as the source of truth.

---

## Quickstart — develop in **root-azoth**

For people working **in this repo**:

1. **Prerequisites:** Python **3.11+**, `git`, [Claude Code](https://claude.com/claude-code) (primary). Optional: OpenCode, Copilot adapters.
2. **Install Python deps** used by tooling (e.g. Rich for the welcome dashboard):  
   `pip install rich pyyaml` (or your project venv).
3. **Validate:** `python3 -m pytest tests/` (or `ruff` / project scripts if you use them).
4. **After changing** canonical `skills/**`, `agents/**`, or `.claude/commands/**`, sync platform copies:  
   `python3 scripts/azoth-deploy.py`
5. **Session entry:** run `/start` in Claude Code, or `python3 scripts/welcome.py`, then use `/next`, `/intake`, or a custom goal per the command docs in `.claude/commands/`.

Core contributor context lives in **[`CLAUDE.md`](CLAUDE.md)** — read it first.

---

## Quickstart — install Azoth **into another project**

You install **from** a checkout of this repo **into** a target project (not into the Azoth repo itself).

**Interactive entry (recommended):** from the repo root, run `python3 scripts/azoth_init.py` — choose **project** to install into your current directory, or **scaffold** for workshop-only next steps. Non-interactive: `python3 scripts/azoth_init.py --project -y` or `--scaffold -y`.

**Direct installers** (same behavior as project mode):

```bash
cd /path/to/your-app
bash /path/to/root-azoth/install.sh
```

The installer detects your AI toolchain (Claude Code, OpenCode, Copilot, etc.), lays down templates, and wires the bootloader. If you have not bootstrapped before, see **[`docs/DAY0_TUTORIAL.md`](docs/DAY0_TUTORIAL.md)**.

**Windows:** use `install.ps1` the same way (from PowerShell, with paths adjusted), or `python3 scripts/azoth_init.py --project -y` from a checkout of this repo.

---

## Where to go next

**Paths:** In **this** repo (root-azoth), Layer 0 lives at **`kernel/`**. In a **consumer project** after `install.sh`, the same governance text is under **`.azoth/kernel/`** — see architecture **§18** (D42).

| Need | Location |
|------|----------|
| Architecture & decisions | [`docs/AZOTH_ARCHITECTURE.md`](docs/AZOTH_ARCHITECTURE.md) |
| Path duality (scaffold `kernel/` vs `.azoth/kernel/`) | Architecture **§18** (D42) |
| Boot sequence (Activate → Survey → Operate → Harden) | [`kernel/BOOTLOADER.md`](kernel/BOOTLOADER.md) (this repo) · **`BOOTLOADER.md`** under `.azoth/kernel/` after install |
| Trust, entropy, alignment | [`kernel/TRUST_CONTRACT.md`](kernel/TRUST_CONTRACT.md) · or `.azoth/kernel/TRUST_CONTRACT.md` when installed |
| Governance & memory rules | [`kernel/GOVERNANCE.md`](kernel/GOVERNANCE.md) · or `.azoth/kernel/GOVERNANCE.md` when installed |
| Sync / extraction | [`scripts/azoth-sync.py`](scripts/azoth-sync.py), [`sync-config.yaml`](sync-config.yaml) |

---

## Contributing

Work happens under the Azoth trust contract: bounded changes, human approval for kernel promotion, and no scope creep past an approved goal. If you add skills, agents, or slash commands, run **`python3 scripts/azoth-deploy.py`** so OpenCode, Copilot, and Cursor stays stay aligned.

**Slash commands** (`.claude/commands/*.md`) must declare **`azoth_effect: read | write | mixed`** in YAML frontmatter so it is obvious whether the default path can **build** (Write/Edit) or stays read-only — see [`kernel/GOVERNANCE.md`](kernel/GOVERNANCE.md).
