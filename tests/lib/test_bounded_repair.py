from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from lib.bounded_repair import (
    BOUND_REACHED,
    RepairError,
    default_actions,
    dispatch_bounded_repair,
    propose_bounded_repair,
)
from lib.quality_observation import evaluate_quality_observation


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _mcu(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 720), (150, 150, 155))
    draw = ImageDraw.Draw(image)
    draw.ellipse((520, 80, 760, 380), fill=(210, 170, 145))
    draw.rectangle((500, 360, 780, 700), fill=(40, 42, 48))
    draw.rectangle((560, 400, 600, 430), fill=(180, 160, 90))
    image.save(path)


def _parent(project_dir: Path, *, gait: bool = True) -> str:
    rollout_id = "b2-parentfake01"
    out = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": (
                "unhurried approach, full-body locomotion" if gait else "eyes shift, one breath"
            ),
        },
        observation={"character_motion_present": True, "media_valid": True},
        temporal={
            "motion_type": {"segment_1": "LIMITED_LOCAL_MOTION" if gait else "FULL_MOTION"},
            "mouth_motion": "unmeasured",
        },
    )
    _write_json(
        out / "RECEIPT.json",
        {
            "rollout_id": rollout_id,
            "shot_id": "B2",
            "status": "succeeded",
            "output_hash": "parenthash",
            "config": {"duration_seconds": 8.0},
        },
    )
    _write_json(out / "OBSERVATION.json", {"quality": quality, "media_valid": True})
    _write_json(
        project_dir / "working" / "prime_rlm" / "scene_proposals" / "scene_b.json",
        {
            "scene_id": "scene_b",
            "shots": [
                {
                    "id": "B2",
                    "motion_obligation": "PERFORMANCE",
                    "performance_intent": "unhurried approach, full-body locomotion",
                    "character_ids": ["lucien_mercer"],
                }
            ],
        },
    )
    _mcu(project_dir / "working" / "prime_rlm" / "start_frames" / "B2.png")
    return rollout_id


def _fake_h3(calls: list):
    from tools.base_tool import ToolResult

    def invoke(inputs):
        calls.append(inputs)
        out = Path(inputs["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-repair-mp4")
        return ToolResult(success=True, data={"model": "minimax-h3"}, artifacts=[str(out)])

    return invoke


def _fake_see(mp4: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = "abc"
    (out_dir / "temporal_motion_report.json").write_text("{}", encoding="utf-8")
    (out_dir / "frame_packet.json").write_text("{}", encoding="utf-8")
    (out_dir / "audio_event_map.json").write_text("{}", encoding="utf-8")
    return {
        "frame_packet": {"source_sha256": digest, "machine_checks": {"probe_ok": True}, "frames": []},
        "temporal_motion_report": {
            "source_sha256": digest,
            "duration_seconds": 8.0,
            "longest_static_run": 0.2,
            "motion_type": {"segment_1": "FULL_MOTION"},
            "local_character_motion": "present",
            "mouth_motion": "unmeasured",
        },
        "audio_event_map": {"first_sound_seconds": 0.1},
    }


def test_cursor_cannot_propose_repair(tmp_path):
    parent = _parent(tmp_path)
    with pytest.raises(RepairError, match="Cursor cannot impersonate"):
        propose_bounded_repair(tmp_path, parent, caller="cursor")


def test_keyframe_repair_does_not_call_h3(tmp_path):
    parent = _parent(tmp_path, gait=True)
    # identity_weak is absent here; force keyframe action
    out = propose_bounded_repair(tmp_path, parent, caller="prime", actions=["keyframe"])
    assert out["action"] == "keyframe"
    result = dispatch_bounded_repair(tmp_path, tmp_path, parent, caller="prime")
    assert result["status"] == "blocked"
    assert result["error"] == "repair_requires_readable_keyframe"
    assert result["foreman_proven"] is False


def test_temporal_repair_rerolls_once_then_ab_bound(tmp_path):
    parent = _parent(tmp_path, gait=True)
    proposal = propose_bounded_repair(tmp_path, parent, caller="prime")
    assert proposal["action"] == "temporal_reference"
    calls: list = []
    child = dispatch_bounded_repair(
        tmp_path,
        tmp_path,
        parent,
        caller="prime",
        invoke_h3=_fake_h3(calls),
        see_fn=_fake_see,
    )
    assert child["status"] == "succeeded"
    assert child["parent_rollout_id"] == parent
    assert child["awaiting_human_ab"] is True
    assert child["foreman_proven"] is False
    assert calls and calls[0]["h3_ir"]["locomotion"] is True
    pair = json.loads((tmp_path / "working" / "prime_rlm" / "AB_PAIR.json").read_text(encoding="utf-8"))
    assert pair["A"]["rollout_id"] == parent
    assert pair["A"]["output_hash"] == "parenthash"
    assert pair["A"]["repair_dimension"] is None
    assert pair["B"]["rollout_id"] == child["rollout_id"]
    assert pair["B"]["output_hash"]
    assert pair["B"]["repair_dimension"] == "temporal_reference"
    with pytest.raises(RepairError, match=BOUND_REACHED):
        propose_bounded_repair(tmp_path, parent, caller="prime")


def test_eye_shift_repair_targets_prompt_not_more_motion():
    assert default_actions({"blockers": ["eye_shift_not_realized"]}) == ["prompt"]
    assert default_actions({"blockers": ["performance_not_full_motion"]}) == ["abandon"]


def test_quality_passed_with_proven_beats_refuses_invented_repair(tmp_path):
    rollout_id = "s2-beatsproven01"
    out = tmp_path / "working" / "prime_rlm" / "rollouts" / rollout_id
    quality = evaluate_quality_observation(
        contract={
            "motion_obligation": "PERFORMANCE",
            "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
            "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
        },
        observation={"character_motion_present": True, "media_valid": True},
        temporal={
            "motion_type": {
                "segment_1": "LIMITED_LOCAL_MOTION",
                "segment_2": "STATIC_HOLD",
            },
            "local_character_motion": "present",
            "longest_static_run": 0.9,
            "eye_shift": "present",
        },
    )
    assert quality["passed"] is True
    assert quality["beat_realization_unresolved"] is False
    _write_json(out / "RECEIPT.json", {"rollout_id": rollout_id, "shot_id": "S2", "status": "succeeded"})
    _write_json(out / "OBSERVATION.json", {"quality": quality, "media_valid": True})
    with pytest.raises(RepairError, match="quality_passed_nothing_to_repair"):
        propose_bounded_repair(tmp_path, rollout_id, caller="prime")
    parent = _parent(tmp_path, gait=False)
    with pytest.raises(RepairError, match="temporal_beat_realization_unresolved"):
        propose_bounded_repair(tmp_path, parent, caller="prime")


def test_incomplete_observation_does_not_spend_repair_quota(tmp_path):
    parent = _parent(tmp_path, gait=False)
    _write_json(
        tmp_path / "working" / "prime_rlm" / "rollouts" / parent / "OBSERVATION.json",
        {"media_valid": True},
    )
    with pytest.raises(RepairError, match="observation_incomplete"):
        propose_bounded_repair(tmp_path, parent, caller="prime")


def test_frozen_job_cannot_repair(tmp_path):
    parent = _parent(tmp_path)
    _write_json(
        tmp_path / "working" / "prime_rlm" / "JOB_FREEZE.json",
        {"schema_version": "om-job-freeze/v1", "frozen": True},
    )
    with pytest.raises(RepairError, match="frozen"):
        propose_bounded_repair(tmp_path, parent, caller="prime")
