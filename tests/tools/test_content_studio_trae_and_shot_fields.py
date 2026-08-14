from __future__ import annotations

import json
from pathlib import Path

from schemas.artifacts import validate_artifact
from tools.content_studio_runtime import OV_USER_ENV_FORWARD, _write_launcher
from tools.content_studio_trae_harness_check import check as trae_check


def test_trae_harness_files_pass_mechanical_check():
    payload = trae_check()
    assert payload["status"] == "OK"
    assert payload["rule_bytes"] <= 2048
    assert payload["memory_bytes"] <= 2048
    assert payload["mcp_enabled"] is False


def test_vid3_shot_fields_validate_on_existing_scene_plan():
    path = Path("tests/fixtures/content_studio/scene_plan_vid3_shot_fields.json")
    plan = json.loads(path.read_text(encoding="utf-8"))
    validate_artifact("scene_plan", plan)
    scene = plan["scenes"][0]
    assert scene["animation_class"] == "LIMITED"
    assert scene["generation_status"] == "pending"
    assert scene["voice_segment_ids"] == ["v1"]
    assert scene["voice_segment_refs"][0]["segment_id"] == "v1"


def test_existing_eight_column_fixture_still_valid_without_shot_fields():
    path = Path("tests/fixtures/content_studio/scene_plan_8col_valid.json")
    validate_artifact("scene_plan", json.loads(path.read_text(encoding="utf-8")))


def test_openviking_launcher_forwards_hkcu_names_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.content_studio_runtime.LOG_ROOT", tmp_path)
    launcher = _write_launcher("openviking")
    text = launcher.read_text(encoding="ascii")
    assert "BAILIAN_TOKENPLAN_API_KEY" in text
    assert "HKCU\\Environment" in text
    assert "set BAILIAN_TOKENPLAN_API_KEY=" not in text
    assert "set BAILIAN_TOKENPLAN_BASE=" not in text
    assert "sk-" not in text
