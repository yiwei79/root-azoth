"""Persistent entropy session state for P5-002 (TRUST_CONTRACT §1)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class EntropyState:
    version: int = 1
    session_id: str = ""
    cumulative_entropy: float = 0.0
    modified_paths: list[str] = field(default_factory=list)
    created_paths: list[str] = field(default_factory=list)
    lines_total: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict) -> EntropyState:
        return cls(
            version=int(d.get("version", 1)),
            session_id=str(d.get("session_id", "")),
            cumulative_entropy=float(d.get("cumulative_entropy", 0.0)),
            modified_paths=list(d.get("modified_paths", [])),
            created_paths=list(d.get("created_paths", [])),
            lines_total=int(d.get("lines_total", 0)),
        )


def load_state(path: Path) -> EntropyState:
    if not path.is_file():
        return EntropyState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return EntropyState()
        return EntropyState.from_dict(data)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return EntropyState()


def save_state(path: Path, state: EntropyState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(state.to_json(), encoding="utf-8")
    tmp.replace(path)


def reset_if_session_changed(state: EntropyState, session_id: str) -> EntropyState:
    if state.session_id and state.session_id != session_id:
        return EntropyState(session_id=session_id)
    if not state.session_id:
        return EntropyState(session_id=session_id)
    return state
