# Azoth Round-2 Optimization Analysis

**Scope:** everything in the `hermes/azoth-improvements` phase branch (17 commits, ~1,250 LOC production + tests).
**Method:** count, quote, optimize — same as Round 1, but with a sharper lens on **what I missed last time**.

Round 1 fixed 4 wins: deleted 4 guard `main()`, switched tests to direct calls, removed `--strict` flag, fixed missing-checksum invariant. Net: -228 LOC, test suite 1.43s → 0.36s.

Round 2 finds **6 more wins** in territory I didn't fully explore last time.

---

## Finding 1: 4 referenced skills don't exist (the orchestrator's false promise)

**The most important Round-2 finding.** When I slimmed the orchestrator in commit `af524e2`, I moved decision-table content to skill references like:

```
- Route decision table → skills/azoth-route-decision/SKILL.md
- Stage 0 Assumption Checkpoint → skills/azoth-assumption-checkpoint/SKILL.md
- E1–E6 evaluator dispatch → skills/azoth-eval-dispatch/SKILL.md
- Friction-event guards → skills/azoth-fd-guard/SKILL.md
```

But **none of those 4 skills exist**. Verified just now:

```
ls: skills/azoth-assumption-checkpoint/SKILL.md: No such file or directory
ls: skills/azoth-eval-dispatch/SKILL.md: No such file or directory
ls: skills/azoth-fd-guard/SKILL.md: No such file or directory
ls: skills/azoth-route-decision/SKILL.md: No such file or directory
```

This is **the exact anti-slop violation the trust contract prohibits**: the orchestrator claims to load decision tables from skills, but loading them fails (the orchestrator will simply proceed without the decision logic, which is FD-001/FD-002 territory).

**Two options:**

**Option A (delete the references):** Remove the 4 bullet lines from the orchestrator. Either inline the minimal decision logic back into the orchestrator (~30 lines), or accept that the orchestrator references existing skills (`context-map`, `subagent-router`, `auto-router`) which already cover the territory.

**Option B (create the skills):** Extract the decision tables into 4 real SKILL.md files. But: each is 30–80 lines of content. That's 120–320 lines of new files, which makes the orchestrator's "slim" claim a lie (the content moved, didn't disappear).

**My recommendation: Option A.** Reasons:
- The orchestrator's inline-vs-orchestrate decision table is already there (8 lines). That covers 80% of "route decision" needs.
- The "Stage 0 Assumption Checkpoint" was never in the orchestrator before the slim — it was in the prior 385-line version. Removing it is honest.
- The "E1–E6 evaluator dispatch" already lives at `skills/auto-router/SKILL.md` (existing) — the orchestrator's `auto-router` reference covers it.
- The "friction-event guards" reference is misleading because the guard logic is in **Python subprocesses**, not skill content. The orchestrator should say "run `scripts/azoth_guards.py`" — which it already does in the always_do list.

**Net:** remove 4 false references from the orchestrator (-8 lines), keep the script reference.

---

## Finding 2: `test_azoth_guards_runner.py` should also use direct calls

**The inconsistency.** I switched 8 test files to direct `check()` calls in Round 1, but I left `test_azoth_guards_runner.py` on subprocess because "it's testing the runner's subprocess-loading contract." Looking at it again: **the runner's contract is `_load_guard(module_file)` + `_check_guard(name, payload)` + `run(payload)`**, all of which are importable. The runner test can:

- Import `azoth_guards.run` directly
- Pass payloads as dicts
- Assert on the returned dict

The subprocess layer tests whether **bash** can find the script and python can execute it — that's a shell test, not a unit test. The unit test should test the runner's logic.

**The migration:**
- `_run()` helper → `runner.run(payload)` direct call
- 6 test bodies stay identical in shape but use `runner.run(payload)` instead of `proc = _run(...)`
- Remove the `_run` helper entirely
- Remove `tempfile.NamedTemporaryFile`, `subprocess.run`, `sys.executable` imports

**Expected impact:** -20 LOC in test file, +1 test cycle for runner tests (was 0.34s for 5 tests; will be ~0.05s).

**Risk:** the runner test no longer exercises the bash subprocess path. But the `hermes_manifest_check.py` end-to-end test (which I run via shell already) covers that path. The runner's "subprocess-loading contract" is really just "does `importlib.util.spec_from_file_location` work" — which is a Python stdlib guarantee, not something worth a unit test.

---

## Finding 3: `hermes_manifest_check.py` has 5 nearly-identical `_check_*` helper shape

Look at `_check_agents_md_parity`, `_check_tests_directory`, `_check_trust_hosts_md` — they're all the same shape:

```python
def _check_X(repo_root: Path) -> tuple[bool, dict[str, object]]:
    path = repo_root / "Y"
    if not path.is_file():  # or .is_dir()
        return False, {"kind": "X", "ok": False, "reason": "..."}
    # check content
    if condition_fails:
        return False, {"kind": "X", "ok": False, "reason": "..."}
    return True, {"kind": "X", "ok": True}
```

This is the **"existence + content check" pattern**. Three functions, ~30 LOC each, ~90 LOC total.

**The optimization:** extract a generic helper:

```python
def _check_existence(
    name: str,
    target: Path,
    *,
    missing_reason: str,
    content_check: Callable[[], tuple[bool, str | None]] | None = None,
) -> dict[str, object]:
    """Returns {"kind": name, "ok": bool, "reason": str | None}."""
    if not target.is_file():
        return {"kind": name, "ok": False, "reason": missing_reason}
    if content_check:
        ok, reason = content_check()
        if not ok:
            return {"kind": name, "ok": False, "reason": reason}
    return {"kind": name, "ok": True}
```

Then each check becomes:

```python
def _check_agents_md_parity(repo_root):
    def _content():
        text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        if "per scope-gated session" not in text:
            return False, "missing 'per scope-gated session' wording"
        bad = re.findall(r"per session(?! scope-gated)", text)
        if bad:
            return False, f"stale 'per session' wording: {bad}"
        return True, None
    return _check_existence("agents_md_parity", repo_root / "AGENTS.md",
                             missing_reason="AGENTS.md missing",
                             content_check=_content)
```

But wait — this is actually **adding a layer of indirection** for a 3-call-site refactor. The pattern is too small. **Verdict: skip this optimization.** The repetition is real but each function is small enough that the helper would obscure the specific check logic. Better to leave it inline.

---

## Finding 4: `_check_kernel_files_present` duplicates `_check_kernel_checksum`'s path computation

```python
def _check_kernel_files_present(repo_root):
    kdir = _kernel_dir(repo_root)  # = repo_root / "kernel"
    results = []
    for name in KERNEL_FILES:
        path = kdir / name
        results.append({"kind": "kernel_file", "name": name, "path": str(path), "present": path.is_file()})
    return results
```

And `_check_kernel_checksum` recomputes the same paths:

```python
def _check_kernel_checksum(repo_root):
    kdir = _kernel_dir(repo_root)  # = repo_root / "kernel"
    # ... iterates KERNEL_FILES, computes kdir / name each time
```

The `_kernel_dir()` helper is already factored; that's fine. The repetition is minor. **Verdict: skip.**

---

## Finding 5: `_check_kernel_files_present` should join the main `run_check` result

The current `run_check` does:

```python
kernel_present = _check_kernel_files_present(repo_root)
kernel_ok = all(c["present"] for c in kernel_present)
# ...
checks.extend(kernel_present)  # 4 dicts
```

The 4 `kernel_file` entries could be a single dict with the file list:

```python
checks.append({
    "kind": "kernel_files",
    "name": "all_4_present",
    "ok": kernel_ok,
    "files": [{"name": name, "path": str(kdir / name), "present": (kdir / name).is_file()}
              for name in KERNEL_FILES],
})
```

**This is a breaking JSON schema change** — every test and consumer expecting 4 separate `kernel_file` entries would need updating. The Round-1 round kept the existing shape on purpose for backward compatibility.

**Verdict: skip.** The schema stability is more valuable than the ~10 LOC saving. If the schema needs to evolve, do it explicitly with a deprecation note.

---

## Finding 6: The `_check_*` helper signatures are inconsistent

Some return `tuple[bool, list[dict]]`, others return `tuple[bool, dict]`. That's not a code smell — it's intentional (kernel_files has 4 entries, the others are 1 each). **Verdict: skip.**

---

## Finding 7: `_kernel_dir` and `_checksums_path` helpers are used twice each

```python
def _kernel_dir(repo_root): return repo_root / "kernel"
def _checksums_path(repo_root): return repo_root / ".azoth" / "kernel-checksums.sha256"
```

Both are called twice (once in `_check_kernel_files_present`, once in `_check_kernel_checksum`). The helpers save a little repetition but cost two extra function definitions. Could inline:

```python
# In _check_kernel_files_present:
for name in KERNEL_FILES:
    path = repo_root / "kernel" / name
# In _check_kernel_checksum:
sums = repo_root / ".azoth" / "kernel-checksums.sha256"
```

**Verdict: keep the helpers.** They document the intent ("this is where the kernel lives", "this is where the checksum file lives"). Inlining would obscure the layout. **-2 LOC saved, -2 LOC of documentation lost.**

---

## Finding 8: `_check_trust_hosts_md` parses with string contains instead of YAML parse

Currently:

```python
text = path.read_text(encoding="utf-8")
if "<!-- trust_hosts:start -->" not in text or "<!-- trust_hosts:end -->" not in text:
    return False, ...
```

The `test_trust_hosts_contract.py` test parses the YAML block between the fences:

```python
def _parse_trust_hosts_markdown(text):
    start = text.find("<!-- trust_hosts:start -->")
    end = text.find("<!-- trust_hosts:end -->")
    block = text[start + len("<!-- trust_hosts:start -->"):end].strip()
    return yaml.safe_load(block)
```

**Two checks of the same file with different parsing strategies.** This is real duplication. The manifest check could call the same `_parse_trust_hosts_markdown` helper (move it into a shared location) and verify the YAML parses correctly, not just that fences are present.

**The optimization:**
1. Move the YAML-fence parser to a shared helper (`tests/_shared_helpers.py` or a new `scripts/_kernel_helpers.py`).
2. Have `_check_trust_hosts_md` in the manifest check use the same parser, return `ok: True` only if the YAML parses + has the expected structure.

**Expected impact:**
- Manifest check becomes more thorough: catches malformed YAML inside the fence.
- Test suite consistency: same parser in both places.
- LOC: similar but quality is better.

**Recommendation: do it, but as a new module.** Create `scripts/_azoth_yaml.py` with the fence parser, import from both `hermes_manifest_check.py` and the test file. ~15 LOC new file, ~10 LOC removed from the test, ~3 LOC added to the manifest check. Net: ~2 LOC saved, but **the correctness win is bigger than the LOC count**: a YAML parse failure now blocks the manifest check.

---

## Finding 9: `azoth_guards.py` has a TODO-worthy structural pattern

The runner's `run()` function:

```python
def run(payload):
    guards = {}
    total_violations = 0
    for guard_id, _module_name in GUARD_MODULES.items():
        section_key = {
            "fd_003": "friction_check",
            "fd_004": "hydration_check",
            "fd_005": "completion_check",
            "fd_008": "subagent_contract_check",
        }[guard_id]  # ← rebuilt every iteration
        section_payload = payload.get(section_key) or {}
        result = _check_guard(guard_id, section_payload)
        guards[guard_id] = result
        total_violations += len(result.get("violations") or [])
    ok = all(g.get("ok") for g in guards.values())
    return {"ok": ok, "violation_count": total_violations, "guards": guards}
```

The `section_key` dict is **rebuilt inside the loop on every iteration**. Should be a module-level constant:

```python
GUARD_TO_SECTION_KEY = {
    "fd_003": "friction_check",
    "fd_004": "hydration_check",
    "fd_005": "completion_check",
    "fd_008": "subagent_contract_check",
}
```

Move it next to `GUARD_MODULES`, and the loop reads from it.

**Same pattern in `GUARD_MODULES`** — the iteration `_module_name` is unused; should be `GUARD_MODULES.values()` directly.

**Expected impact:** ~5 LOC of micro-cleanup, slight readability gain. This is a YAGNI-borderline change — it's clear as-is. But it is a true inefficiency (dict rebuilt each iteration).

**Recommendation: do it.** It's 1 minute of work and it's the kind of detail that compounds.

---

## Finding 10: azoth.yaml duplicates trust_bearing_hosts list (in two places)

`azoth.yaml` has:

```yaml
trust_bearing_hosts:
  - hermes
  - codex
  - opencode
# ...
platforms:
  hermes: trust-bearing    # Primary substrate (D55, D56)
  opencode: trust-bearing  # Co-trust (D55)
  codex: trust-bearing     # Co-trust (D55)
  claude_code: best-effort  # ...
  copilot: adapter         # ...
  cursor: adapter          # ...
  gemini: adapter          # ...
  antigravity: adapter     # ...
```

Two issues:

1. **The trust-bearing list appears twice** (in `trust_bearing_hosts` and embedded in `platforms`).
2. **The semantic mapping is wrong**: `trust_bearing_hosts` is a list, `platforms.{host}` is a string. They encode different things — the list says "who's trust-bearing", the dict says "what role each host plays". But the role values are inconsistent: `hermes: trust-bearing` (correct), `claude_code: best-effort` (correct), `copilot: adapter` (not "best-effort" — different word).

The cleanest fix is to **derive `platforms` from `trust_bearing_hosts` + `best_effort_mirrors`** at load time. Since `azoth.yaml` is parsed by various tools, that needs care. A safer immediate fix: align the values (`adapter` → `best-effort` everywhere except trust-bearing hosts) and remove the duplication by using a flat list.

**Recommendation: align values + drop one of the two.** The `trust_bearing_hosts` list is the authoritative one (used by the deploy script and the manifest check); the `platforms` dict is documentation. Drop the `platforms` dict's per-host trust-bearing markers; keep just `platforms` as a flat list of all supported platforms.

**Expected impact:** -8 lines in `azoth.yaml`, one less place to update when a host changes trust posture.

---

## Finding 11: The orchestrator's `tools:` list says `bash, task` — but the slim version doesn't use them

Look at the slim orchestrator. The body says "Use `delegate_task` (Hermes) or `Agent(subagent_type=...)` (Claude Code) — never inline." That's it for tools. The `tools:` frontmatter says `[read, grep, glob, bash, task]`. **Five tools listed, only `bash` is actually exercised** (for running `scripts/azoth_guards.py`).

**But this is the host-platform's tool list**, not a runtime declaration. The orchestrator frontmatter is what the agent platform uses to gate which tools the agent can call. **Removing `task` would prevent the orchestrator from spawning subagents in Claude Code**, which is the entire point. **Removing `read/grep/glob` would prevent repo inspection.** So all 5 are correct.

**Verdict: skip.** The frontmatter is the agent's actual capability, not a hint.

---

## Finding 12: `~/.hermes/profiles/azoth-personal-cockpit/skills/azoth-substrate/SKILL.md` mentions scripts that no longer have standalone CLIs

Look at the SKILL.md lines 64–67:

```
python3 /Users/yiwei/GithubRepos/root-azoth/scripts/check_fd_003_subagent_isolation.py --input ... --json
python3 /Users/yiwei/GithubRepos/root-azoth/scripts/check_fd_004_hydration_scope.py --input ... --json
python3 /Users/yiwei/GithubRepos/root-azoth/scripts/check_fd_005_completion_semantics.py --input ... --json
python3 /Users/yiwei/GithubRepos/root-azoth/scripts/check_fd_008_subagent_contract.py --input ... --json
```

After Round 1, these guard scripts **no longer have standalone CLIs** (`main()` was removed). The SKILL.md tells operators to invoke them as scripts; they'll silently exit 0 without doing anything.

**The fix:** remove the "Or individually:" section. The combined runner is the canonical entry point. If someone really wants to run one guard, they can construct a single-section payload and pass it to `azoth_guards.py`.

**Expected impact:** -6 lines from the SKILL.md. Plus correctness: operators following the skill won't be confused by silent exits.

---

## Finding 13: `docs/personal-control-plane/README.md` references the K0–K7 doc by path

Look at the new README I wrote in commit `779f115`:

```
historical roadmap entries (`.azoth/roadmap-specs/v0.2.0/T-040..T-053`) reference the
retired doc by path — those pointers are now stale but the entries themselves
are historical evidence of the 7-phase plan that was superseded.
```

That's a 4-line aside explaining the staleness. It's fine — operator-facing context. **Verdict: skip.**

---

## Summary — what to do in Round 2

| # | Finding | LOC saved | Effort | Recommendation |
|---|---|---|---|---|
| **1** | **4 skill references don't exist** | **-8 LOC orchestrator + 4 false promises fixed** | 5 min | **DO — highest priority** |
| **2** | **runner tests use subprocess unnecessarily** | **-20 LOC tests** | 10 min | **DO — speedup** |
| **3** | Existence+content pattern | -10 LOC | 15 min | skip (obscuring) |
| **4** | path computation dup | 0 LOC | — | skip (helper already factored) |
| **5** | kernel_files dict shape | -10 LOC | breaking change | skip (schema stability) |
| **6** | `_check_*` signature inconsistency | 0 LOC | — | skip (intentional) |
| **7** | helper function definitions | -2 LOC | — | skip (helpers document intent) |
| **8** | shared YAML fence parser | -8 LOC + correctness win | 30 min | **DO — correctness > LOC** |
| **9** | section_key dict rebuilt in loop | -5 LOC + micro-cleanup | 5 min | **DO** |
| **10** | trust_bearing_hosts duplicated in azoth.yaml | -8 LOC | 15 min | **DO** |
| **11** | orchestrator tools list | 0 LOC | — | skip (correct as-is) |
| **12** | **SKILL.md mentions dead guard CLIs** | **-6 LOC skill** | 5 min | **DO — correctness** |
| **13** | README staleness aside | 0 LOC | — | skip (intentional) |

**Recommended Round-2 changes (5 items):**
- **Finding 1**: Remove 4 false skill references from orchestrator. **Correctness win.**
- **Finding 2**: Switch runner tests to direct `run()` calls. **Speedup + LOC win.**
- **Finding 8**: Move YAML-fence parser to shared helper. **Correctness win.**
- **Finding 9**: Move section_key dict to module-level constant. **Micro-cleanup.**
- **Finding 10**: Align `azoth.yaml` trust-bearing values, drop redundant list. **Single-source-of-truth win.**
- **Finding 12**: Remove dead guard CLI references from `azoth-substrate/SKILL.md`. **Correctness win.**

**Expected Round-2 delta:**
- Production: ~12 LOC saved
- Tests: ~20 LOC saved
- Skills: ~6 LOC saved
- azoth.yaml: ~8 LOC saved
- **Total: ~46 LOC**, plus **3 correctness wins** (Finding 1, 8, 12) and **1 speedup** (Finding 2).

**The Round-2 finding I'd flag as highest priority is Finding 1.** The orchestrator is currently claiming to load skills that don't exist. This is the same anti-slop anti-pattern as the manifest-vs-reality gap the trust contract prohibits. The "delete the false references" fix is 5 minutes.
