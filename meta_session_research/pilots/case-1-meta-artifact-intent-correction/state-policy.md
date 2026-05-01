# Pilot State Policy

Date: 2026-05-01

## Policy

For Pilot 001, all profile runs are non-invasive research runs.

`azoth-full` uses dry-run semantics:

- no `.azoth/pipeline-gate.json` write;
- no `.azoth/run-ledger.local.yaml` write;
- no `.azoth/memory/episodes.jsonl` append;
- no roadmap/backlog/spec mutation;
- no command contract or validator creation.

The only allowed writes are:

- files under `meta_session_research/`;
- explicit deletion of untracked contamination files named by the human.

## Reason

The research is about whether Azoth's native shape is appropriate. Letting the
pilot mutate native Azoth state would bias the result and recreate the capture
risk the case is meant to test.

## Current State After Cleanup

The four dirty untracked native harness-rethink files were deleted:

- `.azoth/research/azoth-harness-rethink-source-matrix-2026-05-01.yaml`;
- `.azoth/roadmap-specs/v0.2.0/AZOTH-HARNESS-RETHINK-CONTRACT.yaml`;
- `scripts/harness_rethink_validate.py`;
- `tests/test_harness_rethink.py`.

`git status --short` for the relevant surface now shows only:

- `META_REAL_RESEARCH_PLAN.md`;
- `meta_session_research/`.

The tracked `.azoth/proposals/azoth-harness-rethink-2026.yaml` was observed but
not deleted because it was not dirty untracked contamination.

