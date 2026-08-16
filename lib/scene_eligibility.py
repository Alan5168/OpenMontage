"""Cheap layer: is this a film, or technical previz?

Pixel motion is not character performance. Grammar-clear is not director-reviewable.
High-cost visual critique is illegal while this report says ineligible.
"""

from __future__ import annotations

from typing import Any

from lib.creative_loop import CreativeLoopError

REPORT_VERSION = "scene-eligibility/v0.1"

KEN_BURNS_MAX_FRACTION = 0.20
SOURCE_REUSE_MAX_FRACTION = 0.25
FIRST_SOUND_MAX_SECONDS = 0.5
SILENCE_DB = -40.0


def evaluate_scene_eligibility(
    *,
    duration_seconds: float,
    cuts: list[dict[str, Any]] | None,
    temporal_report: dict[str, Any] | None,
    audio_map: dict[str, Any] | None,
    declaration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cuts = [c for c in (cuts or []) if isinstance(c, dict)]
    declaration = declaration if isinstance(declaration, dict) else {}
    audio_map = audio_map if isinstance(audio_map, dict) else {}
    duration = max(float(duration_seconds or 0), 0.001)
    blockers: list[str] = []

    placeholder = bool(declaration.get("placeholder_composite")) or any(
        c.get("placeholder_composite") for c in cuts
    )
    if placeholder:
        blockers.append("placeholder_composite_present")

    reuse = _source_reuse_fraction(cuts, duration)
    if reuse > SOURCE_REUSE_MAX_FRACTION:
        blockers.append("same_source_reuse_over_cap")

    ken = _ken_burns_fraction(cuts, duration)
    if ken > KEN_BURNS_MAX_FRACTION:
        blockers.append("ken_burns_over_cap")

    first_sound = audio_map.get("first_sound_seconds")
    if first_sound is None or float(first_sound) > FIRST_SOUND_MAX_SECONDS:
        blockers.append("first_sound_missing_or_late")

    silence_15 = float(audio_map.get("unplanned_silence_seconds_first_15") or 0)
    if silence_15 > 1.0:
        blockers.append("unplanned_silence_in_opening")

    if audio_map.get("intent_coverage", 0) < 1.0 and audio_map.get("measured"):
        if float(audio_map.get("audible_fraction") or 0) < 0.85:
            blockers.append("audio_timeline_incomplete")

    split = _motion_split(temporal_report, cuts)
    for cut in cuts:
        if cut.get("requires_performance") and _cut_has_no_performance(cut, temporal_report):
            blockers.append(f"performance_shot_without_character_motion:{cut.get('id')}")
            break

    eligible = not blockers
    return {
        "version": REPORT_VERSION,
        "director_review_eligible": eligible,
        "blockers": blockers,
        "duration_seconds": round(duration, 3),
        "character_performance_motion": split["character_performance_motion"],
        "camera_only_motion": split["camera_only_motion"],
        "overlay_or_ambient_fx_motion": split["overlay_or_ambient_fx_motion"],
        "pixel_motion_coverage": (temporal_report or {}).get("motion_coverage"),
        "pixel_motion_is_not_performance": True,
        "same_source_reuse": round(reuse, 4),
        "ken_burns_fraction": round(ken, 4),
        "placeholder_composite_present": placeholder,
        "unplanned_audio_silence_seconds": round(float(audio_map.get("unplanned_silence_seconds") or 0), 3),
        "first_sound_seconds": first_sound,
        "judgment": "eligibility_only",
        "note": "Ineligible means technical previz. Do not call a high-cost visual critic. Do not offer as scene master.",
    }


def assert_director_review_eligible(report: dict[str, Any] | None) -> None:
    if not isinstance(report, dict) or report.get("version") != REPORT_VERSION:
        raise CreativeLoopError("SEE incomplete: scene eligibility report required before director review")
    if report.get("director_review_eligible") is not True:
        blockers = report.get("blockers") or ["ineligible"]
        raise CreativeLoopError(
            "technical previz, not a film; director review blocked: " + ", ".join(str(b) for b in blockers)
        )


def _source_reuse_fraction(cuts: list[dict[str, Any]], duration: float) -> float:
    by_src: dict[str, float] = {}
    for cut in cuts:
        src = str(cut.get("source_asset") or "").strip()
        if not src:
            continue
        by_src[src] = by_src.get(src, 0.0) + max(0.0, float(cut.get("t_end") or 0) - float(cut.get("t_start") or 0))
    if not by_src:
        return 0.0
    return max(by_src.values()) / duration


def _ken_burns_fraction(cuts: list[dict[str, Any]], duration: float) -> float:
    total = 0.0
    for cut in cuts:
        intent = str(cut.get("temporal_intent") or "")
        if intent in {"camera_only"} and not cut.get("requires_performance"):
            plate = str(cut.get("plate_kind") or "")
            if plate in {"environment_only", "still", "environment_with_character"} and not cut.get("cycle_allowed"):
                total += max(0.0, float(cut.get("t_end") or 0) - float(cut.get("t_start") or 0))
    return total / duration


def _motion_split(temporal: dict[str, Any] | None, cuts: list[dict[str, Any]]) -> dict[str, str]:
    motion = (temporal or {}).get("motion_type") or {}
    types = list(motion.values()) if isinstance(motion, dict) else list(motion)
    if any(c.get("requires_performance") for c in cuts) and types and set(types) <= {"STATIC_HOLD", "CAMERA_ONLY"}:
        character = "very_low"
    elif "FULL_MOTION" in types:
        character = "present"
    elif "LIMITED_LOCAL_MOTION" in types:
        character = "unseparated_from_fx_or_loop"
    else:
        character = "very_low"
    camera = "high" if "CAMERA_ONLY" in types else ("present" if types else "none")
    fx = "medium" if "LIMITED_LOCAL_MOTION" in types else "low"
    return {
        "character_performance_motion": character,
        "camera_only_motion": camera,
        "overlay_or_ambient_fx_motion": fx,
    }


def _cut_has_no_performance(cut: dict[str, Any], temporal: dict[str, Any] | None) -> bool:
    if not temporal:
        return True
    t0 = float(cut.get("t_start") or 0)
    t1 = float(cut.get("t_end") or t0)
    segs = [s for s in (temporal.get("segments") or []) if isinstance(s, dict)]
    kinds = []
    for seg in segs:
        a, b = float(seg.get("t_start") or 0), float(seg.get("t_end") or 0)
        if b > t0 and a < t1:
            kinds.append(str(seg.get("motion_type")))
    return bool(kinds) and set(kinds) <= {"STATIC_HOLD", "CAMERA_ONLY"}
