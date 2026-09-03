from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from lib.scene_eligibility import evaluate_scene_eligibility, assert_director_review_eligible
from lib.creative_loop import CreativeLoopError
from schemas.artifacts import validate_artifact

JOB = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs")) / "vid3-blacklisted-chef-90s-v1"

_AUDIO_OK = {
    "first_sound_seconds": 0.0,
    "unplanned_silence_seconds_first_15": 0,
    "intent_coverage": 1.0,
    "measured": True,
    "audible_fraction": 1.0,
    "unplanned_silence_seconds": 0.0,
}


def test_placeholder_is_not_director_reviewable():
    report = evaluate_scene_eligibility(
        duration_seconds=30,
        cuts=[{
            "id": "A4", "t_start": 12, "t_end": 17,
            "temporal_intent": "camera_only",
            "plate_kind": "environment_with_character",
            "placeholder_composite": True,
        }],
        temporal_report={"motion_type": {"segment_1": "CAMERA_ONLY"}, "segments": []},
        audio_map={"first_sound_seconds": 0.2, "unplanned_silence_seconds_first_15": 0, "intent_coverage": 1.0, "measured": True, "audible_fraction": 1.0},
        declaration={"placeholder_composite": True},
    )
    assert report["director_review_eligible"] is False
    assert "placeholder_composite_present" in report["blockers"]
    try:
        assert_director_review_eligible(report)
        raise SystemExit("should have blocked")
    except CreativeLoopError as exc:
        assert "previz" in str(exc)


def test_source_reuse_cap():
    cuts = [
        {"id": "A3", "t_start": 4.5, "t_end": 12, "source_asset": "loop640"},
        {"id": "A5", "t_start": 17, "t_end": 25, "source_asset": "loop640"},
        {"id": "A6", "t_start": 25, "t_end": 30, "source_asset": "loop640"},
    ]
    report = evaluate_scene_eligibility(
        duration_seconds=30,
        cuts=cuts,
        temporal_report={"motion_type": {"s": "LIMITED_LOCAL_MOTION"}, "segments": []},
        audio_map={"first_sound_seconds": 0.1, "unplanned_silence_seconds_first_15": 0, "intent_coverage": 1.0, "measured": True, "audible_fraction": 1.0},
    )
    assert report["same_source_reuse"] > 0.6
    assert "same_source_reuse_over_cap" in report["blockers"]


def _v5_temporal() -> dict:
    path = JOB / "working" / "scene_a" / "see" / "temporal_motion_report.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _v5_cuts() -> list[dict]:
    path = JOB / "working" / "scene_a" / "LIMITED_GRAMMAR_CUTS.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return [row for row in payload["cuts"] if isinstance(row, dict)]


def _v5_audio() -> dict:
    path = JOB / "working" / "scene_a" / "see" / "audio_event_map.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.mark.skipif(
    not (JOB / "working" / "scene_a" / "see" / "scene_eligibility.json").is_file(),
    reason="Scene A corpus fixture not present",
)
def test_false_director_eligibility_01_fail_closed():
    """Scene A v5 master: PERFORMANCE cuts observed as steam/HUD LIMITED_LOCAL."""
    fossil = JOB / "working" / "scene_a" / "see" / "scene_eligibility.json"
    observed = json.loads(fossil.read_text(encoding="utf-8-sig"))
    assert observed["director_review_eligible"] is True
    assert observed["pixel_motion_coverage"] == 0.5858
    assert observed["character_performance_motion"] == "unseparated_from_fx_or_loop"

    report = evaluate_scene_eligibility(
        duration_seconds=30.0,
        cuts=_v5_cuts(),
        temporal_report=_v5_temporal(),
        audio_map=_v5_audio(),
    )
    validate_artifact("scene_eligibility", report)
    assert report["director_review_eligible"] is False
    assert report["pixel_motion_is_not_performance"] is True
    blockers = report["blockers"]
    assert any(b.startswith("performance_shot_without_character_motion:") for b in blockers)
    assert any(row["cut_id"] in {"A5", "A6"} and row["result"] == "FAIL" for row in report["temporal_intent_realization"])
    assert "LIMITED_LOCAL_MOTION" in {
        kind
        for row in report["temporal_intent_realization"]
        if row["result"] == "FAIL"
        for kind in row["observed"]
    }
    fossil_after = json.loads(fossil.read_text(encoding="utf-8-sig"))
    assert fossil_after == observed


def test_intentional_static_hold_still_passes():
    report = evaluate_scene_eligibility(
        duration_seconds=4.0,
        cuts=[{
            "id": "A2",
            "t_start": 0.0,
            "t_end": 4.0,
            "temporal_intent": "intentional_hold",
            "intentional_hold": True,
            "motion_obligation": "NONE",
            "requires_performance": False,
            "character_ids": ["avery_sterling"],
        }],
        temporal_report={
            "motion_type": {"segment_1": "STATIC_HOLD"},
            "motion_coverage": 0.0,
            "segments": [{"t_start": 0.0, "t_end": 4.0, "motion_type": "STATIC_HOLD"}],
        },
        audio_map=_AUDIO_OK,
    )
    validate_artifact("scene_eligibility", report)
    assert report["director_review_eligible"] is True
    assert report["blockers"] == []
    assert report["temporal_intent_realization"] == []


def test_isolated_performance_full_motion_not_false_killed():
    """A5/A6-shaped PERFORMANCE cuts with matching FULL_MOTION observation still PASS."""
    temporal = {
        "motion_type": {"segment_1": "FULL_MOTION"},
        "motion_coverage": 0.82,
        "segments": [{"t_start": 0.0, "t_end": 5.0, "motion_type": "FULL_MOTION"}],
    }
    for shot_id, obligation in (("A5", "PERFORMANCE"), ("A6", "PERFORMANCE")):
        report = evaluate_scene_eligibility(
            duration_seconds=5.0,
            cuts=[{
                "id": shot_id,
                "t_start": 0.0,
                "t_end": 5.0,
                "motion_obligation": obligation,
                "animation_class": "I2V_HARD",
                "requires_performance": True,
                "character_ids": ["avery_sterling"],
                "temporal_beats": [{
                    "kind": "CHARACTER_PERFORMANCE",
                    "t_start": 0.0,
                    "t_end": 5.0,
                }],
            }],
            temporal_report=temporal,
            audio_map=_AUDIO_OK,
        )
        validate_artifact("scene_eligibility", report)
        assert report["director_review_eligible"] is True, shot_id
        assert report["blockers"] == []
        assert report["temporal_intent_realization"][0]["result"] == "PASS"


def test_limited_local_fx_does_not_count_as_performance():
    report = evaluate_scene_eligibility(
        duration_seconds=8.0,
        cuts=[{
            "id": "A5",
            "t_start": 0.0,
            "t_end": 8.0,
            "motion_obligation": "PERFORMANCE",
            "requires_performance": True,
            "animation_class": "I2V_HARD",
            "character_ids": ["avery_sterling"],
        }],
        temporal_report={
            "motion_type": {"segment_1": "LIMITED_LOCAL_MOTION"},
            "motion_coverage": 0.58,
            "segments": [{"t_start": 0.0, "t_end": 8.0, "motion_type": "LIMITED_LOCAL_MOTION"}],
            "local_character_motion": "present",
        },
        audio_map=_AUDIO_OK,
    )
    assert report["director_review_eligible"] is False
    assert "performance_shot_without_character_motion:A5" in report["blockers"]
    assert report["character_performance_motion"] == "unseparated_from_fx_or_loop"


if __name__ == "__main__":
    test_placeholder_is_not_director_reviewable()
    test_source_reuse_cap()
    test_false_director_eligibility_01_fail_closed()
    test_intentional_static_hold_still_passes()
    test_isolated_performance_full_motion_not_false_killed()
    test_limited_local_fx_does_not_count_as_performance()
    print("ok")
