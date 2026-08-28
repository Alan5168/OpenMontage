#!/usr/bin/env python3
"""Inspect or compile the Windows H3 capability manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.h3_capabilities import capability_health, compile_dispatch, load_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("capability_id")
    doctor.add_argument("--model-root", required=True)
    doctor.add_argument("--runtime-root")
    doctor.add_argument("--verify-hashes", action="store_true")

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--capability-id")
    compile_parser.add_argument("--cut-id", required=True)
    compile_parser.add_argument("--rights", required=True)
    compile_parser.add_argument("--adapter-gate-pass", action="store_true")
    compile_parser.add_argument("--final-asset", action="store_true")
    compile_parser.add_argument("--runtime-root")

    args = parser.parse_args()
    if args.command == "list":
        payload = load_manifest()
        result = {
            key: {
                "status": value["status"],
                "role": value["role"],
                "explicit_only": value["explicit_only"],
                "previs_only": value["previs_only"],
            }
            for key, value in payload["capabilities"].items()
        }
    elif args.command == "doctor":
        result = capability_health(
            args.capability_id,
            model_root=args.model_root,
            runtime_root=args.runtime_root,
            verify_hashes=args.verify_hashes,
        )
    else:
        route = {
            "cut_id": args.cut_id,
            "dispatch_class": "I2V_HARD",
            "h3_allowed": True,
        }
        result = compile_dispatch(
            route,
            capability_id=args.capability_id,
            reference_provenance={"rights": args.rights},
            adapter_gate_pass=args.adapter_gate_pass,
            final_asset=args.final_asset,
            runtime_root=args.runtime_root,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
