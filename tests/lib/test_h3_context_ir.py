"""H3 Context-IR compiler — local substitute, not MiniMax hosted IR."""

from lib.h3_context_ir import (
    align_frame_count,
    compile_from_scene,
    compile_h3_ir,
    frames_for_duration,
)


def test_frame_grid_matches_comfy_node():
    assert align_frame_count(120) == 124
    assert frames_for_duration(5) == 124
    assert align_frame_count(5) == 5


def test_compile_forbids_empty():
    try:
        compile_h3_ir({})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_compile_writes_official_i2va_fields():
    out = compile_h3_ir(
        {
            "mode": "i2va",
            "style": "limited TV anime",
            "overview": "Avery cannot move at the cooler.",
            "identity": {
                "character": "Avery Sterling",
                "must": ["ash-brown hair", "black hoodie", "lunchbox lid closed"],
                "must_not": ["glasses", "smile"],
            },
            "duration_seconds": 5,
            "camera": "locked-off static",
            "shots": [
                {
                    "t0": 0,
                    "t1": 5,
                    "framing": "medium close-up",
                    "action": "Chest rises too fast. Fingers tighten. Steam from lid.",
                    "camera": "locked-off static",
                }
            ],
            "audio": ["kitchen compressor", "shaky breath"],
            "avoid": ["smile", "push-in", "open lid", "walk cycle", "new face"],
        }
    )
    p = out["prompt"]
    assert out["hosted_minimax_ir"] is False
    assert out["length"] == 124
    assert out["fps"] == 24
    assert "<Picture 1> (from [Shot 1]) is fully referenced." in p
    assert "integrated_multimodal_description:" in p
    assert "[Shot 1]" in p
    assert "The camera holds a static shot." in p
    assert "overall_soundscape:" in p
    assert "non_diegetic_music: N/A" in p
    assert "The subject does not smile." in p
    assert "The camera does not push in." in p
    assert "Do not invent a smile" in p
    assert "Avery Sterling" in p
    assert "Shot 1 [0s-5s]" not in p


def test_last_frame_switches_to_fl2va_header():
    out = compile_h3_ir(
        {
            "overview": "path between frames",
            "duration_seconds": 5,
            "first_frame": "a.jpg",
            "last_frame": "b.jpg",
            "camera": "locked-off static",
        }
    )
    assert out["mode"] == "fl2va"
    assert "Picture 2 (from Shot 1) aligns with the 5.00-second mark" in out["prompt"]


def test_compile_from_scene_uses_nested_h3_ir():
    out = compile_from_scene(
        {
            "id": "A5",
            "duration_seconds": 5,
            "h3_ir": {
                "overview": "body threat",
                "avoid": ["smile"],
                "camera": "locked-off static",
            },
        }
    )
    assert "body threat" in out["prompt"]
    assert "smile" in out["avoid"]


def test_i2v_hard_shot_prompt_uses_h3_compiler():
    from lib.shot_prompt_builder import build_shot_prompt

    prompt = build_shot_prompt(
        {
            "id": "A5",
            "animation_class": "I2V_HARD",
            "description": "Chest rises too fast.",
            "duration_seconds": 5,
            "avoid": ["smile", "push-in"],
            "shot_language": {"camera_movement": "static", "shot_size": "medium_close"},
        }
    )
    assert "[Shot 1]" in prompt
    assert "The subject does not smile." in prompt
    assert "Do not invent a smile" in prompt
    assert "integrated_multimodal_description:" in prompt
