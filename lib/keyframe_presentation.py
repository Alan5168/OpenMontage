"""PERFORMANCE start/end stills must be readable original art.

Not a Human APPROVE gate. Not A4 geometry. Cheap pixel checks only:
identity visible, costume resolved, body not silhouette-only,
shot composition valid, start/end state usable.

A colorful kitchen behind a far black stick still FAILS.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

PRESENTATION_SCHEMA = "om-keyframe-presentation/v1"
PRESENTATION_UNUSABLE = "keyframe_presentation_unusable"

_MIN_W = 640
_MIN_H = 360
_SAMPLE = (160, 90)


def evaluate_keyframe_presentation(
    path: Path | str,
    *,
    framing: str = "medium_close",
) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return _report(source, False, ["still_missing"], {}, framing)
    try:
        from PIL import Image
    except ImportError:
        return _report(source, False, ["pillow_missing"], {}, framing)

    try:
        image = Image.open(source).convert("RGB")
    except Exception:
        return _report(source, False, ["still_undecodable"], {}, framing)

    width, height = image.size
    blockers: list[str] = []
    if width < _MIN_W or height < _MIN_H:
        blockers.append("still_too_small")

    sample = image.resize(_SAMPLE)
    pixels = list(sample.getdata())
    figure = _far_silhouette_figure(pixels, _SAMPLE[0], _SAMPLE[1])
    stats = _pixel_stats(pixels)
    stats["far_silhouette_figure"] = figure
    identity_visible = figure is None and stats["face_like_fraction"] >= 0.03
    costume_resolved = figure is None and (
        stats["midtone_chroma_fraction"] >= 0.05 or stats["subject_width_fraction"] >= 0.18
    )
    body_not_silhouette = figure is None
    composition_valid = _composition_ok(stats, framing, figure)

    if not identity_visible:
        blockers.append("identity_not_visible")
    if not costume_resolved:
        blockers.append("costume_unresolved")
    if not body_not_silhouette:
        blockers.append("body_silhouette_only")
    if not composition_valid:
        blockers.append("composition_unusable")

    usable = not blockers
    return _report(
        source,
        usable,
        blockers,
        {
            "width": width,
            "height": height,
            **stats,
            "identity_visible": identity_visible,
            "costume_resolved": costume_resolved,
            "body_not_silhouette_only": body_not_silhouette,
            "shot_composition_valid": composition_valid,
            "start_end_state_usable": usable,
        },
        framing,
    )


def assert_performance_keyframe_usable(
    path: Path | str,
    *,
    framing: str = "medium_close",
) -> dict[str, Any]:
    report = evaluate_keyframe_presentation(path, framing=framing)
    if report["usable"] is not True:
        raise KeyframePresentationError(
            PRESENTATION_UNUSABLE + ": " + ", ".join(report["blockers"])
        )
    return report


class KeyframePresentationError(ValueError):
    """PERFORMANCE still is not readable original art."""


def _report(
    source: Path,
    usable: bool,
    blockers: list[str],
    measurements: dict[str, Any],
    framing: str,
) -> dict[str, Any]:
    return {
        "schema_version": PRESENTATION_SCHEMA,
        "path": str(source),
        "framing": framing,
        "usable": usable,
        "blockers": blockers,
        "identity_visible": bool(measurements.get("identity_visible")),
        "costume_resolved": bool(measurements.get("costume_resolved")),
        "body_not_silhouette_only": bool(measurements.get("body_not_silhouette_only")),
        "shot_composition_valid": bool(measurements.get("shot_composition_valid")),
        "start_end_state_usable": bool(measurements.get("start_end_state_usable", usable)),
        "measurements": measurements,
        "judgment": "presentation_only",
        "note": (
            "H3 does not invent a face from a far silhouette. "
            "EST silhouette stills are legal for NONE holds, not PERFORMANCE starts."
        ),
    }


def _luma_chroma(pixel: tuple[int, int, int]) -> tuple[float, float]:
    r, g, b = pixel
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    chroma = max(r, g, b) - min(r, g, b)
    return luma, chroma


def _pixel_stats(pixels: list[tuple[int, int, int]]) -> dict[str, float]:
    n = max(len(pixels), 1)
    w, h = _SAMPLE
    midtone_chroma = 0
    face_like = 0
    silhouette = 0
    lumas = []
    chromas = []
    for i, pixel in enumerate(pixels):
        luma, chroma = _luma_chroma(pixel)
        lumas.append(luma)
        chromas.append(chroma)
        if luma < 28 and chroma < 18:
            silhouette += 1
        if 35 <= luma <= 210 and chroma >= 14:
            midtone_chroma += 1
        y, x = i // w, i % w
        if 0.18 * h <= y <= 0.55 * h and 0.28 * w <= x <= 0.72 * w:
            r, g, b = pixel
            fire = r > 160 and g > 70 and b < 90 and (r - b) > 80
            if (not fire) and 50 <= luma <= 200 and chroma >= 10:
                face_like += 1
    face_n = max(int(0.37 * h) * int(0.44 * w), 1)
    return {
        "mean_luma": sum(lumas) / n,
        "mean_chroma": sum(chromas) / n,
        "silhouette_fraction": silhouette / n,
        "midtone_chroma_fraction": midtone_chroma / n,
        "face_like_fraction": face_like / face_n,
        "subject_width_fraction": 0.0,
    }


def _far_silhouette_figure(
    pixels: list[tuple[int, int, int]],
    width: int,
    height: int,
) -> dict[str, Any] | None:
    mask = [False] * (width * height)
    for i, pixel in enumerate(pixels):
        luma, chroma = _luma_chroma(pixel)
        mask[i] = luma <= 34 and chroma <= 24
    seen = [False] * (width * height)
    best: dict[str, Any] | None = None
    for i, on in enumerate(mask):
        if not on or seen[i]:
            continue
        cells = _flood(mask, seen, i, width, height)
        if len(cells) < 18:
            continue
        xs = [c % width for c in cells]
        ys = [c // width for c in cells]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        w_frac = bw / width
        h_frac = bh / height
        aspect = bh / max(bw, 1)
        cx = (x0 + x1) / 2 / width
        chromas = []
        for cell in cells:
            _, chroma = _luma_chroma(pixels[cell])
            chromas.append(chroma)
        mean_chroma = sum(chromas) / max(len(chromas), 1)
        blob = {
            "w_frac": round(w_frac, 4),
            "h_frac": round(h_frac, 4),
            "aspect": round(aspect, 3),
            "cx": round(cx, 3),
            "mean_chroma": round(mean_chroma, 2),
            "area_frac": round(len(cells) / (width * height), 4),
        }
        far = (
            aspect >= 2.2
            and w_frac <= 0.085
            and h_frac >= 0.18
            and 0.32 <= cx <= 0.68
            and mean_chroma < 18
        )
        if far and (best is None or blob["area_frac"] > best["area_frac"]):
            best = blob
    return best


def _flood(
    mask: list[bool],
    seen: list[bool],
    start: int,
    width: int,
    height: int,
) -> list[int]:
    queue: deque[int] = deque([start])
    seen[start] = True
    cells = [start]
    while queue:
        pos = queue.popleft()
        x, y = pos % width, pos // width
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                nxt = ny * width + nx
                if mask[nxt] and not seen[nxt]:
                    seen[nxt] = True
                    queue.append(nxt)
                    cells.append(nxt)
    return cells


def _composition_ok(
    stats: dict[str, Any],
    framing: str,
    figure: dict[str, Any] | None,
) -> bool:
    if stats["mean_luma"] < 8 and stats["mean_chroma"] < 6:
        return False
    if figure is not None:
        return False
    if framing in {"medium_close", "close_up", "insert", "mcu"}:
        return stats["face_like_fraction"] >= 0.03
    return True
