"""Did the contracted performance happen? Cheap failures only.

Evidence binding (hash / frames / duration) already exists on Observation.
This layer answers contract questions. It is not a taste model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.keyframe_presentation import evaluate_keyframe_presentation
from lib.reference_atom import infer_atom_ids, locomotion_declared

QUALITY_SCHEMA = "om-quality-observation/v1"
# Walk/gait contracts may use FULL_MOTION. MCU PERFORMANCE may use LIMITED_LOCAL_MOTION.
LOCOMOTION_TYPES = frozenset({"FULL_MOTION"})
CHARACTER_SCALE_TYPES = frozenset({"FULL_MOTION", "LIMITED_LOCAL_MOTION"})
MCU_BEATS = ("freeze_notice", "breath_tension", "eye_shift_hold")
# weight_shift is judged from existing SEE motion classes, not a pose classifier.
SENSOR_BEATS = MCU_BEATS + ("weight_shift",)


def evaluate_quality_observation(
    *,
    contract: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    temporal: dict[str, Any] | None,
    start_still: Path | str | None = None,
    last_still: Path | str | None = None,
    framing: str = "medium_close",
) -> dict[str, Any]:
    contract = contract if isinstance(contract, dict) else {}
    observation = observation if isinstance(observation, dict) else {}
    temporal = temporal if isinstance(temporal, dict) else {}
    checks: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []

    start_report = (
        evaluate_keyframe_presentation(start_still, framing=framing)
        if start_still
        else None
    )
    last_report = (
        evaluate_keyframe_presentation(last_still, framing=framing)
        if last_still
        else None
    )

    obligation = str(contract.get("motion_obligation") or "")
    intent = str(contract.get("performance_intent") or contract.get("visual_intent") or "")
    needs_performance = obligation == "PERFORMANCE" or locomotion_declared(intent)

    identity_start = bool(start_report and start_report.get("usable"))
    identity_last = None if last_report is None else bool(last_report.get("usable"))
    if start_report and not identity_start:
        checks["identity_drift"] = {
            "result": "FAIL",
            "detail": "start_identity_weak",
            "blockers": start_report.get("blockers") or [],
        }
        blockers.append("identity_weak")
    elif last_report is not None and identity_start and identity_last is False:
        checks["identity_drift"] = {
            "result": "FAIL",
            "detail": "identity_lost_by_end",
            "blockers": last_report.get("blockers") or [],
        }
        blockers.append("identity_drift")
    elif start_report is None:
        checks["identity_drift"] = {"result": "UNMEASURED", "detail": "no_start_still"}
    else:
        checks["identity_drift"] = {"result": "PASS", "detail": "identity_held"}

    if last_report is not None and (
        "identity_not_visible" in (last_report.get("blockers") or [])
        or "costume_unresolved" in (last_report.get("blockers") or [])
    ):
        checks["face_costume_disappear"] = {
            "result": "FAIL",
            "detail": last_report.get("blockers"),
        }
        blockers.append("face_or_costume_disappear")
    elif last_report is None:
        checks["face_costume_disappear"] = {"result": "UNMEASURED", "detail": "no_last_still"}
    else:
        checks["face_costume_disappear"] = {"result": "PASS"}

    motion_types = _motion_types(temporal)
    local_character = str(temporal.get("local_character_motion") or "")
    character_moved = bool(observation.get("character_motion_present")) or bool(
        motion_types & CHARACTER_SCALE_TYPES
    ) or local_character == "present"
    if needs_performance and not character_moved:
        checks["character_actually_moves"] = {
            "result": "FAIL",
            "detail": "no_character_motion",
            "motion_types": sorted(motion_types) or ["none"],
        }
        blockers.append("character_did_not_move")
    else:
        checks["character_actually_moves"] = {
            "result": "PASS" if character_moved or not needs_performance else "UNMEASURED",
            "detail": sorted(motion_types),
            "note": (
                "FULL_MOTION is not required for PERFORMANCE. "
                "LIMITED_LOCAL_MOTION may satisfy MCU freeze/breath/eye-hold."
            ),
        }

    checks["requested_direction"] = {
        "result": "UNMEASURED",
        "detail": "no_optical_flow_direction_probe",
    }

    loco = locomotion_declared(intent)
    if loco and not (motion_types & LOCOMOTION_TYPES):
        checks["limb_gait_gross"] = {
            "result": "FAIL",
            "detail": "locomotion_without_full_motion",
            "motion_types": sorted(motion_types),
        }
        blockers.append("gait_failure")
    elif loco:
        checks["limb_gait_gross"] = {
            "result": "UNMEASURED",
            "detail": "full_motion_present_but_gait_quality_not_scored",
        }
    else:
        checks["limb_gait_gross"] = {"result": "PASS", "detail": "not_a_locomotion_contract"}

    if last_report is None and needs_performance:
        checks["end_state_reached"] = {"result": "UNMEASURED", "detail": "no_last_still"}
    elif last_report is not None and last_report.get("usable") is not True and loco:
        checks["end_state_reached"] = {
            "result": "FAIL",
            "detail": "end_frame_unreadable",
        }
        blockers.append("end_state_unreadable")
    else:
        checks["end_state_reached"] = {"result": "UNMEASURED", "detail": "stop_distance_not_measured"}

    mouth = str(temporal.get("mouth_motion") or "unmeasured")
    if mouth == "unmeasured":
        checks["mouth_state"] = {"result": "UNMEASURED", "detail": "mouth_motion_unmeasured"}
    else:
        checks["mouth_state"] = {"result": "PASS", "detail": mouth}

    beat_checks, beat_blockers, unresolved = _evaluate_declared_beats(
        contract=contract,
        temporal=temporal,
        observation=observation,
        motion_types=motion_types,
        local_character=local_character,
        character_moved=character_moved,
    )
    checks.update(beat_checks)
    blockers.extend(beat_blockers)

    passed = not blockers
    verdict = None
    if passed and unresolved:
        verdict = "NO_VALID_BLOCKER_FROM_CURRENT_RULE; TEMPORAL_BEAT_REALIZATION_UNRESOLVED"
    return {
        "schema_version": QUALITY_SCHEMA,
        "passed": passed,
        "blockers": blockers,
        "checks": checks,
        "beat_realization_unresolved": bool(unresolved) and passed,
        "unresolved_beats": unresolved,
        "verdict": verdict,
        "start_presentation": start_report,
        "last_presentation": last_report,
        "judgment": "contract_measurement",
        "note": (
            "Not a taste model. PERFORMANCE does not require FULL_MOTION. "
            "Judge declared temporal beats. Incomplete beat probes are unresolved, "
            "not FIRST_TAKE_ACCEPTABLE and not content FAIL. "
            "Not APPROVED. Not PRIME_FOREMAN_PROVEN."
        ),
    }


def last_extracted_still(frame_packet: dict[str, Any] | None) -> Path | None:
    frames = (frame_packet or {}).get("frames") or []
    if not frames:
        return None
    last = frames[-1]
    path = Path(str(last.get("path") or ""))
    return path if path.is_file() else None


def _motion_types(temporal: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    mapping = temporal.get("motion_type") or {}
    if isinstance(mapping, dict):
        found.update(str(v) for v in mapping.values() if v)
    for row in temporal.get("segments") or []:
        if isinstance(row, dict) and row.get("motion_type"):
            found.add(str(row["motion_type"]))
    return found


def _evaluate_declared_beats(
    *,
    contract: dict[str, Any],
    temporal: dict[str, Any],
    observation: dict[str, Any],
    motion_types: set[str],
    local_character: str,
    character_moved: bool,
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    """Verify declared MCU beats. Missing probes are unresolved, not invented FAILs."""
    checks: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    unresolved: list[str] = []
    intent = str(contract.get("performance_intent") or contract.get("visual_intent") or "")
    if locomotion_declared(intent):
        return checks, blockers, unresolved
    declared = [atom_id for atom_id in infer_atom_ids(contract) if atom_id in SENSOR_BEATS]
    if not declared:
        return checks, blockers, unresolved

    static_run = float(temporal.get("longest_static_run") or 0.0)
    freeze_ok = "STATIC_HOLD" in motion_types or static_run >= 0.4
    local_ok = "LIMITED_LOCAL_MOTION" in motion_types and (
        local_character == "present" or character_moved
    )
    eye_flag = temporal.get("eye_shift")
    if eye_flag is None:
        eye_flag = observation.get("eye_shift")

    if "freeze_notice" in declared:
        if freeze_ok:
            checks["freeze_notice"] = {"result": "PASS", "detail": "static_hold_or_static_run"}
        else:
            checks["freeze_notice"] = {"result": "UNMEASURED", "detail": "hold_not_classified"}
            unresolved.append("freeze_notice")

    if "weight_shift" in declared:
        if local_ok or (character_moved and bool(motion_types & CHARACTER_SCALE_TYPES)):
            checks["weight_shift"] = {
                "result": "PASS",
                "detail": "character_scale_local_or_full_motion",
                "note": "Existing SEE motion class only. Not a head-pose or fist classifier.",
            }
        elif not character_moved and "CAMERA_ONLY" in motion_types:
            checks["weight_shift"] = {"result": "FAIL", "detail": "camera_only_no_local_character"}
            blockers.append("weight_shift_not_realized")
        else:
            checks["weight_shift"] = {"result": "UNMEASURED", "detail": "no_local_motion_probe"}
            unresolved.append("weight_shift")

    if "breath_tension" in declared:
        if local_ok:
            checks["breath_tension"] = {
                "result": "PASS",
                "detail": "limited_local_character_motion",
                "note": "Local motion evidence, not a chest-breath classifier.",
            }
        elif not character_moved and "CAMERA_ONLY" in motion_types:
            checks["breath_tension"] = {"result": "FAIL", "detail": "camera_only_no_local_character"}
            blockers.append("breath_tension_not_realized")
        else:
            checks["breath_tension"] = {"result": "UNMEASURED", "detail": "no_local_motion_probe"}
            unresolved.append("breath_tension")

    if "eye_shift_hold" in declared:
        flag = str(eye_flag or "").strip().lower()
        if flag in {"present", "detected", "true", "yes"}:
            checks["eye_shift_hold"] = {"result": "PASS", "detail": "eye_shift_probe"}
        elif flag in {"absent", "missing", "false", "no"}:
            checks["eye_shift_hold"] = {"result": "FAIL", "detail": "eye_shift_probe_absent"}
            blockers.append("eye_shift_not_realized")
        else:
            checks["eye_shift_hold"] = {"result": "UNMEASURED", "detail": "no_eye_shift_probe"}
            unresolved.append("eye_shift_hold")

    return checks, blockers, unresolved
