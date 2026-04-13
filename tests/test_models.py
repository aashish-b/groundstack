from __future__ import annotations

import json
from pathlib import Path

from groundstack.models import ContextBundle, EvidenceBundle, ScanResult, TraversalPlan
from groundstack.planner import build_evidence_bundle, build_traversal_plan
from groundstack.render import assemble_context_bundle
from groundstack.scanner import scan_repo
from groundstack.serialization import model_to_stable_json


def test_public_models_round_trip(fixtures_root: Path) -> None:
    scan_result = scan_repo(fixtures_root / "python_service")
    traversal_plan = build_traversal_plan(scan_result, "Fix the auth token refresh bug", mode="high_token")
    evidence_bundle = build_evidence_bundle(scan_result, traversal_plan)
    context_bundle = assemble_context_bundle(scan_result, traversal_plan, evidence_bundle)

    round_trip_scan = ScanResult.model_validate_json(model_to_stable_json(scan_result))
    round_trip_plan = TraversalPlan.model_validate_json(model_to_stable_json(traversal_plan))
    round_trip_evidence = EvidenceBundle.model_validate_json(model_to_stable_json(evidence_bundle))
    round_trip_context = ContextBundle.model_validate_json(model_to_stable_json(context_bundle))

    assert round_trip_scan == scan_result
    assert round_trip_plan == traversal_plan
    assert round_trip_evidence == evidence_bundle
    assert round_trip_context == context_bundle


def test_schema_snapshot() -> None:
    snapshot_path = Path(__file__).parent / "snapshots" / "public_model_schemas.json"
    snapshot = snapshot_path.read_text(encoding="utf-8")
    payload = {
        "ScanResult": ScanResult.model_json_schema(),
        "TraversalPlan": TraversalPlan.model_json_schema(),
        "EvidenceBundle": EvidenceBundle.model_json_schema(),
        "ContextBundle": ContextBundle.model_json_schema(),
    }
    assert json.loads(snapshot) == payload
