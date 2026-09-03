"""Pack ShotContract refs for Seedance reference-to-video (≤9 images).

Translator, not director. Does not dispatch, does not enable H3, does not
treat identity stills as SHOT_KEYFRAME. Moyin/StarReel factories pack a
ref folder; this only orders OM roles onto the existing Seedance ceiling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.character_variant import still_refs_of

MAX_REF_IMAGES = 9
MAX_REF_VIDEOS = 3
MAX_REF_AUDIO = 3

_KIND_ROLE = {
    "character": "IDENTITY_REFERENCE",
    "scene": "SCENE_REFERENCE",
    "prop": "PROP_REFERENCE",
    "composition": "COMPOSITION_REFERENCE",
    "style": "STYLE_REFERENCE",
}


class SeedanceRefPackError(ValueError):
    """Ref pack exceeds Seedance ceilings or is internally illegal."""


def _norm(path: Any) -> str:
    return str(path or "").replace("\\", "/").strip()


def pack_seedance_refs(
    shot: dict[str, Any] | None,
    *,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    shot = shot if isinstance(shot, dict) else {}
    slots: list[dict[str, Any]] = []
    seen: set[str] = set()
    warnings: list[str] = []

    def add(role: str, path: Any) -> None:
        key = _norm(path)
        if not key or key in seen:
            return
        seen.add(key)
        slots.append({"role": role, "path": key})

    variant = shot.get("character_variant") if isinstance(shot.get("character_variant"), dict) else {}
    variant_stills = still_refs_of(variant)
    variant_set = set(variant_stills)

    start = _norm(shot.get("start_frame_ref"))
    visual = shot.get("visual_ref") if isinstance(shot.get("visual_ref"), dict) else {}
    start = start or _norm(visual.get("path"))
    readiness = (
        shot.get("first_frame_readiness")
        if isinstance(shot.get("first_frame_readiness"), dict)
        else {}
    )
    declared_keyframe = bool(
        readiness.get("shot_ready") or readiness.get("role") == "SHOT_KEYFRAME"
    )
    if start and start in variant_set:
        add("IDENTITY_REFERENCE", start)
        warnings.append("start_frame_ref is a character_variant still; packed as IDENTITY_REFERENCE")
    elif start and declared_keyframe:
        add("SHOT_KEYFRAME", start)
    elif start:
        add("SHOT_KEYFRAME", start)
        warnings.append("start_frame_ref packed as SHOT_KEYFRAME candidate; H3 still needs 9:16 bound composition")

    for row in shot.get("anchor_bindings") or []:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or _KIND_ROLE.get(str(row.get("kind") or ""), "") or "").strip()
        if not role:
            continue
        add(role, row.get("path"))

    for path in variant_stills:
        add("IDENTITY_REFERENCE", path)

    if len(slots) > MAX_REF_IMAGES:
        roles = ", ".join(f"{row['role']}:{row['path']}" for row in slots)
        raise SeedanceRefPackError(
            f"Seedance 2.0 reference_to_video accepts at most {MAX_REF_IMAGES} "
            f"reference images; got {len(slots)}: {roles}"
        )

    owner = str(variant.get("character_id") or "").strip() or None
    keyframes = [row for row in slots if row["role"] == "SHOT_KEYFRAME"]
    other = [row for row in slots if row["role"] != "SHOT_KEYFRAME"]
    ordered = list(keyframes + other)
    if shot.get("experimental_reference_binding"):
        from lib.reference_binding import annotate_packed_role

        ordered = [
            annotate_packed_role(row, owner=owner, experimental=True)
            for row in ordered
        ]
    if other:
        operation = "reference_to_video"
        image_path = None
        ref_paths = [row["path"] for row in ordered]
    elif keyframes:
        operation = "image_to_video"
        image_path = keyframes[0]["path"]
        ref_paths = []
    else:
        operation = "text_to_video"
        image_path = None
        ref_paths = []
        warnings.append("no stills to pack; Seedance would fall back to text_to_video")

    if not keyframes:
        warnings.append("no SHOT_KEYFRAME in pack; H3 dispatch remains illegal")

    missing: list[str] = []
    root = Path(project_dir) if project_dir else None
    for row in ordered:
        raw = Path(row["path"])
        candidates = [raw]
        if root is not None:
            candidates.append(root / raw)
        if not any(path.is_file() for path in candidates):
            missing.append(row["path"])
    if missing:
        warnings.append("missing on disk: " + ", ".join(missing))

    return {
        "ok": True,
        "operation": operation,
        "image_path": image_path,
        "reference_image_paths": ref_paths,
        "roles": ordered,
        "h3_dispatch_allowed": False,
        "warnings": warnings,
        "ceilings": {
            "images": MAX_REF_IMAGES,
            "videos": MAX_REF_VIDEOS,
            "audio": MAX_REF_AUDIO,
        },
    }
