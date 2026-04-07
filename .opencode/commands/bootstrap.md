---
description: Day 0 bootstrap — create the Azoth kernel from the architecture plan
---

# Azoth Day 0 Bootstrap

You are bootstrapping the Azoth Universal Agentic Toolkit from its architecture plan.
This is a guided process — you implement, the human reviews each phase.

## Pre-Flight

Before starting, read these files completely:
1. `CLAUDE.md` — project instructions and pointers to current phase
2. `skills/orientation/SKILL.md` — full v0.1.0 phase roadmap and expanded workflow (lazy-loaded)
3. `docs/AZOTH_ARCHITECTURE.md` — the full architecture plan (28 decisions)

Confirm you understand:
- The four-layer Water Molecule Model
- The 3-layer memory system (M1/M2/M3)
- The Trust Contract concept
- The platform adapter pattern
- The 7-stage pipeline architecture (D21)
- The auto-pipeline composition (D23)
- The Proactive Agent Posture tiers (D26)
- The v0.1.0 phase roadmap (detail in `skills/orientation/SKILL.md`)

## Bootstrap Sequence

Present this to the human:

```
╔══════════════════════════════════════════════════╗
║           🧪 AZOTH — Day 0 Bootstrap            ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Welcome. This is the first bootstrap of Azoth.  ║
║  I'll guide you through creating the kernel.     ║
║                                                  ║
║  What we'll build today:                         ║
║                                                  ║
║  Phase 1: Kernel Extraction                      ║
║  ├── kernel/BOOTLOADER.md                        ║
║  ├── kernel/TRUST_CONTRACT.md                    ║
║  ├── kernel/GOVERNANCE.md                        ║
║  ├── kernel/PROMOTION_RUBRIC.md                  ║
║  ├── kernel/templates/ (5 template files)        ║
║  ├── kernel/templates/platform-adapters/         ║
║  ├── install.sh + install.ps1                    ║
║  └── azoth.yaml (update status)                  ║
║                                                  ║
║  Phase 1.5: Sync Infrastructure                  ║
║  ├── scripts/azoth-sync.py                       ║
║  ├── sync-config.yaml                            ║
║  └── .claude/commands/sync.md                    ║
║                                                  ║
║  Your role: Review each phase, approve/adjust    ║
║  My role: Implement, validate, report            ║
║                                                  ║
║  Ready? Type 'go' or ask questions first.        ║
╚══════════════════════════════════════════════════╝
```

## Phase 1: Kernel Extraction

### Step 1.1: kernel/BOOTLOADER.md
Extract the bootloader pattern from the architecture plan.
Source reference: Layer 0 Molecule specification.
The bootloader defines the 4-phase boot sequence: Activate → Survey → Operate → Harden.

After creating, report to human:
- File created with N lines
- Key sections: [list]
- Alignment check: matches architecture plan? Yes/No

### Step 1.2: kernel/TRUST_CONTRACT.md
This is a NEW design (not extracted from source framework).
Core components:
- Entropy Ceiling (bounded blast radius per agent turn)
- Alignment Protocol (PULL-based, phone-friendly summaries)
- Drift Detection (kernel integrity checks)
- Recovery Protocol (git-based checkpoints)
- Sustainable Velocity Principle (quality > speed)
- Anti-Slop Commitment

After creating, report to human with alignment check.

### Step 1.3: kernel/GOVERNANCE.md
Distill governance rules:
- Append-only memory (never edit/delete episodes)
- Drift detection contract
- Human-in-the-loop gates
- Promotion flow (M3 → M2 → M1)

### Step 1.4: kernel/PROMOTION_RUBRIC.md
Extract the 4-question decision tree:
- A. Scope Test (repo-specific?)
- B. Reuse Test (useful elsewhere?)
- C. Preference Test (personal style?)
- D. Maturity Test (proven enough?)
Four homes: Generic Toolkit, Repo-Local, Personal, Not Yet.

### Step 1.5: kernel/templates/
Create template files used by `azoth init`:
- CLAUDE.md.template — what consumer projects get
- settings.json.template — Claude Code permissions
- copilot-instructions.md.template — Copilot redirect to CLAUDE.md
- bootloader-state.md.template — project bootloader state

### Step 1.6: kernel/templates/platform-adapters/
Templates for platform-specific files:
- claude/ — .claude/commands/, .claude/agents/ templates
- opencode/ — .opencode/agent/, opencode.jsonc templates
- copilot/ — .github/agents/, .github/prompts/ templates

### Step 1.7: Installer Scripts
Create install.sh (macOS/Linux primary) and install.ps1 (Windows).
Must:
- Detect target platform(s)
- Deploy kernel files
- Generate CLAUDE.md from template
- Set up memory directory (.azoth/memory/)
- Present interactive options for skill/agent deployment
- Validate deployment structure

### Step 1.8: Validate Phase 1
Run structural validation:
1. Count kernel files — should be 4 + templates/
2. Verify CLAUDE.md exists and contains project routing
3. Verify install.sh is syntactically valid
4. Compare directory tree against AZOTH_ARCHITECTURE.md
5. Print drift report: EXPECTED vs ACTUAL
6. Update azoth.yaml with new status
7. Present alignment summary to human

## Phase 1.5: Sync Infrastructure

### Step 1.5.1: scripts/azoth-sync.py
Python script for deterministic sync extraction:
- SCAN: Read source framework directory
- DIFF: Compare against Azoth's current state
- PROPOSE: Apply promotion rubric to each delta
- SANITIZE: Strip org-specific references
Must use pathlib, work cross-platform, have clear CLI interface.

### Step 1.5.2: sync-config.yaml
Sanitization rules — patterns to strip, paths to exclude.

### Step 1.5.3: /sync command
Claude Code command for agent-driven sync with proposal generation.

### Step 1.5.4: Validate Phase 1.5
- azoth-sync.py runs without errors (--help flag)
- sync-config.yaml is valid YAML
- /sync command has correct frontmatter

## Completion

After all phases complete:
1. Update `skills/orientation/SKILL.md` phase checklist (and one-line pointer in `CLAUDE.md` if needed)
2. Update azoth.yaml status
3. Git commit with message: "feat: Phase 1 + 1.5 — Kernel extraction and sync infrastructure"
4. Print final alignment summary:

```
╔══════════════════════════════════════════════════╗
║        🧪 AZOTH — Bootstrap Complete            ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  Phase 1: Kernel Extraction    ✅ Complete       ║
║  Phase 1.5: Sync Infrastructure ✅ Complete      ║
║                                                  ║
║  Files created: [N]                              ║
║  Kernel integrity: [PASS/FAIL]                   ║
║  Architecture drift: [NONE/details]              ║
║                                                  ║
║  Next: Phase 2 (Core Skills)                     ║
║  Command: /deliver phase-2                       ║
║                                                  ║
╚══════════════════════════════════════════════════╝
```

$ARGUMENTS
