from __future__ import annotations

import json
from pathlib import Path

from lib.quality_observation import evaluate_quality_observation, last_extracted_still

SHOWPIECE = Path(r"C:\ContentStudio\jobs\vid-showpiece-kitchen-mcu-v1")
S2 = SHOWPIECE / "working" / "prime_rlm" / "rollouts" / "s2-10869730e0b7"


def test_s2_live_limited_local_is_not_full_motion_fail():
    observation = json.loads((S2 / "OBSERVATION.json").read_text(encoding="utf-8-sig"))
    temporal = json.loads((S2 / "see" / "temporal_motion_report.json").read_text(encoding="utf-8-sig"))
    proposal = json.loads(
        (SHOWPIECE / "working" / "prime_rlm" / "scene_proposals" / "scene_showpiece.json").read_text(
            encoding="utf-8-sig"
        )
    )
    shot = next(row for row in proposal["shots"] if row["id"] == "S2")
    quality = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=temporal,
        start_still=SHOWPIECE / "working" / "prime_rlm" / "keyframes" / "S2.png",
        last_still=last_extracted_still(
            json.loads((S2 / "see" / "frame_packet.json").read_text(encoding="utf-8-sig"))
        ),
        framing="medium_close",
    )
    assert "performance_not_full_motion" not in quality["blockers"]
    assert quality["blockers"] == []
    assert quality["passed"] is True
    assert quality["checks"]["freeze_notice"]["result"] == "PASS"
    assert quality["checks"]["breath_tension"]["result"] == "PASS"
    assert quality["checks"]["eye_shift_hold"]["result"] == "UNMEASURED"
    assert quality["beat_realization_unresolved"] is True
    assert "eye_shift_hold" in quality["unresolved_beats"]

JOB = Path(r"C:\ContentStudio\jobs\vid3-blacklisted-chef-90s-v1")
B2 = JOB / "working" / "prime_rlm" / "rollouts" / "b2-8d6a7c3d89ed"


def test_b2_live_rollout_fails_identity_and_gait_contract():
    observation = json.loads((B2 / "OBSERVATION.json").read_text(encoding="utf-8-sig"))
    temporal = json.loads((B2 / "see" / "temporal_motion_report.json").read_text(encoding="utf-8-sig"))
    packet = json.loads((B2 / "see" / "frame_packet.json").read_text(encoding="utf-8-sig"))
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "unhurried approach, full-body locomotion",
            "visual_intent": "Lucien Mercer walks the length of the kitchen toward Avery",
        },
        observation=observation,
        temporal=temporal,
        start_still=JOB / "working" / "prime_rlm" / "keyframes" / "B1.png",
        last_still=last_extracted_still(packet),
        framing="full_body",
    )
    assert quality["passed"] is False
    assert "identity_weak" in quality["blockers"]
    assert "gait_failure" in quality["blockers"]
    assert "performance_not_full_motion" not in quality["blockers"]
    assert quality["checks"]["character_actually_moves"]["result"] == "PASS"
    assert observation["media_valid"] is True
    assert observation["source_hash_matches"] is True


def test_mcu_performance_with_full_motion_does_not_invent_gait_fail():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one breath, hold",
        },
        observation={"character_motion_present": True},
        temporal={"motion_type": {"segment_1": "FULL_MOTION"}, "mouth_motion": "unmeasured"},
    )
    assert "gait_failure" not in quality["blockers"]
    assert "performance_not_full_motion" not in quality["blockers"]
    assert quality["checks"]["limb_gait_gross"]["result"] == "PASS"
    assert quality["checks"]["mouth_state"]["result"] == "UNMEASURED"
    assert quality["checks"]["character_actually_moves"]["result"] == "PASS"


def test_mcu_limited_local_is_not_a_full_motion_fail():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
            "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
        },
        observation={"character_motion_present": True},
        temporal={
            "motion_type": {
                "segment_1": "LIMITED_LOCAL_MOTION",
                "segment_2": "STATIC_HOLD",
                "segment_3": "CAMERA_ONLY",
            },
            "local_character_motion": "present",
            "longest_static_run": 0.9,
            "mouth_motion": "unmeasured",
        },
    )
    assert quality["passed"] is True
    assert quality["blockers"] == []
    assert "performance_not_full_motion" not in quality["blockers"]
    assert quality["checks"]["freeze_notice"]["result"] == "PASS"
    assert quality["checks"]["breath_tension"]["result"] == "PASS"
    assert quality["checks"]["eye_shift_hold"]["result"] == "UNMEASURED"
    assert quality["beat_realization_unresolved"] is True
    assert "eye_shift_hold" in quality["unresolved_beats"]
    assert "TEMPORAL_BEAT_REALIZATION_UNRESOLVED" in (quality["verdict"] or "")


def test_mcu_eye_shift_absent_is_the_real_blocker():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
            "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
        },
        observation={"character_motion_present": True},
        temporal={
            "motion_type": {
                "segment_1": "LIMITED_LOCAL_MOTION",
                "segment_2": "STATIC_HOLD",
            },
            "local_character_motion": "present",
            "longest_static_run": 0.9,
            "eye_shift": "absent",
            "mouth_motion": "unmeasured",
        },
    )
    assert quality["passed"] is False
    assert quality["blockers"] == ["eye_shift_not_realized"]
    assert quality["beat_realization_unresolved"] is False


def test_mcu_declared_beats_proven_is_first_take_not_unresolved():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
            "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
        },
        observation={"character_motion_present": True},
        temporal={
            "motion_type": {
                "segment_1": "LIMITED_LOCAL_MOTION",
                "segment_2": "STATIC_HOLD",
            },
            "local_character_motion": "present",
            "longest_static_run": 0.9,
            "eye_shift": "present",
            "mouth_motion": "unmeasured",
        },
    )
    assert quality["passed"] is True
    assert quality["blockers"] == []
    assert quality["beat_realization_unresolved"] is False
    assert quality["checks"]["eye_shift_hold"]["result"] == "PASS"


def test_declared_freeze_and_weight_shift_never_opens_eye_probe():
    from lib.reference_atom import infer_atom_ids

    contract = {
        "motion_obligation": "PERFORMANCE",
        "performance_intent": "freeze, raise or turn the head, clench a hand, stop. No locomotion.",
        "reference_atoms": ["freeze_notice", "weight_shift"],
    }
    assert infer_atom_ids(contract) == ["freeze_notice", "weight_shift"]
    quality = evaluate_quality_observation(
        contract=contract,
        observation={"character_motion_present": True},
        temporal={
            "motion_type": {
                "segment_1": "STATIC_HOLD",
                "segment_2": "LIMITED_LOCAL_MOTION",
                "segment_3": "STATIC_HOLD",
            },
            "local_character_motion": "present",
            "longest_static_run": 0.8,
        },
    )
    assert "eye_shift_hold" not in quality["checks"]
    assert "eye_shift_hold" not in (quality.get("unresolved_beats") or [])
    assert quality["checks"]["freeze_notice"]["result"] == "PASS"
    assert quality["checks"]["weight_shift"]["result"] == "PASS"
    assert quality["passed"] is True
    assert quality["beat_realization_unresolved"] is False


def test_weight_shift_camera_only_is_a_real_blocker():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "freeze, turn the head, stop. No locomotion.",
            "reference_atoms": ["freeze_notice", "weight_shift"],
        },
        observation={"character_motion_present": False},
        temporal={
            "motion_type": {"segment_1": "CAMERA_ONLY"},
            "local_character_motion": "absent",
            "longest_static_run": 0.0,
        },
    )
    assert "weight_shift_not_realized" in quality["blockers"]
    assert "character_did_not_move" in quality["blockers"]
    assert "eye_shift_not_realized" not in quality["blockers"]


def test_blink_false_is_not_eye_shift_fail():
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
            "reference_atoms": ["eye_shift_hold"],
        },
        observation={"character_motion_present": True},
        temporal={
            "motion_type": {"segment_1": "LIMITED_LOCAL_MOTION"},
            "local_character_motion": "present",
            "blink_detected": False,
        },
    )
    assert "eye_shift_not_realized" not in quality["blockers"]
    assert quality["checks"]["eye_shift_hold"]["result"] == "UNMEASURED"
