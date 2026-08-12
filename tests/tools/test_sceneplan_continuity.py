from __future__ import annotations

from tools.sceneplan_continuity import evaluate_visual_continuity


def test_single_mother_passes():
    plan = {
        "scenes": [
            {"id": "c01", "t2i_prompt": "gate"},
            {"id": "c02", "reuse": {"source_cut_id": "c01"}, "t2i_prompt": "ignored"},
        ]
    }
    assert evaluate_visual_continuity(plan)["status"] == "PASS"


def test_independent_mothers_fail_without_package():
    plan = {
        "scenes": [
            {"id": "c01", "t2i_prompt": "world A camera front"},
            {"id": "c04", "t2i_prompt": "world B camera top"},
            {"id": "c06", "t2i_prompt": "world C wide room"},
        ]
    }
    result = evaluate_visual_continuity(plan)
    assert result["status"] == "FAIL"
    assert result["verdict_tag"].startswith("CONTINUITY_FAIL")


def test_allowed_mode_with_world_lock_passes():
    plan = {
        "visual_continuity_package": {
            "generation_mode": "one_mother_edit",
            "world_lock": {"palette": "matte red boundary", "hero": "result card"},
            "hero_prop_id": "result_card_gate",
            "camera_language": "locked three-quarter editorial",
            "alan_continuous_animation_ok": None,
        },
        "scenes": [
            {"id": "c01", "t2i_prompt": "mother"},
            {"id": "c04", "t2i_prompt": "edit of mother"},
        ],
    }
    assert evaluate_visual_continuity(plan)["status"] == "PASS"
