# Pilot Summary

Date: 2026-05-01

Case: Everyday Engineering Overhead.

Pilot type: focused verification analysis.

## What This Pilot Shows

For low-risk engineering checks, full Azoth is too heavy as a default. The
useful work was:

- check status;
- run focused tests;
- scan for known gaps;
- collect test ids after a targeting miss;
- stop without inventing a bug.

That workflow needs discipline, but not roadmap, run-ledger, command routing, or
closeout machinery.

## Profile Implication

`stock-lite` is very strong when the task is pure read/test verification.

`azoth-lite` is the best current default candidate because it keeps the same
speed while adding explicit boundaries: preserve dirty worktree, do not invent a
bug, do not edit without evidence, record a small trace.

`azoth-full` should be reserved for cases where risk appears: governed state,
adapter parity, release, roadmap mutation, dependencies, kernel/governance, or
multi-stage work with real isolation needs.

`meta-harness-experimental` remains the best target shape if implemented:
minimal hands, explicit side effects, built-in trace, and escalation to governed
mode when risk rises.

## What This Pilot Does Not Prove

It does not prove a narrow code edit would be equally smooth, because no real
failing test was found.

It does show that the default harness should not force heavy process before the
task has demonstrated risk.

## Cross-Pilot Pattern So Far

Case 1:

Light profiles win because native-shape capture is the risk.

Case 3:

Governed or permissioned boundaries win because planning-state mutation is the
risk.

Case 6:

Light profiles win because everyday verification has low risk and high
sensitivity to overhead.

## Emerging Decision Shape

Do not choose a single profile for every task.

The research is pointing toward:

- `azoth-lite` as the likely current default;
- `azoth-full` as governed mode for high-risk/high-audit work;
- `meta-harness-experimental` as a future substrate worth designing after more
  evidence;
- `stock-lite` as a useful baseline and possibly acceptable for low-risk,
  read/test-only tasks.

This is still a provisional analysis, not a migration recommendation.

## Recommended Next Step

Write a first decision memo draft with confidence levels and contradictions, or
run one fresh independent profile comparison before drafting the memo.

The stronger research move is one fresh independent comparison, because the
current pilots are desk/dry-run/focused-analysis rather than isolated fresh
sessions.

