from __future__ import annotations

from pathlib import Path

from groundstack.planner import build_evidence_bundle, build_traversal_plan
from groundstack.render import assemble_context_bundle
from groundstack.scanner import scan_repo
from groundstack.serialization import model_to_stable_json


def test_context_bundle_shape_and_stability(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    plan = build_traversal_plan(scan_result, "Fix the auth token refresh bug", mode="high_token")
    evidence = build_evidence_bundle(scan_result, plan)
    bundle_one = assemble_context_bundle(scan_result, plan, evidence)
    bundle_two = assemble_context_bundle(scan_result, plan, evidence)

    section_names = [section.name for section in bundle_one.rendered_sections]
    assert section_names == [
        "instructions",
        "task",
        "repo_map",
        "selected_evidence",
        "constraints",
        "output_contract",
    ]
    assert bundle_one.citations
    assert bundle_one.stable_prefix == bundle_two.stable_prefix
    assert bundle_one.cache_record.prefix_hash == bundle_two.cache_record.prefix_hash


def test_rendered_bundle_matches_snapshot(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    plan = build_traversal_plan(scan_result, "Fix the auth token refresh bug", mode="high_token")
    evidence = build_evidence_bundle(scan_result, plan)
    bundle = assemble_context_bundle(scan_result, plan, evidence)

    json_snapshot = (Path(__file__).parent / "snapshots" / "python_service_bundle.json").read_text(encoding="utf-8")
    prompt_snapshot = (Path(__file__).parent / "snapshots" / "python_service_prompt.txt").read_text(encoding="utf-8")

    assert model_to_stable_json(bundle).strip() == json_snapshot.strip()
    assert bundle.prompt.strip() == prompt_snapshot.strip()
