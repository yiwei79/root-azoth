# Azoth Source-of-Truth Inventory

**Purpose:** Make existing authority boundaries explicit so simplification removes duplicate truth instead of creating new authority.

**Rule:** This file is an index. It does not supersede the canonical sources below.

## Canonical Truths

| Topic | Canonical Source | Generated Mirrors | Validation Gate |
|---|---|---|---|
| Decisions count and decision IDs | `docs/DECISIONS_INDEX.md` | `CLAUDE.md`, `GEMINI.md`, generated host context text | No complete gate yet; drift observed between 53, D1-D54, and D57 references |
| Trust-bearing hosts | `kernel/TRUST_HOSTS.md` and `azoth.yaml` trust host lists | `AGENTS.md`, `docs/HOST_TRUST_MATRIX.md`, platform guides | `tests/test_trust_hosts_contract.py`, `scripts/hermes_manifest_check.py` presence/parsing checks |
| Kernel checksum set | `kernel/GOVERNANCE.md` Integrity Check Mechanism and `scripts/kernel-integrity.py` `CHECKSUM_REL` | `.azoth/kernel-checksums.sha256`, installer-generated consumer checksum files | `python3 scripts/kernel-integrity.py --verify-checksums`, `tests/test_kernel_integrity.py`, `tests/test_kernel_contract_doc_consistency.py`, `tests/test_install_sh_kernel_checksums.py`, `tests/test_hermes_manifest_check.py` |
| Agent definitions | `agents/**/*.agent.md` | `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, `.codex/agents/*.toml`, `.gemini/agents/` | `python3 scripts/azoth-deploy.py --check`, `tests/test_azoth_deploy.py` |
| Skills | `skills/*/SKILL.md` and `skills/index.yaml` | `.opencode/skills/`, `.agents/skills/`, command-wrapper skills under `.agents/skills/azoth-*` | `python3 scripts/azoth-deploy.py --check`, skills tests under `tests/test_skills.py` and related P3 tests |
| Commands | `commands/<name>/command.yaml` when present; legacy `.claude/commands/*.md` while migration is incomplete | `.claude/commands/`, `.github/prompts/`, `.opencode/commands/`, `.agents/workflows/`, `.agents/skills/azoth-*`, `.gemini/commands/` | `python3 scripts/azoth-deploy.py --check`, `docs/CANONICAL_COMMAND_CONTRACT.md`, command parity tests |
| Pipelines | `pipelines/*.pipeline.yaml` and `pipelines/pipeline.schema.yaml` | No host mirrors; routing logic is also duplicated in skills such as `skills/auto-router/SKILL.md` | `scripts/pipeline_lint.py`; schema is not currently the runtime validator |
| Installer behavior | `install.sh` and `install.ps1` | Consumer-project `.azoth/`, host directories, generated `CLAUDE.md` | Installer tests such as `tests/test_install_sh_kernel_checksums.py`; not currently unified with `azoth-deploy.py` |
| Deploy projection | `scripts/azoth-deploy.py` | All generated host mirrors and `AGENTS.md` | `python3 scripts/azoth-deploy.py --check`, `tests/test_azoth_deploy.py`, CI deploy parity step |
| Memory tiers | `kernel/GOVERNANCE.md`, `kernel/PROMOTION_RUBRIC.md`, `skills/remember/SKILL.md`, `skills/context-recall/SKILL.md` | `.azoth/memory/episodes.jsonl`, `.azoth/memory/patterns.yaml`, closeout/readback surfaces | `tests/test_episode_store.py`, `scripts/context_recall_quality.py`, `scripts/reinforcement_count.py`, promotion-related tests |
| Public product extraction | `sync-config.yaml` `product_extraction` and `scripts/azoth_extract_product.py` | Extracted public `azoth` tree | `python3 scripts/azoth_extract_product.py --validate-only`, extraction tests |

## Contradictions To Resolve

| Topic | Conflicting Files | Proposed Owner | Decision Needed |
|---|---|---|---|
| Primary platform story | `README.md`, `CLAUDE.md`, `docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md`, `kernel/TRUST_HOSTS.md`, `AGENTS.md` | `kernel/TRUST_HOSTS.md` should own trust posture; README/platform guides should own user-facing support posture | Choose whether to keep trust-bearing and user-facing support as separate axes or collapse them |
| Decision count references | `CLAUDE.md`, `GEMINI.md`, `docs/DECISIONS_INDEX.md`, `kernel/templates/platform-adapters/gemini/GEMINI.md.template` | `docs/DECISIONS_INDEX.md` | Add generation or tests so mirrors cannot stale-count decisions |
| `.claude/skills/` path | `AGENTS.md`, `scripts/azoth-deploy.py`, actual `.claude/` directory | `scripts/azoth-deploy.py` generator | Decide whether Claude Code should receive skills, or generated table should say no Claude skills directory |
| Trust hosts checksum coverage | `kernel/TRUST_HOSTS.md`, `.azoth/kernel-checksums.sha256`, `scripts/kernel-integrity.py`, `kernel/GOVERNANCE.md` | `kernel/GOVERNANCE.md` plus `scripts/kernel-integrity.py` | Resolved: `TRUST_HOSTS.md` is checksum-covered with the other root kernel docs |
| Pipeline runtime authority | `pipelines/auto.pipeline.yaml`, `pipelines/pipeline.schema.yaml`, `scripts/pipeline_lint.py`, `skills/auto-router/SKILL.md`, `scripts/autonomous_loop.py` | One of: `pipeline_lint.py` as actual validator, or schema as generated/loaded source | Decide whether YAML drives behavior or documents behavior; remove duplicate routing tables or add parity check |
| Installer vs deployer | `install.sh`, `install.ps1`, `scripts/azoth-deploy.py` | `scripts/azoth-deploy.py` should own host projection | Decide when installers should call deployer instead of duplicating copy logic |
| Portable toolkit vs operator cockpit | `README.md`, `docs/personal-control-plane/`, `scripts/personal_*`, `scripts/cockpit_*`, tracked `.azoth/` state | No single owner yet | Classify each surface as `core-toolkit`, `operator-extension`, or `local-state` |

## Do Not Add New Owners

- Do not create a second architecture index while `docs/DECISIONS_INDEX.md` exists.
- Do not create new generated host mirrors by hand; change canonical sources and run `scripts/azoth-deploy.py`.
- Do not create a new platform posture document until `kernel/TRUST_HOSTS.md` and `docs/CO_PRIMARY_PLATFORM_BLUEPRINT.md` are reconciled.
- Do not create a new pipeline schema until `pipeline_lint.py` and `pipelines/pipeline.schema.yaml` have one owner.
- Do not create a new memory tier vocabulary; use M3, M2, and M1 as defined in kernel governance docs.

## Next Simplification Target

Resolve one contradiction at a time. Recommended first target: decision-count references, because the canonical owner is clear (`docs/DECISIONS_INDEX.md`) and the fix can be guarded by a small regression test without changing platform strategy.
