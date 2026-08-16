from lib.freeze_hold import (
    apply_static_hold_pad,
    freeze_hold_error,
    is_pure_static_hold,
)


def test_static_hold_over_limit_fails_with_explainer_default_pad():
    error = freeze_hold_error(
        {
            "profile": "fiction_anime_episode",
            "edit_decisions": {
                "cuts": [
                    {
                        "id": "c001",
                        "in_seconds": 0,
                        "out_seconds": 3.5,
                        "animation": "static",
                    }
                ]
            },
        },
        composition_id="Explainer",
        props={
            "cuts": [
                {
                    "id": "c001",
                    "in_seconds": 0,
                    "out_seconds": 3.5,
                    "animation": "static",
                }
            ]
        },
    )
    assert error
    assert "3.5" in error


def test_static_hold_at_limit_passes_when_pad_stripped():
    props = apply_static_hold_pad(
        {
            "cuts": [
                {
                    "id": "c001",
                    "in_seconds": 0,
                    "out_seconds": 3.5,
                    "animation": "static",
                }
            ]
        },
        "fiction_anime_episode",
    )
    assert props["padEndSeconds"] == 0
    error = freeze_hold_error(
        {"profile": "fiction_anime_episode"},
        composition_id="Explainer",
        props=props,
    )
    assert error is None


def test_ken_burns_is_not_pure_static_hold():
    assert not is_pure_static_hold({"animation": "ken-burns", "in_seconds": 0, "out_seconds": 8})
    assert (
        freeze_hold_error(
            {
                "profile": "fiction_anime_episode",
                "edit_decisions": {
                    "cuts": [
                        {
                            "id": "c002",
                            "in_seconds": 0,
                            "out_seconds": 8,
                            "animation": "ken-burns",
                        }
                    ]
                },
            }
        )
        is None
    )


def test_other_profiles_are_untouched():
    assert (
        freeze_hold_error(
            {
                "profile": "report_explainer_xhs_zh",
                "edit_decisions": {
                    "cuts": [
                        {
                            "id": "c001",
                            "in_seconds": 0,
                            "out_seconds": 6,
                            "animation": "static",
                        }
                    ]
                },
            }
        )
        is None
    )
