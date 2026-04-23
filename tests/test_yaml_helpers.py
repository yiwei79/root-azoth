from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import yaml_helpers  # noqa: E402


def test_safe_loader_prefers_csafe_when_available() -> None:
    expected = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    assert yaml_helpers.YAML_SAFE_LOADER is expected


def test_safe_load_yaml_path_reads_utf8_mapping(tmp_path: Path) -> None:
    path = tmp_path / "sample.yaml"
    path.write_text("title: cafe\ncount: 2\n", encoding="utf-8")

    loaded = yaml_helpers.safe_load_yaml_path(path)

    assert loaded == {"title": "cafe", "count": 2}
