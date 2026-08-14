"""L0 overlay compiler: clip / CJK orphan / safe area, no model."""

from __future__ import annotations

from lib.checkpoint import get_pipeline_stages
from lib.overlay_preflight import check_layout, repair_layout, run_overlay_preflight
from lib.pipeline_loader import get_stage_order, load_pipeline
from schemas.artifacts import validate_artifact


def test_orphan_line_is_l0():
    issues = check_layout(
        ["已经会自己修改自己的规则", "了"],
        font_size=72,
        max_width=918,
        max_lines=3,
        line_height=1.2,
        canvas=(1080, 1920),
    )
    assert any(item["code"] == "orphan_line" for item in issues)


def test_repair_removes_single_glyph_widow():
    result = repair_layout("一二三四五六七八九十甲乙了", "hero_title")
    assert result["ok"], result["issues"]
    assert len(result["lines"][-1].strip()) > 1 or len(result["lines"]) == 1


def test_empty_overlays_do_not_block():
    report = run_overlay_preflight(
        {"version": "1.0", "render_runtime": "remotion", "cuts": []},
    )
    assert report["ok"]
    validate_artifact("overlay_preflight", report["artifact"])


def test_hero_title_is_patched_into_edit_decisions():
    report = run_overlay_preflight(
        {
            "version": "1.0",
            "render_runtime": "remotion",
            "cuts": [],
            "overlays": [
                {
                    "type": "hero_title",
                    "in_seconds": 1,
                    "out_seconds": 3,
                    "text": "一二三四五六七八九十甲乙了",
                }
            ],
        }
    )
    assert report["ok"], report["unresolved"]
    patched = report["patched_edit_decisions"]["overlays"][0]
    assert "\n" in patched["text"] or patched["text"].endswith("了")
    assert not patched["text"].endswith("\n了")
    assert patched["font_size"] == patched["fontSize"]


def test_edit_decisions_schema_keeps_on_screen_text():
    payload = {
        "version": "1.0",
        "render_runtime": "remotion",
        "cuts": [
            {
                "id": "hook",
                "source": "k1.mp4",
                "type": "hero_title",
                "text": "已经会自己修改自己的规则了",
                "font_size": 72,
                "in_seconds": 0,
                "out_seconds": 3,
            }
        ],
        "overlays": [
            {
                "asset_id": "title-png",
                "type": "hero_title",
                "text": "已经会自己修改自己的规则了",
                "start_seconds": 1,
                "end_seconds": 3,
                "position": {"x": 40, "y": 200},
            }
        ],
    }
    validate_artifact("edit_decisions", payload)


def test_ffmpeg_compose_gate_blocks_unresolved_layout():
    from tools.video.video_compose import VideoCompose

    block, _patched = VideoCompose()._overlay_preflight_gate(
        {
            "version": "1.0",
            "render_runtime": "ffmpeg",
            "cuts": [
                {
                    "id": "hook",
                    "source": "k1.mp4",
                    "type": "hero_title",
                    "text": "字" * 200,
                    "in_seconds": 0,
                    "out_seconds": 3,
                }
            ],
        },
        {"output_path": "/tmp/overlay_gate_out.mp4"},
    )
    assert block is not None
    assert block.success is False


def test_unresolved_layout_blocks():
    result = repair_layout("字" * 200, "hero_title")
    assert result["ok"] is False
    assert result["issues"]


def test_overlay_preflight_is_before_compose():
    order = get_stage_order(load_pipeline("animated-explainer"))
    assert order.index("edit") < order.index("overlay_preflight") < order.index("compose")
    assert get_pipeline_stages("research-report-explainer").index("overlay_preflight") < (
        get_pipeline_stages("research-report-explainer").index("compose")
    )
