# Comparison Profiles

Started: 2026-05-01

Purpose: define profile packets that can be used to run the same benchmark case
under different harness assumptions.

These are not implementation specs. They are research controls.

## Shared Run Rules

Every profile run should record:

- model and reasoning setting;
- initial context packet;
- loaded instructions;
- available tools;
- tools actually used;
- side effects;
- user interventions;
- final artifact;
- verification evidence;
- stop reason.

Each profile must make completion explicit:

- `done`: task completed with evidence;
- `blocked`: cannot continue without missing input or failed prerequisite;
- `paused`: intentionally stopped with resumable state;
- `escalate`: human approval or decision required.

## Profile A: `stock-lite`

Purpose:

Test what GPT-5.5 can do in this repo with minimal Azoth-specific ceremony.

Initial context:

- short repo orientation;
- [README.md](../README.md);
- [AGENTS.md](../AGENTS.md) only as a broad manifest, not as mandatory staged
  process;
- the specific files needed for the case.

Instructions loaded:

- normal Codex developer instructions;
- concise task-specific goal;
- local codebase facts discovered by tool use;
- no Azoth command contract unless the case is specifically about commands.

Tools available:

- shell/read/edit/test/git status;
- web if the case needs current external facts;
- no mandatory Azoth scripts except as ordinary repo tools when relevant.

Durable state:

- none beyond git worktree and artifacts produced by the case;
- run notes captured in the meta-session research pack after the run.

Gates:

- normal destructive-action caution;
- human approval for risky operations;
- no Azoth scope gate or pipeline gate.

Expected strengths:

- low context load;
- low ceremony;
- tests whether the model can handle repo work directly.

Expected risks:

- weaker audit trail;
- less durable pause/resume;
- may miss Azoth-specific governance expectations.

## Profile B: `azoth-lite`

Purpose:

Test the smallest likely useful Azoth kernel.

Initial context:

- trust boundaries summarized from [kernel/TRUST_CONTRACT.md](../kernel/TRUST_CONTRACT.md);
- mandatory human gates summarized from [kernel/GOVERNANCE.md](../kernel/GOVERNANCE.md);
- generated context view for the case;
- relevant skills by trigger only.

Instructions loaded:

- explicit goal and success criteria;
- side-effect boundary;
- selected skills, opened only when needed;
- trace capture expectations;
- explicit stop states.

Tools available:

- shell/read/edit/test/git status;
- relevant Azoth scripts as hands, not as a mandatory command flow;
- optional lightweight session note.

Durable state:

- meta-session run trace;
- optional compact session event list;
- no roadmap mutation unless the case is about roadmap mutation and a human
  explicitly approves it.

Gates:

- human approval for destructive, kernel, governance, dependency, roadmap, and
  cross-surface state mutation;
- runtime check before risky writes;
- explicit done/blocked/paused/escalate.

Expected strengths:

- preserves trust primitives;
- lower context load than full Azoth;
- clearer distinction between model strategy and execution hands.

Expected risks:

- may under-specify Azoth-specific process when process is the point;
- may require manual trace discipline until tooling exists.

## Profile C: `azoth-full`

Purpose:

Test the current governed system or nearest honest equivalent.

Initial context:

- bootloader expectations;
- trust contract;
- governance;
- current command contract;
- relevant command body or skill;
- relevant roadmap/backlog/run-ledger state.

Instructions loaded:

- selected Azoth command semantics;
- pipeline/stage expectations;
- gate protocol;
- run-ledger requirements;
- memory/closeout expectations.

Tools available:

- all normal tools;
- Azoth gate scripts;
- run-ledger scripts;
- roadmap and closeout scripts;
- relevant validators and tests.

Durable state:

- `.azoth` state as required by the command;
- run-ledger/session/closeout artifacts;
- memory capture if the command requires it.

Gates:

- full Azoth human/agent gate model;
- scope gate and pipeline gate where applicable;
- command effect labels.

Expected strengths:

- strongest audit trail;
- best match for current governance;
- can catch side-effect and lifecycle mistakes if gates are surfaced correctly.

Expected risks:

- high context and cognitive load;
- may encourage stage narration over actual separation;
- may bias research by treating current Azoth shape as ground truth.

## Profile D: `meta-harness-experimental`

Purpose:

Test the target shape suggested by external evidence and the current plan.

Initial context:

- strategic goal;
- concise policy kernel;
- generated context view;
- selected skills;
- previous session/event slices;
- active risks;
- stop condition.

Instructions loaded:

- one strategic brain owns route choice;
- execution hands are explicit and side-effectful;
- session log is the source of truth;
- skills are progressive disclosure;
- runtime guards are preferred over prompt walls;
- profile can escalate into governed mode when the task warrants it.

Tools available:

- normal tools;
- execution hands with names and side-effect classes;
- lightweight trace/event log;
- optional evaluator pass after the run.

Durable state:

- session/event trace;
- artifacts produced by hands;
- evaluation card;
- only promoted into Azoth-native state after human approval.

Gates:

- permission gates for high-risk hands;
- trace grader after completion;
- explicit finality state.

Expected strengths:

- tests the likely future architecture;
- combines broad model agency with durable trust;
- separates stable primitives from orchestration tactics.

Expected risks:

- not yet implemented as a real harness;
- may require simulated discipline during pilot runs;
- could under-measure the cost of building the new substrate.

## First Profile-Readiness Gaps

Before running a fair pilot:

- define the exact initial context packet for each selected case;
- decide whether `azoth-full` runs should use real `.azoth` gate mutation or a
  dry-run trace simulation for non-invasive research;
- create a common trace template;
- choose whether the same model instance or fresh sessions should run each
  profile;
- mark the existing native harness-rethink artifacts as excluded context unless
  a case explicitly studies them.

