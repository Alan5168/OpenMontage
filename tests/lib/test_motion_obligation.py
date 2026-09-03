from __future__ import annotations

import pytest

from lib.motion_obligation import (
    COMPILE_FAIL,
    ShotCompileError,
    compile_cut,
    resolve_motion_obligation,
)
from lib.motion_router import MotionRouterError, route_cut


def test_explicit_performance_cannot_be_limited():
    with pytest.raises(ShotCompileError, match="PERFORMANCE cannot be satisfied"):
        compile_cut(
            {
                "id": "A4",
                "motion_obligation": "PERFORMANCE",
                "animation_class": "LIMITED",
                "performance_intent": "Avery walks toward cooler",
                "renderer": "local_compose",
            }
        )


def test_walk_intent_infers_performance_and_defaults_h3():
    out = compile_cut(
        {
            "id": "A4",
            "performance_intent": "Avery walks toward cooler",
            "character_ids": ["avery_sterling"],
        }
    )
    assert out["motion_obligation"] == "PERFORMANCE"
    assert out["dispatch_class"] == "I2V_HARD"
    assert out["renderer"] == "h3"
    assert out["h3_mode"] == "fl2va"
    assert out["h3_default"] is True
    assert out["generate"] is False


def test_declared_hold_stays_limited():
    out = compile_cut(
        {
            "id": "A2",
            "motion_obligation": "NONE",
            "intentional_hold": True,
            "animation_class": "LIMITED",
            "description": "Avery already frozen at cooler MCU",
        }
    )
    assert out["dispatch_class"] == "LIMITED"
    assert out["renderer"] == "local_compose"
    assert out["h3_mode"] is None
    assert out["h3_default"] is False


def test_i2v_hard_infers_performance_fl2va():
    out = compile_cut(
        {
            "id": "A5",
            "animation_class": "I2V_HARD",
            "character_ids": ["avery_sterling"],
            "visual_intent": "Threat sits in the body. Mouth closed.",
        }
    )
    assert out["motion_obligation"] == "PERFORMANCE"
    assert out["renderer"] == "h3"
    assert out["h3_mode"] == "fl2va"


def test_two_characters_interaction_blocks_without_ref2va_runtime():
    with pytest.raises(ShotCompileError, match="R2VA_RUNTIME_UNAVAILABLE") as exc:
        compile_cut(
            {
                "id": "B1",
                "animation_class": "I2V_HARD",
                "character_ids": ["avery_sterling", "lucien_mercer"],
            }
        )
    assert "preferred_renderer=h3_ref2va" in str(exc.value)
    assert "capability_available=false" in str(exc.value)


def test_interaction_compiles_to_ref2va_only_when_runtime_exists(monkeypatch, tmp_path):
    unet = tmp_path / "diffusion_models" / "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
    unet.parent.mkdir(parents=True)
    unet.write_bytes(b"fake")
    workflow = tmp_path / "minimax-h3-r2v.json"
    workflow.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("H3_MODELS_DIR", str(tmp_path))
    monkeypatch.setattr("lib.motion_obligation.ref2va_runtime_available", lambda: True)
    out = compile_cut(
        {
            "id": "B1",
            "animation_class": "I2V_HARD",
            "character_ids": ["avery_sterling", "lucien_mercer"],
        }
    )
    assert out["motion_obligation"] == "INTERACTION"
    assert out["preferred_renderer"] == "h3_ref2va"
    assert out["capability_available"] is True
    assert out["renderer"] == "h3_ref2va"
    assert out["h3_mode"] == "r2va"
    assert out["h3_mode_label"] == "ref2va"


def test_limited_hud_is_not_stuffed_into_h3():
    out = compile_cut(
        {
            "id": "A1",
            "animation_class": "LIMITED",
            "visual_intent": "HUD wakes on black",
            "character_ids": [],
        }
    )
    assert out["motion_obligation"] == "LOCAL"
    assert out["dispatch_class"] == "LIMITED"
    assert out["renderer"] == "local_compose"
    assert out["h3_default"] is False
    assert out["h3_mode"] is None


def test_local_visible_motion_cannot_be_a_still_hold():
    from lib.motion_obligation import LOCAL_HOLD_FAIL, assert_motion_obligation

    with pytest.raises(ShotCompileError, match="LOCAL visible motion"):
        assert_motion_obligation(
            {
                "motion_obligation": "LOCAL",
                "animation_class": "LIMITED",
                "renderer": "ffmpeg-hold",
            }
        )
    assert "still hold" in LOCAL_HOLD_FAIL.lower() or "LOCAL" in LOCAL_HOLD_FAIL


def test_holds_the_note_is_not_a_walk():
    assert resolve_motion_obligation({"description": "Jesse holds the note."}) in {"NONE", "LOCAL"}


def test_route_cut_raises_before_stills_when_limited_covers_a_walk():
    with pytest.raises((ShotCompileError, MotionRouterError), match="PERFORMANCE|LIMITED"):
        route_cut(
            {
                "id": "dyn",
                "animation_class": "LIMITED",
                "performance_intent": "Avery walks toward cooler",
            }
        )
