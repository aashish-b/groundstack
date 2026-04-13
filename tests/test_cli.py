from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _cli() -> str:
    return str(Path(sys.prefix).resolve() / "bin" / "groundstack")


def test_cli_help() -> None:
    result = subprocess.run([_cli(), "--help"], capture_output=True, text=True, check=True)
    assert "scan" in result.stdout
    assert "bundle" in result.stdout


def test_cli_bundle_matches_snapshot(fixtures_root: Path) -> None:
    repo = fixtures_root / "python_service"
    result = subprocess.run(
        [_cli(), "bundle", str(repo), "--task", "Fix the auth token refresh bug"],
        capture_output=True,
        text=True,
        check=True,
    )
    snapshot = (Path(__file__).parent / "snapshots" / "python_service_bundle.json").read_text(encoding="utf-8")
    assert json.loads(result.stdout) == json.loads(snapshot)


def test_cli_dump_matches_snapshot(fixtures_root: Path) -> None:
    repo = fixtures_root / "python_service"
    result = subprocess.run(
        [_cli(), "dump", str(repo), "--task", "Fix the auth token refresh bug"],
        capture_output=True,
        text=True,
        check=True,
    )
    snapshot = (Path(__file__).parent / "snapshots" / "python_service_prompt.txt").read_text(encoding="utf-8")
    assert result.stdout.strip() == snapshot.strip()
