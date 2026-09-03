from lib.h3_capability_map import classify_h3_capability
from lib.h3_coverage_previs import (
    ETHANFEL_VIEW_FRAMES,
    build_coverage_prompt,
)


def test_coverage_prompt_fills_picture_one_and_eight_shots():
    prompt = build_coverage_prompt()
    assert prompt.count("<Picture 1>") >= 8
    for n in range(1, 9):
        assert f"[Shot {n}]" in prompt
    assert "00:04.167" in prompt
    assert "COMP_" not in prompt
    assert "SHOT_KEYFRAME" not in prompt
    assert "in," not in prompt.split("subject_definitions", 1)[-1][:80]


def test_ethanfel_extract_table_is_eight_frames():
    assert ETHANFEL_VIEW_FRAMES == (2, 15, 31, 46, 62, 77, 92, 108)


def test_composition_previs_is_opt_in_not_inferred():
    assert (
        classify_h3_capability({"h3_capability": "COMPOSITION_PREVIS"})
        == "COMPOSITION_PREVIS"
    )
    assert (
        classify_h3_capability(
            {
                "motion_obligation": "PERFORMANCE",
                "performance_intent": "Hold.",
                "shot_language": {"camera_movement": "static"},
            }
        )
        != "COMPOSITION_PREVIS"
    )
