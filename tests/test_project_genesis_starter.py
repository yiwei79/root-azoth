from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import project_genesis_starter as starter  # noqa: E402


def _args(**overrides: str) -> object:
    defaults = {
        "domain": "music_production",
        "project_id": "music-production-lab",
        "project_name": "Music Production Lab",
        "project_path": "",
        "azoth_source": "public_install",
        "version_or_commit": "",
        "upgrade_path": "",
        "why_now": "",
        "desired_help": "",
        "prompt": "",
    }
    defaults.update(overrides)
    return type("Args", (), defaults)()


def test_profile_generates_valid_music_packet() -> None:
    packet = starter.build_profile(_args())

    assert packet["packet_type"] == "project_genesis_starter"
    assert packet["domain"] == "music_production"
    assert packet["cockpit_route"]["pointer_only"] is True
    assert starter.validate_packet(packet) == []

def test_validate_rejects_mutating_cockpit_route() -> None:
    packet = starter.build_profile(_args())
    packet["cockpit_route"]["pointer_only"] = False

    assert "cockpit_route.pointer_only must be true" in starter.validate_packet(packet)


def test_cli_validate_accepts_generated_packet(tmp_path: Path, capsys) -> None:
    packet_path = tmp_path / "packet.yaml"
    packet_path.write_text(yaml.safe_dump(starter.build_profile(_args()), sort_keys=False), encoding="utf-8")

    assert starter.main(["validate", str(packet_path)]) == 0
    assert "OK:" in capsys.readouterr().out
