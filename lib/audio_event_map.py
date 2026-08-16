"""Measure whether the timeline has audible events. Not taste."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def probe_audio_map(mp4: Path, *, window: float = 0.5, silence_db: float = -40.0) -> dict[str, Any]:
    src = Path(mp4)
    duration = _duration(src)
    windows = _window_means(src, window=window)
    silent = [row for row in windows if row["mean_db"] <= silence_db]
    first_sound = next((row["t"] for row in windows if row["mean_db"] > silence_db), None)
    audible = [row for row in windows if row["mean_db"] > silence_db]
    first_15 = [row for row in windows if row["t"] < 15]
    silence_15 = sum(window for row in first_15 if row["mean_db"] <= silence_db)
    return {
        "version": "audio-event-map/v0.1",
        "source_mp4": str(src),
        "duration_seconds": duration,
        "measured": True,
        "first_sound_seconds": first_sound,
        "audible_fraction": round(len(audible) / max(len(windows), 1), 4),
        "unplanned_silence_seconds": round(len(silent) * window, 3),
        "unplanned_silence_seconds_first_15": round(silence_15, 3),
        "intent_coverage": 1.0 if first_sound is not None and first_sound <= 0.5 else 0.0,
        "mean_windows": windows[:8],
        "note": "Windows below silence_db count as unplanned silence unless a cut declares intentional mute.",
    }


def _duration(src: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
        text=True,
    )
    return float(raw.strip() or 0)


def _window_means(src: Path, *, window: float) -> list[dict[str, Any]]:
    duration = _duration(src)
    out: list[dict[str, Any]] = []
    t = 0.0
    while t < duration - 0.05:
        mean = _mean_db(src, t, min(window, duration - t))
        out.append({"t": round(t, 3), "mean_db": mean})
        t += window
    return out


def _mean_db(src: Path, start: float, length: float) -> float:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
            "-i", str(src), "-af", "volumedetect", "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    blob = result.stderr or ""
    for line in blob.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except ValueError:
                return -99.0
    return -99.0
