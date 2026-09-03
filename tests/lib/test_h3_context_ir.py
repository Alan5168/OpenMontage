"""H3 Context-IR compiler — local substitute, not MiniMax hosted IR."""

from lib.h3_context_ir import (
    I2VA_ALIGN,
    OFFICIAL_CORE_FIELDS,
    R2VA_NOT_IN_BASE_COMPILER,
    align_frame_count,
    compile_from_scene,
    compile_h3_ir,
    frames_for_duration,
)


def test_frame_grid_matches_comfy_node():
    assert align_frame_count(120) == 124
    assert frames_for_duration(5) == 124
    assert align_frame_count(5) == 5


def test_ship_grid_caps_eight_seconds_unless_allow_long():
    from lib.h3_context_ir import SHIP_FRAMES, SHIP_SECONDS, ship_duration_seconds

    assert ship_duration_seconds(8) == SHIP_SECONDS
    assert frames_for_duration(ship_duration_seconds(8)) == SHIP_FRAMES
    assert ship_duration_seconds(8, allow_long=True) == 8
    capped = compile_h3_ir({"overview": "x", "duration_seconds": 8})
    assert capped["length"] == 124
    assert capped["duration_capped_to_ship_grid"] is True
    assert capped["requested_duration_seconds"] == 8
    long = compile_h3_ir(
        {"overview": "x", "duration_seconds": 8, "h3_allow_long": True}
    )
    assert long["length"] == 192
    assert long["duration_capped_to_ship_grid"] is False


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
    assert I2VA_ALIGN in p
    assert "integrated_multimodal_description:" in p
    assert "[Shot 1]" in p
    assert "The camera holds a static shot." in p
    assert "overall_soundscape:" in p
    assert "non_diegetic_music: N/A" in p
    for field in OFFICIAL_CORE_FIELDS:
        assert f"{field}:" in p
    assert out["prompt_dialect"] == "minimax-h3-prompt-writing/base-en"
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


def test_locomotion_does_not_ban_walking():
    from lib.reference_atom import compile_performance_h3_spec

    spec = compile_performance_h3_spec(
        {
            "performance_intent": "Lucien walks toward Avery ominously",
            "character_ids": ["lucien_mercer"],
        },
        first_frame="a.png",
        last_frame=None,
        duration_seconds=8,
    )
    spec["h3_allow_long"] = True
    out = compile_h3_ir(spec)
    assert spec["locomotion"] is True
    assert spec["shots"][0]["atom_id"] == "freeze_notice"
    assert "controlled_approach" in {row["atom_id"] for row in spec["shots"]}
    assert "The subject does not walk." not in out["prompt"]
    assert "walk cycle" not in out["avoid"]
    assert "Perform the declared temporal beats." in out["prompt"]
    assert "[Shot 2]" in out["prompt"]


def test_r2va_does_not_reuse_i2va_three_fields():
    try:
        compile_h3_ir({"mode": "r2va", "overview": "x", "duration_seconds": 5})
        assert False, "expected R2VA_PROMPT_NOT_IN_BASE_COMPILER"
    except ValueError as exc:
        assert "R2VA_PROMPT_NOT_IN_BASE_COMPILER" in str(exc)
        assert "ref-en.txt" in str(exc)


def test_l2va_uses_official_last_frame_header():
    out = compile_h3_ir(
        {
            "mode": "l2va",
            "overview": "land on the last frame",
            "duration_seconds": 6,
            "h3_allow_long": True,
            "last_frame": "end.jpg",
            "camera": "locked-off static",
        }
    )
    assert out["mode"] == "l2va"
    assert (
        "<Picture 1> (from [Shot 1]) aligns with the 6.00-second mark "
        "of the target video."
    ) in out["prompt"]
    for field in OFFICIAL_CORE_FIELDS:
        assert f"{field}:" in out["prompt"]


def test_vendor_h3_prompt_writing_skill_is_present():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    skill = root / "vendor" / "minimax-h3" / "h3-prompt-writing"
    base = (skill / "references" / "base-en.txt").read_text(encoding="utf-8")
    assert (skill / "SKILL.md").is_file()
    assert (skill / "references" / "ref-en.txt").is_file()
    for field in OFFICIAL_CORE_FIELDS:
        assert f"{field}:" in base
    assert I2VA_ALIGN in base
    assert R2VA_NOT_IN_BASE_COMPILER.startswith("R2VA_PROMPT_NOT_IN_BASE_COMPILER")
