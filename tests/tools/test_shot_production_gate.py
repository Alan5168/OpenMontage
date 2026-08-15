from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.motion_router import MotionRouterError, route_cut, summarize_scenes
from lib.shot_production_gate import ShotGateError, assert_dispatch, evaluate_plan, motion_dispatch_error
from tools.video.video_compose import VideoCompose
from tools.video.video_selector import VideoSelector


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"visual-lock")
    return path


def _vid3_plan() -> dict:
    path = Path("tests/fixtures/content_studio/scene_plan_vid3_shot_fields.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _ready_plan(tmp_path: Path, animation_class: str | None = "LIMITED") -> dict:
    sheet = _touch(tmp_path / "locks" / "master_sheet.png")
    start = _touch(tmp_path / "bible" / "jesse" / "approved" / "idle.png")
    scene = {
        "id": "c001",
        "type": "character_scene",
        "description": "Jesse holds the note.",
        "start_seconds": 0,
        "end_seconds": 3,
        "character_ids": ["jesse"],
        "start_frame_ref": str(start),
        "visual_ref": {"kind": "local_image", "path": str(start)},
        "generation_status": "pending",
    }
    if animation_class:
        scene["animation_class"] = animation_class
    return {
        "version": "1.0",
        "style_playbook": "anime-ghibli",
        "scenes": [scene],
        "metadata": {
            "pipeline": "anime-hybrid",
            "profile": "fiction_anime_episode",
            "master_sheet_path": str(sheet),
            "master_sheet_locked": True,
        },
    }


def test_vid3_fixture_cannot_leave_planning():
    plan = _vid3_plan()
    overview = evaluate_plan(plan, project_dir=None)
    assert overview["applies"] is True
    assert overview["render_allowed"] is False
    assert overview["dispatchable_cut_ids"] == []
    assert "c001" in overview["planning_cut_ids"]
    row = route_cut(plan["scenes"][0], scene_plan=plan)
    assert row["department"] == "planning"
    assert row["h3_allowed"] is False
    assert row["production_ready"] is False
    assert "visual_ref_placeholder" in row["blockers"]
    with pytest.raises(ShotGateError, match="visual-constraint"):
        assert_dispatch(plan)
    assert motion_dispatch_error({"scene_plan": plan, "cut_id": "c001"})


def test_stored_render_allowed_true_cannot_bypass_missing_stills():
    plan = _vid3_plan()
    plan["metadata"]["render_allowed"] = True
    with pytest.raises(ShotGateError):
        assert_dispatch(plan)
    assert route_cut(plan["scenes"][0], scene_plan=plan)["render_allowed"] is False


def test_production_ready_limited_enters_local_compose(tmp_path: Path):
    plan = _ready_plan(tmp_path, "LIMITED")
    row = route_cut(plan["scenes"][0], scene_plan=plan, project_dir=tmp_path)
    assert row["department"] == "local_compose"
    assert row["h3_allowed"] is False
    assert row["production_ready"] is True
    assert_dispatch(plan, project_dir=tmp_path, cut_ids=["c001"])


def test_production_ready_hard_may_use_h3(tmp_path: Path):
    plan = _ready_plan(tmp_path, "I2V_HARD")
    row = route_cut(plan["scenes"][0], scene_plan=plan, project_dir=tmp_path)
    assert row["h3_allowed"] is True
    assert row["department"] == "h3"


def test_limited_still_cannot_request_h3_after_ready(tmp_path: Path):
    plan = _ready_plan(tmp_path, "LIMITED")
    plan["scenes"][0]["primary_model"] = "h3-comfyui"
    with pytest.raises(MotionRouterError, match="H3"):
        route_cut(plan["scenes"][0], scene_plan=plan, project_dir=tmp_path)


def test_incomplete_class_intent_is_not_a_live_route():
    payload = summarize_scenes(
        [
            {"id": "a", "animation_class": "LIMITED"},
            {"id": "b", "animation_class": "I2V_STANDARD"},
            {"id": "c", "animation_class": "I2V_HARD"},
        ]
    )
    assert payload["class_counts"]["LIMITED"] == 1
    assert payload["dispatch_class_counts"]["LIMITED"] == 0
    assert payload["h3_cut_ids"] == []
    assert set(payload["planning_cut_ids"]) == {"a", "b", "c"}


def test_video_selector_blocks_vid3():
    result = VideoSelector().execute(
        {
            "prompt": "do not render this",
            "operation": "image_to_video",
            "scene_plan": _vid3_plan(),
            "cut_id": "c001",
        }
    )
    assert result.success is False
    assert "visual-constraint" in (result.error or "")


def test_video_compose_blocks_vid3():
    plan = _vid3_plan()
    result = VideoCompose().execute(
        {
            "operation": "render",
            "scene_plan": plan,
            "edit_decisions": {
                "render_runtime": "ffmpeg",
                "renderer_family": "stock",
                "cuts": [{"id": "c001", "source": "missing.mp4"}],
            },
            "asset_manifest": {"assets": []},
        }
    )
    assert result.success is False
    assert "visual-constraint" in (result.error or "")


def test_minimum_contract_allows_limited_draft_without_end_frame_or_animatic(tmp_path: Path):
    plan = _ready_plan(tmp_path, "LIMITED")
    assert "end_frame_ref" not in plan["scenes"][0]
    assert "animatic_path" not in plan["metadata"]
    row = route_cut(plan["scenes"][0], scene_plan=plan, project_dir=tmp_path)
    assert row["department"] == "local_compose"
    assert row["production_ready"] is True


def test_missing_class_drafts_as_limited_after_identity_lock(tmp_path: Path):
    plan = _ready_plan(tmp_path, None)
    row = route_cut(plan["scenes"][0], scene_plan=plan, project_dir=tmp_path)
    assert row["dispatch_class"] == "LIMITED"
    assert row["department"] == "local_compose"
    assert row["h3_allowed"] is False


def test_overlay_l0_blocks_motion_after_identity_lock(tmp_path: Path):
    plan = _ready_plan(tmp_path, "I2V_STANDARD")
    error = motion_dispatch_error(
        {
            "scene_plan": plan,
            "cut_id": "c001",
            "project_dir": str(tmp_path),
            "edit_decisions": {
                "version": "1.0",
                "render_runtime": "ffmpeg",
                "cuts": [],
                "overlays": [
                    {
                        "type": "hero_title",
                        "in_seconds": 1,
                        "out_seconds": 3,
                        "text": "字" * 200,
                    }
                ],
            },
        }
    )
    assert error
    assert "Overlay L0" in error
