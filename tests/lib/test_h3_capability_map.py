from lib.h3_capability_map import classify_h3_capability, route_h3_capability


def test_micro_performance_routes_to_turbo_candidate():
    row = route_h3_capability(
        {
            "motion_obligation": "PERFORMANCE",
            "character_ids": ["avery_sterling"],
            "performance_intent": "Hold. Shallow breath. Fingers tighten.",
            "shot_language": {"camera_movement": "static"},
        }
    )
    assert row["capability"] == "MICRO_PERFORMANCE"
    assert row["ship"] == "h3_fl2va_nvfp4"
    assert "h3_fl2va_turbo_v4" in row["candidates"]
    assert "h3_fl2va_pdd_acc_8" in row["candidates"]
    assert row["turbo_in_ship_graph"] is False
    assert row["pdd_in_ship_graph"] is False
    assert row["ref2va_runtime_available"] is False


def test_two_shot_is_interaction_not_a_style_lora():
    assert (
        classify_h3_capability(
            {
                "motion_obligation": "INTERACTION",
                "character_ids": ["avery_sterling", "lucien_mercer"],
            }
        )
        == "INTERACTION"
    )


def test_walk_is_locomotion():
    assert (
        classify_h3_capability(
            {
                "motion_obligation": "PERFORMANCE",
                "character_ids": ["lucien_mercer"],
                "performance_intent": "Lucien walks toward Avery.",
            }
        )
        == "LOCOMOTION"
    )


def test_push_in_is_camera_motion():
    assert (
        classify_h3_capability(
            {
                "motion_obligation": "PERFORMANCE",
                "character_ids": ["avery_sterling"],
                "performance_intent": "Hold.",
                "shot_language": {"camera_movement": "dolly_in"},
            }
        )
        == "CAMERA_MOTION"
    )
