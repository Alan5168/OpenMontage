"""Creative Loop v0.1 contracts: explicit reentry, grounded critique, no retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.checkpoint import get_pipeline_stages
from lib.creative_loop import (
    CreativeLoopError,
    extract_frames,
    retrieve_learning_events,
    validate_critique_grounding,
    write_learning_event,
)
from lib.pipeline_loader import get_stage_order, load_pipeline
from schemas.artifacts import validate_artifact

A = "a" * 64
B = "b" * 64
C = "c" * 64


def _intent() -> dict:
    return {
        "version": "creative-intent/v0.1",
        "source_render": "draft.mp4",
        "segments": [
            {
                "id": "hook",
                "t_start": 0,
                "t_end": 4,
                "intent": "establish concrete conflict immediately",
                "must_convey": "demand booming but the tool is not ready",
                "creative_freedom": "high",
            }
        ],
    }


def _finding(**overrides) -> dict:
    row = {
        "t_start": 0,
        "t_end": 4,
        "frame_ids": ["f00"],
        "intent_id": "hook",
        "failure_class": "hook_too_abstract",
        "evidence": "At 0.0s frame f00 still shows a generic title card with no conflict.",
        "why_it_fails_intent": "Intent required concrete conflict in the first 4s; the picture does not.",
    }
    row.update(overrides)
    return row


def _critique(findings=None, source=A) -> dict:
    return {
        "version": "editorial-critique/v0.1",
        "source_sha256": source,
        "findings": findings or [_finding()],
    }


def _frames(tmp_path: Path, source=A) -> dict:
    png = tmp_path / "f00.png"
    png.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )
    digest = "d" * 64
    return {
        "version": "frame-packet/v0.1",
        "source_mp4": "draft.mp4",
        "source_sha256": source,
        "duration_seconds": 8,
        "frames": [
            {"id": "f00", "t": 0.0, "path": str(png), "sha256": digest, "kind": "t0"},
            {"id": "f01", "t": 4.0, "path": str(png), "sha256": digest, "kind": "interval"},
            {"id": "f02", "t": 8.0, "path": str(png), "sha256": digest, "kind": "anchor"},
        ],
        "machine_checks": {
            "probe_ok": True,
            "black_frame": False,
            "duration_seconds": 8,
            "width": 1,
            "height": 1,
            "issues": [],
        },
    }


def test_animated_explainer_has_explicit_reentry():
    manifest = load_pipeline("animated-explainer")
    order = get_stage_order(manifest)
    assert order[order.index("compose") : order.index("publish") + 1] == [
        "compose",
        "visual_review",
        "repair_plan",
        "patch",
        "rerender",
        "publish",
    ]
    rerender = next(s for s in manifest["stages"] if s["name"] == "rerender")
    assert rerender["reentry"]["of"] == "compose"
    assert rerender["reentry"]["required_cycle"] is True


def test_research_report_explainer_has_explicit_reentry():
    order = get_pipeline_stages("research-report-explainer")
    assert order[order.index("compose") : order.index("independent_qa") + 1] == [
        "compose",
        "visual_review",
        "repair_plan",
        "patch",
        "rerender",
        "independent_qa",
    ]


def test_intent_rejects_checklist_fields():
    payload = _intent()
    payload["segments"][0]["hook_rule"] = "must open with conflict"
    with pytest.raises(Exception):
        validate_artifact("creative_intent_contract", payload)


def test_generic_critique_is_rejected(tmp_path):
    critique = _critique(
        [
            _finding(
                evidence="节奏可以更紧凑，视觉可以更丰富，整体观感建议再加强一层。",
                why_it_fails_intent="节奏可以更紧凑，视觉可以更丰富，所以整段都要重做。",
            )
        ]
    )
    with pytest.raises(CreativeLoopError, match="generic"):
        validate_critique_grounding(critique, _frames(tmp_path), _intent())


def test_ungrounded_critique_is_rejected(tmp_path):
    critique = _critique([_finding(frame_ids=["nope"])])
    with pytest.raises(CreativeLoopError, match="unknown frames"):
        validate_critique_grounding(critique, _frames(tmp_path), _intent())


def test_grounded_critique_passes(tmp_path):
    validate_critique_grounding(_critique(), _frames(tmp_path), _intent())


def test_learning_event_forbids_retrieval(tmp_path):
    event = {
        "version": "learning-event/v0.1",
        "artifact": "draft.mp4",
        "failure_observed": "hook_too_abstract",
        "evidence": "0.0s title card",
        "failure_class": "hook_too_abstract",
        "constraint_class": "prior",
        "repair": "moved concrete contrast into frame 1",
        "result": "pending_human",
        "human_accept": "pending",
        "applies_when": "explanatory short video",
        "counterexample": "slow-form documentary may delay conflict",
        "auto_retrieve": False,
    }
    out = tmp_path / "LEARNING_EVENT.json"
    write_learning_event(out, event)
    with pytest.raises(CreativeLoopError, match="retrieval"):
        retrieve_learning_events()


def test_learning_event_accepts_human_reject(tmp_path):
    event = {
        "version": "learning-event/v0.1",
        "artifact": "draft.mp4",
        "failure_observed": "orphan_line",
        "evidence": "widow glyph on line 2",
        "failure_class": "orphan_line",
        "constraint_class": "hard",
        "repair": "none",
        "result": "human_reject",
        "human_accept": "reject",
        "human_reason": "orphan line",
        "applies_when": "CJK overlay",
        "counterexample": "none for glyph clip",
        "auto_retrieve": False,
    }
    write_learning_event(tmp_path / "LEARNING_EVENT.json", event)


def test_publish_cannot_skip_the_repair_cycle():
    stages = get_pipeline_stages("animated-explainer")
    assert stages.index("visual_review") < stages.index("rerender")
    assert stages.index("rerender") < stages.index("publish")
    assert get_pipeline_stages("animated-explainer")[-1] == "publish"


def test_extract_frames_requires_real_mp4(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x240:d=2",
            "-pix_fmt",
            "yuv420p",
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )
    packet = extract_frames(mp4, tmp_path / "frames", interval=1.0, anchors=[0.5])
    assert packet["frames"][0]["t"] == 0.0
    assert Path(packet["frames"][0]["path"]).is_file()
    assert packet["machine_checks"]["probe_ok"] is True
