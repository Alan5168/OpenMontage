"""Hard-gate visual continuity for multi-mother scene plans.

Independent T2I trios with mismatched cameras and no world lock must FAIL
before assets / keep-approval can proceed.
"""

from __future__ import annotations

from typing import Any


ALLOWED_GENERATION_MODES = {
    "one_mother_edit",
    "multi_panel_one_request",
    "vector_primary",
}

FORBIDDEN_MODES = {"independent_t2i_trio", "independent_t2i"}


def _mother_scenes(scene_plan: dict[str, Any]) -> list[dict[str, Any]]:
    scenes = scene_plan.get("scenes") or []
    mothers: list[dict[str, Any]] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        if scene.get("reuse"):
            continue
        if scene.get("review_decision") == "omit":
            continue
        # A cut with its own visual_ref / t2i_prompt counts as a mother layout.
        if scene.get("visual_ref") or scene.get("t2i_prompt") or scene.get("type") in {
            "animation",
            "illustration",
            "api_image",
        }:
            mothers.append(scene)
    return mothers


def evaluate_visual_continuity(scene_plan: dict[str, Any]) -> dict[str, Any]:
    package = scene_plan.get("visual_continuity_package")
    if not isinstance(package, dict):
        package = {}
    mothers = _mother_scenes(scene_plan)
    mode = package.get("generation_mode")
    world_lock = package.get("world_lock")
    hero_prop_id = package.get("hero_prop_id")
    camera_language = package.get("camera_language")
    alan_ok = package.get("alan_continuous_animation_ok", None)

    reasons: list[str] = []
    status = "PASS"

    if len(mothers) <= 1:
        return {
            "status": "PASS",
            "reason": "single_or_zero_mother",
            "mother_count": len(mothers),
            "generation_mode": mode,
            "alan_continuous_animation_ok": alan_ok,
            "package_present": bool(package),
        }

    if mode in FORBIDDEN_MODES or mode is None:
        status = "FAIL"
        reasons.append(
            "multi-mother sceneplan requires generation_mode in "
            f"{sorted(ALLOWED_GENERATION_MODES)}; got {mode!r}"
        )
    elif mode not in ALLOWED_GENERATION_MODES:
        status = "FAIL"
        reasons.append(f"unknown generation_mode: {mode!r}")

    if not world_lock:
        status = "FAIL"
        reasons.append("missing world_lock for multi-mother continuity")
    if not hero_prop_id:
        status = "FAIL"
        reasons.append("missing hero_prop_id for cross-mother recognition")
    if not camera_language:
        status = "FAIL"
        reasons.append("missing camera_language continuous shot family")

    # Heuristic: distinct prompts without shared world package ≈ independent T2I.
    prompts = {str(m.get("t2i_prompt") or "").strip() for m in mothers if m.get("t2i_prompt")}
    if len(prompts) >= 2 and mode not in ALLOWED_GENERATION_MODES:
        status = "FAIL"
        if "independent_t2i_suspected" not in reasons:
            reasons.append("independent_t2i_suspected: multiple distinct t2i_prompt mothers")

    return {
        "status": status,
        "reason": "; ".join(reasons) if reasons else "ok",
        "reasons": reasons,
        "mother_count": len(mothers),
        "mother_ids": [m.get("id") for m in mothers],
        "generation_mode": mode,
        "world_lock_present": bool(world_lock),
        "hero_prop_id": hero_prop_id,
        "camera_language_present": bool(camera_language),
        "alan_continuous_animation_ok": alan_ok,
        "package_present": bool(package),
        "verdict_tag": (
            "CONTINUITY_FAIL / MUST_REGENERATE_AFTER_CONTRACT" if status == "FAIL" else "CONTINUITY_OK"
        ),
    }


def assert_continuity_or_raise(scene_plan: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_visual_continuity(scene_plan)
    if result["status"] != "PASS":
        raise ValueError(
            f"Sceneplan visual continuity hard gate FAIL: {result['reason']} "
            f"[{result.get('verdict_tag')}]"
        )
    return result
