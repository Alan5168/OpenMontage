"""Creative Loop v0.1 — visual cognition contracts.

Graph stages live in the pipeline YAML. This module only:
  extract frames from the actual mp4
  reject generic / ungrounded critique
  keep intent contracts short
  land LEARNING_EVENT without retrieving it
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from schemas.artifacts import validate_artifact

GENERIC_BANS = (
    "节奏可以更紧凑",
    "视觉可以更丰富",
    "画面可以更好",
    "整体不错",
    "看起来还行",
    "render successful",
    "render_success",
)


class CreativeLoopError(ValueError):
    """Contract failure for SEE / critique / repair."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_mp4(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration:format=duration",
        "-of", "json",
        str(path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    data = json.loads(raw)
    stream = (data.get("streams") or [{}])[0]
    duration = float(stream.get("duration") or data.get("format", {}).get("duration") or 0)
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration_seconds": duration,
    }


def _has_black_frame(path: Path) -> bool:
    cmd = [
        "ffmpeg", "-hide_banner", "-i", str(path),
        "-vf", "blackdetect=d=0.2:pic_th=0.98",
        "-an", "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return "black_start" in (result.stderr or "")


def _extract_one_frame(
    ffmpeg: str,
    mp4: Path,
    out_dir: Path,
    *,
    index: int,
    stamp: float | None,
    kind: str,
    sseof: bool = False,
) -> dict[str, Any] | None:
    if sseof:
        label = "sseof"
        dest = out_dir / f"f{index:02d}_t{label}.png"
        cmd = [
            ffmpeg, "-y", "-sseof", "-0.08", "-i", str(mp4),
            "-frames:v", "1", "-q:v", "2", str(dest),
        ]
    else:
        assert stamp is not None
        dest = out_dir / f"f{index:02d}_t{stamp:.3f}.png"
        cmd = [
            ffmpeg, "-y", "-ss", f"{stamp:.3f}", "-i", str(mp4),
            "-frames:v", "1", "-q:v", "2", str(dest),
        ]
    subprocess.run(cmd, check=False, capture_output=True)
    if not dest.is_file() or dest.stat().st_size < 32:
        if dest.is_file():
            dest.unlink()
        return None
    t_value = float(stamp) if stamp is not None else probe_mp4(mp4)["duration_seconds"] - 0.08
    return {
        "id": f"f{index:02d}",
        "t": round(max(0.0, t_value), 3),
        "path": str(dest),
        "sha256": sha256_file(dest),
        "kind": kind,
    }


def extract_frames(
    mp4: Path,
    out_dir: Path,
    *,
    interval: float = 4.0,
    anchors: list[float] | None = None,
) -> dict[str, Any]:
    if not mp4.is_file():
        raise CreativeLoopError(f"mp4 not found: {mp4}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise CreativeLoopError("ffmpeg is required to SEE the artifact")
    probe = probe_mp4(mp4)
    duration = probe["duration_seconds"]
    times = [0.0]
    t = interval
    while t < duration:
        times.append(round(t, 3))
        t += interval
    last = round(max(0.0, duration - (1.0 / 24.0)), 3)
    if last > 0:
        times.append(last)
    if duration > 0 and len(set(times)) < 3:
        times.append(round(duration * 0.5, 3))
    times = sorted(set(times))
    for anchor in anchors or []:
        if 0 <= float(anchor) <= max(0.0, duration - 0.05):
            times.append(round(float(anchor), 3))
    last = round(max(0.0, duration - 0.08), 3)
    times = sorted({t for t in times if 0.0 <= t <= last})
    if duration > 0:
        mid = round(duration * 0.5, 3)
        if mid not in times and 0.0 < mid <= last:
            times.append(mid)
            times = sorted(set(times))
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []
    for index, stamp in enumerate(times):
        kind = "t0" if stamp == 0 else ("anchor" if anchors and stamp in anchors else "interval")
        grabbed = _extract_one_frame(ffmpeg, mp4, out_dir, index=index, stamp=stamp, kind=kind)
        if grabbed is None:
            if stamp <= 0.0:
                raise CreativeLoopError(f"frame extract produced empty file at t={stamp}")
            continue
        frames.append(grabbed)
    if len(frames) < 3 and duration > 0:
        for stamp, kind in (
            (round(max(0.0, duration - 0.15), 3), "interval"),
            (round(duration * 0.5, 3), "interval"),
        ):
            if any(abs(row["t"] - stamp) < 0.02 for row in frames):
                continue
            grabbed = _extract_one_frame(
                ffmpeg, mp4, out_dir, index=len(frames), stamp=stamp, kind=kind
            )
            if grabbed is not None:
                frames.append(grabbed)
            if len(frames) >= 3:
                break
    if len(frames) < 3:
        grabbed = _extract_one_frame(
            ffmpeg, mp4, out_dir, index=len(frames), stamp=None, kind="interval", sseof=True
        )
        if grabbed is not None:
            frames.append(grabbed)
    if len(frames) < 3:
        raise CreativeLoopError("frame extract produced no readable stills")
    frames.sort(key=lambda row: float(row["t"]))
    for index, row in enumerate(frames):
        row["id"] = f"f{index:02d}"
    packet = {
        "version": "frame-packet/v0.1",
        "source_mp4": str(mp4),
        "source_sha256": sha256_file(mp4),
        "duration_seconds": duration,
        "frames": frames,
        "machine_checks": {
            "probe_ok": duration > 0 and probe["width"] > 0,
            "black_frame": _has_black_frame(mp4),
            "duration_seconds": duration,
            "width": probe["width"],
            "height": probe["height"],
            "issues": [],
        },
    }
    if not packet["machine_checks"]["probe_ok"]:
        packet["machine_checks"]["issues"].append("ffprobe failed")
    validate_artifact("frame_packet", packet)
    return packet


def _is_generic(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.lower())
    for banned in GENERIC_BANS:
        if re.sub(r"\s+", "", banned.lower()) in compact:
            return True
    return False


def see_mp4(
    mp4: Path,
    out_dir: Path,
    *,
    interval: float = 4.0,
    anchors: list[float] | None = None,
    cuts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Frames plus temporal measurement. Sparse keyframes alone are not SEE."""
    from lib.temporal_motion import analyze_temporal_motion, write_temporal_motion_report

    out_dir = Path(out_dir)
    packet = extract_frames(mp4, out_dir, interval=interval, anchors=anchors)
    (out_dir / "frame_packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = analyze_temporal_motion(mp4, work_dir=out_dir / "temporal_samples")
    write_temporal_motion_report(out_dir / "temporal_motion_report.json", report)
    result: dict[str, Any] = {
        "frame_packet": packet,
        "temporal_motion_report": report,
        "limited_grammar_report": None,
    }
    if cuts is not None:
        from lib.limited_grammar import evaluate_limited_grammar

        grammar = evaluate_limited_grammar(list(cuts), report)
        validate_artifact("limited_grammar_report", grammar)
        plan = grammar.get("repair_plan")
        if plan:
            validate_artifact("repair_plan", plan)
        (out_dir / "limited_grammar_report.json").write_text(
            json.dumps(grammar, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result["limited_grammar_report"] = grammar
    from lib.audio_event_map import probe_audio_map
    from lib.scene_eligibility import evaluate_scene_eligibility

    audio_map = probe_audio_map(mp4)
    (out_dir / "audio_event_map.json").write_text(
        json.dumps(audio_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    declaration = None
    if cuts:
        declaration = {
            "placeholder_composite": any(c.get("placeholder_composite") for c in cuts if isinstance(c, dict)),
        }
    eligibility = evaluate_scene_eligibility(
        duration_seconds=float(report.get("duration_seconds") or packet.get("duration_seconds") or 0),
        cuts=list(cuts or []),
        temporal_report=report,
        audio_map=audio_map,
        declaration=declaration,
    )
    validate_artifact("scene_eligibility", eligibility)
    (out_dir / "scene_eligibility.json").write_text(
        json.dumps(eligibility, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result["audio_event_map"] = audio_map
    result["scene_eligibility"] = eligibility
    return result


def validate_critique_grounding(
    critique: dict[str, Any],
    frame_packet: dict[str, Any],
    intent: dict[str, Any],
    temporal_report: dict[str, Any] | None = None,
    eligibility_report: dict[str, Any] | None = None,
) -> None:
    from lib.temporal_motion import assert_temporal_see
    from lib.scene_eligibility import assert_director_review_eligible

    assert_temporal_see(temporal_report)
    assert_director_review_eligible(eligibility_report)
    if temporal_report["source_sha256"] != frame_packet["source_sha256"]:
        raise CreativeLoopError("temporal report source_sha256 does not match the seen mp4")
    validate_artifact("editorial_critique", critique)
    validate_artifact("frame_packet", frame_packet)
    validate_artifact("creative_intent_contract", intent)
    known_frames = {frame["id"] for frame in frame_packet["frames"]}
    known_intents = {segment["id"] for segment in intent["segments"]}
    if critique["source_sha256"] != frame_packet["source_sha256"]:
        raise CreativeLoopError("critique source_sha256 does not match the seen mp4")
    for finding in critique["findings"]:
        missing = [fid for fid in finding["frame_ids"] if fid not in known_frames]
        if missing:
            raise CreativeLoopError(f"finding cites unknown frames: {missing}")
        if finding["intent_id"] not in known_intents:
            raise CreativeLoopError(f"finding cites unknown intent {finding['intent_id']}")
        blob = finding["evidence"] + " " + finding["why_it_fails_intent"]
        if _is_generic(blob):
            raise CreativeLoopError("generic critique is not Visual Cognition")
        if not re.search(r"\d+(\.\d+)?s|t\s*=|\d{1,2}:\d{2}", blob):
            raise CreativeLoopError("evidence must name a timestamp")


def assert_hash_changed(before: str, after: str) -> None:
    if not before or not after or before == after:
        raise CreativeLoopError("rerender hash must differ from draft hash")


def write_learning_event(path: Path, event: dict[str, Any]) -> None:
    if event.get("auto_retrieve") is not False:
        raise CreativeLoopError("v0.1 LEARNING_EVENT must set auto_retrieve=false")
    validate_artifact("learning_event", event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def retrieve_learning_events(*_args: Any, **_kwargs: Any) -> None:
    raise CreativeLoopError("v0.1 records LEARNING_EVENT only; retrieval is not in this loop")
