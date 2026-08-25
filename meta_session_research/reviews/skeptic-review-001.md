# Skeptic Review 001

Date: 2026-05-01

Target:

[Decision Memo 001](../decision-memos/decision-memo-001-profile-split-provisional.md)

Status: critique before migration planning.

## Bottom Line

The profile-split hypothesis is plausible, but the evidence is not strong
enough to authorize implementation planning.

The memo's main risk is that it may be over-crediting `azoth-lite` and
`meta-harness-experimental` for behavior that was supplied by the current
researcher, not by a real reusable harness.

## Major Concerns

### 1. The Pilots Are Not Independent

Case 1 was a desk replay. Case 5 was a same-session packet comparison. Case 3
used real code and tests but was still interpreted by the same researcher. Case
6 was focused verification, not a bugfix.

Risk:

The research may be measuring the researcher's current judgment rather than
profile behavior.

Required countermeasure:

Run at least one true fresh-session comparison with only the fixture and profile
packet visible to the model.

### 2. `azoth-lite` Does Not Exist As A Stable Harness

The pilots assume `azoth-lite` has:

- concise context views;
- side-effect boundaries;
- trace capture;
- stop states;
- skill triggers;
- mutation escalation.

But these are currently manual behaviors in the meta research pack.

Risk:

The memo may underprice implementation and maintenance cost.

Required countermeasure:

Before calling `azoth-lite` a default, define the minimum concrete runtime
surface it needs and estimate its maintenance cost.

### 3. `meta-harness-experimental` Is Over-Scored

The target architecture scores well because it has the best conceptual shape:
brain, hands, session log, permissioned effects, event trace. But it has not
faced real implementation constraints.

Risk:

The research may prefer an idealized future system over a messy current system
that actually catches failures.

Required countermeasure:

Keep `meta-harness-experimental` out of default recommendations until a small
prototype or manual runbook demonstrates it on at least one real task.

### 4. `azoth-full` May Be Under-Valued

The pilots intentionally avoided real `.azoth` mutation after cleanup. That was
right for anti-capture, but it also means `azoth-full` did not get many chances
to show its core value in live governed work.

Risk:

The research may conclude "full is too heavy" from cases that were mostly
designed not to need full governance.

Required countermeasure:

Include one high-audit delivery or closeout case where `azoth-full` is expected
to win, then measure how much of its ceremony is useful versus avoidable.

### 5. Case 5 Fixture Was Too Obvious

The fixture explicitly said the worktree is dirty and asked whether the campaign
is complete. That made the correct answer almost unavoidable for all profiles.

Risk:

The case did not meaningfully distinguish model competence under ambiguous
finality conditions.

Required countermeasure:

Run a subtler finality case where dirty state is present in tool output but not
called out in the prompt.

### 6. User Burden Is Estimated, Not Measured

The pilots score user burden, but most runs did not involve actual user
steering beyond this live meta-session.

Risk:

The "lighter feels better" conclusion may be valid but under-evidenced.

Required countermeasure:

For future runs, record actual user interventions, clarification requests, and
turn count.

### 7. Traceability Is Being Treated As Cheap

`azoth-lite` gets credit for small traces. But if trace capture remains manual,
it may be forgotten under pressure. If automated, it becomes new harness
machinery.

Risk:

The proposed light profile may recreate Azoth complexity over time.

Required countermeasure:

Define a minimal trace event format and decide whether it is manual, scripted,
or host-integrated before recommending `azoth-lite`.

## What The Memo Gets Right

The memo correctly refuses a single universal profile.

It correctly distinguishes:

- native-shape capture risk;
- mutation-boundary safety;
- finality honesty;
- everyday engineering overhead.

It correctly keeps migration artifacts out of scope.

It correctly treats `meta-harness-experimental` as a hypothesis rather than a
current default.

## Skeptic Recommendation

Do not migrate yet.

Proceed with a validation batch:

1. True fresh-session Case 5 or subtler finality variant.
2. One high-audit `azoth-full`-favored case.
3. One actual narrow code edit with a real failing test.
4. A minimal `azoth-lite` runtime-surface definition.

Only after that should the team decide whether to create Azoth-native migration
planning artifacts.

