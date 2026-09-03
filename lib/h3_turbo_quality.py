"""Turbo quality A/B on a directed still — not a 9:16 SHOT_KEYFRAME bind.

vid-yt-chef-s1-v1 still has briefs only. Identity 9x16 plates are
IDENTITY_REFERENCE. Frozen showpiece S2 / foreman S1 stills stay untouched.

Picture 1 is a copy of vid3 Scene A ``A2_mcu.png`` (16:9 MCU). Canvas is the
H3 ship grid 1344×768. Queue via ``tools/h3_capability_sandbox.py turbo-quality``.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

MCU_STILL_SRC = Path(
    r"C:\ContentStudio\jobs\vid3-blacklisted-chef-90s-v1"
    r"\assets\stills\scene_a\A2_mcu.png"
)

COMPARE_FRAMES: tuple[int, ...] = (0, 60, 120)

QUALITY_SPEC: dict[str, Any] = {
    "mode": "i2va",
    "style": "limited TV anime",
    "overview": (
        "Kitchen MCU from <Picture 1>. The young man in the black hoodie holds "
        "the blue lunchbox. Steam at the lid. Gaze stays down and off-axis."
    ),
    "identity": {
        "name": "figure in Picture 1",
        "must": [
            "same face as Picture 1",
            "black hoodie",
            "blue lunchbox with metal lid",
            "no costume change",
        ],
    },
    "duration_seconds": 5,
    "width": 1344,
    "height": 768,
    "camera": "locked-off static",
    "shots": [
        {
            "t0": 0,
            "t1": 5,
            "framing": "medium close-up",
            "action": (
                "Chest rises once. Hands stay on the lunchbox. Steam drifts. "
                "No walk. No smile. No camera move. Lid stays closed."
            ),
            "camera": "locked-off static",
        }
    ],
    "audio": ["quiet kitchen room tone", "one restrained breath"],
    "avoid": ["smile", "grin", "push-in", "walk cycle", "new face", "open lid"],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_mcu_still(dest: Path, src: Path = MCU_STILL_SRC) -> dict[str, str]:
    if not src.is_file():
        raise FileNotFoundError(f"MCU still missing (read-only copy): {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "src": str(src).replace("\\", "/"),
        "dest": str(dest).replace("\\", "/"),
        "sha256": sha256_file(dest),
        "kind": "directed_16x9_mcu_copy",
        "not_shot_keyframe_9x16": "true",
        "note": (
            "Semantic Picture 1 copy. vid3 still not rewritten. "
            "Not identity 9x16. Not frozen S2."
        ),
    }


def extract_compare_frames(
    video: Path,
    dest_dir: Path,
    arm: str,
    *,
    ffmpeg: str | None = None,
    frames: tuple[int, ...] = COMPARE_FRAMES,
) -> list[Path]:
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise FileNotFoundError("ffmpeg not on PATH")
    if not video.is_file():
        raise FileNotFoundError(video)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for frame in frames:
        out = dest_dir / f"{arm}_f{frame:03d}.png"
        proc = subprocess.run(
            [
                exe,
                "-y",
                "-i",
                str(video),
                "-vf",
                rf"select=eq(n\,{frame})",
                "-vframes",
                "1",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
            raise RuntimeError(
                f"ffmpeg extract {arm} frame {frame} failed: {proc.stderr[-800:]}"
            )
        paths.append(out)
    return paths


def stitch_compare_grid(
    cells: list[Path],
    dest: Path,
    *,
    n_cols: int,
    ffmpeg: str | None = None,
) -> Path:
    """Row-major grid: times down, arms across."""
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise FileNotFoundError("ffmpeg not on PATH")
    if n_cols < 1 or len(cells) % n_cols != 0:
        raise ValueError(f"Need a rectangular grid, got {len(cells)} cells and {n_cols} cols")
    n_rows = len(cells) // n_cols
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [exe, "-y"]
    for cell in cells:
        cmd.extend(["-i", str(cell)])
    row_parts: list[str] = []
    for row in range(n_rows):
        start = row * n_cols
        labels = "".join(f"[{start + col}]" for col in range(n_cols))
        if n_cols == 1:
            row_parts.append(f"{labels}copy[r{row}]")
        else:
            row_parts.append(f"{labels}hstack=inputs={n_cols}[r{row}]")
    row_labels = "".join(f"[r{row}]" for row in range(n_rows))
    if n_rows == 1:
        stack = f"{row_labels}copy[out]"
    else:
        stack = f"{row_labels}vstack=inputs={n_rows}[out]"
    filter_complex = ";".join([*row_parts, stack])
    cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", str(dest)])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError(f"ffmpeg quality sheet failed: {proc.stderr[-800:]}")
    return dest


def stitch_quality_sheet(cells: list[Path], dest: Path, *, ffmpeg: str | None = None) -> Path:
    """Row-major 3×3: arms across, times down."""
    if len(cells) != 9:
        raise ValueError(f"Need 9 cells, got {len(cells)}")
    return stitch_compare_grid(cells, dest, n_cols=3, ffmpeg=ffmpeg)
