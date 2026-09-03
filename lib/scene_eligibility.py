"""Cheap layer: is this a film, or technical previz?

Pixel motion is not character performance. Grammar-clear is not director-reviewable.
High-cost visual critique is illegal while this report says ineligible.

LIMITED_LOCAL (steam / HUD / ambient) does not realize a PERFORMANCE obligation.
Intentional STATIC_HOLD is legal when the shot did not declare performance.
"""

from __future__ import annotations

from typing import Any

from lib.creative_loop import CreativeLoopError
from lib.motion_obligation import DYNAMIC, ShotCompileError, resolve_motion_obligation

REPORT_VERSION = "scene-eligibility/v0.1"

KEN_BURNS_MAX_FRACTION = 0.20
SOURCE_REUSE_MAX_FRACTION = 0.25
FIRST_SOUND_MAX_SECONDS = 0.5
SILENCE_DB = -40.0
CHARACTER_PERFORMANCE_TYPES = frozenset({"FULL_MOTION"})


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
    realization = _temporal_intent_realization(cuts, temporal_report)
    for row in realization:
        if row["result"] == "FAIL":
            blockers.append(f"performance_shot_without_character_motion:{row['cut_id']}")
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
        "temporal_intent_realization": realization,
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


def _cut_window(cut: dict[str, Any]) -> tuple[float, float]:
    t0 = cut.get("t_start", cut.get("start_seconds"))
    t1 = cut.get("t_end", cut.get("end_seconds"))
    start = float(t0 or 0)
    end = float(t1 if t1 is not None else start)
    return start, end


def _obligation(cut: dict[str, Any]) -> str:
    try:
        return resolve_motion_obligation(cut)
    except ShotCompileError:
        if cut.get("requires_performance") is True:
            return "PERFORMANCE"
        return "NONE"


def _performance_windows(cut: dict[str, Any]) -> list[tuple[float, float, str]]:
    """Windows that must show character performance, not FX MAD."""
    cut_t0, cut_t1 = _cut_window(cut)
    windows: list[tuple[float, float, str]] = []
    for beat in cut.get("temporal_beats") or []:
        if not isinstance(beat, dict):
            continue
        kind = str(beat.get("kind") or "").strip().upper()
        if kind != "CHARACTER_PERFORMANCE":
            continue
        b0 = float(beat.get("t_start") if beat.get("t_start") is not None else cut_t0)
        b1 = float(beat.get("t_end") if beat.get("t_end") is not None else cut_t1)
        windows.append((b0, b1, kind))
    if windows:
        return windows
    if _obligation(cut) in DYNAMIC or cut.get("requires_performance") is True:
        return [(cut_t0, cut_t1, "CHARACTER_PERFORMANCE")]
    return []


def _overlapping_types(
    temporal: dict[str, Any] | None,
    t0: float,
    t1: float,
) -> list[str]:
    if not temporal:
        return []
    kinds: list[str] = []
    for seg in temporal.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        a, b = float(seg.get("t_start") or 0), float(seg.get("t_end") or 0)
        if b > t0 and a < t1:
            kinds.append(str(seg.get("motion_type") or ""))
    if kinds:
        return kinds
    motion = temporal.get("motion_type") or {}
    if isinstance(motion, dict):
        return [str(v) for v in motion.values()]
    if isinstance(motion, list):
        return [str(v) for v in motion]
    return []


def _temporal_intent_realization(
    cuts: list[dict[str, Any]],
    temporal: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cut in cuts:
        for t0, t1, declared in _performance_windows(cut):
            observed = _overlapping_types(temporal, t0, t1)
            realized = any(kind in CHARACTER_PERFORMANCE_TYPES for kind in observed)
            rows.append(
                {
                    "cut_id": str(cut.get("id") or ""),
                    "declared": declared,
                    "observed": observed,
                    "result": "PASS" if realized else "FAIL",
                }
            )
    return rows


def _cut_has_no_performance(cut: dict[str, Any], temporal: dict[str, Any] | None) -> bool:
    """True when a declared performance window was not realized. Fail closed."""
    return any(row["result"] == "FAIL" for row in _temporal_intent_realization([cut], temporal))
