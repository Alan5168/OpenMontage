#!/usr/bin/env python3
"""Prime-facing Goodcase ReferenceAtom retrieval and H3 semantic compiler.

This tool never sends a Goodcase clip to a provider. It retrieves structured
reference cards, verifies the reference-only rights boundary, and compiles
only transferable timing/performance/camera/environment/audio fields into the
local H3 Context-IR grammar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

OM_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ROOT = Path(
    os.environ.get(
        "OPENVIKING_CONTEXT_ROOT",
        r"C:\ContentStudio\context\openviking\content-studio",
    )
)
ATOM_ROOT = CONTEXT_ROOT / "goodcases" / "reference-atoms"
BRIDGE = OM_ROOT / "tools" / "om_context_bridge.py"
ATOM_ID_RE = re.compile(r"[a-z][a-z0-9_-]{2,127}")
ATOM_URI_RE = re.compile(r"/reference-atoms/([a-z][a-z0-9_-]{2,127})\.json")
NON_H3_RE = re.compile(
    r"\b(map|hud|chart|graph|timeline|year card|infographic|table)\b|"
    r"地图|图表|年份卡|信息图|数据表",
    re.IGNORECASE,
)
SCHEMA = "om-goodcase-reference-selection/v1"


class GoodcaseReferenceError(RuntimeError):
    """Invalid reference, retrieval failure, or rights-boundary failure."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def route_intent(query: str) -> dict[str, Any]:
    if NON_H3_RE.search(query or ""):
        return {
            "route": "REMOTION",
            "h3_reference_recommended": False,
            "reason": {
                "field": "deterministic_non_h3_router",
                "value": "map/HUD/chart/timeline content is not character-performance reference work",
            },
        }
    return {
        "route": "REFERENCE_ATOM_RETRIEVAL",
        "h3_reference_recommended": True,
    }


def _load_atom(atom_id: str) -> tuple[dict[str, Any], Path]:
    if not ATOM_ID_RE.fullmatch(atom_id):
        raise GoodcaseReferenceError(f"invalid atom id: {atom_id}")
    path = ATOM_ROOT / f"{atom_id}.json"
    if not path.is_file():
        raise GoodcaseReferenceError(f"atom not found: {path}")
    try:
        atom = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoodcaseReferenceError(f"invalid atom JSON: {path}: {exc}") from exc
    if atom.get("schema_version") != "om-goodcase-reference-atom/v1":
        raise GoodcaseReferenceError(f"unsupported atom schema: {path}")
    if atom.get("reference_atom_id") != atom_id:
        raise GoodcaseReferenceError(f"atom id mismatch: {path}")
    rights = (atom.get("source") or {}).get("rights")
    if rights != "reference_only_not_for_render":
        raise GoodcaseReferenceError(f"rights gate failed: {path}: {rights}")
    return atom, path


def search_reference_atoms(query: str, *, top_k: int = 3) -> dict[str, Any]:
    route = route_intent(query)
    if not route["h3_reference_recommended"]:
        return {
            "schema_version": SCHEMA,
            "query": query,
            **route,
            "candidates": [],
            "provider_call_made": False,
        }
    proc = subprocess.run(
        [
            sys.executable,
            str(BRIDGE),
            "search",
            query,
            "--scope",
            "goodcase",
            "--top-k",
            "20",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if proc.returncode != 0:
        raise GoodcaseReferenceError(
            f"OpenViking retrieval failed: {(proc.stdout or proc.stderr)[-1200:]}"
        )
    payload = json.loads(proc.stdout)
    best: dict[str, dict[str, Any]] = {}
    for hit in payload.get("results") or []:
        uri = str(hit.get("viking_uri") or "")
        match = ATOM_URI_RE.search(uri)
        if not match:
            continue
        atom_id = match.group(1)
        score = float(hit.get("score") or 0.0)
        if atom_id not in best or score > best[atom_id]["score"]:
            best[atom_id] = {"atom_id": atom_id, "score": score, "uri": uri}
    ranked = sorted(best.values(), key=lambda row: row["score"], reverse=True)[: max(1, top_k)]
    candidates = []
    for rank, row in enumerate(ranked, start=1):
        atom, path = _load_atom(row["atom_id"])
        candidates.append(
            {
                "rank": rank,
                **row,
                "atom_sha256": _sha256_file(path),
                "reason": {
                    "field": "retrieval_text",
                    "value": atom.get("retrieval_text"),
                },
                "executor_fit": atom.get("executor_fit"),
                "rights": atom["source"]["rights"],
            }
        )
    return {
        "schema_version": SCHEMA,
        "query": query,
        **route,
        "candidates": candidates,
        "trajectory": payload.get("trajectory"),
        "provider_call_made": False,
    }


def compile_h3_semantic_reference(
    atom_id: str,
    *,
    intent: str,
    duration_seconds: float = 5.0,
    first_frame: str = "<TARGET_FIRST_FRAME>",
) -> dict[str, Any]:
    atom, path = _load_atom(atom_id)
    source_duration = float(atom["source"]["duration_seconds"])
    target_duration = float(duration_seconds)
    if target_duration < 4 or target_duration > 15:
        raise GoodcaseReferenceError("H3 target duration must be 4-15 seconds")
    scale = target_duration / source_duration
    timeline_beats = []
    cameras = []
    for row in atom.get("observed_timeline") or []:
        action = "; ".join(
            value
            for value in (
                str(row.get("performance") or "").strip(),
                str(row.get("environment_motion") or "").strip(),
            )
            if value
        )
        t0 = round(float(row.get("t0") or 0) * scale, 3)
        t1 = round(float(row.get("t1") or 0) * scale, 3)
        camera = str(row.get("camera") or "locked-off static")
        cameras.append(camera)
        timeline_beats.append(
            f"From {t0:.3f}s to {t1:.3f}s: {action}"
        )
    # Atom rows are temporal beats inside one reference shot. Passing each row
    # as H3 `shots[]` makes the H3 compiler invent camera cuts and contradicts
    # locked-camera references.
    camera = (atom.get("transferable", {}).get("camera") or cameras or ["locked-off static"])[0]
    shots = [
        {
            "t0": 0.0,
            "t1": target_duration,
            "framing": "wide" if "environment" in intent.lower() or "环境" in intent else "medium",
            "action": " ".join(timeline_beats),
            "camera": camera,
        }
    ]
    avoid_map = {
        "character_identity": "copying the source character identity",
        "costume": "copying source costume",
        "historical_symbols": "copying source historical symbols",
        "dialogue": "copying source dialogue",
        "exact_composition": "recreating the source composition",
        "source_art_style": "imitating the source creator art style",
    }
    forbidden = atom.get("forbidden_transfer") or []
    spec = {
        "mode": "i2va",
        "style": "the target project's locked visual style",
        "overview": intent,
        "duration_seconds": target_duration,
        "camera": camera,
        "shots": shots,
        "audio": atom.get("transferable", {}).get("audio") or [],
        "avoid": [avoid_map[item] for item in forbidden if item in avoid_map],
        "first_frame": first_frame,
    }
    sys.path.insert(0, str(OM_ROOT))
    from lib.h3_context_ir import compile_h3_ir

    compiled = compile_h3_ir(spec)
    prompt = compiled["prompt"]
    source = atom["source"]
    forbidden_literals = [
        str(source.get("video_id") or ""),
        str(source.get("source_url") or ""),
        str(source.get("clip_pointer") or ""),
    ]
    violations = [literal for literal in forbidden_literals if literal and literal in prompt]
    return {
        "schema_version": "om-h3-goodcase-reference-compile/v1",
        "reference_mode": "semantic_only",
        "provider_call_made": False,
        "source_clip_sent_to_h3": False,
        "reference_atom_receipt": {
            "reference_atom_id": atom_id,
            "atom_sha256": _sha256_file(path),
            "source_sha256": source["source_sha256"],
            "clip_sha256": source["clip_sha256"],
            "rights": source["rights"],
        },
        "h3_spec": spec,
        "h3_compiled": compiled,
        "forbidden_transfer_violations": violations,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="om goodcase-reference")
    sub = parser.add_subparsers(dest="command", required=True)
    search_p = sub.add_parser("search")
    search_p.add_argument("--query", required=True)
    search_p.add_argument("--top-k", type=int, default=3)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--atom-id", required=True)
    compile_p.add_argument("--intent", required=True)
    compile_p.add_argument("--duration-seconds", type=float, default=5.0)
    compile_p.add_argument("--first-frame", default="<TARGET_FIRST_FRAME>")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "search":
            payload = search_reference_atoms(args.query, top_k=args.top_k)
        else:
            payload = compile_h3_semantic_reference(
                args.atom_id,
                intent=args.intent,
                duration_seconds=args.duration_seconds,
                first_frame=args.first_frame,
            )
    except (GoodcaseReferenceError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
