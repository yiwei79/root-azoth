# Validation Batch 001 Plan

Date: 2026-05-01

Status: research plan, not implementation.

Latest update: the manual `azoth-lite` surface trial is complete. The remaining
open validation items are the actual narrow code edit and, if desired, a
tool-enabled isolated-worktree packaging action.

## Purpose

Address Skeptic Review 001 before any Azoth-native migration planning.

## Required Runs

### 1. True Fresh Finality Run

Run Case 5 or a subtler finality variant in fresh sessions.

Requirement:

Each profile gets only the fixture and its profile packet.

Success signal:

The model distinguishes green loop from packaged delivery without being led too
hard by the prompt.

### 2. High-Audit Full-Azoth-Favored Run

Select a case where `azoth-full` should win:

- governed closeout;
- packaging after real dirty state;
- roadmap/backlog/spec mutation;
- release readiness;
- adapter parity change.

Success signal:

`azoth-full` catches a risk that lighter profiles miss or makes audit materially
better.

### 3. Actual Narrow Code Edit

Wait for or create only through normal development a real failing test or real
bug. Do not manufacture a fake defect for research convenience.

Success signal:

Compare overhead, test discipline, edit size, and final quality.

### 4. Azoth-Lite Surface Trial

Use [azoth-lite-runtime-surface-v0.md](azoth-lite-runtime-surface-v0.md) as a
manual runbook on one low-risk task.

Success signal:

The runbook catches escalation boundaries without becoming mini-`azoth-full`.

Status:

Complete. See
[../manual-trials/azoth-lite-trial-001-decision-readiness/](../manual-trials/azoth-lite-trial-001-decision-readiness/).

## Batch Exit Criteria

After these four runs, update Decision Memo 001.

Possible outcomes:

- strengthen profile split;
- weaken `azoth-lite` default claim;
- preserve `azoth-full` as broader default;
- prioritize `meta-harness-experimental` prototype;
- stop because evidence is inconclusive.

## Explicit Stop

Do not create `.azoth` tasks, validators, command changes, or migration plans
until this validation batch is reviewed.
