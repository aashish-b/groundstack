from __future__ import annotations

from pathlib import Path

from groundstack.scanner import scan_repo


def test_scan_respects_gitignore_and_binary_skips(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    assert "ignored.log" in scan_result.skipped_paths

    mixed_scan = scan_repo(fixtures_root / "mixed_repo")
    assert "generated.json" in mixed_scan.skipped_paths
    assert "assets/logo.png" in mixed_scan.skipped_paths


def test_markdown_and_structured_blocks_are_preserved(fixtures_root: Path) -> None:
    mixed_scan = scan_repo(fixtures_root / "mixed_repo")
    docs_by_path = {document.path: document for document in mixed_scan.documents}

    readme = docs_by_path["README.md"]
    assert readme.blocks[0].title == "Mixed Repo"
    assert any(block.title == "Architecture" for block in readme.blocks)

    settings = docs_by_path["config/settings.toml"]
    assert {block.title for block in settings.blocks} == {"service", "ci"}

    app_json = docs_by_path["data/app.json"]
    assert {block.title for block in app_json.blocks} == {"featureFlags", "service"}
