#!/usr/bin/env python3
"""Validate personal knowledge cards, import batches, and root skeletons."""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

try:
    from yaml_helpers import safe_load_yaml_path
except ModuleNotFoundError:  # pragma: no cover - defensive fallback for direct reuse.
    YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

    def safe_load_yaml_path(path: Path) -> Any:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_SAFE_LOADER)


ROOT = Path(__file__).resolve().parent.parent
CARD_SCHEMA_PATH = ROOT / "schemas" / "personal-knowledge-card.schema.yaml"
BATCH_SCHEMA_PATH = ROOT / "schemas" / "personal-knowledge-import-batch.schema.yaml"

KNOWLEDGE_DIR = Path(".azoth/knowledge")
CARD_DIR = KNOWLEDGE_DIR / "cards"
IMPORT_BATCH_DIR = KNOWLEDGE_DIR / "imports" / "batches"

REQUIRED_SKELETON_FILES = (
    KNOWLEDGE_DIR / "README.md",
    KNOWLEDGE_DIR / "policy.yaml",
    KNOWLEDGE_DIR / "preferences.yaml",
    KNOWLEDGE_DIR / "principles.yaml",
    KNOWLEDGE_DIR / "glossary.yaml",
    KNOWLEDGE_DIR / "indexes" / "topic-index.yaml",
    KNOWLEDGE_DIR / "indexes" / "authority-index.yaml",
    KNOWLEDGE_DIR / "imports" / "ledger.yaml",
)
REQUIRED_SKELETON_DIRS = (
    CARD_DIR / "root-azoth",
    CARD_DIR / "projects",
    CARD_DIR / "personal",
    KNOWLEDGE_DIR / "indexes",
    IMPORT_BATCH_DIR,
)

CARD_PATH_PREFIX = PurePosixPath(".azoth/knowledge/cards")
CARD_SUFFIXES = {".yaml", ".yml"}
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


class PersonalKnowledgeValidationError(Exception):
    """One or more fail-closed personal knowledge validation errors."""

    def __init__(self, errors: str | list[str]):
        if isinstance(errors, str):
            self.errors = [errors]
        else:
            self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _load_yaml_mapping(path: Path, *, label: str | None = None) -> dict[str, Any]:
    label = label or str(path)
    if not path.is_file():
        raise PersonalKnowledgeValidationError(f"{label}: file does not exist")
    try:
        loaded = safe_load_yaml_path(path)
    except yaml.YAMLError as exc:
        raise PersonalKnowledgeValidationError(f"{label}: invalid YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PersonalKnowledgeValidationError(f"{label}: root must be a mapping")
    return loaded


def _load_schema(path: Path) -> dict[str, Any]:
    return _load_yaml_mapping(path, label=path.relative_to(ROOT).as_posix())


def _field_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _require_fields(doc: dict[str, Any], required: list[str], *, label: str) -> None:
    missing = [field for field in required if not _field_present(doc.get(field))]
    if missing:
        raise PersonalKnowledgeValidationError(
            f"{label}: missing required field(s): {', '.join(missing)}"
        )


def _require_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PersonalKnowledgeValidationError(f"{label}: must be a mapping")
    return value


def _require_non_empty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalKnowledgeValidationError(f"{label}: must be a non-empty string")
    return value.strip()


def _require_non_empty_list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise PersonalKnowledgeValidationError(f"{label}: must be a non-empty list")
    return value


def _require_schema_version(doc: dict[str, Any], *, label: str) -> None:
    if doc.get("schema_version") != 1:
        raise PersonalKnowledgeValidationError(f"{label}: schema_version must be 1")


def _require_enum(
    doc: dict[str, Any],
    key: str,
    allowed: list[str],
    *,
    label: str,
) -> None:
    value = doc.get(key)
    if value not in allowed:
        raise PersonalKnowledgeValidationError(
            f"{label}: {key} must be one of {allowed}, got {value!r}"
        )


def _require_date_like(value: Any, *, label: str) -> None:
    text = _require_non_empty_string(value, label=label)
    try:
        if "T" in text:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            date.fromisoformat(text)
    except ValueError as exc:
        raise PersonalKnowledgeValidationError(f"{label}: must be an ISO date or datetime") from exc


def _is_safe_relative_path(value: str) -> bool:
    if not value or value.startswith(("/", "~")) or "\\" in value:
        return False
    if WINDOWS_DRIVE_RE.match(value):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() in {"", "."}:
        return False
    return ".." not in path.parts


def _require_safe_relative_path(value: Any, *, label: str) -> PurePosixPath:
    text = _require_non_empty_string(value, label=label)
    if not _is_safe_relative_path(text):
        raise PersonalKnowledgeValidationError(f"{label}: must be a safe relative path")
    return PurePosixPath(text)


def _require_card_path(value: Any, *, label: str) -> None:
    path = _require_safe_relative_path(value, label=label)
    if path.suffix not in CARD_SUFFIXES:
        raise PersonalKnowledgeValidationError(f"{label}: must end in .yaml or .yml")
    if path.parts[: len(CARD_PATH_PREFIX.parts)] != CARD_PATH_PREFIX.parts:
        raise PersonalKnowledgeValidationError(
            f"{label}: must live under {CARD_PATH_PREFIX.as_posix()}/"
        )
    if len(path.parts) <= len(CARD_PATH_PREFIX.parts):
        raise PersonalKnowledgeValidationError(f"{label}: must name a card file")


def _validate_source_refs(value: Any, *, label: str) -> None:
    source_refs = _require_non_empty_list(value, label=label)
    for index, source_ref in enumerate(source_refs):
        ref_label = f"{label}[{index}]"
        ref = _require_mapping(source_ref, label=ref_label)
        if not any(_field_present(ref.get(key)) for key in ("repo", "path", "url")):
            raise PersonalKnowledgeValidationError(
                f"{ref_label}: must include at least one of repo, path, or url"
            )
        if "path" in ref and _field_present(ref.get("path")):
            _require_safe_relative_path(ref["path"], label=f"{ref_label}.path")
        for key in ("repo", "commit", "url"):
            if key in ref and not _field_present(ref.get(key)):
                raise PersonalKnowledgeValidationError(
                    f"{ref_label}.{key}: must be a non-empty string when present"
                )


def _validate_string_list(value: Any, *, label: str) -> None:
    items = _require_non_empty_list(value, label=label)
    for index, item in enumerate(items):
        _require_non_empty_string(item, label=f"{label}[{index}]")


def _validate_card_doc(doc: dict[str, Any], *, label: str) -> None:
    schema = _load_schema(CARD_SCHEMA_PATH)
    required = schema.get("required")
    enums = schema.get("enums")
    constraints = schema.get("constraints")
    if (
        not isinstance(required, list)
        or not isinstance(enums, dict)
        or not isinstance(
            constraints,
            dict,
        )
    ):
        raise PersonalKnowledgeValidationError(
            "schemas/personal-knowledge-card.schema.yaml: invalid schema contract"
        )

    _require_fields(doc, required, label=label)
    _require_schema_version(doc, label=label)
    for key in ("id", "title", "authority_home", "body"):
        _require_non_empty_string(doc.get(key), label=f"{label}: {key}")
    for key in ("type", "status", "privacy", "confidence"):
        allowed = enums.get(key)
        if not isinstance(allowed, list):
            raise PersonalKnowledgeValidationError(
                f"schemas/personal-knowledge-card.schema.yaml: missing enum {key}"
            )
        _require_enum(doc, key, allowed, label=label)

    _validate_string_list(doc.get("scope"), label=f"{label}: scope")
    _validate_source_refs(doc.get("source_refs"), label=f"{label}: source_refs")
    _validate_string_list(doc.get("allowed_use"), label=f"{label}: allowed_use")
    _validate_string_list(doc.get("forbidden_use"), label=f"{label}: forbidden_use")

    freshness = _require_mapping(doc.get("freshness"), label=f"{label}: freshness")
    _require_date_like(freshness.get("reviewed_at"), label=f"{label}: freshness.reviewed_at")
    if doc.get("status") == "active" and constraints.get("review_after_required_for_active"):
        _require_date_like(
            freshness.get("review_after"),
            label=f"{label}: freshness.review_after",
        )
    elif "review_after" in freshness and _field_present(freshness.get("review_after")):
        _require_date_like(
            freshness.get("review_after"),
            label=f"{label}: freshness.review_after",
        )

    body = _require_non_empty_string(doc.get("body"), label=f"{label}: body")
    body_min = int(constraints.get("body_min_chars", 0))
    body_max = int(constraints.get("body_max_chars", 0))
    if len(body) < body_min or (body_max and len(body) > body_max):
        raise PersonalKnowledgeValidationError(
            f"{label}: body length must be between {body_min} and {body_max} characters"
        )


def validate_card(path: Path) -> None:
    """Validate a single personal knowledge card YAML file."""
    doc = _load_yaml_mapping(path)
    _validate_card_doc(doc, label=str(path))


def _validate_candidate(
    candidate: Any,
    *,
    label: str,
    candidate_required: list[str],
    enums: dict[str, Any],
    has_operator_deploy_approval: bool,
) -> None:
    candidate_doc = _require_mapping(candidate, label=label)
    _require_fields(candidate_doc, candidate_required, label=label)
    _require_non_empty_string(candidate_doc.get("candidate_id"), label=f"{label}: candidate_id")
    decisions = enums.get("candidate_decision")
    safety_classifications = enums.get("safety_classification")
    privacy_values = enums.get("privacy")
    if (
        not isinstance(decisions, list)
        or not isinstance(
            safety_classifications,
            list,
        )
        or not isinstance(privacy_values, list)
    ):
        raise PersonalKnowledgeValidationError(
            "schemas/personal-knowledge-import-batch.schema.yaml: missing candidate enum contract"
        )
    _require_enum(candidate_doc, "decision", decisions, label=label)
    _require_non_empty_string(candidate_doc.get("rationale"), label=f"{label}: rationale")
    _require_enum(
        candidate_doc,
        "safety_classification",
        safety_classifications,
        label=label,
    )
    _require_enum(candidate_doc, "privacy", privacy_values, label=label)
    _require_non_empty_string(
        candidate_doc.get("authority_home"),
        label=f"{label}: authority_home",
    )
    freshness = _require_mapping(candidate_doc.get("freshness"), label=f"{label}: freshness")
    _require_date_like(freshness.get("reviewed_at"), label=f"{label}: freshness.reviewed_at")
    _require_date_like(freshness.get("review_after"), label=f"{label}: freshness.review_after")
    _validate_source_refs(candidate_doc.get("source_refs"), label=f"{label}: source_refs")

    card_path = candidate_doc.get("card_path")
    if _field_present(card_path):
        _require_card_path(card_path, label=f"{label}: card_path")

    decision = candidate_doc.get("decision")
    if decision == "approved":
        _require_card_path(card_path, label=f"{label}: card_path")
        if not has_operator_deploy_approval:
            raise PersonalKnowledgeValidationError(
                f"{label}: operator_review.approved must be true before deploy"
            )
    elif decision == "rejected":
        _require_non_empty_string(
            candidate_doc.get("rejection_reason"),
            label=f"{label}: rejection_reason",
        )

    proposed_card = candidate_doc.get("proposed_card")
    if proposed_card is not None:
        _validate_card_doc(
            _require_mapping(proposed_card, label=f"{label}: proposed_card"),
            label=f"{label}: proposed_card",
        )


def _validate_import_batch_doc(doc: dict[str, Any], *, label: str) -> None:
    schema = _load_schema(BATCH_SCHEMA_PATH)
    required = schema.get("required")
    candidate_required = schema.get("candidate_required")
    enums = schema.get("enums")
    if (
        not isinstance(required, list)
        or not isinstance(candidate_required, list)
        or not isinstance(
            enums,
            dict,
        )
    ):
        raise PersonalKnowledgeValidationError(
            "schemas/personal-knowledge-import-batch.schema.yaml: invalid schema contract"
        )

    _require_fields(doc, required, label=label)
    _require_schema_version(doc, label=label)
    _require_non_empty_string(doc.get("id"), label=f"{label}: id")
    _require_date_like(doc.get("created_at"), label=f"{label}: created_at")
    source_planes = enums.get("source_plane")
    decisions = enums.get("candidate_decision")
    if not isinstance(source_planes, list) or not isinstance(decisions, list):
        raise PersonalKnowledgeValidationError(
            "schemas/personal-knowledge-import-batch.schema.yaml: missing enum contract"
        )
    _require_enum(doc, "source_plane", source_planes, label=label)
    _validate_source_refs(doc.get("source_refs"), label=f"{label}: source_refs")

    operator_review = _require_mapping(
        doc.get("operator_review"),
        label=f"{label}: operator_review",
    )
    has_operator_deploy_approval = operator_review.get("approved") is True
    if has_operator_deploy_approval:
        if not any(
            _field_present(operator_review.get(key)) for key in ("approved_by", "reviewed_by")
        ):
            raise PersonalKnowledgeValidationError(
                f"{label}: operator_review must name approved_by or reviewed_by"
            )

    candidates = _require_non_empty_list(doc.get("candidates"), label=f"{label}: candidates")
    for index, candidate in enumerate(candidates):
        _validate_candidate(
            candidate,
            label=f"{label}: candidates[{index}]",
            candidate_required=candidate_required,
            enums=enums,
            has_operator_deploy_approval=has_operator_deploy_approval,
        )


def validate_import_batch(path: Path) -> None:
    """Validate a single personal knowledge import batch YAML file."""
    doc = _load_yaml_mapping(path)
    _validate_import_batch_doc(doc, label=str(path))


def _iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.rglob("*") if item.is_file())


def _iter_yaml_files(path: Path) -> list[Path]:
    return [item for item in _iter_files(path) if item.suffix in CARD_SUFFIXES]


def _rel_label(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def ensure_required_skeleton_dirs(root: Path) -> None:
    """Create only required empty skeleton directories for a restored checkout."""
    root = root.resolve()
    for rel_dir in REQUIRED_SKELETON_DIRS:
        (root / rel_dir).mkdir(parents=True, exist_ok=True)


def validate_root(
    root: Path,
    *,
    empty_skeleton: bool = False,
    init_skeleton_dirs: bool = False,
) -> None:
    """Validate a personal-root `.azoth/knowledge` skeleton and known artifacts."""
    errors: list[str] = []
    root = root.resolve()
    knowledge = root / KNOWLEDGE_DIR

    if init_skeleton_dirs:
        ensure_required_skeleton_dirs(root)

    for rel_dir in REQUIRED_SKELETON_DIRS:
        path = root / rel_dir
        if not path.is_dir():
            errors.append(f"{rel_dir.as_posix()}: required directory is missing")

    for rel_file in REQUIRED_SKELETON_FILES:
        path = root / rel_file
        if not path.is_file():
            errors.append(f"{rel_file.as_posix()}: required file is missing")
            continue
        if path.suffix in CARD_SUFFIXES:
            try:
                doc = _load_yaml_mapping(path, label=rel_file.as_posix())
            except PersonalKnowledgeValidationError as exc:
                errors.extend(exc.errors)
                continue
            if doc.get("schema_version") != 1:
                errors.append(f"{rel_file.as_posix()}: schema_version must be 1")

    card_files = _iter_files(root / CARD_DIR)
    batch_files = _iter_files(root / IMPORT_BATCH_DIR)
    if empty_skeleton:
        for path in [*card_files, *batch_files]:
            errors.append(
                f"{_rel_label(path, root)}: empty skeleton must not contain card or import batch files"
            )
    else:
        for path in _iter_yaml_files(root / CARD_DIR):
            try:
                validate_card(path)
            except PersonalKnowledgeValidationError as exc:
                errors.extend(exc.errors)
        for path in _iter_yaml_files(root / IMPORT_BATCH_DIR):
            try:
                validate_import_batch(path)
            except PersonalKnowledgeValidationError as exc:
                errors.extend(exc.errors)

    if not knowledge.is_dir():
        errors.append(f"{KNOWLEDGE_DIR.as_posix()}: required knowledge directory is missing")

    if errors:
        raise PersonalKnowledgeValidationError(errors)


def _collect_validation_errors(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []

    def run_validation(callable_, *call_args: Any, **call_kwargs: Any) -> None:
        try:
            callable_(*call_args, **call_kwargs)
        except PersonalKnowledgeValidationError as exc:
            errors.extend(exc.errors)

    if args.root is not None:
        run_validation(
            validate_root,
            args.root,
            empty_skeleton=args.empty_skeleton,
            init_skeleton_dirs=args.init_skeleton_dirs,
        )
    for card in args.card:
        run_validation(validate_card, card)
    for batch in args.batch:
        run_validation(validate_import_batch, batch)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate personal knowledge cards, import batches, and skeleton roots."
    )
    parser.add_argument("--root", type=Path, help="Personal root path to validate.")
    parser.add_argument("--card", action="append", type=Path, default=[], help="Card YAML path.")
    parser.add_argument(
        "--batch",
        action="append",
        type=Path,
        default=[],
        help="Import batch YAML path.",
    )
    parser.add_argument(
        "--empty-skeleton",
        action="store_true",
        help="Require the root knowledge skeleton to contain no cards or import batches.",
    )
    parser.add_argument(
        "--init-skeleton-dirs",
        action="store_true",
        help=(
            "Create missing required skeleton directories before validation. Intended "
            "for temporary restore drill checkouts where git cannot preserve empty dirs."
        ),
    )
    args = parser.parse_args(argv)

    if args.root is None and not args.card and not args.batch:
        parser.error("provide at least one of --root, --card, or --batch")

    errors = _collect_validation_errors(args)
    if errors:
        print("personal knowledge validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("personal knowledge validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
