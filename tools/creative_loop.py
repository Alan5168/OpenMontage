#!/usr/bin/env python3
"""CLI for Creative Loop v0.1. Does not retrieve casebook events."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.creative_loop import (  # noqa: E402
    CreativeLoopError,
    extract_frames,
    retrieve_learning_events,
    see_mp4,
    validate_critique_grounding,
    write_learning_event,
)
from lib.temporal_motion import analyze_temporal_motion, write_temporal_motion_report  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    extract = sub.add_parser("extract-frames")
    extract.add_argument("--mp4", required=True, type=Path)
    extract.add_argument("--out", required=True, type=Path)
    extract.add_argument("--anchors", default="", help="comma-separated seconds")

    temporal = sub.add_parser("temporal-report")
    temporal.add_argument("--mp4", required=True, type=Path)
    temporal.add_argument("--out", required=True, type=Path)

    see = sub.add_parser("see")
    see.add_argument("--mp4", required=True, type=Path)
    see.add_argument("--out", required=True, type=Path)
    see.add_argument("--anchors", default="", help="comma-separated seconds")
    see.add_argument("--cuts", type=Path, help="LIMITED grammar cuts JSON")

    critique = sub.add_parser("validate-critique")
    critique.add_argument("--critique", required=True, type=Path)
    critique.add_argument("--frames", required=True, type=Path)
    critique.add_argument("--intent", required=True, type=Path)
    critique.add_argument("--temporal", required=True, type=Path)
    critique.add_argument("--eligibility", required=True, type=Path)

    learn = sub.add_parser("record-learning-event")
    learn.add_argument("--event", required=True, type=Path)
    learn.add_argument("--out", required=True, type=Path)

    sub.add_parser("retrieve-learning-events")

    args = parser.parse_args()
    try:
        if args.cmd == "extract-frames":
            anchors = [float(x) for x in args.anchors.split(",") if x.strip()]
            packet = extract_frames(args.mp4, args.out, anchors=anchors)
            (args.out / "frame_packet.json").write_text(
                json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({"frames": len(packet["frames"]), "sha256": packet["source_sha256"]}))
            return 0
        if args.cmd == "temporal-report":
            report = analyze_temporal_motion(args.mp4)
            write_temporal_motion_report(args.out, report)
            print(json.dumps({
                "duration_seconds": report["duration_seconds"],
                "scene_changes": report["scene_changes"],
                "motion_coverage": report["motion_coverage"],
                "longest_static_run": report["longest_static_run"],
                "motion_type": report["motion_type"],
            }))
            return 0
        if args.cmd == "see":
            anchors = [float(x) for x in args.anchors.split(",") if x.strip()]
            cuts = None
            if args.cuts:
                blob = _load(args.cuts)
                cuts = blob.get("cuts") if isinstance(blob, dict) else blob
            result = see_mp4(args.mp4, args.out, anchors=anchors, cuts=cuts)
            report = result["temporal_motion_report"]
            grammar = result["limited_grammar_report"]
            print(json.dumps({
                "frames": len(result["frame_packet"]["frames"]),
                "sha256": result["frame_packet"]["source_sha256"],
                "duration_seconds": report["duration_seconds"],
                "motion_coverage": report["motion_coverage"],
                "longest_static_run": report["longest_static_run"],
                "motion_type": report["motion_type"],
                "limited_grammar_ok": None if grammar is None else grammar["ok"],
                "limited_grammar_classes": [] if grammar is None else [
                    row["failure_class"] for row in grammar["findings"]
                ],
                "director_review_eligible": (result.get("scene_eligibility") or {}).get("director_review_eligible"),
                "eligibility_blockers": (result.get("scene_eligibility") or {}).get("blockers"),
            }))
            eligible = (result.get("scene_eligibility") or {}).get("director_review_eligible")
            if eligible is False:
                return 3
            return 0 if grammar is None or grammar["ok"] else 2
        if args.cmd == "validate-critique":
            validate_critique_grounding(
                _load(args.critique),
                _load(args.frames),
                _load(args.intent),
                temporal_report=_load(args.temporal),
                eligibility_report=_load(args.eligibility) if getattr(args, "eligibility", None) else None,
            )
            print("OK")
            return 0
        if args.cmd == "record-learning-event":
            write_learning_event(args.out, _load(args.event))
            print("OK")
            return 0
        retrieve_learning_events()
        return 1
    except (CreativeLoopError, Exception) as exc:
        from lib.temporal_motion import TemporalMotionError
        if isinstance(exc, (CreativeLoopError, TemporalMotionError)):
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
