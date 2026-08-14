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
    validate_critique_grounding,
    write_learning_event,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    extract = sub.add_parser("extract-frames")
    extract.add_argument("--mp4", required=True, type=Path)
    extract.add_argument("--out", required=True, type=Path)
    extract.add_argument("--anchors", default="", help="comma-separated seconds")

    critique = sub.add_parser("validate-critique")
    critique.add_argument("--critique", required=True, type=Path)
    critique.add_argument("--frames", required=True, type=Path)
    critique.add_argument("--intent", required=True, type=Path)

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
        if args.cmd == "validate-critique":
            validate_critique_grounding(_load(args.critique), _load(args.frames), _load(args.intent))
            print("OK")
            return 0
        if args.cmd == "record-learning-event":
            write_learning_event(args.out, _load(args.event))
            print("OK")
            return 0
        retrieve_learning_events()
        return 1
    except CreativeLoopError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
