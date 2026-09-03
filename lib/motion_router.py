"""Per-cut motion routing for the Limited Anime Studio.

LIMITED is declared temporal grammar (NONE/LOCAL), not the cheap fallback.
PERFORMANCE / INTERACTION default to H3. Compile rejects still+zoom+loop
on a dynamic ShotContract. loop/zoom cannot impersonate performance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.motion_obligation import ShotCompileError, compile_cut  # noqa: E402
from lib.shot_production_gate import PLANNING, UNCLASSIFIED, evaluate_cut, evaluate_plan

ANIMATION_CLASSES = ("LIMITED", "I2V_STANDARD", "I2V_HARD")

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
    raw = str(scene.get("animation_class") or "").strip().upper()
    if raw not in ANIMATION_CLASSES:
        raise MotionRouterError(f"unknown animation_class: {raw!r}")
    return raw


def department_for_class(cls: str) -> tuple[str, list[str], bool]:
    if cls == "LIMITED":
        # Department, not definition. Grammar is measured later by temporal_motion.
        return LOCAL_COMPOSE, ["remotion", "ffmpeg", "overlay"], False
    if cls == "I2V_STANDARD":
        return VIDEO_MODEL, ["video-gen-pool"], False
    if cls == "I2V_HARD":
        return H3, ["h3-comfyui", "video-gen-pool"], True
    raise MotionRouterError(f"unknown animation_class: {cls!r}")


def route_cut(
    scene: dict[str, Any],
    *,
    scene_plan: dict[str, Any] | None = None,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return the legal department for one cut, or planning if unconstrained."""
    planned = str(scene.get("animation_class") or "").strip().upper() or None
    if str(scene.get("review_decision") or "").strip().lower() == "omit":
        return {
            "cut_id": scene.get("id"),
            "animation_class": planned,
            "planned_class": planned,
            "dispatch_class": None,
            "department": "omitted",
            "h3_allowed": False,
            "equipment": [],
            "generation_status": scene.get("generation_status") or "pending",
            "render_allowed": False,
            "production_ready": False,
            "blockers": ["review_decision_omit"],
        }
    compiled = compile_cut(scene)
    if planned is None:
        scene = {**scene, "animation_class": compiled["dispatch_class"]}
        planned = compiled["dispatch_class"]
    animation_class_of(scene)
    root = Path(project_dir) if project_dir is not None else None
    gate = evaluate_cut(scene, scene_plan=scene_plan, project_dir=root)
    requested = str(scene.get("primary_model") or scene.get("motion_route") or "")
    dispatch_class = gate.get("dispatch_class") or planned
    if dispatch_class != "I2V_HARD" and _looks_like_h3(requested):
        raise MotionRouterError(
            f"cut {scene.get('id')!r} is {dispatch_class or 'LIMITED'}; H3 is not on this edge"
        )
    if not gate["production_ready"]:
        return {
            "cut_id": scene.get("id"),
            "animation_class": planned,
            "planned_class": planned,
            "dispatch_class": None,
            "department": PLANNING if (planned or gate["applies"]) else UNCLASSIFIED,
            "h3_allowed": False,
            "equipment": [],
            "generation_status": scene.get("generation_status") or "pending",
            "render_allowed": False,
            "production_ready": False,
            "blockers": gate["blockers"],
        }
    department, equipment, h3_allowed = department_for_class(dispatch_class)
    return {
        "cut_id": scene.get("id"),
        "animation_class": dispatch_class,
        "planned_class": planned,
        "dispatch_class": dispatch_class,
        "department": department,
        "h3_allowed": h3_allowed,
        "equipment": equipment,
        "generation_status": scene.get("generation_status") or "pending",
        "render_allowed": True,
        "production_ready": True,
        "blockers": [],
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


def summarize_scenes(
    scenes: list[dict[str, Any]],
    *,
    scene_plan: dict[str, Any] | None = None,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    plan = scene_plan if isinstance(scene_plan, dict) else {"scenes": scenes, "metadata": {}}
    if scenes and not plan.get("scenes"):
        plan = {**plan, "scenes": scenes}
    rows = [
        route_cut(scene, scene_plan=plan, project_dir=project_dir)
        for scene in (plan.get("scenes") or scenes)
        if isinstance(scene, dict)
    ]
    planned_counts = {cls: 0 for cls in ANIMATION_CLASSES}
    dispatch_counts = {cls: 0 for cls in ANIMATION_CLASSES}
    for row in rows:
        planned = row.get("planned_class")
        if planned in planned_counts:
            planned_counts[planned] += 1
        if row.get("production_ready") and row.get("dispatch_class") in dispatch_counts:
            dispatch_counts[row["dispatch_class"]] += 1
    root = Path(project_dir) if project_dir is not None else None
    overview = evaluate_plan(plan, root)
    return {
        "cut_count": len(rows),
        "class_counts": planned_counts,
        "dispatch_class_counts": dispatch_counts,
        "h3_cut_ids": [row["cut_id"] for row in rows if row["h3_allowed"]],
        "planning_cut_ids": overview["planning_cut_ids"],
        "dispatchable_cut_ids": overview["dispatchable_cut_ids"],
        "unclassified_cut_ids": overview["unclassified_cut_ids"],
        "job_blockers": overview["job_blockers"],
        "render_allowed": overview["render_allowed"],
        "cuts": rows,
    }
