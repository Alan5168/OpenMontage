"""Cinematic Multishot Coverage as composition previs — not a director, not a bind.

ethanfel/H3_Cinematic_Multishot_Coverage is a UI graph (1344×768, 124 frames,
25 steps, subgraph contact sheet). This module only supplies:

- a Picture-1-complete H3 prompt (their concat left ``<Picture 1>`` holes)
- the eight extract indices from that workflow
- ffmpeg view extract + 4×2 sheet

Queueing is ``tools/h3_capability_sandbox.py coverage-previs`` on the proven
``minimax-h3-r2v.json`` API graph. Generated views are not ``COMP_*`` and not
``SHOT_KEYFRAME``.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

ETHANFEL_VIEW_FRAMES: tuple[int, ...] = (2, 15, 31, 46, 62, 77, 92, 108)

SCENE_PLATE_SRC = Path(
    r"C:\ContentStudio\jobs\vid3-blacklisted-chef-90s-v1"
    r"\bible\avery\approved\backkitchen_wide.jpg"
)

# Plate is an empty kitchen. Do not invent a seated figure.
DEFAULT_COVERAGE_TARGET = (
    "the far range under the hood at the end of the stained aisle in <Picture 1>"
)

COVERAGE_WIDTH = 864
COVERAGE_HEIGHT = 480
COVERAGE_LENGTH = 124
COVERAGE_STEPS = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_scene_plate(dest: Path, src: Path = SCENE_PLATE_SRC) -> dict[str, str]:
    if not src.is_file():
        raise FileNotFoundError(f"Scene plate missing (read-only copy): {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "src": str(src).replace("\\", "/"),
        "dest": str(dest).replace("\\", "/"),
        "sha256": sha256_file(dest),
        "note": "Semantic Picture 1 copy. vid3 plate not rewritten. Not SHOT_KEYFRAME.",
    }


def build_coverage_prompt(*, coverage_target: str = DEFAULT_COVERAGE_TARGET) -> str:
    target = coverage_target.strip()
    if "<Picture 1>" not in target:
        target = f"{target} in <Picture 1>"
    return (
        "For the target video, at 0.00 seconds into the target video, "
        "<Picture 1> (from [Shot 1]) is fully referenced.\n\n"
        "integrated_multimodal_description:\n"
        "subject_definitions:\n"
        "<Picture 1> is the complete photographed scene, including every visible "
        "person, object, surface, room boundary, prop, material, light source, "
        "shadow, color relationship, and world-space relationship. The persistent "
        f"cinematic coverage target is {target}. Keep this exact target as the "
        "compositional center in every shot. This target phrase identifies only "
        "the camera's compositional center. It does not permit any person, object, "
        "pose, expression, gaze, wardrobe, prop, geometry, lighting, or scene "
        "state to change.\n\n"
        "summary:\n"
        "[reference generation] The target video creates eight static cinematic "
        "coverage views of <Picture 1> around the designated target, using the "
        "same source-defined scene and exact subject identities. The views are "
        "joined only by instantaneous editorial hard cuts.\n\n"
        "retention_analysis:\n"
        "<Picture 1> (appears in [Shot 1], [Shot 2], [Shot 3], [Shot 4], "
        "[Shot 5], [Shot 6], [Shot 7], and [Shot 8]): fully_preserved - preserve "
        "the source scene's identities, wardrobe, pose, expression, gaze, hair, "
        "fabric folds, props, furniture, architecture, materials, colors, lighting "
        "direction, shadow placement, relative scale, and world-space layout. "
        "Infer only surfaces hidden from <Picture 1>, conservatively and "
        "consistently.\n\n"
        "detailed_description:\n"
        "A coherent cinematic scene-coverage study matching <Picture 1>'s visual "
        "medium, texture, color science, lighting, and production design. Treat "
        "<Picture 1> as one rigid frozen world. Every person is perfectly "
        "motionless: no breathing, blinking, gaze change, facial change, gesture, "
        "hair movement, cloth movement, or pose change. Every object, wall, floor, "
        "opening, furnishing, reflection, practical light, cast shadow, and "
        "contact shadow remains fixed in world space. The designated target "
        "remains the same exact entity and anchors composition in all eight shots.\n\n"
        "These are eight discrete camera placements, not points along a visible "
        "camera path. At every stated timestamp, execute a true instantaneous "
        "scene cut. The first frame after each cut is already fully resolved, "
        "sharp, and stable at the new camera position. Never show the camera "
        "travelling between placements. No orbit, pan, tilt, truck, dolly, "
        "pedestal, crane, zoom, whip-pan, speed ramp, motion blur, optical flow, "
        "morph, dissolve, crossfade, transitional frame, or intermediate angle. "
        "Within each shot, the camera is locked off and static.\n\n"
        "[Shot 1] Source-oriented establishing view of <Picture 1>, matching the "
        "source image's general camera side, camera height, framing logic, and "
        "lens character. The designated target is clearly readable and the scene "
        "is frozen.\n\n"
        "[Shot 2] At 00:00.333, the shot cuts to a camera placed exactly 45 "
        "degrees clockwise around the designated target at eye level, using a "
        "40 mm lens and a medium-wide three-quarter composition. The camera is "
        "immediately locked off.\n\n"
        "[Shot 3] At 00:00.958, the shot cuts to a camera placed exactly 90 "
        "degrees clockwise around the designated target at eye level, using a "
        "65 mm lens and a clean profile composition. The camera is immediately "
        "locked off.\n\n"
        "[Shot 4] At 00:01.583, the shot cuts to a camera placed exactly 135 "
        "degrees clockwise around the designated target, slightly below eye "
        "level, using a 35 mm lens and a low three-quarter composition. The "
        "camera is immediately locked off.\n\n"
        "[Shot 5] At 00:02.250, the shot cuts to a camera placed exactly 180 "
        "degrees clockwise around the designated target at eye level, using a "
        "32 mm lens and a reverse wide composition that reveals the opposite "
        "side of the frozen scene. The camera is immediately locked off.\n\n"
        "[Shot 6] At 00:02.917, the shot cuts to a camera placed exactly 225 "
        "degrees clockwise around the designated target, slightly above eye "
        "level, using a 50 mm lens and a high three-quarter composition. The "
        "camera is immediately locked off.\n\n"
        "[Shot 7] At 00:03.500, the shot cuts to a camera placed exactly 270 "
        "degrees clockwise around the designated target at eye level, using an "
        "85 mm lens and a compressed profile or detail composition. The camera "
        "is immediately locked off.\n\n"
        "[Shot 8] At 00:04.167, the shot cuts to a camera placed exactly 315 "
        "degrees clockwise around the designated target at eye level, using a "
        "50 mm lens and a balanced hero three-quarter composition. Hold this "
        "final camera completely static through the end.\n\n"
        "overall_soundscape:\n"
        "No dialogue, voices, room tone, Foley, ambience, or sound effects; "
        "complete silence.\n\n"
        "non_diegetic_music:\n"
        "N/A"
    )


def extract_coverage_views(video: Path, dest_dir: Path, *, ffmpeg: str | None = None) -> list[Path]:
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise FileNotFoundError("ffmpeg not on PATH")
    if not video.is_file():
        raise FileNotFoundError(video)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, frame in enumerate(ETHANFEL_VIEW_FRAMES, start=1):
        out = dest_dir / f"view_{index:02d}_frame{frame}.png"
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
                f"ffmpeg extract frame {frame} failed: {proc.stderr[-800:]}"
            )
        paths.append(out)
    return paths


def stitch_contact_sheet(views: list[Path], dest: Path, *, ffmpeg: str | None = None) -> Path:
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise FileNotFoundError("ffmpeg not on PATH")
    if len(views) != 8:
        raise ValueError(f"Need 8 views, got {len(views)}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [exe, "-y"]
    for view in views:
        cmd.extend(["-i", str(view)])
    cmd.extend(
        [
            "-filter_complex",
            "[0][1][2][3]hstack=inputs=4[top];"
            "[4][5][6][7]hstack=inputs=4[bot];"
            "[top][bot]vstack=inputs=2[out]",
            "-map",
            "[out]",
            str(dest),
        ]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError(f"ffmpeg contact sheet failed: {proc.stderr[-800:]}")
    return dest
