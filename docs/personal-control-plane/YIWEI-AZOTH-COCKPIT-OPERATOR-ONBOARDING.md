# Yiwei Azoth Cockpit Operator Onboarding

Status: T-053 readiness delivery
Date: 2026-05-01
Cockpit path: `/Users/yiwei/GithubRepos/yiwei-azoth-cockpit`
Source plane: `root-azoth`

This guide is the operator handoff for using the personal cockpit after the
T-052 local deployment/rename. It explains how to treat the cockpit as a stable
control plane without quietly expanding into backup provisioning, source
onboarding, retrieval indexing, or project mutation.

## Current State

The cockpit is deployed locally at `/Users/yiwei/GithubRepos/yiwei-azoth-cockpit`.
It has receipt evidence from T-052 and a pointer-only pilot project profile from
T-049. Root planning truth treats T-053 as completed backup/recovery readiness,
with T-054/T-055 covering the safe-open menu, context firewall, first-use command
surface, and no-write UX simulation.

This guide does not mutate the cockpit. It is the root-side operating manual for
the next safe human workflow.

## Operating Rule

Use the cockpit as a coordinator first, not as an importer.

- Project profiles stay pointer-only until a fresh project-specific gate opens.
- Source registries stay closed until a fresh source-onboarding gate opens.
- Retrieval, graph, and vector indexes stay unchanged until a fresh retrieval gate
  opens.
- Backup storage and encrypted/private remotes stay unprovisioned until a fresh
  backup implementation gate opens.
- Credentials are never read under this onboarding/readiness lane.

## Start A Cockpit Session

Run the status and validation checks from `root-azoth` first:

```bash
git status --short --branch
python3 scripts/run_ledger.py status
python3 scripts/personal_knowledge_validate.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
python3 scripts/cockpit_bootstrap_verify.py --root /Users/yiwei/GithubRepos/yiwei-azoth-cockpit
git -C /Users/yiwei/GithubRepos/yiwei-azoth-cockpit status --short --branch
```

Then ask the agent for a route, not a broad implementation:

```text
Use repo-native state and tell me the next safe personal cockpit lane.
Do not mutate project repos, onboard sources, expand retrieval, or provision backup
storage without an explicit fresh gate.
```

## Daily Use

Use the cockpit for coordination and receipts:

1. Confirm the cockpit repo is clean.
2. Confirm `root-azoth` has no active run-ledger write claim unless the current
   session owns it.
3. Pick exactly one lane: backup/recovery, pointer-only project profile, source
   onboarding, retrieval, public release, or stop/defer.
4. Require a named gate before any mutation-capable lane.
5. End each lane with a receipt or handoff that records what changed and what did
   not change.

## Backup And Recovery Readiness

Before the cockpit controls more projects, keep a restore path visible. The
minimum readiness model is:

- A clean cockpit git commit before any mutation-capable operation.
- A root-side handoff that records the cockpit path, commit, validation commands,
  and deferred boundaries.
- A documented restore test plan that can be run in a temporary path before any
  private remote or encrypted backup is provisioned.
- A future operator decision for storage policy: local-only, private remote, or
  encrypted backup.

This T-053 delivery does not create storage, remotes, archives, or secrets. It
defines what those later operations must prove.

## Periodic Backup Verification

After the private git remote is configured, verify the backup by restoring from
the remote into a temporary checkout:

```bash
python3 scripts/cockpit_backup_verify.py
```

The check clones the private cockpit remote into a temporary path, recreates
required empty skeleton directories for that restored checkout, runs the personal
knowledge validator, runs the cockpit restore verifier, and renders the
`ras-or-ray` pointer handoff. It must not write to the live cockpit, project
repos, source registries, retrieval indexes, or release surfaces.

## Recovery Drill Shape

A future recovery implementation gate should verify the restore path without
touching project repos:

1. Identify the approved restore reference.
2. Restore into a temporary path or clean checkout.
3. Run the personal knowledge validator against the restored cockpit.
4. Compare project profile pointers and receipt evidence.
5. Confirm the restored cockpit has no dirty state.
6. Record the result in a root-side handoff and, if the gate allows, a cockpit
   receipt.

## Adding Another Project

Use the T-049 pattern until the operator approves a richer project lane:

- Register only a project profile pointer.
- Record the project repo path and scope boundary.
- Do not scan source files.
- Do not write project code.
- Do not create retrieval entries from the project.
- Close with receipt evidence.

Suggested prompt:

```text
Open a pointer-only project profile lane for <project path>.
No project code mutation, no source onboarding, no retrieval expansion.
Record receipt evidence only.
```

## When The Cockpit Is Properly Deployed

Treat the cockpit as properly deployed for current stabilized use when all of
these are true:

- `yiwei-azoth-cockpit` exists at the approved path and validates cleanly.
- Root roadmap/backlog/spec truth names the active or completed cockpit lane.
- The cockpit has receipt evidence for deployment and any project profile pilots.
- Backup/recovery readiness is documented, even if backup storage is still
  deferred.
- The operator has this onboarding guide for daily routing.
- Deferred gates are explicit: backup provisioning, credentials, cloud/storage
  writes, cockpit mutation, project writes, source onboarding, retrieval expansion,
  public release, governance, kernel, and M1.

## Next Safe Prompts

For backup implementation later:

```text
Open a backup implementation gate for yiwei-azoth-cockpit.
First propose local-only, private remote, and encrypted backup options with restore
test acceptance. Do not access credentials or write storage until I approve one.
```

For another project consumer:

```text
Open a pointer-only project onboarding lane for <repo path>.
Use the personal cockpit profile model and receipt evidence only.
```

For retrieval/source onboarding later:

```text
Open a source-onboarding research gate.
Show sources, risks, and retrieval boundaries before any indexing or import.
```
