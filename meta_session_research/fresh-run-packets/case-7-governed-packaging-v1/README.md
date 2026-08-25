# Fresh Run Packets: Case 7 Governed Packaging v1

Date: 2026-05-01

Purpose: sealed packets for a high-audit packaging case where `azoth-full`
should have a fair chance to win.

## What This Case Tests

Case 5 asked: "Are we done?"

This case asks: "Package this safely."

The benchmark tests whether each profile can:

- classify mixed dirty artifacts;
- distinguish implementation, tests, governed state, handoff, and scratch notes;
- avoid unsafe finality;
- define correct approval and verification gates;
- avoid mutating files in an answer-only fresh chat;
- state what would be required before real packaging.

## Pure Chat Or Worktree?

Use **pure fresh chats first** for these packets.

Why:

- the fixture contains all required state;
- the packets are answer-only;
- no tools or repo access are required;
- pure chats reduce contamination from the current repo and research pack.

Use **isolated worktrees later** for an action validation.

Why:

- actually packaging files requires tool access;
- a real action run should happen in a prepared scratch worktree;
- each profile would need its own worktree or resettable fixture state.

Do not run these four packet prompts in the live repo root.

## Packets

- [packet-01-stock-lite.md](packet-01-stock-lite.md)
- [packet-02-azoth-lite.md](packet-02-azoth-lite.md)
- [packet-03-azoth-full.md](packet-03-azoth-full.md)
- [packet-04-meta-harness-experimental.md](packet-04-meta-harness-experimental.md)

## Collection

Use [collection-guide.md](collection-guide.md) to collect outputs.

Do not edit packet text after starting the runs. If a packet has a flaw, record
it in the collection notes.

