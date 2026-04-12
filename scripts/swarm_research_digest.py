#!/usr/bin/env python3
"""Create, append to, and validate SWARM_RESEARCH_DIGEST.yaml (DYNAMIC-FULL-AUTO+).

Canonical path pattern: .azoth/roadmap-specs/<roadmap_version>/SWARM_RESEARCH_DIGEST.yaml
See skills/dynamic-full-auto/SKILL.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

EXIT_OK = 0
EXIT_USER = 1
EXIT_IO = 2

REQUIRED_TOP = (
    "schema_version",
    "roadmap_version",
    "consensus_themes",
    "research_packs",
    "explore_swarm_summary",
    "mapped_roadmap_tasks",
)


def _die(code: int, msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=88,
    )


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except OSError as e:
        _die(EXIT_IO, f"write failed: {e}")


def _normalize_pack(raw: dict[str, Any]) -> dict[str, Any]:
    pack = dict(raw)
    if "research_pack_id" in pack and "id" not in pack:
        pack["id"] = pack.pop("research_pack_id")
    return pack


def validate_research_pack(pack: Any, label: str) -> list[str]:
    """Validate a single research_packs[] element."""
    errs: list[str] = []
    if not isinstance(pack, dict):
        return [f"{label}: pack must be a mapping"]
    pid = pack.get("id")
    if not isinstance(pid, str) or not pid.strip():
        errs.append(f"{label}: id must be a non-empty str")
    if "topic" not in pack or not isinstance(pack.get("topic"), str):
        errs.append(f"{label}: topic must be a str")
    src = pack.get("sources")
    if not isinstance(src, list):
        errs.append(f"{label}: sources must be a list")
    else:
        for j, row in enumerate(src):
            if not isinstance(row, dict):
                errs.append(f"{label}: sources[{j}] must be a mapping")
                continue
            for k2 in ("title", "url"):
                if k2 not in row or not isinstance(row.get(k2), str):
                    errs.append(f"{label}: sources[{j}] needs string {k2!r}")
    for lst_key in ("implications_for_azoth", "risks"):
        v = pack.get(lst_key)
        if not isinstance(v, list):
            errs.append(f"{label}: {lst_key} must be a list")
        else:
            for j, line in enumerate(v):
                if not isinstance(line, str):
                    errs.append(f"{label}: {lst_key}[{j}] must be str")
    return errs


def validate_digest(data: Any, *, path: str | None = None) -> list[str]:
    """Return a list of validation errors; empty means valid."""
    errs: list[str] = []
    label = path or "digest"

    if not isinstance(data, dict):
        return [f"{label}: root must be a mapping"]

    for key in REQUIRED_TOP:
        if key not in data:
            errs.append(f"{label}: missing required key {key!r}")

    if errs:
        return errs

    if not isinstance(data["schema_version"], int):
        errs.append(f"{label}: schema_version must be int")
    if not isinstance(data["roadmap_version"], str) or not data["roadmap_version"]:
        errs.append(f"{label}: roadmap_version must be non-empty str")

    ct = data["consensus_themes"]
    if not isinstance(ct, list):
        errs.append(f"{label}: consensus_themes must be a list")
    else:
        for i, item in enumerate(ct):
            if not isinstance(item, dict):
                errs.append(f"{label}: consensus_themes[{i}] must be a mapping")
                continue
            if "id" not in item or not isinstance(item.get("id"), str):
                errs.append(f"{label}: consensus_themes[{i}].id must be a non-empty str")
            if "summary" not in item or not isinstance(item.get("summary"), str):
                errs.append(f"{label}: consensus_themes[{i}].summary must be a str")
            cp = item.get("contributing_packs")
            if cp is not None:
                if not isinstance(cp, list):
                    errs.append(f"{label}: consensus_themes[{i}].contributing_packs must be a list")
                else:
                    for j, ref in enumerate(cp):
                        if not isinstance(ref, str) or not ref.strip():
                            errs.append(
                                f"{label}: consensus_themes[{i}].contributing_packs[{j}] "
                                "must be non-empty str"
                            )

    packs = data["research_packs"]
    if not isinstance(packs, list):
        errs.append(f"{label}: research_packs must be a list")
    else:
        seen: set[str] = set()
        for i, pack in enumerate(packs):
            perrs = validate_research_pack(pack, f"{label}: research_packs[{i}]")
            errs.extend(perrs)
            if isinstance(pack, dict):
                pid = pack.get("id")
                if isinstance(pid, str) and pid.strip():
                    if pid in seen:
                        errs.append(f"{label}: duplicate research_packs id {pid!r}")
                    else:
                        seen.add(pid)

    ex = data["explore_swarm_summary"]
    if not isinstance(ex, dict):
        errs.append(f"{label}: explore_swarm_summary must be a mapping")
    else:
        if "wave" not in ex or not isinstance(ex.get("wave"), str):
            errs.append(f"{label}: explore_swarm_summary.wave must be a str")
        fin = ex.get("findings")
        if not isinstance(fin, list):
            errs.append(f"{label}: explore_swarm_summary.findings must be a list")
        else:
            for i, f in enumerate(fin):
                if not isinstance(f, str):
                    errs.append(f"{label}: explore_swarm_summary.findings[{i}] must be str")

    mrt = data["mapped_roadmap_tasks"]
    if not isinstance(mrt, list):
        errs.append(f"{label}: mapped_roadmap_tasks must be a list")
    else:
        for i, tid in enumerate(mrt):
            if not isinstance(tid, str):
                errs.append(f"{label}: mapped_roadmap_tasks[{i}] must be str")

    mn = data.get("mapping_notes")
    if mn is not None:
        if not isinstance(mn, dict):
            errs.append(f"{label}: mapping_notes must be a mapping")
        else:
            for k, v in mn.items():
                if not isinstance(k, str) or not k.strip():
                    errs.append(f"{label}: mapping_notes keys must be non-empty str")
                elif not isinstance(v, str) or not v.strip():
                    errs.append(f"{label}: mapping_notes[{k!r}] must be non-empty str")

    if "meta" in data and data["meta"] is not None and not isinstance(data["meta"], dict):
        errs.append(f"{label}: meta must be a mapping when present")

    return errs


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.digest)
    if path.exists() and not args.force:
        _die(EXIT_USER, f"refuse: {path} exists (use --force to overwrite)")
    skeleton: dict[str, Any] = {
        "schema_version": args.schema_version,
        "roadmap_version": args.roadmap_version,
        "consensus_themes": [],
        "research_packs": [],
        "explore_swarm_summary": {"wave": "", "findings": []},
        "mapped_roadmap_tasks": [],
    }
    text = "# SWARM_RESEARCH_DIGEST — see skills/dynamic-full-auto/SKILL.md\n" + _dump(skeleton)
    try:
        _atomic_write(path, text)
    except SystemExit:
        raise
    except Exception as e:
        _die(EXIT_IO, str(e))


def cmd_append_pack(args: argparse.Namespace) -> None:
    path = Path(args.digest)
    if not path.is_file():
        _die(EXIT_IO, f"no file: {path}")
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
    except OSError as e:
        _die(EXIT_IO, f"read failed: {e}")
    except yaml.YAMLError as e:
        _die(EXIT_USER, f"YAML parse error: {e}")

    errs = validate_digest(data, path=str(path))
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        _die(EXIT_USER, "existing digest failed validation; fix before append-pack")

    if args.pack:
        try:
            pack_src = Path(args.pack).read_text(encoding="utf-8")
        except OSError as e:
            _die(EXIT_IO, f"read pack failed: {e}")
    else:
        pack_src = sys.stdin.read()
    try:
        loaded = yaml.safe_load(pack_src)
    except yaml.YAMLError as e:
        _die(EXIT_USER, f"pack YAML error: {e}")

    if not isinstance(loaded, dict):
        _die(EXIT_USER, "pack must be a single YAML mapping (one research pack)")

    pack = _normalize_pack(loaded)
    perrs = validate_research_pack(pack, "pack")
    if perrs:
        for e in perrs:
            print(e, file=sys.stderr)
        _die(EXIT_USER, "pack validation failed")

    pid = pack.get("id")
    if not isinstance(pid, str) or not pid.strip():
        _die(EXIT_USER, "pack id missing after validation (internal error)")
    for existing in data["research_packs"]:
        if isinstance(existing, dict) and existing.get("id") == pid:
            _die(EXIT_USER, f"refuse: research_pack id {pid!r} already exists")

    data["research_packs"].append(pack)
    errs2 = validate_digest(data, path=str(path))
    if errs2:
        for e in errs2:
            print(e, file=sys.stderr)
        _die(EXIT_USER, "digest invalid after append")

    # Preserve leading comment lines if any
    header = ""
    lines = raw_text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("#"):
        header += lines[i]
        i += 1
    out = header + _dump(data)
    _atomic_write(path, out)


def cmd_validate(args: argparse.Namespace) -> None:
    path = Path(args.digest)
    if not path.is_file():
        _die(EXIT_IO, f"no file: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        _die(EXIT_IO, f"read failed: {e}")
    except yaml.YAMLError as e:
        _die(EXIT_USER, f"YAML error: {e}")

    errs = validate_digest(data, path=str(path))
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        _die(EXIT_USER, "validation failed")
    if not args.quiet:
        print(f"OK: {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="SWARM_RESEARCH_DIGEST.yaml helper.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="write skeleton digest")
    pi.add_argument("digest", type=Path, help="path to YAML file to create")
    pi.add_argument("--roadmap-version", default="v0.0.0", help="roadmap_version field")
    pi.add_argument("--schema-version", type=int, default=1, help="schema_version field")
    pi.add_argument("--force", action="store_true", help="overwrite existing file")
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append-pack", help="append one research pack (stdin or --pack)")
    pa.add_argument("digest", type=Path)
    pa.add_argument("--pack", type=Path, default=None, help="YAML file with one pack mapping")
    pa.set_defaults(func=cmd_append_pack)

    pv = sub.add_parser("validate", help="structural validation")
    pv.add_argument("digest", type=Path)
    pv.add_argument("--quiet", action="store_true")
    pv.set_defaults(func=cmd_validate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
