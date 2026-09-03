"""character_variant is a ShotContract slot, not a SHOT_KEYFRAME."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.character_variant import (
    VARIANT_ID_NOT_IN_CAST,
    VARIANT_STILL_AS_START,
    CharacterVariantError,
    cut_variant_blockers,
    identity_from_variant,
    normalize_character_variant,
    resolve_from_character_cards,
    start_frame_is_variant_still,
    world_lock_wardrobe_keys,
)
from lib.h3_context_ir import compile_from_scene
from lib.reference_atom import compile_performance_h3_spec
from lib.shot_director import first_frame_readiness
from lib.shot_production_gate import evaluate_cut
from schemas.artifacts import validate_artifact


def test_normalize_rejects_cast_mismatch():
    with pytest.raises(CharacterVariantError, match=VARIANT_ID_NOT_IN_CAST):
        normalize_character_variant(
            {"character_id": "avery_sterling", "costume": "apron"},
            ["lucien_mercer"],
        )


def test_identity_prompt_does_not_use_still_as_picture():
    ident = identity_from_variant(
        {
            "character_ids": ["avery_sterling"],
            "character_variant": {
                "character_id": "avery_sterling",
                "phase": "系统傀儡期",
                "costume": "居家围裙装",
                "must_show": "apron over casual clothes",
                "still_refs": ["bible/avery/apron_3q.png"],
            },
        }
    )
    assert ident["name"] == "avery_sterling"
    assert "apron over casual clothes" in ident["must"]
    assert "reference_bindings" not in ident
    assert "apron_3q.png" not in json.dumps(ident)
    compiled = compile_from_scene(
        {
            "description": "hold at the cooler",
            "duration_seconds": 5,
            "character_ids": ["avery_sterling"],
            "character_variant": {
                "character_id": "avery_sterling",
                "phase": "系统傀儡期",
                "costume": "居家围裙装",
                "must_show": "apron over casual clothes",
                "still_refs": ["bible/avery/apron_3q.png"],
            },
        }
    )
    prompt = compiled["prompt"]
    assert "matching <Picture 1>" in prompt
    assert "experimental_reference_binding" not in prompt
    assert "Do not inherit sheet background" not in prompt
    assert "apron_3q.png" not in prompt


def test_experimental_reference_binding_is_opt_in():
    scene = {
        "description": "hold at the cooler",
        "duration_seconds": 5,
        "experimental_reference_binding": True,
        "character_ids": ["avery_sterling"],
        "character_variant": {
            "character_id": "avery_sterling",
            "still_refs": ["bible/avery/apron_3q.png"],
        },
    }
    ident = identity_from_variant(scene)
    assert ident["reference_bindings"][0]["experimental"] is True
    prompt = compile_from_scene(scene)["prompt"]
    assert "[experimental_reference_binding]" in prompt
    assert "CHARACTER_IDENTITY owned by avery_sterling only" in prompt
    assert "apron_3q.png" not in prompt


def test_start_frame_cannot_be_a_variant_still():
    scene = {
        "id": "c001",
        "type": "character_scene",
        "character_ids": ["jesse"],
        "start_frame_ref": "bible/jesse/sheets/kitchen_3q.png",
        "visual_ref": {"kind": "local_image", "path": "bible/jesse/sheets/kitchen_3q.png"},
        "character_variant": {
            "character_id": "jesse",
            "still_refs": ["bible/jesse/sheets/kitchen_3q.png"],
        },
        "animation_class": "LIMITED",
    }
    assert start_frame_is_variant_still(scene) is True
    assert VARIANT_STILL_AS_START in cut_variant_blockers(scene)
    row = evaluate_cut(scene, scene_plan={"scenes": [scene], "metadata": {"pipeline": "anime-hybrid"}})
    assert VARIANT_STILL_AS_START in row["blockers"]
    assert row["production_ready"] is False


def test_variant_still_is_not_h3_first_frame():
    cut = {
        "composition_anchor": "COMP_X",
        "character_ids": ["avery_sterling"],
        "start_frame_ref": "bible/avery/apron_3q.png",
        "character_variant": {
            "character_id": "avery_sterling",
            "still_refs": ["bible/avery/apron_3q.png"],
        },
    }
    bindings = [{"id": "COMP_X", "status": "bound"}]
    plate = {"kind": "character", "path": "bible/avery/apron_3q.png", "aspect_note": ""}
    ready = first_frame_readiness(cut, bindings, plate, require_h3=True)
    assert ready["h3_dispatch_allowed"] is False
    assert ready["shot_ready"] is False
    assert any("character_variant" in item or "IDENTITY" in item for item in ready["blockers"])


def test_compile_from_scene_reads_variant_identity():
    out = compile_from_scene(
        {
            "id": "c1",
            "description": "Avery holds the cooler.",
            "duration_seconds": 5,
            "character_variant": {
                "character_id": "avery_sterling",
                "must_show": "black hoodie, lunchbox lid closed",
            },
            "shot_language": {"camera_movement": "static", "shot_size": "medium_close"},
        }
    )
    assert "avery_sterling" in out["prompt"]
    assert "black hoodie" in out["prompt"]


def test_performance_spec_keeps_default_name_without_variant():
    spec = compile_performance_h3_spec(
        {"performance_intent": "Hold.", "character_ids": ["lucien_mercer"]},
        first_frame="a.png",
        last_frame=None,
        duration_seconds=5,
    )
    assert spec["identity"] == {"name": "lucien_mercer"}


def test_resolve_from_character_cards_uses_generated_as_identity_refs():
    cards = {
        "characters": [
            {
                "om_id": "avery_sterling",
                "phase": "系统傀儡期",
                "variant": "居家围裙装",
                "must_show": "same identity; home apron",
                "generated": ["working/xiaoyunque_stills/avery_apron_3q.png"],
            }
        ]
    }
    variant = resolve_from_character_cards(
        cards,
        character_id="avery_sterling",
        phase="系统傀儡期",
        costume="居家围裙装",
    )
    assert variant["character_id"] == "avery_sterling"
    assert variant["costume"] == "居家围裙装"
    assert variant["still_refs"] == ["working/xiaoyunque_stills/avery_apron_3q.png"]


def test_world_lock_rejects_wardrobe_keys():
    assert world_lock_wardrobe_keys({"palette": "warm tungsten"}) == []
    assert "wardrobe" in world_lock_wardrobe_keys({"palette": "warm", "wardrobe": "apron"})


def test_optional_variant_is_schema_legal():
    plan = json.loads(
        Path("tests/fixtures/content_studio/scene_plan_vid3_shot_fields.json").read_text(
            encoding="utf-8"
        )
    )
    validate_artifact("scene_plan", plan)


def test_plans_without_variant_still_validate():
    validate_artifact(
        "scene_plan",
        json.loads(Path("tests/fixtures/content_studio/scene_plan_8col_valid.json").read_text(encoding="utf-8")),
    )
