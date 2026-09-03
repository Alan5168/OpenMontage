"""H3 capability routing — which keep-set, not which HF card is trending.

Ship renderer stays FL2VA NVFP4 20-step. Turbo / Ref2VA / LoRAs are candidates.
"""

from __future__ import annotations

from typing import Any

from lib.motion_obligation import ShotCompileError, resolve_motion_obligation
from lib.reference_atom import locomotion_declared

SHIP_RENDERER = "h3_fl2va_nvfp4"
SHIP_STEPS = 20
TURBO_LORA = "minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors"
TURBO_STEPS = (6, 8)

CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "MICRO_PERFORMANCE": {
        "ship": SHIP_RENDERER,
        "ship_steps": SHIP_STEPS,
        "candidates": ["h3_fl2va_turbo_v4", "h3_fl2va_pdd_acc_8"],
        "turbo_steps": list(TURBO_STEPS),
        "note": (
            "Turbo and PDD Acc are isolated candidates. Neither is in the ship graph. "
            "Do not stack Turbo + PDD + Spectrum + EasyCache."
        ),
    },
    "LOCOMOTION": {
        "ship": SHIP_RENDERER,
        "candidates": ["h3_ref2va", "spatial_physics_lora"],
        "note": "Ref2VA is a candidate until 16GB spike is promoted.",
    },
    "INTERACTION": {
        "ship": None,
        "preferred": "h3_ref2va",
        "candidates": ["h3_ref2va", "spatial_physics_lora"],
        "note": "Compile stays R2VA_RUNTIME_UNAVAILABLE until promote_to_production.",
    },
    "CAMERA_MOTION": {
        "ship": SHIP_RENDERER,
        "candidates": ["camera_motion_lora"],
        "note": "Do not stack camera LoRA on MCU micro-performance.",
    },
    "COMPOSITION_PREVIS": {
        "ship": None,
        "candidates": ["h3_cinematic_multishot_coverage"],
        "note": "Previs only. Human locks COMP_*. Generated views are not SHOT_KEYFRAME.",
    },
    "CHARACTER_BIBLE": {
        "ship": None,
        "candidates": ["h3_character_sheet_generator"],
        "note": "New projects only. Do not relock Avery/Lucien.",
    },
    "HERO_DETAIL": {
        "ship": SHIP_RENDERER,
        "candidates": ["h3_z_image_graft"],
        "note": "Month-2 A/B. Do not replace baseline.",
    },
    "NOT_H3": {
        "ship": None,
        "candidates": [],
        "note": "NONE/LOCAL stay on local_compose.",
    },
}

_STATIC_CAMERA = frozenset(
    {"", "static", "locked-off static", "locked off static", "static shot", "none"}
)


def classify_h3_capability(shot: dict[str, Any] | None) -> str:
    shot = shot if isinstance(shot, dict) else {}
    if shot.get("h3_capability"):
        key = str(shot["h3_capability"]).strip().upper()
        if key in CAPABILITY_MAP:
            return key
    try:
        obligation = resolve_motion_obligation(shot)
    except ShotCompileError:
        return "NOT_H3"
    if obligation == "INTERACTION":
        return "INTERACTION"
    if obligation in {"NONE", "LOCAL"}:
        return "NOT_H3"
    language = shot.get("shot_language") if isinstance(shot.get("shot_language"), dict) else {}
    camera = str(
        language.get("camera_movement") or shot.get("movement") or shot.get("camera") or ""
    ).strip().lower().replace("_", " ")
    if camera and camera not in _STATIC_CAMERA:
        return "CAMERA_MOTION"
    text = " ".join(
        str(shot.get(key) or "")
        for key in ("performance_intent", "visual_intent", "shot_intent", "description")
    )
    if obligation == "PERFORMANCE" and locomotion_declared(text):
        return "LOCOMOTION"
    if obligation == "PERFORMANCE":
        return "MICRO_PERFORMANCE"
    return "NOT_H3"


def route_h3_capability(shot: dict[str, Any] | None) -> dict[str, Any]:
    capability = classify_h3_capability(shot)
    row = dict(CAPABILITY_MAP[capability])
    row["capability"] = capability
    row["turbo_in_ship_graph"] = False
    row["pdd_in_ship_graph"] = False
    row["ref2va_promoted"] = False
    try:
        from lib.h3_runtime import ref2va_promoted_to_production, ref2va_runtime_available

        row["ref2va_promoted"] = ref2va_promoted_to_production()
        row["ref2va_runtime_available"] = ref2va_runtime_available()
    except Exception:
        row["ref2va_runtime_available"] = False
    return row
