from __future__ import annotations

from pathlib import Path

from groundstack.planner import build_traversal_plan
from groundstack.scanner import scan_repo


def test_auth_task_ranks_expected_file_high_and_low(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    high_plan = build_traversal_plan(scan_result, "Fix the auth token refresh bug", mode="high_token")
    low_plan = build_traversal_plan(scan_result, "Fix the auth token refresh bug", mode="low_token")

    assert "service/auth.py" in [item.path for item in high_plan.candidate_files[:5]]
    assert "service/auth.py" in [item.path for item in low_plan.candidate_files[:3]]
    assert any(symbol.name == "refresh_token" for symbol in high_plan.candidate_symbols[:5])


def test_ci_task_ranks_workflow_file(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "mixed_repo")
    plan = build_traversal_plan(scan_result, "Explain the broken CI workflow and config layout", mode="low_token")

    top_paths = [item.path for item in plan.candidate_files[:3]]
    assert ".github/workflows/ci.yml" in top_paths


def test_architecture_request_surfaces_docs(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "mixed_repo")
    plan = build_traversal_plan(scan_result, "Explain the repository architecture", mode="high_token")
    assert "README.md" in [item.path for item in plan.candidate_files[:5]]
