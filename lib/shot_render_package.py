"""Provider-neutral SHOT_RENDER_PACKAGE_v1.

Creative intent lives here. Provider compilers only translate.
Does not call dispatch_cut, produce_keyframe, or compose_scene.
A packed folder is not a useful revision and not OM PASS.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "shot_render_package_v1"

RENDER_TARGETS = frozenset(
    {"local_h3", "local_deterministic", "runninghub", "xiaoyunque", "libtv"}
)
STAGES = frozenset({"PREVIS", "DRAFT", "FINAL", "HERO"})
FRAME_KINDS = frozenset(
    {
        "SHOT_KEYFRAME",
        "DIRECTED_MCU_COPY",
        "IDENTITY_REFERENCE",
        "SCENE_REFERENCE",
        "COMPOSITION_REFERENCE",
        "MISSING",
    }
)

XIAOYUNQUE_TEACHER_ONLY = (
    "XIAOYUNQUE_TEACHER_ONLY: do not compile a renderer API. "
    "Export a bundle for operator/teacher study. Do not automate the black box."
)
LIBTV_LAB_ONLY = (
    "LIBTV_LAB_ONLY: Creative Compiler / canvas lab. "
    "No LibTV API from this adapter. Human preflight stays outside OM state."
)


class ShotPackageError(ValueError):
    """Illegal or incomplete SHOT_RENDER_PACKAGE."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _frame_probe(path: Path | None) -> tuple[int | None, int | None]:
    if path is None or not path.is_file():
        return None, None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.size[0]), int(image.size[1])
    except Exception:
        return None, None


def asset_ref(*, id: str, path: Path | None = None, kind: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"id": id, "kind": kind, "asset_ref": None, "sha256": None}
    if path is not None and path.is_file():
        row["asset_ref"] = str(path).replace("\\", "/")
        row["sha256"] = sha256_file(path)
    return row


def frame_ref(*, kind: str, path: Path | None = None) -> dict[str, Any]:
    if kind not in FRAME_KINDS:
        raise ShotPackageError(f"unknown first_frame kind: {kind}")
    width, height = _frame_probe(path)
    row: dict[str, Any] = {
        "kind": kind,
        "asset_ref": str(path).replace("\\", "/") if path and path.is_file() else None,
        "sha256": sha256_file(path) if path and path.is_file() else None,
        "width": width,
        "height": height,
    }
    return row


def pack_shot(
    *,
    project_id: str,
    scene_id: str,
    shot_id: str,
    shot_intent: str,
    duration_s: float,
    aspect_ratio: str,
    motion_obligation: str,
    first_frame: dict[str, Any],
    render_policy: dict[str, Any],
    acceptance: dict[str, Any],
    audience_state_before: str | None = None,
    audience_state_after: str | None = None,
    shot_size: str | None = None,
    camera: dict[str, Any] | None = None,
    anchors: dict[str, Any] | None = None,
    last_frame: dict[str, Any] | None = None,
    temporal_beats: list[dict[str, Any]] | None = None,
    audio: dict[str, Any] | None = None,
    provider_prompt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = str((render_policy or {}).get("preferred_target") or "")
    if target not in RENDER_TARGETS:
        raise ShotPackageError(f"illegal preferred_target: {target}")
    stage = str((render_policy or {}).get("stage") or "")
    if stage not in STAGES:
        raise ShotPackageError(f"illegal stage: {stage}")
    if first_frame.get("kind") == "IDENTITY_REFERENCE":
        raise ShotPackageError("IDENTITY_REFERENCE cannot be first_frame")
    if first_frame.get("kind") == "SHOT_KEYFRAME" and not first_frame.get("sha256"):
        raise ShotPackageError("SHOT_KEYFRAME first_frame has no pixels")
    package: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "package_sha256": None,
        "creative": {
            "shot_intent": shot_intent,
            "audience_state_before": audience_state_before,
            "audience_state_after": audience_state_after,
            "shot_size": shot_size,
            "duration_s": duration_s,
            "aspect_ratio": aspect_ratio,
            "camera": camera or {"type": "LOCKED", "movement": None},
        },
        "anchors": anchors or {},
        "frames": {"first_frame": first_frame, "last_frame": last_frame},
        "performance": {
            "motion_obligation": motion_obligation,
            "temporal_beats": temporal_beats or [],
        },
        "audio": audio or {"dialogue": [], "sfx": [], "music_intent": None},
        "render_policy": render_policy,
        "provider_prompt": provider_prompt or {"neutral_prompt": "", "negative_constraints": []},
        "acceptance": acceptance,
    }
    package["package_sha256"] = sha256_json({k: v for k, v in package.items() if k != "package_sha256"})
    return package


def write_package(package: dict[str, Any], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def compile_provider(package: dict[str, Any], target: str) -> dict[str, Any]:
    """Translate the same package. Does not submit."""
    if target == "xiaoyunque":
        raise ShotPackageError(XIAOYUNQUE_TEACHER_ONLY)
    if target == "libtv":
        raise ShotPackageError(LIBTV_LAB_ONLY)
    if target == "runninghub":
        from lib.runninghub_adapter import compile_runninghub

        return compile_runninghub(package)
    if target in {"local_h3", "local_deterministic"}:
        from lib.h3_context_ir import compile_h3_ir

        prompt_bits = package.get("provider_prompt") or {}
        creative = package.get("creative") or {}
        performance = package.get("performance") or {}
        spec = {
            "mode": "i2va",
            "style": "limited TV anime",
            "overview": creative.get("shot_intent") or prompt_bits.get("neutral_prompt") or "",
            "duration_seconds": float(creative.get("duration_s") or 5),
            "camera": (creative.get("camera") or {}).get("type") or "locked-off static",
            "avoid": list(prompt_bits.get("negative_constraints") or []),
            "shots": [
                {
                    "t0": 0,
                    "t1": float(creative.get("duration_s") or 5),
                    "action": " ".join(
                        str(beat.get("action") or "")
                        for beat in (performance.get("temporal_beats") or [])
                    )
                    or str(creative.get("shot_intent") or ""),
                    "camera": "locked-off static",
                }
            ],
        }
        compiled = compile_h3_ir(spec)
        compiled["target"] = target
        compiled["submit"] = False
        return compiled
    raise ShotPackageError(f"unknown compile target: {target}")
