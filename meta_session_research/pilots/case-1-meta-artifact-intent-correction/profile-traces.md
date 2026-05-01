# Profile Traces

Date: 2026-05-01

Pilot type: desk replay against frozen context packets.

Important limitation:

These are not fresh independent executions. They are profile-lens traces over
the observed session and should be treated as calibration evidence, not final
benchmark evidence.

## Trace P001-stock-lite

trace_id: P001-stock-lite

case_id: Case 1, Meta-Artifact Intent Correction

profile: `stock-lite`

model: GPT-5.5-class Codex session

reasoning_setting: inherited current session

initial_context_packet:

- shared case packet;
- root README only if needed;
- git status.

loaded_instructions:

- normal coding-agent instructions;
- explicit user request;
- no Azoth command/gate machinery.

available_tools:

- shell/read/edit/status;
- apply patch.

tools_used in observed equivalent:

- status/read commands;
- apply patch.

side_effects:

- would create the requested root or meta research artifact;
- would delete explicitly named untracked contamination.

user_interventions:

- likely lower than observed if the first artifact stayed tightly scoped;
- no native process prompt would have encouraged `.azoth` artifacting.

errors_or_recoveries:

- risk: may miss that `.azoth` artifacts are contamination unless status is
  checked carefully;
- recovery: direct deletion is simple when user corrects.

final_artifact:

- meta research plan and/or research pack outside `.azoth`.

verification:

- `git status --short`;
- file existence checks.

stop_state: done

notes:

`stock-lite` likely performs well on this case because the task is primarily
intent-following and file placement. Its weakness is weaker audit and less
explicit anti-capture framing.

## Trace P001-azoth-lite

trace_id: P001-azoth-lite

case_id: Case 1, Meta-Artifact Intent Correction

profile: `azoth-lite`

model: GPT-5.5-class Codex session

reasoning_setting: inherited current session

initial_context_packet:

- shared case packet;
- concise trust and side-effect summary;
- skills only by trigger.

loaded_instructions:

- meta-session boundary;
- no roadmap/governance mutation;
- explicit side-effect classes;
- trace capture.

available_tools:

- shell/read/edit/status;
- apply patch;
- no mandatory gate scripts.

tools_used in observed equivalent:

- status/read commands;
- apply patch;
- web for external evidence in Batch 0.

side_effects:

- writes under `meta_session_research/`;
- deletion of explicit untracked contamination.

user_interventions:

- expected lower than observed if the anti-capture boundary is loaded up front.

errors_or_recoveries:

- likely prevents native artifact creation by making "do not mutate `.azoth`"
  part of the case context;
- manual trace discipline still required.

final_artifact:

- meta research plan;
- meta research pack;
- cleanup notes.

verification:

- `git status --short`;
- meta research files present;
- deleted contamination no longer found.

stop_state: done

notes:

`azoth-lite` is the strongest candidate for this case because it preserves the
trust boundary without pulling in the full command/pipeline surface.

## Trace P001-azoth-full

trace_id: P001-azoth-full

case_id: Case 1, Meta-Artifact Intent Correction

profile: `azoth-full`

model: GPT-5.5-class Codex session

reasoning_setting: inherited current session

initial_context_packet:

- shared case packet;
- bootloader/governance/command awareness;
- dry-run native-state rule.

loaded_instructions:

- full Azoth stage/gate concepts in dry-run mode;
- no real `.azoth` mutation.

available_tools:

- normal tools;
- Azoth scripts inspectable but not used for state mutation.

tools_used in observed equivalent:

- status/read commands;
- apply patch.

side_effects:

- would write only meta research artifacts;
- no pipeline gate or run-ledger writes.

user_interventions:

- expected higher than `azoth-lite` because the user must keep the full harness
  from recapturing the meta-session.

errors_or_recoveries:

- primary risk is native-shape capture: proposals, roadmap specs, validators,
  and tests look "proper" from an Azoth-full perspective but violate the case.
- dry-run rule mitigates but also means this is not a true full-Azoth run.

final_artifact:

- meta research artifacts only if dry-run boundary is obeyed.

verification:

- no dirty `.azoth` harness-rethink artifacts;
- no new validator/test artifacts.

stop_state: done, with caveat

notes:

`azoth-full` is useful as a contrast profile, but it is mismatched to the case.
Its strengths are audit and gates; its default shape is exactly what the user
asked the research to avoid.

## Trace P001-meta-harness-experimental

trace_id: P001-meta-harness-experimental

case_id: Case 1, Meta-Artifact Intent Correction

profile: `meta-harness-experimental`

model: GPT-5.5-class Codex session

reasoning_setting: inherited current session

initial_context_packet:

- shared case packet;
- explicit hands and event slice;
- active anti-capture risk.

loaded_instructions:

- one strategic brain;
- explicit execution hands;
- session/event trace;
- progressive-disclosure skills;
- runtime boundary over prompt bulk.

available_tools:

- `read_status`;
- `write_research_artifact`;
- `delete_untracked_contamination`;
- `record_trace`;
- `stop`.

tools_used in observed equivalent:

- shell/read/status;
- apply patch.

side_effects:

- meta research writes;
- deletion of named untracked contamination.

user_interventions:

- expected low after initial anti-capture boundary is represented as active
  risk.

errors_or_recoveries:

- would classify the first synthesis artifact as an incorrect hand output and
  correct it before proceeding;
- risk: since this harness does not exist yet, the discipline is simulated.

final_artifact:

- meta research plan and research pack with trace evidence.

verification:

- file placement;
- status;
- explicit done.

stop_state: done

notes:

This profile best matches the desired future shape, but the evidence is partly
aspirational because the substrate is not implemented.

