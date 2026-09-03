"""Shot-director semantic lint: beats must be observable in the current framing."""

from __future__ import annotations

import pytest

from lib.shot_director import (
    AVERY_FEAR_SIGNATURE,
    ShotDirectorError,
    classify_shot,
    compile_beat_actions,
    lint_temporal_beats,
)


def _cut(**overrides):
    base = {
        "cut_id": "TEST",
        "framing": "medium_close_up",
        "visual": "MCU Avery pressed against the cooler.",
        "action": "He doesn't move.",
        "character_ids": ["avery_sterling"],
        "motion_obligation": "CHARACTER_PERFORMANCE",
        "h3_eligible": True,
        "hard_flags": [],
        "dialogue": [],
    }
    base.update(overrides)
    return base


def test_avery_mcu_keeps_fear_beats():
    cut = _cut()
    assert classify_shot(cut)["framing_class"] == "MCU_BODY"
    actions = compile_beat_actions(cut, "PERFORMANCE")
    lint_temporal_beats(cut, actions)
    assert AVERY_FEAR_SIGNATURE in " ".join(actions)


def test_hand_ecu_rejects_knees_and_shoulders():
    cut = _cut(
        cut_id="E01_B1_C",
        framing="extreme_close_up",
        visual="Trembling fingers around the thermal lunchbox handle. Lid closed.",
        action="Box does not drop.",
    )
    assert classify_shot(cut)["framing_class"] == "ECU_HAND"
    actions = compile_beat_actions(cut, "PERFORMANCE")
    lint_temporal_beats(cut, actions)
    joined = " ".join(actions).lower()
    assert "knee" not in joined
    assert "shoulder" not in joined
    with pytest.raises(ShotDirectorError):
        lint_temporal_beats(cut, [AVERY_FEAR_SIGNATURE, "Knees soften. Shoulders contract."])


def test_lucien_watch_is_not_avery_fear():
    cut = _cut(
        cut_id="E01_B2_B",
        framing="medium_shot",
        visual="Lucien stops an easy ten feet off. Watches. Avery still against the cooler.",
        action="Stop and hold. Do not close the gap.",
        character_ids=["lucien_mercer", "avery_sterling"],
    )
    assert classify_shot(cut)["framing_class"] == "TWO_SHOT"
    actions = compile_beat_actions(cut, "PERFORMANCE")
    lint_temporal_beats(cut, actions)
    joined = " ".join(actions).lower()
    assert "lucien" in joined
    assert AVERY_FEAR_SIGNATURE.lower() not in joined
    assert "knee" not in joined


def test_arrive_has_displacement():
    cut = _cut(
        cut_id="E01_B2_A",
        framing="wide",
        visual="A figure resolves at the far end of the kitchen, backlit. Avery still pinned.",
        action="Lucien is arriving. Avery does not run.",
        character_ids=["lucien_mercer", "avery_sterling"],
    )
    assert classify_shot(cut)["framing_class"] == "WIDE_LOCO"
    actions = compile_beat_actions(cut, "PERFORMANCE")
    lint_temporal_beats(cut, actions)
    joined = " ".join(actions).lower()
    assert "lucien" in joined
    assert any(w in joined for w in ("step", "plant", "settle"))


def test_steam_has_no_character_physiology():
    cut = _cut(
        cut_id="E01_B7_C",
        framing="extreme_close_up",
        visual="Steam still curls from the seams of the sealed lunchbox. Lid closed.",
        action="Steam only.",
        character_ids=[],
        motion_obligation="AMBIENT",
        h3_eligible=False,
    )
    assert classify_shot(cut)["framing_class"] == "PROP_ONLY"
    actions = compile_beat_actions(cut, "LOCAL")
    lint_temporal_beats(cut, actions)
    joined = " ".join(actions).lower()
    assert "steam" in joined
    assert "knee" not in joined
    assert "avery" not in joined
