from lib.h3_context_ir import compile_h3_ir
from lib.h3_turbo_quality import (
    COMPARE_FRAMES,
    MCU_STILL_SRC,
    QUALITY_SPEC,
)


def test_quality_still_is_directed_mcu_not_identity_or_frozen_s2():
    assert MCU_STILL_SRC.name == "A2_mcu.png"
    assert "scene_a" in str(MCU_STILL_SRC)
    assert "9x16" not in MCU_STILL_SRC.name.lower()
    assert "S2.png" not in str(MCU_STILL_SRC)


def test_quality_spec_compiles_i2va_with_picture_one():
    prompt = compile_h3_ir(QUALITY_SPEC)["prompt"]
    assert "<Picture 1>" in prompt
    assert "smile" in prompt.lower() or "grin" in prompt.lower()
    assert compile_h3_ir(QUALITY_SPEC)["mode"] == "i2va"
    assert compile_h3_ir(QUALITY_SPEC)["width"] == 1344
    assert compile_h3_ir(QUALITY_SPEC)["height"] == 768


def test_compare_frames_are_start_mid_end():
    assert COMPARE_FRAMES == (0, 60, 120)
