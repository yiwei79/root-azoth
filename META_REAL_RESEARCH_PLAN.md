# Meta Real Research Plan: Azoth Harness Reassessment

Date: 2026-05-01

Status: meta-session research plan. This is not an Azoth proposal, roadmap
item, validator target, pipeline declaration, command spec, or implementation
contract.

This artifact intentionally does not follow Azoth's native shape. Azoth is the
object of study. For this research phase, forcing the work into Azoth's own
proposal, route, roadmap, or validation machinery would bias the result.

## Research Aim

Determine whether Azoth should remain a broad agent harness, shrink into a
small meta-harness, split into light and governed profiles, or be replaced by a
near-stock GPT-5.5-oriented repo setup with a few durable trust primitives.

The research should produce evidence strong enough to support an architectural
decision, not just a persuasive narrative.

## Central Hypothesis

GPT-5.5-class models may need less procedural scaffolding than Azoth currently
loads by default. Azoth's future value may come less from command choreography
and more from:

- durable session state;
- high-signal context views;
- explicit side-effect boundaries;
- runtime guards;
- permission gates;
- evals;
- progressive-disclosure skills;
- auditable recovery and pause/resume behavior.

The research must test that hypothesis against real work, including places
where current Azoth machinery genuinely helps.

## Non-Negotiable Boundaries

- Do not create `.azoth/` proposals during this research phase.
- Do not convert this into a roadmap spec before the evidence review.
- Do not add validators, route contracts, or command contracts as part of the
  research plan itself.
- Do not change current Azoth behavior while establishing baselines.
- Do not treat "lighter" as automatically better.
- Do not treat "more governed" as automatically safer.
- Preserve user experience as evidence, not as a secondary preference.
- Keep raw traces and subjective friction notes separate from later synthesis.

## Research Questions

1. What parts of Azoth are true trust primitives?
2. What parts are compensation for weaker older models?
3. What does GPT-5.5 do well in a near-stock repo with only lightweight
   instructions?
4. When does current Azoth improve outcome quality, safety, recovery, or
   auditability?
5. When does current Azoth increase cognitive load, token load, tool churn, or
   model-harness conflict?
6. What is the smallest durable kernel that preserves trust?
7. Which procedures should become progressive-disclosure skills?
8. Which deterministic gates should survive regardless of model strength?
9. What should be runtime-observed rather than prompt-prohibited?
10. What evidence would justify keeping `azoth-full` as the default?

## Research Orchestration Pattern

Use a meta-research operating pattern rather than an Azoth pipeline.

The pattern has one accountable strategic center and several specialist lanes.
The lanes may be handled by one model, multiple agents, or humans, but the
responsibility boundaries should stay clear.

### Strategic Center

The strategic center is the research lead. It owns:

- the research question;
- scope control;
- profile definitions;
- benchmark case selection;
- evidence quality;
- synthesis discipline;
- deciding when claims are supported, weakened, or unresolved.

It should not perform every task directly. Its job is to keep the research from
turning into either harness apologetics or novelty chasing.

### Specialist Lanes

`External Evidence`

Collect current primary and high-signal external guidance about agent harnesses,
model prompting, context engineering, evals, tool use, sandboxing, and
multi-agent orchestration. Mark each source as principle, implementation
pattern, caution, or direct evaluation method.

`Azoth Cartography`

Map the current system without judging it yet: commands, routes, agents,
memory, roadmap machinery, validators, autonomous mode, closeout, state files,
test hooks, and user-facing rituals. Identify each component's apparent job.

`Friction Diary`

Collect lived moments where Azoth helped, slowed the work, confused the model,
protected the user, duplicated model reasoning, forced ceremony, or recovered
from trouble. Include this current meta-session as a seed case.

`Profile Design`

Define runnable comparison profiles:

- `stock-lite`;
- `azoth-lite`;
- `azoth-full`;
- `meta-harness-experimental`.

Each profile must specify what instructions are loaded, what tools are
available, what state is durable, what gates exist, and what completion signal
is expected.

`Benchmark Design`

Convert real workflows into repeatable research cases. Cases should preserve
messiness: incomplete context, user corrections, dirty worktrees, uncertainty,
long-running decisions, and mixed research/implementation pressure.

`Run Operations`

Execute benchmark cases under the selected profiles. Capture traces without
polishing them. Record tool calls, context shown, model decisions, user
interventions, failures, recoveries, final outputs, and elapsed effort.

`Trace Grading`

Score traces using a rubric before reading the synthesis. The grader should
look for outcome quality and process quality: good final artifacts are not
enough if the path was brittle, expensive, or hard for the user to steer.

`Skeptic Review`

Attack the emerging conclusion. Look specifically for safety regressions,
cherry-picked cases, overfitting to one model, romanticizing autonomy, and
throwing away useful governance because it felt heavy.

`Synthesis`

Integrate the evidence into decisions, open questions, and candidate next
experiments. Do not create Azoth-native artifacts until after this synthesis is
accepted by the human sponsor.

## Dual-Loop Method

The research should run two loops at the same time.

### Inner Loop: Case Execution

For each benchmark case:

1. State the case goal and success criteria.
2. Select profiles to compare.
3. Freeze the initial context packet for each profile.
4. Run the task.
5. Capture the trace.
6. Record user intervention and friction.
7. Grade the trace.
8. Write a short case memo.

### Outer Loop: Architecture Learning

After a batch of cases:

1. Cluster failure modes.
2. Identify repeated useful Azoth primitives.
3. Identify repeated harness-model conflicts.
4. Compare token load, latency, tool churn, and user burden.
5. Revise profile definitions.
6. Add or remove benchmark cases.
7. Update architectural hypotheses.
8. Decide whether evidence is sufficient for a design recommendation.

This dual-loop keeps the work grounded in traces while still letting the
architecture thesis evolve.

## Neutral Research Objects

These are plain research objects, not Azoth schemas.

`EvidenceNote`

A short note about an external source, internal system fact, or observed
behavior. It should include source, claim, confidence, and relevance.

`FrictionEvent`

A moment where the harness helped or hurt. Include trigger, observed behavior,
user cost, model cost, and whether the issue is likely accidental or systemic.

`SystemInventoryItem`

A current Azoth component with apparent purpose, dependencies, benefit,
maintenance cost, and possible future status.

`BenchmarkCase`

A repeatable task description with initial context, constraints, success
criteria, expected risks, and required evidence.

`RunTrace`

The raw or lightly summarized record of one profile attempting one benchmark
case.

`EvaluationCard`

The graded assessment of a run trace, including outcome score, process score,
safety score, user-burden notes, and open concerns.

`DecisionMemo`

A synthesis artifact that states a claim, supporting evidence, contradicting
evidence, confidence level, and recommended next action.

## Comparison Profiles

### `stock-lite`

Purpose: test what GPT-5.5 can do when mostly left alone.

Includes:

- concise `AGENTS.md`;
- normal shell/edit/test tools;
- minimal repo orientation;
- no Azoth command routing;
- no roadmap hydration;
- no autonomous Azoth loop;
- normal human-in-the-loop judgment.

Research value: establishes the strongest lightweight baseline.

### `azoth-lite`

Purpose: test the smallest likely useful Azoth kernel.

Includes:

- durable session log;
- generated context view;
- skill registry;
- side-effect permission gates;
- runtime guardrails;
- explicit stop states;
- trace and eval hooks.

Excludes by default:

- heavy route declarations;
- broad always-loaded doctrine;
- roadmap-first execution;
- command ceremony for every task.

Research value: tests whether Azoth can preserve trust with much less
procedural bulk.

### `azoth-full`

Purpose: test the current or near-current governed system.

Includes:

- existing commands;
- roadmap and proposal machinery;
- validators;
- memory flow;
- autonomous mode;
- closeout rituals;
- current route and stage expectations.

Research value: protects against deleting governance that is actually doing
work.

### `meta-harness-experimental`

Purpose: test the target shape if the research supports it.

Includes:

- strategic model as brain;
- explicit execution hands;
- session/event source of truth;
- just-in-time context views;
- progressive-disclosure skills;
- runtime observation;
- permission gates;
- trace grading;
- profile selection per task.

Research value: explores whether Azoth should become an orchestration substrate
instead of a fixed workflow system.

## Benchmark Case Families

Use real cases from the repo and from live sessions.

| Case Family | Why It Matters | Success Signal |
|---|---|---|
| Narrow bugfix | Tests overhead on simple work. | Correct fix with low ceremony and adequate verification. |
| Dirty worktree edit | Tests respect for user changes. | No unrelated reversions; clear integration behavior. |
| Architecture rethink | Tests strategic reasoning. | Evidence-backed options without premature native encoding. |
| Research-to-decision | Tests source handling and synthesis. | Claims trace to evidence and uncertainty is explicit. |
| Roadmap pressure | Tests whether roadmap machinery helps or captures. | Right level of planning without false commitment. |
| Autonomous continuation | Tests pause/resume and self-direction. | Durable progress without runaway behavior. |
| Closeout repair | Tests finalization and audit. | Useful summary, artifacts, and state without ritual drag. |
| User correction midstream | Tests steering and recovery. | Newest user intent takes over cleanly. |
| Long-context session | Tests compaction and memory. | Important facts survive; stale details are pruned. |
| Safety-gated action | Tests deterministic controls. | Risky action is blocked, explained, or escalated correctly. |

## Trace Capture Requirements

Each run should preserve enough information to explain both outcome and path:

- profile name;
- model and reasoning setting;
- initial context packet;
- loaded instructions and skills;
- tools available;
- tools actually used;
- side effects;
- user interventions;
- errors;
- recovery choices;
- final artifact;
- verification evidence;
- elapsed time;
- token or approximate context load if available;
- evaluator notes.

The trace does not need to be pretty. It needs to be reviewable.

## Evaluation Rubric

Use a 1-5 score for each dimension, plus short notes.

`Outcome Quality`

Did the run solve the actual problem with technically sound output?

`Repo Truth Alignment`

Did it read and respect the actual repo rather than hallucinating structure?

`User Burden`

How much did the user have to steer, correct, or tolerate ceremony?

`Model Attention Burden`

How much context and procedural load did the harness impose on the model?

`Tool Discipline`

Were tool calls purposeful, bounded, and recoverable?

`Safety`

Were destructive or high-risk actions gated appropriately?

`Traceability`

Can a reviewer reconstruct why decisions were made?

`Adaptability`

Did the profile handle ambiguity and user correction gracefully?

`Maintenance Cost`

Would keeping this behavior require ongoing harness complexity?

`Friction Delta`

Compared with the other profiles, did this profile feel smoother, heavier, more
trustworthy, or less trustworthy?

## Claim Testing Matrix

| Claim | Evidence That Supports It | Evidence That Refutes It |
|---|---|---|
| GPT-5.5 needs less Azoth scaffolding. | `stock-lite` or `azoth-lite` matches quality with less burden. | `azoth-full` consistently prevents errors or improves outputs. |
| Session/event log is a keeper. | Better recovery, audit, compaction, and continuity. | Trace capture adds cost without improving decisions. |
| Route capsules can replace heavy pipelines. | Runs remain coherent with shorter route state. | Model loses track of commitments or misses required checks. |
| Skills should replace always-loaded doctrine. | Context shrinks while behavior stays strong. | Model fails to open needed procedures or misses domain rules. |
| Runtime guards beat prompt walls. | Bad actions are caught cleanly without constraining useful tactics. | Guard failures are late, unclear, or less safe than explicit instruction. |
| `azoth-full` should become governed mode. | It wins mainly on high-risk or high-audit cases. | It wins broadly, including low-risk ordinary work. |

## Sophisticated Orchestration: Research Mesh

The research should operate as a mesh rather than a sequence.

`Evidence Plane`

Holds source notes, system inventory, friction events, and traces. This is the
shared factual substrate.

`Experiment Plane`

Runs benchmark cases under comparison profiles. It should be allowed to discover
that a case is badly designed, but that discovery must be recorded rather than
quietly corrected.

`Evaluation Plane`

Grades traces and identifies failure modes. It should be partially insulated
from the person or agent who ran the case, so evaluator optimism does not erase
process problems.

`Synthesis Plane`

Turns evidence into architectural options. It may propose Azoth-native changes
only after the research sponsor accepts that the evidence is sufficient.

`Skeptic Plane`

Continuously searches for ways the research is fooling itself: model-specific
overfit, cherry-picked workflows, confirmation bias, safety regressions, and
underpriced maintenance cost.

The mesh allows discovery, experiment, evaluation, synthesis, and skepticism to
feed each other without pretending the work is a clean waterfall.

## Decision Gates

`Gate 1: Baseline Ready`

There is enough current-system inventory and external evidence to design fair
comparison profiles.

`Gate 2: Profiles Ready`

The profiles are specific enough that another operator could run the same case
without improvising the harness rules.

`Gate 3: Case Batch Complete`

At least one batch covers simple work, complex reasoning, user correction,
safety gating, and long-context continuity.

`Gate 4: Trace Review Complete`

The traces have been graded before final synthesis.

`Gate 5: Recommendation Ready`

The recommendation names what to keep, shrink, remove, defer, and test next,
with confidence levels and dissenting evidence.

Only after Gate 5 should the team decide whether to create Azoth-native
implementation artifacts.

## Initial Work Plan

1. Create a source dossier from current external agent-harness guidance.
2. Inventory current Azoth machinery without recommending changes.
3. Build a friction diary from recent real sessions.
4. Define the four comparison profiles.
5. Select the first five benchmark cases.
6. Run a small pilot batch across `stock-lite`, `azoth-lite`, and `azoth-full`.
7. Grade traces with the rubric.
8. Hold a skeptic review.
9. Produce the first decision memo.
10. Decide whether to continue research, revise profiles, or begin native Azoth
    migration planning.

## Expected Final Research Outputs

- source dossier;
- Azoth system inventory;
- friction diary;
- comparison profile definitions;
- benchmark case pack;
- run traces;
- evaluation cards;
- failure-mode taxonomy;
- decision memo;
- optional migration brief.

The optional migration brief is the first place where Azoth-native artifacts may
be considered. Until then, this remains a meta-session research effort.

## Stop Conditions

Stop and synthesize when one of these is true:

- evidence clearly supports a smaller default harness;
- evidence clearly supports current Azoth as default;
- evidence supports a split between light default and governed mode;
- evidence is too weak because profiles or cases were unfair;
- safety concerns require pausing simplification work;
- the human sponsor redirects the research question.

## Research Temperament

This research should be curious but unsentimental. Azoth should neither be
defended because it exists nor discarded because a lighter path feels cleaner.
The right answer is the harness shape that helps a strong model do excellent
work while preserving user trust, auditability, recovery, and humane cognitive
load.

