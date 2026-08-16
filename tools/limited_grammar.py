#!/usr/bin/env python3
"""LIMITED grammar preflight. Measurement + contract. No model. Does not render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.limited_grammar import evaluate_limited_grammar  # noqa: E402
from schemas.artifacts import validate_artifact  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuts", required=True, type=Path)
    parser.add_argument("--temporal-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    cuts_blob = json.loads(args.cuts.read_text(encoding="utf-8"))
    cuts = cuts_blob.get("cuts") if isinstance(cuts_blob, dict) else cuts_blob
    report = json.loads(args.temporal_report.read_text(encoding="utf-8"))
    payload = evaluate_limited_grammar(list(cuts or []), report)
    validate_artifact("limited_grammar_report", payload)
    plan = payload.get("repair_plan")
    if plan:
        validate_artifact("repair_plan", plan)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": payload["ok"],
        "finding_count": payload["finding_count"],
        "classes": [row["failure_class"] for row in payload["findings"]],
    }))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
