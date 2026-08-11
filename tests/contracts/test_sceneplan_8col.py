import json
from copy import deepcopy
from pathlib import Path

import pytest

from lib.sceneplan_contract import EightColumnValidationError, validate_eight_column_scene_plan


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "content_studio" / "scene_plan_8col_valid.json"


def valid_plan() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_eight_column_fixture_passes() -> None:
    validate_eight_column_scene_plan(valid_plan(), require_review_decisions=True)


def test_visual_intent_is_required_separately_from_prompt() -> None:
    plan = valid_plan()
    plan["scenes"][0].pop("visual_intent")
    assert plan["scenes"][0]["t2i_prompt"]
    with pytest.raises(EightColumnValidationError, match="visual_intent"):
        validate_eight_column_scene_plan(plan)


def test_prompt_change_does_not_overwrite_visual_intent() -> None:
    plan = valid_plan()
    intent = deepcopy(plan["scenes"][0]["visual_intent"])
    plan["scenes"][0]["t2i_prompt"] = "a corrected exact provider prompt"
    validate_eight_column_scene_plan(plan)
    assert plan["scenes"][0]["visual_intent"] == intent
