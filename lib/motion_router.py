"""Per-cut motion routing for the Limited Anime Studio.

OM owns the graph. Agents may propose PATCH. They cannot approve.
H3 is the motion department: I2V_HARD only.
"""

from __future__ import annotations

from typing import Any

ANIMATION_CLASSES = ("LIMITED", "I2V_STANDARD", "I2V_HARD")
DEFAULT_CLASS = "LIMITED"

LOCAL_COMPOSE = "local_compose"
VIDEO_MODEL = "video_model"
H3 = "h3"

# Agent-written events cannot land on these terminals.
HUMAN_ONLY_STATES = frozenset(
    {
        "APPROVED",
        "FINAL_GATE_PASS",
        "WINDOWS_PI_APPROVED",
        "PUBLISHED",
    }
)
AGENT_ACTORS = frozenset({"prime", "pi", "trae", "agent", "qwen"})
FORBIDDEN_EDGES = frozenset(
    {
        ("PATCH_PROPOSAL", "APPROVED"),
        ("CRITIQUE", "APPROVED"),
        ("EDITORIAL_CRITIQUE", "APPROVED"),
        ("EDITORIAL_CRITIQUE", "FINAL_GATE_PASS"),
        ("REPAIR_PLAN", "APPROVED"),
        ("PATCH", "APPROVED"),
    }
)


class MotionRouterError(ValueError):
    """Illegal animation_class, equipment, or graph edge."""


def animation_class_of(scene: dict[str, Any]) -> str:
    raw = str(scene.get("animation_class") or DEFAULT_CLASS).strip().upper()
    if raw not in ANIMATION_CLASSES:
        raise MotionRouterError(f"unknown animation_class: {raw!r}")
    return raw


def route_cut(scene: dict[str, Any]) -> dict[str, Any]:
    """Return the cheapest legal motion department for one cut."""
    cls = animation_class_of(scene)
    h3_allowed = cls == "I2V_HARD"
    if cls == "LIMITED":
        department = LOCAL_COMPOSE
        equipment = ["remotion", "ffmpeg", "overlay"]
    elif cls == "I2V_STANDARD":
        department = VIDEO_MODEL
        equipment = ["video-gen-pool"]
    else:
        department = H3
        equipment = ["h3-comfyui", "video-gen-pool"]
    requested = str(scene.get("primary_model") or scene.get("motion_route") or "")
    if not h3_allowed and _looks_like_h3(requested):
        raise MotionRouterError(
            f"cut {scene.get('id')!r} is {cls}; H3 is not on this edge"
        )
    return {
        "cut_id": scene.get("id"),
        "animation_class": cls,
        "department": department,
        "h3_allowed": h3_allowed,
        "equipment": equipment,
        "generation_status": scene.get("generation_status") or "pending",
        "render_allowed": bool((scene.get("visual_ref") or {}).get("kind") not in {None, "placeholder"}),
    }


def _looks_like_h3(value: str) -> bool:
    lowered = value.lower()
    return "h3" in lowered or "comfy" in lowered


def assert_transition(src: str, dst: str, *, actor: str) -> None:
    """Delete the 08-12 overreach edges. Human is the only writer of APPROVED."""
    edge = (str(src).upper(), str(dst).upper())
    who = str(actor).strip().lower()
    if edge in FORBIDDEN_EDGES:
        raise MotionRouterError(f"forbidden edge {edge[0]} → {edge[1]}")
    if dst.upper() in HUMAN_ONLY_STATES and who in AGENT_ACTORS:
        raise MotionRouterError(
            f"{who} cannot write {dst}; that node is human-only"
        )


def summarize_scenes(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [route_cut(scene) for scene in scenes if isinstance(scene, dict)]
    counts = {cls: 0 for cls in ANIMATION_CLASSES}
    for row in rows:
        counts[row["animation_class"]] += 1
    return {
        "cut_count": len(rows),
        "class_counts": counts,
        "h3_cut_ids": [row["cut_id"] for row in rows if row["h3_allowed"]],
        "cuts": rows,
    }
