# Profile Split Open Questions

Date: 2026-05-01

Status: questions to resolve before Azoth-native planning or implementation.

## Must Answer Before Implementation

1. Should `azoth-lite` classification be model-only, scripted, or hybrid?

   Recommendation: start hybrid. Use a small deterministic classifier for path
   and action triggers, with model judgment for ambiguous goal intent.

2. Where should `azoth-lite` traces live after the meta-session?

   Options:

   - no trace by default, final-answer summary only;
   - local non-governed trace folder outside `.azoth/`;
   - `.azoth` trace state, which would make lite too governed by default.

   Recommendation: avoid `.azoth` trace state until the profile proves that
   trace capture is worth productizing.

3. Does Codex freeform routing need to stop opening `.azoth/session-gate.json`
   for exploratory goals?

   Recommendation: do not change it immediately. First test whether session
   gates are useful continuity or unwanted native-state capture for lite work.

4. How does `azoth-lite` hand off to `azoth-full` without making the user repeat
   the whole goal?

   Recommendation: standardize the handoff packet before touching route code.

5. What exactly counts as "ordinary local edit" in root-azoth?

   Recommendation: source/docs/tests/research artifacts outside `.azoth/`,
   `kernel/`, hooks, command contracts, generated adapters, release state, and
   dependency manifests.

6. Should changing `commands/*/command.yaml` count as governed state or
   kernel/governance?

   Recommendation: treat command contracts as governed/high-audit even though
   they live outside `.azoth/`, because they control runtime behavior and
   generated platform projections.

7. Which existing tests are the minimum no-regression gate?

   Recommendation: scope-gate, run-ledger, session closeout, command parity,
   Codex control plane, adapter templates, and any new profile classifier tests.

## Can Defer To Later Phases

1. Should `stock-lite` become an explicit selectable profile in user-facing
   commands, or remain an eval baseline and informal mode?

2. Should `azoth-lite` have a named command, or should it stay as the default
   posture behind `/start`?

3. Should `azoth-lite` traces eventually join M3 memory, and if so, under what
   human gate?

4. Should `meta-harness-experimental` use the existing run ledger, a separate
   event log, or a new trace model?

5. Can host-level tool approvals replace some Azoth prompt-time gates on
   platforms with strong permission APIs?

6. How should the profile split be represented in public product extraction?

7. Do generated adapters need distinct profile surfaces per platform, or can
   they share one source profile guide?

## Explicit Non-Questions For Now

These should not be reopened during the first implementation phase:

- whether to delete `azoth-full`;
- whether to remove scope gates;
- whether to bypass human gates for kernel/governance work;
- whether to fold closeout into `azoth-lite`;
- whether `meta-harness-experimental` should replace current Azoth immediately;
- whether to mutate `.azoth` roadmap/backlog/specs as part of this proposal
  pack.

## Recommended Review Prompts

Use these prompts to review the pack:

1. Does the proposed `azoth-lite` surface stay small enough to be real?
2. Are escalation triggers too broad, too narrow, or about right?
3. Does the proposal preserve the pieces of full Azoth that actually catch
   historical failures?
4. Which migration phase should be the first Azoth-native artifact, if any?
5. What evidence would change the recommendation back toward full-by-default or
   stock-lite-by-default?

