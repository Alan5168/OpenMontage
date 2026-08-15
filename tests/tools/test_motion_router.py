from __future__ import annotations

import pytest

from lib.motion_router import MotionRouterError, assert_transition, route_cut, summarize_scenes


def test_limited_cut_stays_in_planning_without_stills():
    row = route_cut({"id": "c001", "animation_class": "LIMITED"})
    assert row["department"] == "planning"
    assert row["h3_allowed"] is False
    assert row["production_ready"] is False


def test_hard_intent_does_not_enable_h3_before_stills():
    row = route_cut({"id": "c009", "animation_class": "I2V_HARD"})
    assert row["h3_allowed"] is False
    assert row["department"] == "planning"


def test_limited_cannot_request_h3_model():
    with pytest.raises(MotionRouterError, match="H3"):
        route_cut({"id": "c002", "animation_class": "LIMITED", "primary_model": "h3-comfyui"})


def test_agent_cannot_approve():
    with pytest.raises(MotionRouterError, match="forbidden edge"):
        assert_transition("PATCH_PROPOSAL", "APPROVED", actor="prime")
    with pytest.raises(MotionRouterError, match="forbidden edge"):
        assert_transition("CRITIQUE", "APPROVED", actor="human")
    with pytest.raises(MotionRouterError, match="human-only"):
        assert_transition("HUMAN_SELECT", "APPROVED", actor="prime")
    assert_transition("PATCH_PROPOSAL", "HUMAN_SELECT", actor="prime")
    assert_transition("HUMAN_SELECT", "APPROVED", actor="human")


def test_summarize_counts_planned_classes_not_live_routes():
    payload = summarize_scenes(
        [
            {"id": "a", "animation_class": "LIMITED"},
            {"id": "b", "animation_class": "I2V_STANDARD"},
            {"id": "c", "animation_class": "I2V_HARD"},
        ]
    )
    assert payload["class_counts"]["LIMITED"] == 1
    assert payload["h3_cut_ids"] == []
    assert payload["dispatchable_cut_ids"] == []
