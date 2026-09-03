"""Motion obligation — compile-time, not a prompt.

PERFORMANCE / INTERACTION cannot be satisfied by static LIMITED grammar.
H3 FL2VA is the executable default for PERFORMANCE. INTERACTION prefers
Ref2VA (`h3_ref2va`) but compile blocks unless that runtime exists.
LIMITED is legal only when the cut declares NONE or LOCAL.

Do not educate the Agent. Delete the still-loop edge.
"""
from __future__ import annotations

from typing import Any

from lib.h3_runtime import R2VA_RUNTIME_UNAVAILABLE, ref2va_runtime_available

OBLIGATIONS = ("NONE", "LOCAL", "PERFORMANCE", "INTERACTION")
DYNAMIC = frozenset({"PERFORMANCE", "INTERACTION"})
STATIC_CLASSES = frozenset({"LIMITED"})
STATIC_RENDERERS = frozenset(
    {
        "local_compose",
        "ffmpeg",
        "ffmpeg-hold",
        "remotion",
        "still",
        "still_loop",
        "png_loop",
    }
)
HOLD_RENDERERS = frozenset(
    {"ffmpeg-hold", "still", "still_loop", "png_loop"}
)

COMPILE_FAIL = (
    "COMPILE FAIL: PERFORMANCE cannot be satisfied by static LIMITED grammar."
)
LOCAL_HOLD_FAIL = (
    "COMPILE FAIL: LOCAL visible motion cannot be satisfied by a still hold."
)

# Locomotion / acting. Do not include "hold" — that is pose or 止め絵.
_PERFORMANCE_MARKERS = (
    "walk",
    "walks",
    "walking",
    "step",
    "steps",
    "turn",
    "turns",
    "turning",
    "grab",
    "grabs",
    "reach",
    "reaches",
    "approach",
    "approaches",
    "flinch",
    "recoil",
    "tighten",
    "handoff",
    "interact",
    "toward the cooler",
    "takes two",
    "two steps",
    "picks up",
    "puts down",
)


class ShotCompileError(ValueError):
    """Illegal ShotContract. Do not dispatch."""


def resolve_motion_obligation(cut: dict[str, Any]) -> str:
    raw = str(cut.get("motion_obligation") or "").strip().upper()
    if raw:
        if raw not in OBLIGATIONS:
            raise ShotCompileError(f"unknown motion_obligation: {raw!r}")
        return raw
    if cut.get("requires_performance") is True:
        ids = [c for c in (cut.get("character_ids") or []) if str(c).strip()]
        if len(ids) >= 2:
            return "INTERACTION"
        return "PERFORMANCE"
    if cut.get("intentional_hold") is True:
        return "NONE"
    blob = " ".join(
        str(cut.get(key) or "")
        for key in ("performance_intent", "visual_intent", "description", "shot_intent")
    ).lower()
    if any(marker in blob for marker in _PERFORMANCE_MARKERS):
        ids = [c for c in (cut.get("character_ids") or []) if str(c).strip()]
        if len(ids) >= 2:
            return "INTERACTION"
        return "PERFORMANCE"
    intent = str(cut.get("temporal_intent") or "").strip().lower()
    if intent in {"intentional_hold", "overlay_information_change"}:
        return "NONE"
    if intent in {"limited_local_motion", "camera_only"}:
        return "LOCAL"
    planned = str(cut.get("animation_class") or "").strip().upper()
    if planned in {"I2V_HARD", "I2V_STANDARD"}:
        ids = [c for c in (cut.get("character_ids") or []) if str(c).strip()]
        if len(ids) >= 2:
            return "INTERACTION"
        return "PERFORMANCE"
    return "LOCAL" if planned == "LIMITED" else "NONE"


def default_animation_class(obligation: str) -> str:
    if obligation == "INTERACTION":
        return "I2V_HARD"
    if obligation == "PERFORMANCE":
        return "I2V_HARD"
    if obligation == "LOCAL":
        return "LIMITED"
    return "LIMITED"


def default_renderer(obligation: str, dispatch_class: str) -> str:
    if obligation == "INTERACTION":
        return "h3_ref2va"
    if obligation == "PERFORMANCE":
        return "h3"
    if dispatch_class == "I2V_HARD":
        return "h3"
    if dispatch_class == "I2V_STANDARD":
        return "video_model"
    return "local_compose"


def default_h3_mode(obligation: str) -> str | None:
    if obligation == "INTERACTION":
        return "r2va"
    if obligation == "PERFORMANCE":
        return "fl2va"
    return None


def assert_motion_obligation(cut: dict[str, Any], *, dispatch_class: str | None = None, department: str | None = None) -> str:
    """Raise if a dynamic shot is on a still/zoom/loop renderer."""
    obligation = resolve_motion_obligation(cut)
    planned = str(cut.get("animation_class") or dispatch_class or "").strip().upper() or None
    renderer = str(cut.get("renderer") or department or "").strip().lower()
    if obligation == "LOCAL" and renderer in HOLD_RENDERERS:
        raise ShotCompileError(LOCAL_HOLD_FAIL)
    if obligation not in DYNAMIC:
        return obligation
    if planned in STATIC_CLASSES:
        raise ShotCompileError(COMPILE_FAIL)
    if renderer in STATIC_RENDERERS or renderer in HOLD_RENDERERS:
        raise ShotCompileError(COMPILE_FAIL)
    return obligation


def compile_cut(cut: dict[str, Any]) -> dict[str, Any]:
    """Return obligation + default class. Raises on illegal LIMITED+PERFORMANCE."""
    obligation = resolve_motion_obligation(cut)
    planned = str(cut.get("animation_class") or "").strip().upper() or None
    assert_motion_obligation(cut, dispatch_class=planned, department=cut.get("renderer"))
    dispatch = planned or default_animation_class(obligation)
    if obligation in DYNAMIC and dispatch == "LIMITED":
        raise ShotCompileError(COMPILE_FAIL)
    if obligation not in DYNAMIC and planned is None:
        dispatch = default_animation_class(obligation)
    renderer = default_renderer(obligation, dispatch)
    h3_mode = default_h3_mode(obligation)
    if renderer == "h3" and h3_mode is None and dispatch == "I2V_HARD":
        h3_mode = "fl2va"
    if obligation == "INTERACTION":
        available = ref2va_runtime_available()
        payload = {
            "cut_id": cut.get("id"),
            "motion_obligation": obligation,
            "planned_class": planned,
            "dispatch_class": dispatch,
            "preferred_renderer": "h3_ref2va",
            "capability_available": available,
            "renderer": "h3_ref2va" if available else None,
            "h3_mode": "r2va" if available else None,
            "h3_mode_label": "ref2va" if available else None,
            "h3_default": False,
            "generate": False,
            "fallback": None,
        }
        if not available:
            raise ShotCompileError(R2VA_RUNTIME_UNAVAILABLE)
        return payload
    return {
        "cut_id": cut.get("id"),
        "motion_obligation": obligation,
        "planned_class": planned,
        "dispatch_class": dispatch,
        "renderer": renderer,
        "h3_mode": h3_mode,
        "h3_mode_label": "ref2va" if h3_mode == "r2va" else h3_mode,
        "h3_default": obligation in DYNAMIC,
        "generate": False,
        "fallback": "h3_retry_then_video_provider_then_split_or_repair"
        if obligation in DYNAMIC
        else None,
    }
