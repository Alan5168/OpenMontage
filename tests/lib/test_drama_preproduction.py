"""Drama beats compile onto the eight-column scene_plan table, not a new ledger."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from lib.drama_preproduction import (
    compile_scene_plan,
    compile_t2i_prompt,
    cut_to_scene,
    detect_macro_shot,
    load_ep01_golden_cuts,
)
from lib.sceneplan_contract import validate_eight_column_scene_plan
from schemas.artifacts import validate_artifact

CONTENT_STUDIO = Path(__file__).resolve().parents[4]
EPISODE = (
    CONTENT_STUDIO
    / "jobs"
    / "vid-yt-chef-s1-v1"
    / "working"
    / "source"
    / "episodes"
    / "episode_01.json"
)
SCENE_A = {
    "E01_CO_A": "A1",
    "E01_CO_B": "A2",
    "E01_CO_C": "A3",
    "E01_B1_A": "A4",
    "E01_B1_B": "A5",
    "E01_B1_C": "A6",
}


def test_macro_shot_detector_catches_multi_camera_beats():
    blob = (
        "Wide establishing shot of the kitchen. Push in slow on Avery. "
        "Cut to scarred knuckles. Cut to dead-still eyes."
    )
    assert detect_macro_shot(blob) is True
    assert detect_macro_shot("MCU Avery pressed against the cooler. Mouth closed.") is False


def test_ep01_golden_rows_are_one_camera():
    for cut in load_ep01_golden_cuts():
        assert detect_macro_shot(cut["visual"]) is False, cut["cut_id"]


def test_cut_to_scene_keeps_intent_prompt_sound_split():
    cut = load_ep01_golden_cuts()[4]  # E01_B1_B H3 MCU
    scene = cut_to_scene(cut)
    assert scene["id"] == "E01_B1_B"
    assert scene["motion_route"] == "H3"
    assert scene["sound_intent"]["se"]
    assert "bgm_mood" in scene["sound_intent"]
    assert scene["visual_intent"]
    assert scene["t2i_prompt"]
    assert scene["i2v_prompt"]
    assert scene["visual_intent"] != scene["t2i_prompt"]
    assert scene["visual_intent"] != scene["i2v_prompt"]
    assert "hosted_minimax_ir" in scene["h3_ir"]
    assert scene["h3_ir"]["dispatch"] is False


def test_prompt_change_does_not_overwrite_visual_intent():
    cut = load_ep01_golden_cuts()[4]
    scene = cut_to_scene(cut)
    intent = scene["visual_intent"]
    scene["t2i_prompt"] = compile_t2i_prompt(cut) + " [revised still prompt]"
    scene["i2v_prompt"] = scene["i2v_prompt"] + "\n[revised motion prompt]"
    assert scene["visual_intent"] == intent


def test_compile_ep01_is_valid_eight_column_scene_plan():
    plan = compile_scene_plan(EPISODE)
    validate_artifact("scene_plan", plan)
    validate_eight_column_scene_plan(plan, require_review_decisions=False)
    scenes = plan["scenes"]
    assert 25 <= len(scenes) <= 35
    assert plan["metadata"]["presentation_contract"] == "eight-column-v1"
    assert plan["metadata"]["dispatch"] is False
    assert plan["metadata"]["checkpoint"] is False
    by_id = {row["id"]: row for row in scenes}
    for cut_id, scene_a in SCENE_A.items():
        assert f"scene_a:{scene_a}" in by_id[cut_id]["flags"]
    for row in scenes:
        assert row["sound_intent"]["se"]
        assert "bgm_mood" in row["sound_intent"]
        assert row["visual_intent"].strip()
        assert row["t2i_prompt"].strip()
        assert row["visual_intent"] != row["t2i_prompt"]
        if row["motion_route"] == "H3":
            assert row["i2v_prompt"].strip()
            assert row["visual_intent"] != row["i2v_prompt"]
            assert row["animation_class"] == "I2V_HARD"
    cov = plan["metadata"]["coverage"]
    assert 0.97 <= cov["coverage_ratio_vs_target"] <= 1.02
    assert cov["not_a_quality_verdict"] is True


def test_eight_column_h3_row_rejects_copied_intent_as_prompt():
    plan = compile_scene_plan(EPISODE)
    h3 = next(s for s in plan["scenes"] if s.get("motion_route") == "H3")
    bad = deepcopy(plan)
    target = next(s for s in bad["scenes"] if s["id"] == h3["id"])
    target["i2v_prompt"] = target["visual_intent"]
    try:
        validate_eight_column_scene_plan(bad)
        assert False, "expected EightColumnValidationError"
    except Exception as exc:
        assert "i2v_prompt" in str(exc)


def _by_id(plan):
    return {row["id"]: row for row in plan["scenes"]}


def test_anchors_bind_real_plates_on_benchmark_mcu():
    plan = compile_scene_plan(EPISODE)
    scene = _by_id(plan)["E01_B1_B"]
    assert scene["visual_ref"]["kind"] == "local_image"
    assert scene["visual_ref"]["path"]
    bound = [row for row in scene["anchor_bindings"] if row["status"] == "bound"]
    assert bound
    assert all(row.get("sha256") for row in bound)
    assert any(row["id"] == "CHAR_AVERY_V1" and row["status"] == "bound" for row in scene["anchor_bindings"])


def test_local_visible_motion_is_not_a_still_hold():
    plan = compile_scene_plan(EPISODE)
    by_id = _by_id(plan)
    steam = by_id["E01_B7_C"]
    door = by_id["E01_B7_A"]
    hud = by_id["E01_CO_A"]
    for scene in (steam, door, hud):
        assert scene["motion_obligation"] == "LOCAL"
        assert scene["renderer"] != "ffmpeg-hold"
        assert scene["motion_route"] == "PROGRAMMATIC"
        assert scene.get("local_motion_fn")
    assert steam["local_motion_fn"] == "steam_rise"
    assert door["local_motion_fn"] == "door_decay"


def test_performance_cannot_compile_to_hold():
    from lib.motion_obligation import ShotCompileError, assert_motion_obligation

    try:
        assert_motion_obligation(
            {
                "motion_obligation": "PERFORMANCE",
                "animation_class": "I2V_HARD",
                "renderer": "ffmpeg-hold",
            }
        )
        assert False, "expected ShotCompileError"
    except ShotCompileError as exc:
        assert "PERFORMANCE" in str(exc)


def test_h3_cuts_have_real_temporal_beats():
    plan = compile_scene_plan(EPISODE)
    for scene in plan["scenes"]:
        if scene.get("motion_route") != "H3":
            continue
        beats = scene["temporal_beats"]
        assert len(beats) >= 3, scene["id"]
        assert all(beat.get("action") for beat in beats), scene["id"]
        prompt = scene["i2v_prompt"]
        assert "[Shot 2]" in prompt or "0.00" in prompt
        shots = scene["h3_ir"]["shots"]
        assert len(shots) >= 3, scene["id"]


def test_run_and_arrive_prompts_do_not_ban_walk_cycle():
    plan = compile_scene_plan(EPISODE)
    by_id = _by_id(plan)
    for cut_id in ("E01_B6_A", "E01_B2_A"):
        prompt = by_id[cut_id]["i2v_prompt"].lower()
        assert "walk cycle" not in prompt, cut_id
        assert "does not walk" not in prompt, cut_id
        assert by_id[cut_id]["h3_ir"]["locomotion"] is True


def test_audience_state_is_not_a_copy_of_shot_intent():
    plan = compile_scene_plan(EPISODE)
    for scene in plan["scenes"]:
        assert scene["audience_state_change"] != scene["shot_intent"], scene["id"]
        assert scene["audience_state_before"] != scene["audience_state_change"], scene["id"]


def test_fear_template_does_not_leak_across_shots():
    from lib.shot_director import AVERY_FEAR_SIGNATURE

    plan = compile_scene_plan(EPISODE)
    by_id = _by_id(plan)
    fear = AVERY_FEAR_SIGNATURE.lower()
    leaked = []
    for scene in plan["scenes"]:
        text = " ".join(beat.get("action") or "" for beat in scene.get("temporal_beats") or []).lower()
        if fear in text and scene["id"] != "E01_B1_B":
            leaked.append(scene["id"])
    assert leaked == []
    a = by_id["E01_B1_B"]
    assert a["shot_profile"]["framing_class"] == "MCU_BODY"
    assert "knee" in " ".join(b["action"] for b in a["temporal_beats"]).lower()
    hand = " ".join(b["action"] for b in by_id["E01_B1_C"]["temporal_beats"]).lower()
    assert "knee" not in hand
    assert "shoulder" not in hand
    assert "finger" in hand or "grip" in hand or "handle" in hand
    lucien = " ".join(b["action"] for b in by_id["E01_B2_B"]["temporal_beats"]).lower()
    assert "lucien" in lucien
    assert "knee" not in lucien
    eyes = " ".join(b["action"] for b in by_id["E01_B2_D"]["temporal_beats"]).lower()
    assert "knee" not in eyes
    assert "grip" not in eyes
    assert "eye" in eyes
    arrive = " ".join(b["action"] for b in by_id["E01_B2_A"]["temporal_beats"]).lower()
    assert "lucien" in arrive
    assert any(w in arrive for w in ("step", "plant", "settle"))
    two = " ".join(b["action"] for b in by_id["E01_B2_E"]["temporal_beats"]).lower()
    assert "avery" in two and "lucien" in two
    steam = " ".join(b["action"] for b in by_id["E01_B7_C"]["temporal_beats"]).lower()
    assert "steam" in steam
    assert "knee" not in steam


def test_h3_first_frame_is_not_a_character_sheet():
    plan = compile_scene_plan(EPISODE)
    by_id = _by_id(plan)
    for cut_id in ("E01_B1_B", "E01_B2_A", "E01_B2_E", "E01_B7_C"):
        scene = by_id[cut_id]
        ready = scene["first_frame_readiness"]
        assert ready["shot_ready"] is False
        assert ready["h3_dispatch_allowed"] is False
        if scene.get("motion_route") == "H3":
            assert not scene["h3_ir"].get("first_frame")
            assert "h3_first_frame_blocked" in scene["flags"]
    assert by_id["E01_B2_A"]["first_frame_readiness"]["role"] != "SHOT_KEYFRAME"
    assert by_id["E01_B2_E"]["first_frame_readiness"]["role"] != "SHOT_KEYFRAME"
    assert any(
        "unresolved" in b or "IDENTITY" in b or "16:9" in b
        for b in by_id["E01_B2_A"]["first_frame_readiness"]["blockers"]
    )
