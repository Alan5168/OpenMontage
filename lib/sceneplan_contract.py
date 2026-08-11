"""Strict seven-column checks layered on the canonical scene_plan artifact."""

from __future__ import annotations

from typing import Any

from schemas.artifacts import validate_artifact


class SevenColumnValidationError(ValueError):
    """Raised when a canonical scene_plan cannot be presented as seven columns."""


def _required_text(scene: dict[str, Any], field: str) -> None:
    if field not in scene or not isinstance(scene[field], str) or not scene[field].strip():
        raise SevenColumnValidationError(f"{scene.get('id', '<missing>')}: missing {field}")


def validate_seven_column_scene_plan(
    plan: dict[str, Any],
    *,
    require_review_decisions: bool = False,
) -> None:
    """Validate the human seven-column contract without creating another SSOT."""
    validate_artifact("scene_plan", plan)
    scenes = plan.get("scenes") or []
    ids = [scene.get("id") for scene in scenes]
    if len(ids) != len(set(ids)):
        raise SevenColumnValidationError("scene_plan.scenes[].id must be unique")

    seen: set[str] = set()
    for scene in scenes:
        sid = scene["id"]
        _required_text(scene, "script_section_id")
        _required_text(scene, "description")
        _required_text(scene, "layout_notes")
        if "dialogue" not in scene or not isinstance(scene["dialogue"], str):
            raise SevenColumnValidationError(f"{sid}: dialogue/VO column missing")
        voice_ids = scene.get("voice_segment_ids")
        if not isinstance(voice_ids, list) or not voice_ids:
            raise SevenColumnValidationError(f"{sid}: voice_segment_ids join missing")
        if scene["end_seconds"] <= scene["start_seconds"]:
            raise SevenColumnValidationError(f"{sid}: duration must be positive")
        sound = scene.get("sound_intent")
        if not isinstance(sound, dict) or "se" not in sound or "bgm_mood" not in sound:
            raise SevenColumnValidationError(f"{sid}: sound_intent column incomplete")

        visual = scene.get("visual_ref")
        reuse = scene.get("reuse")
        if bool(visual) == bool(reuse):
            raise SevenColumnValidationError(
                f"{sid}: provide exactly one of visual_ref or reuse"
            )
        if reuse:
            source = reuse.get("source_cut_id")
            if source not in seen:
                raise SevenColumnValidationError(
                    f"{sid}: reuse source_cut_id must reference an earlier cut"
                )
        elif visual.get("kind") == "api_image":
            _required_text(scene, "t2i_prompt")
            provenance = scene.get("image_provenance")
            required = {
                "provider", "model", "seed", "size", "request_id",
                "cost_or_plan_usage", "output_hash", "license_policy",
            }
            if not isinstance(provenance, dict) or not required.issubset(provenance):
                raise SevenColumnValidationError(f"{sid}: API reference provenance incomplete")
        elif visual.get("kind") == "placeholder" and not visual.get("placeholder_reason"):
            raise SevenColumnValidationError(f"{sid}: placeholder_reason required")

        if require_review_decisions:
            decision = scene.get("review_decision")
            if decision not in {"keep", "change", "merge", "omit"}:
                raise SevenColumnValidationError(f"{sid}: final cut decision missing")
            if decision == "merge" and not scene.get("merge_target_id"):
                raise SevenColumnValidationError(f"{sid}: merge_target_id required")
        seen.add(sid)


def assert_static_image_capability(tool_info: dict[str, Any]) -> None:
    """Mechanically reject routing a static reference to a video capability."""
    capability = tool_info.get("capability")
    if capability != "image_generation":
        raise SevenColumnValidationError(
            f"Static scene-plan references require image_generation, got {capability!r}"
        )
