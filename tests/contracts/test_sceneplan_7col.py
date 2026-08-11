import json
from copy import deepcopy
from pathlib import Path

import pytest

from lib.sceneplan_contract import (
    SevenColumnValidationError,
    assert_static_image_capability,
    validate_seven_column_scene_plan,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "content_studio" / "scene_plan_7col_valid.json"


def valid_plan() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_seven_column_fixture_passes() -> None:
    validate_seven_column_scene_plan(valid_plan(), require_review_decisions=True)


@pytest.mark.parametrize("field", ["id", "start_seconds", "layout_notes", "dialogue", "voice_segment_ids"])
def test_required_cut_fields_fail_closed(field: str) -> None:
    plan = valid_plan()
    plan["scenes"][0].pop(field)
    with pytest.raises(Exception):
        validate_seven_column_scene_plan(plan)


def test_missing_visual_or_reuse_fails() -> None:
    plan = valid_plan()
    plan["scenes"][1].pop("reuse")
    with pytest.raises(SevenColumnValidationError, match="visual_ref or reuse"):
        validate_seven_column_scene_plan(plan)


def test_broken_reuse_pointer_fails() -> None:
    plan = valid_plan()
    plan["scenes"][1]["reuse"]["source_cut_id"] = "future-cut"
    with pytest.raises(SevenColumnValidationError, match="earlier cut"):
        validate_seven_column_scene_plan(plan)


def test_api_reference_requires_prompt_and_provenance() -> None:
    plan = valid_plan()
    plan["scenes"][0].pop("t2i_prompt")
    with pytest.raises(SevenColumnValidationError, match="t2i_prompt"):
        validate_seven_column_scene_plan(plan)


def test_video_capability_cannot_generate_static_reference() -> None:
    with pytest.raises(SevenColumnValidationError, match="image_generation"):
        assert_static_image_capability({"capability": "video_generation", "name": "video-gen-pool"})
    assert_static_image_capability({"capability": "image_generation", "name": "image_selector"})
