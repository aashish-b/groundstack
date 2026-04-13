from __future__ import annotations

from pathlib import Path

from groundstack.scanner import scan_repo


def test_python_symbol_extraction(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    files = {file_summary.path: file_summary for file_summary in scan_result.files}
    auth_file = files["service/auth.py"]

    names = {symbol.name for symbol in auth_file.symbols}
    assert {"should_refresh", "refresh_token", "AuthService", "AuthService.ensure_token"} <= names
    refresh_symbol = next(symbol for symbol in auth_file.symbols if symbol.name == "refresh_token")
    assert refresh_symbol.start_line < refresh_symbol.end_line


def test_typescript_symbol_extraction(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "js_app")
    files = {file_summary.path: file_summary for file_summary in scan_result.files}
    auth_file = files["src/auth.ts"]

    names = {symbol.name for symbol in auth_file.symbols}
    assert {"Session", "refreshToken"} <= names
    assert "./auth" in files["src/api.ts"].imports


def test_fallback_extractor_stays_conservative(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "mixed_repo")
    files = {file_summary.path: file_summary for file_summary in scan_result.files}
    deploy_file = files["scripts/deploy.sh"]

    assert [symbol.name for symbol in deploy_file.symbols] == ["deploy"]
    assert all(symbol.kind in {"function", "symbol"} for symbol in deploy_file.symbols)
