from __future__ import annotations

import json

from tools import goodcase_reference as ref


def test_map_hud_routes_without_h3_reference():
    out = ref.route_intent("地图 HUD 数据图表 年份卡")
    assert out["route"] == "REMOTION"
    assert out["h3_reference_recommended"] is False


def test_compile_is_semantic_only_and_never_sends_source_clip(tmp_path, monkeypatch):
    atom_root = tmp_path / "reference-atoms"
    atom_root.mkdir()
    atom = {
        "schema_version": "om-goodcase-reference-atom/v1",
        "reference_atom_id": "p3_test_atom",
        "source": {
            "video_id": "source-video-id",
            "source_url": "https://source.invalid/video",
            "source_sha256": "source-sha",
            "clip_pointer": r"C:\reference-only\source.mp4",
            "clip_sha256": "clip-sha",
            "duration_seconds": 5,
            "rights": "reference_only_not_for_render",
        },
        "observed_timeline": [
            {
                "t0": 0,
                "t1": 5,
                "performance": "hands hold the target prop steadily",
                "camera": "locked-off static",
                "environment_motion": "none",
            }
        ],
        "transferable": {"camera": ["locked-off static"], "audio": []},
        "forbidden_transfer": [
            "character_identity",
            "costume",
            "historical_symbols",
            "dialogue",
            "exact_composition",
            "source_art_style",
        ],
    }
    (atom_root / "p3_test_atom.json").write_text(
        json.dumps(atom), encoding="utf-8"
    )
    monkeypatch.setattr(ref, "ATOM_ROOT", atom_root)
    out = ref.compile_h3_semantic_reference(
        "p3_test_atom",
        intent="two hands hold a lunchbox; lid stays closed",
    )
    prompt = out["h3_compiled"]["prompt"]
    assert out["reference_mode"] == "semantic_only"
    assert out["source_clip_sent_to_h3"] is False
    assert out["provider_call_made"] is False
    assert out["forbidden_transfer_violations"] == []
    assert "source-video-id" not in prompt
    assert "https://source.invalid/video" not in prompt
    assert r"C:\reference-only\source.mp4" not in prompt
    assert "[Shot 2]" not in prompt
    assert "camera cuts" not in prompt.lower()
