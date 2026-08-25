# Native PM Campaign Architecture Discovery - Route Truth And Option Board

Date: 2026-05-05
Child scope: `2026-05-05-autonomous-auto-native-pm-campaign-architecture-discovery-1`
Action: `research_initiative`
Status: complete enough for approval-ready declaration

## Authority Boundary

This is a campaign-local research artifact. It does not hydrate tasks, mutate
roadmap/backlog/spec state, change public/cockpit/project repos, commit, push,
or approve protected work.

Canonical authority remains:

- `.azoth/roadmap.yaml`
- `.azoth/backlog.yaml`
- initiative and design banks
- existing guarded route helpers
- explicit operator approval for any later delivery or protected boundary

## Live Route Truth

| Surface | Current read | PM implication |
| --- | --- | --- |
| `autonomous_loop.py status --operator-read` | Previous loop completed Green; new loop active only for this research child. | Old budgets cannot be reused; a fresh declaration is required. |
| `run_ledger.py status` | Current child owns the only active write claim. | Continue only inside this approved research/refinement scope. |
| `pm_orchestrator_mobility.py --json` | Zero safe hydration candidates across `INI-AUTO-001`, `INI-EVI-002`, `INI-MEM-003`, and `INI-PKB-001`. | Do not open hydration or delivery from initiative banks now. |
| Product Strategy Orchestrator | Initiative Discovery is the PM spine; Harness Rethink is the strategic constraint; next real product move needs human choice. | Use PM strategy to select a campaign, not to bypass gates. |
| P4 postmortem | `v0.2.0-p4` is complete; further p4 work needs named-lane approval. | No automatic p4 continuation. |
| Public freshness policy | Public `azoth` v0.2.0 is latest approved installable release; root drift is advisory. | Public product/update strategy is the highest-value unresolved lane, but execution is protected. |
| Phase 4 history board | Four-plane operating model is current historical truth. | Future public/product work must preserve root/public/cockpit/project boundaries. |

## Option Board

| Rank | Candidate | Route | Score | PM judgment |
| ---: | --- | --- | ---: | --- |
| 1 | Public Product Update Policy and Four-Plane Release Boundary Strategy | `research_initiative` then stop for approval | 0.92 | Best next lane. It resolves the biggest product-strategy ambiguity: how root workshop drift should become public product content without collapsing cockpit/project authority. |
| 2 | Four-Plane Vocabulary and Operator Prompt Alignment | `refine_proposal` | 0.86 | Valuable, but best treated as a sub-question of public/update boundary strategy. |
| 3 | Backup/private-remote decision for `yiwei-azoth-cockpit` | stop for protected gate | 0.74 | Important resilience lane, but it likely touches private remote, backup, restore, or credential decisions. |
| 4 | Cockpit receipt/index cleanup | stop or protected delivery gate | 0.70 | Useful UX cleanup, but narrower than the public/product strategy problem and may require cockpit/project writes. |
| 5 | Packaging/commit of completed campaign artifacts | stop for packaging approval | 0.62 | Operationally useful but not a product-management campaign. |
| 6 | Hydration-specific initiative campaign | stop | 0.38 | Current helper reports zero safe hydration candidates. Opening this would repeat stale work. |

## Selected Lane

Select **Public Product Update Policy and Four-Plane Release Boundary Strategy**.

Reasoning:

- It is the highest unresolved product-management question after p4: when and
  how does root workshop drift become public product content?
- It can be researched and refined without public sync, checkout mutation,
  release, cockpit/project writes, credentials, network, dependencies, commits,
  or pushes.
- It naturally includes the four-plane vocabulary problem instead of treating it
  as a shallow documentation cleanup.
- It gives the operator a useful next gate: approve a public-release strategy
  campaign, keep public `azoth` intentionally stale, or split a narrower
  internal language-alignment lane.

## Rejected Alternatives

- **Hydration now:** rejected because PM mobility reports no safe hydration
  candidate.
- **Implementation now:** rejected by the approved campaign budget and because
  the selected question is strategy-first.
- **Backup/private remote now:** rejected because it is protected and may
  involve credentials or external infrastructure.
- **Cockpit/project writes now:** rejected because project and cockpit authority
  are separate gates.
- **Packaging/commit now:** rejected because the approved budget explicitly
  blocks commits and pushes.

## Residual Risks

- Public freshness evidence is current only as a local policy read; a real
  release campaign would need fresh extraction, product smoke, public checkout
  verification, and explicit public sync/release approval.
- The selected next campaign must not mutate public `azoth`; it should stop with
  a strategy and gate packet.
- The four-plane model can become confusing if the campaign treats cockpit or
  controlled project repos as downstream consumers instead of separate authority
  planes.

## Next Artifact

The selected declaration is recorded in:

`.azoth/campaigns/native-pm-campaign-architecture-discovery-20260505/selected-next-campaign-declaration.md`
