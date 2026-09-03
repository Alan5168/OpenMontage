from lib.reference_atom import compile_temporal_reference, infer_atom_ids


def test_explicit_atoms_win_over_walk_words():
    ids = infer_atom_ids(
        {
            "performance_intent": "Lucien walks toward Avery ominously",
            "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
        }
    )
    assert ids == ["freeze_notice", "breath_tension", "eye_shift_hold"]


def test_two_step_stop_is_not_an_eight_second_walk():
    temporal = compile_temporal_reference(
        {"performance_intent": "two-step stop. Alternate legs. Then still."},
        duration_seconds=5,
    )
    assert temporal["atom_ids"] == ["weight_shift", "two_step_stop"]
    assert temporal["locomotion"] is True
    assert temporal["shots"][-1]["atom_id"] == "two_step_stop"
