"""Validate a single L3 architecture proposal dict (P6-003) before writing under `.azoth/proposals/`."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROPOSAL_SCHEMA_VERSION = 1
TITLE_MAX_LEN = 256
SUMMARY_MAX_LEN = 8192

_VALID_STATUSES = frozenset({"draft", "submitted", "approved_for_docs", "superseded", "rejected"})
_VALID_SCOPE_LAYERS = frozenset({"kernel", "skills", "agents", "pipelines", "docs", "mixed"})

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_DECISION_REF_RE = re.compile(r"^D\d+$")

_TOP_KEYS = frozenset(
    {
        "proposal_schema_version",
        "created_at",
        "session_id",
        "backlog_id",
        "title",
        "summary",
        "status",
        "decision_refs",
        "scope_layers",
        "details",
    }
)


class ArchitectureProposalValidationError(Exception):
    pass


def validate_architecture_proposal(doc: Any, *, label: str = "proposal") -> None:
    if not isinstance(doc, dict):
        raise ArchitectureProposalValidationError(f"{label}: must be a JSON/YAML object")
    extra = set(doc.keys()) - _TOP_KEYS
    if extra:
        raise ArchitectureProposalValidationError(
            f"{label}: unknown top-level keys {sorted(extra)}"
        )
    for k in _TOP_KEYS:
        if k not in doc:
            raise ArchitectureProposalValidationError(f"{label}: missing required field {k!r}")

    if doc["proposal_schema_version"] != PROPOSAL_SCHEMA_VERSION:
        raise ArchitectureProposalValidationError(
            f"{label}: proposal_schema_version must be {PROPOSAL_SCHEMA_VERSION}"
        )

    ca = doc["created_at"]
    if not isinstance(ca, str) or not _ISO_RE.match(ca):
        raise ArchitectureProposalValidationError(
            f"{label}: created_at must be ISO-8601 UTC string"
        )
    try:
        if ca.endswith("Z"):
            datetime.fromisoformat(ca.replace("Z", "+00:00"))
        else:
            datetime.fromisoformat(ca)
    except ValueError as e:
        raise ArchitectureProposalValidationError(f"{label}: invalid created_at datetime") from e

    for key, maxlen in (("session_id", 128), ("backlog_id", 64)):
        v = doc[key]
        if not isinstance(v, str) or not (1 <= len(v) <= maxlen):
            raise ArchitectureProposalValidationError(
                f"{label}: {key} must be non-empty str, max {maxlen}"
            )

    title = doc["title"]
    if not isinstance(title, str) or not (1 <= len(title) <= TITLE_MAX_LEN):
        raise ArchitectureProposalValidationError(
            f"{label}: title must be str length 1..{TITLE_MAX_LEN}"
        )

    summary = doc["summary"]
    if not isinstance(summary, str) or not (1 <= len(summary) <= SUMMARY_MAX_LEN):
        raise ArchitectureProposalValidationError(
            f"{label}: summary must be str length 1..{SUMMARY_MAX_LEN}"
        )

    st = doc["status"]
    if st not in _VALID_STATUSES:
        raise ArchitectureProposalValidationError(f"{label}: invalid status {st!r}")

    refs = doc["decision_refs"]
    if not isinstance(refs, list) or len(refs) < 1:
        raise ArchitectureProposalValidationError(f"{label}: decision_refs must be non-empty array")
    for i, ref in enumerate(refs):
        if not isinstance(ref, str) or not _DECISION_REF_RE.match(ref):
            raise ArchitectureProposalValidationError(
                f"{label}: decision_refs[{i}] must match pattern D<number>"
            )

    layers = doc["scope_layers"]
    if not isinstance(layers, list) or len(layers) < 1:
        raise ArchitectureProposalValidationError(f"{label}: scope_layers must be non-empty array")
    for i, layer in enumerate(layers):
        if layer not in _VALID_SCOPE_LAYERS:
            raise ArchitectureProposalValidationError(
                f"{label}: invalid scope_layers[{i}] {layer!r}"
            )

    if not isinstance(doc["details"], dict):
        raise ArchitectureProposalValidationError(f"{label}: details must be an object")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _load_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as e:
            raise SystemExit(
                "architecture_proposal_validate: PyYAML required for .yaml/.yml "
                "(pip install pyyaml)"
            ) from e
        loaded = yaml.safe_load(text)
    elif suffix == ".json":
        loaded = json.loads(text)
    else:
        raise SystemExit(
            f"architecture_proposal_validate: unsupported suffix {path.suffix!r} (use .yaml or .json)"
        )
    if not isinstance(loaded, dict):
        raise SystemExit("architecture_proposal_validate: root must be a mapping")
    return loaded


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate an architecture proposal YAML/JSON file.")
    p.add_argument("path", type=Path, help="Path to .yaml, .yml, or .json proposal")
    args = p.parse_args(argv)
    path: Path = args.path
    if not path.is_file():
        print(f"architecture_proposal_validate: not a file: {path}", file=sys.stderr)
        return 2
    try:
        doc = _load_doc(path)
        validate_architecture_proposal(doc, label=path.name)
    except ArchitectureProposalValidationError as e:
        print(f"architecture_proposal_validate: {e}", file=sys.stderr)
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
