from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.scene_eligibility import evaluate_scene_eligibility, assert_director_review_eligible
from lib.creative_loop import CreativeLoopError


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


if __name__ == "__main__":
    test_placeholder_is_not_director_reviewable()
    test_source_reuse_cap()
    print("ok")
