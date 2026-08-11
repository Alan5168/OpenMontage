"""Validate a canonical scene_plan against the seven-column presentation contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.sceneplan_contract import validate_seven_column_scene_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_plan", type=Path)
    parser.add_argument("--require-decisions", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.scene_plan.read_text(encoding="utf-8"))
    validate_seven_column_scene_plan(plan, require_review_decisions=args.require_decisions)
    print(json.dumps({"status": "PASS", "scene_count": len(plan["scenes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
