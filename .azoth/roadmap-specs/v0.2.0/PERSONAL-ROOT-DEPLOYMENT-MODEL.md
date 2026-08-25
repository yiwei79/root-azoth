# Personal Root Deployment Model

This is the T-038 deployment model for the operator personal root in
`v0.2.0-p4`. It defines the personal root as an installed Azoth deployment, not
as the `root-azoth` development checkout and not as the public `azoth` product
repository.

## Gate

This document is design-only. It does not create a live personal repository,
choose the operator path, publish private knowledge, or install into real
projects. Those actions require a fresh operator-approved deployment scope.

## Three-Plane Model

| Plane | Owner | Purpose | Allowed State | Forbidden State | Update Path |
| --- | --- | --- | --- | --- | --- |
| `root-azoth` | Azoth maintainer/operator | Private development workshop for toolkit evolution, release validation, generated surfaces, and governed roadmap truth. | Roadmap/backlog/specs, tests, source scripts, generated adapters, release-candidate evidence, private development memory. | Personal global knowledge base, real project inventory as operational source of truth, public release authority without review, downstream project secrets. | Produces a reviewed release candidate through extraction and validation; never updates personal root directly by copying root runtime state. |
| Public `azoth` | Azoth maintainer/operator, public users | Clean product surface that can be installed into consumer projects. | Product kernel, install scripts, public docs, platform adapters, publishable skills/agents/commands, minimal CI/release notes. | `root-azoth` `.azoth/` state, private memory, inbox reflections, roadmap internals, local gates, worktrees, caches, credentials. | Receives extracted artifacts from `root-azoth` only after root checks pass and the operator approves public checkout update, tag, push, and release. |
| Personal root | Operator | Daily personal control plane over projects, source connections, and personal knowledge. | Installed Azoth runtime, operator-owned project inventory, personal knowledge, project handoffs, source registry, update ledger, local/private operational memory. | Toolkit source development history, public publishing authority, root roadmap as mutable truth, automatic intake decisions, silent inbox draining, cross-project writes without approval, project secrets committed into repo state. | Updates from an approved public `azoth` release or reviewed RC. Applies updates onward to projects only through explicit project-scoped approval. |

Downstream projects are separate consumer deployments. They may use Azoth at a
minimal, standard, or full setup level, but they do not need to adopt the whole
personal control-plane layer.

## Personal Root Shape

The personal root should be initialized from the public product tree using the
normal consumer installer. The first live install waits for the operator to
approve a target path.

Recommended repository shape after approval:

```text
personal-root/
  CLAUDE.md or platform equivalent
  azoth.yaml
  .azoth/
    kernel/
    memory/
      personal/
      project-summaries/
    projects/
      index.yaml
      handoffs/
    sources/
      registry.yaml
    releases/
      applied.yaml
    inbox/
      pending/
      archived/
```

`kernel/`, platform adapters, and runtime command surfaces come from the
installed Azoth product. `memory/`, `projects/`, `sources/`, `releases/`, and
`inbox/` are operator-owned personal state and are never copied back into
`root-azoth` or public `azoth` by default.

## Knowledge Boundaries

| Knowledge Class | Home | Allowed Flow | Stop Rule |
| --- | --- | --- | --- |
| Toolkit memory | `root-azoth` development memory and public product docs when sanitized | Can inform product improvements through governed release work. | Do not mix personal/project facts into publishable toolkit artifacts without explicit sanitization and approval. |
| Personal memory | Personal root `.azoth/memory/personal/` | Can guide operator-level prioritization, project selection, and daily routing. | Do not publish or copy into project repos unless the operator explicitly chooses a scoped excerpt. |
| Per-project memory | Each project repo, optionally summarized in personal root `project-summaries/` | Can be summarized upward into the personal root by explicit handoff. | Do not let personal root mutate project governance, instructions, secrets, or backlog without project-scoped approval. |
| Inbox/reflection evidence | Originating repo first; personal root may hold pointers or copied excerpts | Can be routed through strategy-preflight or future intake only after approval. | No silent draining, automatic intake decisions, background self-modification, or instruction/governance mutation. |

## Source Connections

The personal root may register sources such as project repositories, local docs,
approved cloud folders, issue trackers, or email summaries. The registry should
record only the minimum operational metadata:

- source id and path or URL,
- owner and privacy class,
- allowed read surface,
- allowed write surface, usually none by default,
- credential location outside the repo,
- refresh cadence,
- last reviewed timestamp,
- project handoff policy.

Credentials, raw mailbox exports, private tokens, and project secrets must stay
outside tracked personal-root state. Source refreshes are explicit operator
actions unless a later governed task defines a supervised schedule.

## Update Cadence

1. `root-azoth` develops and validates toolkit changes under roadmap scope.
2. Product extraction creates a clean public `azoth` release candidate.
3. The operator reviews root evidence, public checkout diff, release notes, and
   installer smoke results before tag/push/release.
4. Personal root updates from the approved public release or explicitly approved
   RC, recording the version in `.azoth/releases/applied.yaml`.
5. Individual project updates happen only after selecting the project and
   approval boundary. The project receives the Azoth update through its own repo
   state, not through an implicit personal-root push.

Recommended cadence for first stable:

- Stable releases may update the personal root after the public release is
  accepted.
- RC builds may update the personal root only for rehearsal or pilot use.
- Project consumers should remain on their current installed version until the
  operator approves a project-level update.

## Project Onboarding Flow

1. Choose a project and privacy class in the personal root project inventory.
2. Record the source path, owner, platform targets, and intended Azoth setup
   level: minimal, standard, or full.
3. Install Azoth into the project from an approved public release or reviewed RC.
4. Run the project welcome/dashboard/check commands appropriate to that repo.
5. Create a handoff note in personal root with installed Azoth version, selected
   setup level, allowed memory flow, and next operator action.
6. Keep future project changes project-scoped. Personal root may coordinate and
   summarize; it does not bypass the project's own gates.

## Rehearsal Boundary

T-036 already proves the public product can be extracted and installed into a
temporary consumer project on this host. T-038 adds the personal-root operating
model and install boundary. A live personal-root repository remains blocked on
operator approval of:

- target path or repository,
- local-only vs private-remote storage,
- first pilot projects,
- privacy policy for personal and project summaries,
- whether the first install uses `v0.2.0-rc.1` or final `v0.2.0`.

Until that approval exists, T-039 may claim only that the model is documented and
that live personal-root creation is intentionally deferred. It may not claim the
personal root has been created.

## Open Decisions

- Personal root target path or repository name.
- Local-only storage, private Git remote, or encrypted private remote.
- Which sources are connected first and which are pointer-only.
- First two pilot projects and setup level for each.
- Whether RC updates are allowed for personal-root rehearsal or only stable
  releases are allowed.
- Retention policy for archived inbox evidence and project handoff notes.
