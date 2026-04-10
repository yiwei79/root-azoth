# Post-Deploy Functional Parity Audit: Azoth

This document evaluates the functional parity established across Claude Code (authoritative), GitHub Copilot (lightweight mirror), and Antigravity (Gemini IDE adapter) after the `INI-PLT-005` deployment integration.

## 1. Instruction & Governance Surface
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `CLAUDE.md` | Primary always-on file loaded by Claude organically. | Base |
| **Copilot** | `CLAUDE.md` / `*.md` | Unstructured read. Copilot doesn't strictly adhere to complex, multi-page always-on governance. | Partial |
| **Antigravity** | `.agents/rules/*.md` | Generates `.agents/rules/azoth-core.md` dynamically from kernel templates. This provides an explicit "Always On" sandbox constraint wrapper. | **Strong Parity** |

## 2. Command Architecture (Slash Commands)
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `.claude/commands/` | Organically maps directory to slash commands. | Base |
| **Copilot** | `.github/prompts/` | Azoth maps via `azoth-deploy.py`, transforming commands to `.prompt.md` files. | High |
| **Antigravity** | `.agents/workflows/` | Azoth maps via `azoth-deploy.py`, mapping `*.md` directly. | **Full Parity** |
*Note: Now that deployment scripting is linked, Antigravity commands update synchronously with Claude commands.*

## 3. Tool Interceptions & Hooks
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `settings.json` | Uses programmatic shell scripts via `PreToolUse` for hard intercepts (e.g. `azoth_effect: write` triggers). | Base |
| **Copilot** | N/A | Does not natively intercept or pause tool chains using bash hooks. | None |
| **Antigravity** | Workspace Config | Relies on IDE-driven "Workspace Validation", sandbox constraints, explicit allowed paths, and the Always On `.agents/rules` strict-mode wrapper rather than shell scripts. | **Behavioral Parity** |

## 4. Skills & Capabilities
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `/skills/` | Read progressively based on prompt needs. | Base |
| **Copilot** | `.github/skills/` | Mirrored mapping via deploy script. | Full |
| **Antigravity** | `.agents/skills/` | Mirrored mapping. Additionally, Antigravity preserves custom local tooling like `deep-research` or `explainer-visuals` unique to its adapter suite. | **Full Parity+** |

## 5. Agent Personas
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `.claude/agents/` | Standalone AI personalities (e.g., Architect, Builder). | Base |
| **Copilot** | `.github/agents/` | Mapped out using specific `.agent.md` file translation. | Full |
| **Antigravity** | Behavioral | Antigravity does not parse standalone custom agent menu lists from files natively. Azoth archetypes are effectively emulated behaviorally through the specialized `.agents/workflows/` and available `.agents/skills/`. | **No structural parity (By Design)** |

## 6. Runtime Local State (`.azoth/`)
| Platform | Source | Mechanism | Parity Result |
| :--- | :--- | :--- | :--- |
| **All Platforms** | `.azoth/` | Standard Operating Files (`session-state.md`, `scope-gate.json`, `pipeline-gate.json`). | **Full Parity** |
*Note: Because Antigravity is now reading the canonical Claude command structures (like `auto.md`), it will correctly ask to read and write to `.azoth/scope-gate.json` symmetrically to Claude Code.*

---

### Conclusion
By shifting Antigravity from a manually maintained "bootstrap loop" folder into an active target of `azoth-deploy.py`, we replaced a bottlenecked system with a fully synchronized adapter layer. 

**Areas to Watch:**
The only deliberate gaps map directly to platform limitations: 
1. The decision not to build a complex hook-bridging system for Antigravity (favoring the built-in IDE Workspace Validation and strict mode rule bounds instead).
2. The lack of bespoke `.agent` files. Given Antigravity executes task loops dynamically based on workflows, the "Agent Personas" are naturally bypassed while maintaining operational cadence.
