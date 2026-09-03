#!/usr/bin/env python3
"""OM Function: layout_geometry_check.

Exception diagnostic. Not the shot pipeline. Measure, do not approve,
do not generate. Run when a still or SEE result is spatially absurd.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.layout_geometry import draw_probe, layout_geometry_check, write_report  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--background", required=True, type=Path)
    p.add_argument("--footpoints", type=Path, help="JSON list of {name,zone,xy_frac}")
    p.add_argument("--actor-height-m", type=float, default=1.75)
    p.add_argument("--requested-height-px", type=float)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--probe-image", type=Path)
    p.add_argument("--no-moge", action="store_true")
    p.add_argument("--no-geocalib", action="store_true")
    args = p.parse_args()
    if args.footpoints:
        feet = json.loads(args.footpoints.read_text(encoding="utf-8"))
    else:
        feet = [
            {"name": "left_foreground", "zone": "left_foreground", "xy_frac": [0.22, 0.90]},
            {"name": "left_midground", "zone": "left_midground", "xy_frac": [0.30, 0.68]},
            {"name": "kitchen_background", "zone": "kitchen_background", "xy_frac": [0.42, 0.52]},
        ]
    report = layout_geometry_check(
        args.background,
        feet,
        actor_height_m=args.actor_height_m,
        requested_height_px=args.requested_height_px,
        use_moge=not args.no_moge,
        use_geocalib=not args.no_geocalib,
    )
    write_report(args.out, report)
    if args.probe_image:
        draw_probe(args.background, report, args.probe_image)
        report["probe_image"] = str(args.probe_image)
        write_report(args.out, report)
    print(json.dumps({
        "ok": True,
        "horizon_y": report["horizon_y"],
        "confidence": report["geometry_confidence"],
        "horizon_source": (report.get("backends") or {}).get("horizon_source"),
        "footpoints": [
            {
                "name": row["name"],
                "height_px": row.get("expected_actor_height_px"),
                "consistency": row.get("geometry_consistency"),
            }
            for row in report["footpoints"]
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
