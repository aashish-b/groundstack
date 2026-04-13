from __future__ import annotations

import argparse
import sys

from .planner import build_evidence_bundle, build_traversal_plan
from .render import assemble_context_bundle
from .scanner import scan_repo
from .serialization import model_to_stable_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="groundstack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a repo into canonical documents and file summaries")
    scan_parser.add_argument("repo")

    map_parser = subparsers.add_parser("map", help="Emit repo map with graph links and symbols")
    map_parser.add_argument("repo")

    plan_parser = subparsers.add_parser("plan", help="Build a traversal plan for a task")
    plan_parser.add_argument("repo")
    plan_parser.add_argument("--task", required=True)
    plan_parser.add_argument("--mode", choices=["high_token", "low_token"], default="high_token")

    bundle_parser = subparsers.add_parser("bundle", help="Build a full context bundle for a task")
    bundle_parser.add_argument("repo")
    bundle_parser.add_argument("--task", required=True)
    bundle_parser.add_argument("--mode", choices=["high_token", "low_token"], default="high_token")

    dump_parser = subparsers.add_parser("dump", help="Print the model-ready prompt bundle")
    dump_parser.add_argument("repo")
    dump_parser.add_argument("--task", required=True)
    dump_parser.add_argument("--mode", choices=["high_token", "low_token"], default="high_token")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"scan", "map"}:
        scan_result = scan_repo(args.repo)
        print(model_to_stable_json(scan_result))
        return 0

    scan_result = scan_repo(args.repo)
    plan = build_traversal_plan(scan_result, args.task, mode=args.mode)
    if args.command == "plan":
        print(model_to_stable_json(plan))
        return 0

    evidence_bundle = build_evidence_bundle(scan_result, plan)
    context_bundle = assemble_context_bundle(scan_result, plan, evidence_bundle)
    if args.command == "bundle":
        print(model_to_stable_json(context_bundle))
        return 0
    if args.command == "dump":
        print(context_bundle.prompt)
        return 0

    raise AssertionError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
