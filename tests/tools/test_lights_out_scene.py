from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ADAPTER_SRC = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "src"
sys.path.insert(0, str(ADAPTER_SRC))

from om_prime_adapter import (  # noqa: E402
    AdapterError,
    compile_cut,
    complete_observation,
    compose_scene,
    dispatch_cut,
    open_job,
    record_human_preference,
    submit_scene_proposal,
)
from om_prime_adapter.production import (  # noqa: E402
    LIGHTS_OUT_STATUS,
    SHOWPIECE_STATUSES,
    _is_lights_out,
    _is_showpiece,
)
from tests.tools.test_prime_production_entry import (  # noqa: E402
    _fake_h3,
    _fake_see,
    _fake_see_limited,
    _lock_lucien,
    _studio_job,
    _write_json,
    _write_readable_mcu_png,
)


def _boom_h3(inputs):
    raise AssertionError("H3 must not run for NONE/LOCAL")


def _fake_local(first, output_path, duration):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"fake-local-mp4")


def _fake_concat(paths, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"".join(p.read_bytes() for p in paths))


def _lights_out_shots() -> list[dict]:
    return [
        {
            "id": "S1",
            "visual_intent": "Wide kitchen establishing hold. Intentional freeze.",
            "motion_obligation": "NONE",
            "animation_class": "LIMITED",
            "intentional_hold": True,
            "character_ids": ["lucien_mercer"],
            "framing": "wide",
            "start_seconds": 0.0,
            "end_seconds": 2.5,
            "review_decision": "candidate",
        },
        {
            "id": "S2",
            "visual_intent": "MCU Lucien. Face, collar, identity readable.",
            "performance_intent": "freeze, raise or turn the head, stop. No locomotion.",
            "motion_obligation": "PERFORMANCE",
            "animation_class": "I2V_HARD",
            "character_ids": ["lucien_mercer"],
            "framing": "medium_close",
            "reference_atoms": ["freeze_notice", "weight_shift"],
            "start_seconds": 2.5,
            "end_seconds": 10.0,
            "review_decision": "candidate",
        },
        {
            "id": "S3",
            "visual_intent": "Insert of steam or board. Not H3.",
            "motion_obligation": "LOCAL",
            "animation_class": "LIMITED",
            "framing": "insert",
            "start_seconds": 10.0,
            "end_seconds": 12.5,
            "review_decision": "candidate",
        },
        {
            "id": "S4",
            "visual_intent": "Still hold reaction. Not PERFORMANCE.",
            "motion_obligation": "NONE",
            "animation_class": "LIMITED",
            "intentional_hold": True,
            "character_ids": ["avery_sterling"],
            "framing": "medium_close",
            "start_seconds": 12.5,
            "end_seconds": 15.0,
            "review_decision": "candidate",
        },
    ]


def _prepare_lights_out(tmp_path, monkeypatch) -> tuple[str, Path]:
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    _write_json(
        project_dir / "JOB_SKELETON.json",
        {
            "status": "LIGHTS_OUT_SCENE_PROOF",
            "scene_id": "scene_lights_out",
            "project_id": job_id,
            "foreman_proven": False,
            "frozen": False,
        },
    )
    return job_id, project_dir


def _submit_four(job_id: str) -> None:
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_lights_out",
            "audience_state_change": "The kitchen holds, Lucien breaks the freeze, then the scene settles.",
            "visual_intent": "Tiny four-cut kitchen. One H3 MCU. Three local holds.",
            "duration_target": "15s",
        },
        caller="prime",
    )
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_lights_out")
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_lights_out",
            "audience_state_change": "The kitchen holds, Lucien breaks the freeze, then the scene settles.",
            "visual_intent": "Tiny four-cut kitchen. One H3 MCU. Three local holds.",
            "duration_target": "15s",
            "shots": _lights_out_shots(),
        },
        caller="prime",
    )


def test_lights_out_is_not_showpiece():
    assert LIGHTS_OUT_STATUS not in SHOWPIECE_STATUSES
    skel = {"status": "LIGHTS_OUT_SCENE_PROOF", "project_id": "vid-lights-out-scene-v1", "scene_id": "scene_lights_out"}
    proposal = {"scene_id": "scene_lights_out"}
    assert _is_lights_out(skel, proposal) is True
    assert _is_showpiece(skel, proposal) is False
    assert _is_showpiece({"status": "PRIME_FOREMAN_PROOF"}, {"scene_id": "scene_foreman"}) is True


def test_next_step_waits_for_continue(tmp_path, monkeypatch):
    job_id, _project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_preference"
    assert "CONTINUE_SCENE" in world["next_step"]["summary"]
    assert world["next_step"]["scene_id"] == "scene_lights_out"


def test_lights_out_walk_local_h3_local_then_compose_and_review_queue(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_lights_out")
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "submit_scene_proposal"
    assert world["next_step"]["shot_ids"] == ["S1", "S2", "S3", "S4"]

    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_lights_out",
            "audience_state_change": "The kitchen holds, Lucien breaks the freeze, then the scene settles.",
            "visual_intent": "Tiny four-cut kitchen. One H3 MCU. Three local holds.",
            "duration_target": "15s",
            "shots": _lights_out_shots(),
        },
        caller="prime",
    )
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    monkeypatch.setattr("lib.compose_scene._concat_mp4s", _fake_concat)
    monkeypatch.setattr("lib.compose_scene._see_mp4", _fake_see)

    performance = 0
    for shot_id in ("S1", "S2", "S3", "S4"):
        world = open_job(job_id)["production_world"]
        assert world["next_step"]["action"] == "compile_cut"
        assert world["next_step"]["shot_id"] == shot_id
        compile_cut(job_id, shot_id, caller="prime")
        world = open_job(job_id)["production_world"]
        assert world["next_step"]["action"] == "produce_keyframe"
        assert world["next_step"]["shot_id"] == shot_id
        _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / f"{shot_id}.png")
        world = open_job(job_id)["production_world"]
        assert world["next_step"]["action"] == "dispatch_cut"
        assert world["next_step"]["shot_id"] == shot_id
        if shot_id == "S2":
            monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
            monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_limited)
            performance += 1
        else:
            monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
        out = dispatch_cut(job_id, shot_id, caller="prime")
        assert out["status"] == "succeeded"
        assert out.get("frozen") is not True
        assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
        if shot_id == "S2":
            assert out["mode"] == "fl2va"
            assert out["renderer"] == "h3"
            assert out["config"]["length"] == 124
            assert out["config"]["requested_duration_seconds"] == 7.5
            assert out["config"]["duration_capped_to_ship_grid"] is True
            assert out["config"]["clip_device"] == "cpu"
        else:
            assert out["mode"] == "still_hold"
            assert out["provider"] == "ffmpeg"
            assert float(out["config"]["duration_seconds"]) <= 3.5

    assert performance == 1
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "compose_scene"
    composed = compose_scene(job_id, caller="prime")
    assert composed["status"] == "succeeded"
    assert composed["stamped"] is False
    queue = json.loads(
        (project_dir / "working" / "prime_rlm" / "REVIEW_QUEUE.json").read_text(encoding="utf-8")
    )
    assert queue["composed_hash"]
    assert set(queue["shot_hashes"]) == {"S1", "S2", "S3", "S4"}
    assert all(queue["shot_hashes"].values())
    assert queue["lights_out_scene_production_proven"] is False
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_preference"
    assert "scene" in world["next_step"]["summary"].lower()
    assert "not per-cut" in world["next_step"]["summary"].lower() or "not cuts" in world["next_step"]["summary"].lower()
    assert "LIGHTS_OUT_SCENE_PRODUCTION_PROVEN" in world["next_step"]["summary"]
    assert world["foreman_proven"] is False


def test_dispatch_cut_none_does_not_call_h3(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    _submit_four(job_id)
    compile_cut(job_id, "S1", caller="prime")
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S1.png")
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    out = dispatch_cut(job_id, "S1", caller="prime")
    assert out["status"] == "succeeded"
    assert out["mode"] == "still_hold"
    assert out.get("frozen") is not True


def test_no_freeze_after_single_succeeded_performance(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    _submit_four(job_id)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    compile_cut(job_id, "S1", caller="prime")
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S1.png")
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    dispatch_cut(job_id, "S1", caller="prime")
    compile_cut(job_id, "S2", caller="prime")
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S2.png")
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_limited)
    out = dispatch_cut(job_id, "S2", caller="prime")
    assert out["status"] == "succeeded"
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] in {"compile_cut", "produce_keyframe", "dispatch_cut"}
    assert world["next_step"]["shot_id"] == "S3"
    assert world["next_step"]["action"] != "first_take_acceptable"


def test_incomplete_observation_rebinds_same_hash_not_redispatch(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    _submit_four(job_id)
    compile_cut(job_id, "S1", caller="prime")
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S1.png")
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    landed = dispatch_cut(job_id, "S1", caller="prime")
    rollout_id = landed["rollout_id"]
    digest = landed["output_hash"]
    out = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    (out / "OBSERVATION.json").unlink(missing_ok=True)
    receipt = json.loads((out / "RECEIPT.json").read_text(encoding="utf-8"))
    receipt["status"] = "failed"
    receipt["error"] = "observation_failed: schema invalid"
    receipt["observation_path"] = None
    _write_json(out / "RECEIPT.json", receipt)
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "observation_incomplete"
    assert world["next_step"]["bind_tool"] == "complete_observation"
    assert world["next_step"]["rollout_id"] == rollout_id
    with pytest.raises(AdapterError, match="rollout_already_landed"):
        dispatch_cut(job_id, "S1", caller="prime")
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    bound = complete_observation(job_id, rollout_id, caller="prime")
    assert bound["status"] == "succeeded"
    assert bound["output_hash"] == digest
    assert bound.get("frozen") is not True


def test_compose_scene_writes_review_queue_with_hashes(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    _submit_four(job_id)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    monkeypatch.setattr("lib.compose_scene._concat_mp4s", _fake_concat)
    monkeypatch.setattr("lib.compose_scene._see_mp4", _fake_see)
    for shot_id in ("S1", "S2", "S3", "S4"):
        compile_cut(job_id, shot_id, caller="prime")
        _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / f"{shot_id}.png")
        if shot_id == "S2":
            monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
            monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_limited)
        else:
            monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
        dispatch_cut(job_id, shot_id, caller="prime")
    payload = compose_scene(job_id, caller="prime")
    queue_path = project_dir / "working" / "prime_rlm" / "REVIEW_QUEUE.json"
    assert queue_path.is_file()
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert queue["composed_hash"] == payload["composed_hash"]
    assert len(queue["composed_hash"]) == 64
    assert all(len(h) == 64 for h in queue["shot_hashes"].values())


def test_cursor_cannot_dispatch_or_compose(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_lights_out(tmp_path, monkeypatch)
    _lock_lucien(project_dir)
    _submit_four(job_id)
    compile_cut(job_id, "S1", caller="prime")
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S1.png")
    with pytest.raises(AdapterError, match="Cursor cannot impersonate"):
        dispatch_cut(job_id, "S1", caller="cursor")
    with pytest.raises(AdapterError, match="Cursor cannot impersonate"):
        compose_scene(job_id, caller="cursor")


def test_lights_out_launcher_flag_and_prompt_exist():
    script = Path(__file__).resolve().parents[2] / "tools" / "run_prime_foreman_session.py"
    text = script.read_text(encoding="utf-8")
    assert "--lights-out" in text
    assert "FOREMAN_LIGHTS_OUT_SCENE_PROOF.md" in text
    assert "7200" in text
    prompt = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "FOREMAN_LIGHTS_OUT_SCENE_PROOF.md"
    assert prompt.is_file()
    body = prompt.read_text(encoding="utf-8")
    assert "vid-lights-out-scene-v1" in body
    assert "scene_lights_out" in body
    assert "compose_scene" in body
    assert "Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN" in body


def test_live_job_exists_and_is_not_stamped(monkeypatch):
    jobs = Path(r"C:\ContentStudio\jobs\vid-lights-out-scene-v1")
    if not (jobs / "project.json").is_file():
        pytest.skip("live lights-out job not on this machine")
    monkeypatch.setenv("OM_PRIME_ADAPTER_ROOT", r"C:\ContentStudio")
    monkeypatch.setenv("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs")
    from schemas.artifacts import validate_artifact

    plan = json.loads((jobs / "artifacts" / "scene_plan.json").read_text(encoding="utf-8"))
    validate_artifact("scene_plan", plan)
    h3 = [row for row in plan["scenes"] if str(row.get("motion_obligation") or "").upper() == "PERFORMANCE"]
    assert [row["id"] for row in h3] == ["S2"]
    assert plan["metadata"]["generate"] is False
    job = open_job("vid-lights-out-scene-v1")
    world = job["production_world"]
    assert world["job_skeleton"]["status"] == "LIGHTS_OUT_SCENE_PROOF"
    assert world["next_step"]["action"] == "lights_out_execution_proven"
    assert world["character_identities"]["lucien_mercer"]["locked"] is True
    assert world["foreman_proven"] is False
    assert world["next_step"].get("lights_out_scene_production_proven") is not True
    freeze = json.loads((jobs / "working" / "prime_rlm" / "JOB_FREEZE.json").read_text(encoding="utf-8"))
    assert freeze["frozen"] is True
    assert freeze["reason"] == "lights_out_execution_proven"
