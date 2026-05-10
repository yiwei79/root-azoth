# Project Genesis Starter Packet

Use this packet when starting or connecting a personal project space to Azoth
without turning the project into a root-azoth delivery task too early.

The packet is planning-only by default. It can capture context, readiness,
starter prompts, cockpit routing intent, validation receipts, and upgrade
provenance. It does not authorize writes to the project repo, personal cockpit,
public Azoth, root roadmap/backlog/specs, kernel, or governance files.

## When To Use

- Starting a new creative or research space.
- Reconnecting an existing project after time away.
- Testing whether a project should use public/installed Azoth, root-azoth
  development support, or only a lightweight local prompt surface.
- Preparing a cockpit pointer without loading project-local context inside the
  cockpit session.
## Command Surface
Generate a planning-only packet to stdout:
```bash
python3 scripts/project_genesis_starter.py profile music_production --project-id music-production-lab --project-name "Music Production Lab"
```
Validate a filled packet:
```bash
python3 scripts/project_genesis_starter.py validate path/to/project-genesis.yaml
```
The helper does not write project, cockpit, public Azoth, roadmap, kernel, or
governance files. Redirecting output into a project repo is a separate
project-local write decision.
## Packet Template
```yaml
packet_schema_version: 1
packet_type: project_genesis_starter
project_id: "<stable-id>"
project_name: "<human name>"
domain: "<music_production | bachelor_thesis | agent_context_project | other>"
created_at: "<ISO-8601 UTC>"

goal:
  why_now: ""
  desired_help: ""
  success_signals: []
  not_success: []

azoth_source_profile:
  source: "<public_install | root_azoth | personal_cockpit | mixed>"
  version_or_commit: ""
  upgrade_path: ""
  boundaries:
    - "Root-azoth owns toolkit development."
    - "Personal cockpit owns pointer-only routing."
    - "The project owns project-local context and write authority."

local_context:
  project_paths: []
  important_artifacts: []
  people_or_roles: []
  current_state: ""
  recent_history: ""
  open_questions: []

starter_prompt:
  intent: ""
  prompt: ""
  expected_outputs:
    - "context map"
    - "open questions"
    - "next low-friction actions"
  forbidden_outputs:
    - "project code mutation"
    - "cockpit write"
    - "root roadmap/backlog/spec hydration"
    - "kernel or governance edit"

readiness:
  status: "discovery_active"
  next_safe_action: ""
  evidence_needed: []
  hydration_blockers:
    - "No project-local approval yet."
    - "No cockpit route approval yet."
    - "No root roadmap/backlog/spec hydration approval yet."

cockpit_route:
  desired_route_id: ""
  route_label: ""
  pointer_only: true
  safe_open_prompt: ""
  must_not_load:
    - "project source"
    - "project-local memory"
    - "project-local gates"

validation_receipt:
  checked_at: ""
  commands_or_checks: []
  changed_files: []
  confirms:
    no_project_repo_mutation: true
    no_cockpit_mutation: true
    no_public_azoth_mutation: true
    no_kernel_governance_mutation: true
  residual_risks: []
```

## Starter Prompts

### Music Production

```text
Help me shape this music-production space without forcing it into software-task
language. Capture my current sound, reference tracks, tools, unfinished ideas,
learning questions, friction, and the next low-friction experiments. Keep the
output as creative context, not a delivery backlog.
```

Expected local state:

- Current sound and direction.
- Tools, plugins, instruments, and workflow constraints.
- Reference tracks and why they matter.
- Sketches, loops, unfinished tracks, and next experiments.
- Creative questions, not just tasks.
### Bachelor Thesis
```text
Help me continue my bachelor thesis. Map the research question, advisor
constraints, deadlines, source state, argument structure, writing gaps, and the
next focused work block. Separate academic uncertainty from execution tasks.
```

Expected local state:

- Research question and current thesis claim.
- Source inventory and evidence gaps.
- Advisor, university, and deadline constraints.
- Outline, chapter state, and writing blockers.
- Next focused reading or writing action.
### Agent Context Project
```text
Help me reconnect this agent/context-management project to Azoth. Identify its
design intent, current artifact or repo state, open risks, compatibility with
Azoth, and safe next experiments. Do not merge it into root-azoth unless we
explicitly decide it belongs there.
```

Expected local state:

- Architecture intent and main objects.
- Repo or artifact pointers.
- Context lifecycle and memory assumptions.
- Compatibility questions with Azoth.
- Safe experiments and tests.
## Quick-Start Profiles
Use these as first-pass starter profiles before creating any project-local file.
They are deliberately lightweight: one chat can refine them into a full packet.
### Music Production Space
```yaml
project_id: music-production-lab
project_name: Music Production Lab
domain: music_production
goal:
  why_now: "I want a place to explore sound, taste, workflow, and unfinished ideas."
  desired_help: "Help me notice patterns, choose experiments, and keep creative momentum."
  success_signals:
    - "I can name the current sound direction."
    - "I have a small list of next experiments."
    - "Old sketches and references stop feeling scattered."
local_context:
  project_paths:
    - "<music folder or DAW project root>"
  important_artifacts:
    - "reference tracks"
    - "unfinished sketches"
    - "plugin/tool notes"
  open_questions:
    - "What sound am I circling around?"
    - "Which unfinished idea deserves one more session?"
readiness:
  status: discovery_active
  next_safe_action: "Create a context map and choose one 30-60 minute experiment."
cockpit_route:
  pointer_only: true
  safe_open_prompt: "Open music-production-lab as a creative exploration space; do not load project files yet."
```
### Bachelor Thesis Space
```yaml
project_id: bachelor-thesis
project_name: Bachelor Thesis
domain: bachelor_thesis
goal:
  why_now: "I need continuity across research, writing, deadlines, and advisor feedback."
  desired_help: "Help me recover the thesis state and choose the next focused work block."
  success_signals:
    - "The research question is visible."
    - "Sources and evidence gaps are separated."
    - "The next writing/research action is concrete."
local_context:
  project_paths:
    - "<thesis notes or document folder>"
  important_artifacts:
    - "proposal or abstract"
    - "advisor feedback"
    - "source bibliography"
    - "chapter outline"
  open_questions:
    - "What is the current claim?"
    - "Which source gap blocks writing?"
readiness:
  status: discovery_active
  next_safe_action: "Map thesis state, then pick one reading or writing block."
cockpit_route:
  pointer_only: true
  safe_open_prompt: "Open bachelor-thesis as an academic work space; do not alter documents yet."
```
### Agent Context Project Space
```yaml
project_id: agent-context-project
project_name: Agent Context Project
domain: agent_context_project
goal:
  why_now: "I want to reconnect a separate agent/context-management idea to Azoth without forcing a merge."
  desired_help: "Help me compare design intent, artifacts, risks, and compatibility with Azoth."
  success_signals:
    - "The project has its own identity."
    - "Compatibility questions with Azoth are explicit."
    - "The next experiment is safe and bounded."
local_context:
  project_paths:
    - "<repo or notes path>"
  important_artifacts:
    - "architecture notes"
    - "prototype scripts"
    - "memory/context examples"
    - "test notes"
  open_questions:
    - "Which ideas belong in this project versus root-azoth?"
    - "What would prove the context model works?"
readiness:
  status: discovery_active
  next_safe_action: "Create a compatibility map and choose one no-mutation experiment."
cockpit_route:
  pointer_only: true
  safe_open_prompt: "Open agent-context-project as a separate project; do not merge or mutate root-azoth."
```
## Validation Checklist
- The packet names a stable project id and domain.
- The packet says where Azoth comes from: public install, root-azoth,
  personal cockpit, or mixed.
- The starter prompt matches the domain instead of using generic delivery-task
  language.
- Cockpit routing is pointer-only unless a separate cockpit session approves a
  route write.
- Project-local context remains inside the project space.
- Root roadmap/backlog/spec hydration remains blocked until a later
  hydration-specific approval names the exact candidate.
- The validation receipt lists changed files and confirms no project, cockpit,
  public Azoth, kernel, or governance mutation.
