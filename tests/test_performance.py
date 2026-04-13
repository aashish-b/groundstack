from __future__ import annotations

import time
from pathlib import Path

from groundstack.planner import build_evidence_bundle, build_traversal_plan
from groundstack.render import assemble_context_bundle
from groundstack.scanner import scan_repo


def test_scan_plan_and_bundle_stay_within_local_budget(fixtures_root: Path) -> None:
    repo = fixtures_root / "mixed_repo"

    scan_start = time.perf_counter()
    scan_result = scan_repo(repo)
    scan_elapsed = time.perf_counter() - scan_start

    plan_start = time.perf_counter()
    plan = build_traversal_plan(scan_result, "Explain the broken CI workflow and config layout", mode="low_token")
    evidence = build_evidence_bundle(scan_result, plan)
    assemble_context_bundle(scan_result, plan, evidence)
    plan_elapsed = time.perf_counter() - plan_start

    assert scan_elapsed < 5.0
    assert plan_elapsed < 2.0
