"""OM Temporal Motion Report — measurement, not taste.

Answers: how did time actually move on this mp4?
Does not PASS/FAIL a hold. STATIC_HOLD is a fact, not a defect.

Sparse keyframe SEE is not this. This samples densely (default 8 fps)
and classifies each shot segment.

LIMITED is temporal grammar, not `ffmpeg -loop 1`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from lib.creative_loop import probe_mp4, sha256_file

REPORT_VERSION = "temporal-motion-report/v0.1"
SAMPLE_FPS = 8.0
# Mean-abs-diff on 8-bit gray, 0–255. Looped stills sit near 0 (encoder dust).
STATIC_MAD = 0.85
CUT_MAD = 16.0
LOCAL_MAD = 4.0
CAMERA_MAD = 10.0

MOTION_TYPES = (
    "STATIC_HOLD",
    "CAMERA_ONLY",
    "LIMITED_LOCAL_MOTION",
    "FULL_MOTION",
)


class TemporalMotionError(ValueError):
    """Could not measure temporal behavior."""


def analyze_temporal_motion(
    mp4: Path,
    *,
    sample_fps: float = SAMPLE_FPS,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    src = Path(mp4)
    if not src.is_file():
        raise TemporalMotionError(f"mp4 not found: {src}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise TemporalMotionError("ffmpeg is required for temporal motion analysis")
    probe = probe_mp4(src)
    duration = float(probe["duration_seconds"] or 0)
    if duration <= 0:
        raise TemporalMotionError("ffprobe duration is 0")

    samples = _sample_gray(ffmpeg, src, sample_fps=sample_fps, work_dir=work_dir)
    if len(samples) < 2:
        raise TemporalMotionError("need at least two sampled frames")

    mads = [_mad(samples[i - 1], samples[i]) for i in range(1, len(samples))]
    dt = duration / len(mads)
    times = [round((i + 1) * dt, 3) for i in range(len(mads))]

    cut_idx = [i for i, v in enumerate(mads) if v >= CUT_MAD]
    bounds = [0.0] + [times[i] for i in cut_idx] + [round(duration, 3)]
    segments: list[dict[str, Any]] = []
    for i in range(len(bounds) - 1):
        t0, t1 = bounds[i], bounds[i + 1]
        lo = 0 if i == 0 else cut_idx[i - 1] + 1
        hi = cut_idx[i] if i < len(cut_idx) else len(mads)
        window = mads[lo:hi] or [0.0]
        segments.append(_segment(t0, t1, window))

    moving = sum(1 for v in mads if v >= STATIC_MAD)
    longest = _longest_static_run(mads, dt)
    report = {
        "version": REPORT_VERSION,
        "source_mp4": str(src),
        "source_sha256": sha256_file(src),
        "duration_seconds": round(duration, 3),
        "sample_fps": sample_fps,
        "sample_count": len(samples),
        "shot_segments": [
            {"t_start": row["t_start"], "t_end": row["t_end"]} for row in segments
        ],
        "motion_coverage": round(moving / max(len(mads), 1), 4),
        "longest_static_run": round(longest, 3),
        "motion_type": {f"segment_{i+1}": row["motion_type"] for i, row in enumerate(segments)},
        "segments": segments,
        "camera_motion": "none" if all(s["motion_type"] != "CAMERA_ONLY" for s in segments) else "present",
        "local_character_motion": "none"
        if all(s["motion_type"] not in {"LIMITED_LOCAL_MOTION", "FULL_MOTION"} for s in segments)
        else "present",
        "mouth_motion": "unmeasured",
        "blink_detected": False,
        "scene_changes": len(cut_idx),
        "judgment": "measurement_only",
        "note": "STATIC_HOLD is a fact, not a fail. Prime decides if that grammar fits the shot.",
    }
    return report


def write_temporal_motion_report(path: Path, report: dict[str, Any]) -> Path:
    from schemas.artifacts import validate_artifact

    validate_artifact("temporal_motion_report", report)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def assert_temporal_see(report: dict[str, Any] | None) -> None:
    """High-cost visual reasoning is illegal without this measurement."""
    from lib.creative_loop import CreativeLoopError

    if not isinstance(report, dict):
        raise CreativeLoopError("SEE incomplete: temporal motion report required before visual judgment")
    if report.get("version") != REPORT_VERSION:
        raise CreativeLoopError("SEE incomplete: temporal motion report version mismatch")
    if "longest_static_run" not in report or "motion_type" not in report:
        raise CreativeLoopError("SEE incomplete: temporal motion report missing measurements")


def _sample_gray(ffmpeg: str, src: Path, *, sample_fps: float, work_dir: Path | None) -> list[Image.Image]:
    tmp_ctx = None
    root = work_dir
    if root is None:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="om-temporal-")
        root = Path(tmp_ctx.name)
    else:
        root.mkdir(parents=True, exist_ok=True)
    dest = root / "samples"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(src),
            "-vf", f"fps={sample_fps}:round=down,scale=320:-2,format=gray",
            str(dest / "s%05d.png"),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        frames = []
        for p in sorted(dest.glob("s*.png")):
            im = Image.open(p).convert("L")
            im.load()
            frames.append(im.copy())
        return frames
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def _mad(a: Image.Image, b: Image.Image) -> float:
    pa, pb = list(a.getdata()), list(b.getdata())
    n = min(len(pa), len(pb))
    if n == 0:
        return 0.0
    return sum(abs(pa[i] - pb[i]) for i in range(n)) / n


def _classify(window: list[float]) -> str:
    if not window:
        return "STATIC_HOLD"
    ordered = sorted(window)
    median = ordered[len(ordered) // 2]
    p95 = ordered[int(0.95 * (len(ordered) - 1))]
    mean = sum(window) / len(window)
    if median < STATIC_MAD and p95 < CUT_MAD * 0.4:
        return "STATIC_HOLD"
    if mean >= CAMERA_MAD and median >= LOCAL_MAD:
        return "FULL_MOTION"
    if mean >= LOCAL_MAD:
        return "CAMERA_ONLY"
    return "LIMITED_LOCAL_MOTION"


def _segment(t0: float, t1: float, window: list[float]) -> dict[str, Any]:
    return {
        "t_start": round(float(t0), 3),
        "t_end": round(float(t1), 3),
        "motion_type": _classify(window),
        "median_mad": round(sorted(window)[len(window) // 2], 4),
        "mean_mad": round(sum(window) / len(window), 4),
    }


def _longest_static_run(mads: list[float], dt: float) -> float:
    best = cur = 0.0
    for v in mads:
        if v < STATIC_MAD:
            cur += dt
            best = max(best, cur)
        else:
            cur = 0.0
    return best
