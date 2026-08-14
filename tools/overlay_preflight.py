#!/usr/bin/env python3
"""Windows Pi/Trae: run before compose. Exit 2 blocks the 160s render. No model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.overlay_preflight import (  # noqa: E402
    OverlayPreflightError,
    format_block_error,
    run_overlay_preflight,
    write_report,
)


def _load(path: Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edit-decisions", required=True, type=Path)
    parser.add_argument("--scene-plan", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--patched-edit-decisions", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    args = parser.parse_args()
    report = run_overlay_preflight(
        _load(args.edit_decisions),
        _load(args.scene_plan),
        canvas=(args.width, args.height),
    )
    write_report(args.out, report)
    if args.patched_edit_decisions:
        args.patched_edit_decisions.parent.mkdir(parents=True, exist_ok=True)
        args.patched_edit_decisions.write_text(
            json.dumps(report["patched_edit_decisions"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if report["ok"]:
        print(json.dumps({"ok": True, "jobs": len(report["jobs"])}))
        return 0
    print(format_block_error(report), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OverlayPreflightError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
