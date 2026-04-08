#!/usr/bin/env python3
"""Append one validated L2 evidence record to the JSONL store (gated). P6-002."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from l2_evidence_validate import validate_l2_evidence_record  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = ROOT / ".azoth" / "memory" / "l2-refinement-evidence.jsonl"
DEFAULT_SCOPE = ROOT / ".azoth" / "scope-gate.json"
DEFAULT_PIPELINE = ROOT / ".azoth" / "pipeline-gate.json"


def _parse_expires(s: str) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"l2_evidence_append: missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _check_gates(
    scope_path: Path,
    pipeline_path: Path,
    expected_session_id: str,
) -> None:
    sg = _load_json(scope_path)
    if not sg.get("approved"):
        sys.exit("l2_evidence_append: scope-gate not approved")
    exp = _parse_expires(sg.get("expires_at", ""))
    if exp is None:
        sys.exit("l2_evidence_append: scope-gate expires_at invalid or missing")
    now = datetime.now(timezone.utc)
    if now > exp:
        sys.exit("l2_evidence_append: scope-gate expired")
    if sg.get("session_id") != expected_session_id:
        sys.exit("l2_evidence_append: session_id mismatch (scope-gate vs --session-id)")

    delivery = sg.get("delivery_pipeline") == "governed"
    m1 = sg.get("target_layer") == "M1"
    if delivery or m1:
        pg = _load_json(pipeline_path)
        if not pg.get("approved"):
            sys.exit("l2_evidence_append: pipeline-gate required but not approved")
        pexp = _parse_expires(pg.get("expires_at", ""))
        if pexp is None or now > pexp:
            sys.exit("l2_evidence_append: pipeline-gate missing, invalid, or expired")
        if pg.get("session_id") != expected_session_id:
            sys.exit("l2_evidence_append: pipeline-gate session_id mismatch")


def main() -> None:
    p = argparse.ArgumentParser(description="Append one L2 evidence record (gated).")
    p.add_argument("--session-id", required=True, help="Must match scope-gate.session_id")
    p.add_argument("--file", type=Path, help="JSON file with single record; else stdin")
    p.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL, help="Output JSONL path")
    p.add_argument("--scope-gate", type=Path, default=DEFAULT_SCOPE)
    p.add_argument("--pipeline-gate", type=Path, default=DEFAULT_PIPELINE)
    p.add_argument(
        "--azoth-dir",
        type=Path,
        default=None,
        help="Root containing .azoth/ (for tests; relocates default paths)",
    )
    args = p.parse_args()

    root = args.azoth_dir if args.azoth_dir is not None else ROOT
    jsonl = args.jsonl
    scope_gate = args.scope_gate if args.azoth_dir is None else root / ".azoth" / "scope-gate.json"
    pipeline_gate = (
        args.pipeline_gate if args.azoth_dir is None else root / ".azoth" / "pipeline-gate.json"
    )
    if args.azoth_dir is not None:
        jsonl = root / ".azoth" / "memory" / "l2-refinement-evidence.jsonl"

    raw = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    doc = json.loads(raw)
    validate_l2_evidence_record(doc)

    if doc.get("session_id") != args.session_id:
        sys.exit("l2_evidence_append: record.session_id must match --session-id")

    _check_gates(scope_gate, pipeline_gate, args.session_id)

    jsonl.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()


if __name__ == "__main__":
    main()
