"""Seedance packer is a translator. It never enables H3 dispatch."""

from __future__ import annotations

import pytest

from lib.metered_provider import quote_metered_tool
from lib.seedance_ref_packer import MAX_REF_IMAGES, SeedanceRefPackError, pack_seedance_refs
from tools.video.seedance_video import SeedanceVideo


def test_packer_orders_keyframe_before_identity():
    packed = pack_seedance_refs(
        {
            "start_frame_ref": "assets/shots/c001_9x16.png",
            "first_frame_readiness": {"shot_ready": True, "role": "SHOT_KEYFRAME"},
            "character_variant": {
                "character_id": "jesse",
                "still_refs": ["bible/jesse/sheets/kitchen_3q.png", "bible/jesse/sheets/profile.png"],
            },
            "anchor_bindings": [
                {
                    "kind": "scene",
                    "role": "SCENE_REFERENCE",
                    "path": "bible/kitchen/wide.png",
                }
            ],
        }
    )
    assert packed["h3_dispatch_allowed"] is False
    assert packed["operation"] == "reference_to_video"
    assert packed["reference_image_paths"][0] == "assets/shots/c001_9x16.png"
    assert packed["roles"][0]["role"] == "SHOT_KEYFRAME"
    assert "inherit" not in packed["roles"][0]
    ident = next(row for row in packed["roles"] if row["role"] == "IDENTITY_REFERENCE")
    assert "do_not_inherit" not in ident
    assert "IDENTITY_REFERENCE" in {row["role"] for row in packed["roles"]}
    assert len(packed["reference_image_paths"]) <= MAX_REF_IMAGES


def test_packer_does_not_promote_variant_still_to_keyframe():
    packed = pack_seedance_refs(
        {
            "start_frame_ref": "bible/jesse/sheets/kitchen_3q.png",
            "character_variant": {
                "character_id": "jesse",
                "still_refs": ["bible/jesse/sheets/kitchen_3q.png"],
            },
        }
    )
    assert packed["h3_dispatch_allowed"] is False
    assert all(row["role"] != "SHOT_KEYFRAME" for row in packed["roles"])
    assert packed["roles"][0]["role"] == "IDENTITY_REFERENCE"
    assert any("IDENTITY_REFERENCE" in item for item in packed["warnings"])


def test_packer_rejects_more_than_nine_images():
    stills = [f"bible/char/view_{i}.png" for i in range(10)]
    with pytest.raises(SeedanceRefPackError, match="at most 9"):
        pack_seedance_refs({"character_variant": {"character_id": "jesse", "still_refs": stills}})


def test_seedance_quote_only_does_not_need_fal_key(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.delenv("FAL_AI_API_KEY", raising=False)
    tool = SeedanceVideo()
    result = tool.execute(
        {"prompt": "x", "quote_only": True, "duration": "5", "model_variant": "fast"}
    )
    assert result.success is True
    assert result.data["execute"] is False
    assert result.data["requires_confirm"] is True
    assert result.data["usd"] > 0
    assert result.cost_usd == 0.0


def test_seedance_execute_fails_closed_on_overpack(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    tool = SeedanceVideo()
    stills = [f"bible/char/view_{i}.png" for i in range(10)]
    result = tool.execute(
        {
            "prompt": "x",
            "shot": {"character_variant": {"character_id": "jesse", "still_refs": stills}},
        }
    )
    assert result.success is False
    assert "at most 9" in (result.error or "")


def test_quote_helper_marks_402_not_retryable():
    tool = SeedanceVideo()
    quote = quote_metered_tool(tool, {"duration": "5", "model_variant": "standard"})
    assert "402" in quote["not_retryable"]
    assert quote["execute"] is False
