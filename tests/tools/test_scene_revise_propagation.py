from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ADAPTER_SRC = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "src"
sys.path.insert(0, str(ADAPTER_SRC))

from om_prime_adapter import (  # noqa: E402
    AdapterError,
    compile_cut,
    compose_scene,
    dispatch_cut,
    open_job,
    record_human_preference,
    submit_revision_proposal,
    submit_scene_proposal,
)
from om_prime_adapter.production import (  # noqa: E402
    REVISE_SCENE,
    REVISE_STATUS,
    _is_lights_out,
    _is_revise,
    _is_showpiece,
)
from tests.tools.test_lights_out_scene import _boom_h3, _lights_out_shots  # noqa: E402
from tests.tools.test_prime_production_entry import (  # noqa: E402
    _fake_see,
    _lock_lucien,
    _studio_job,
    _write_json,
    _write_readable_mcu_png,
)


def _fake_local_revised(first, output_path, duration, metadata=None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"fake-local-revised-mp4")


def _fake_concat_v2(paths, output, metadata=None):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"v2-" + b"".join(p.read_bytes() for p in paths))


def _obs(digest: str) -> dict:
    return {
        "output_hash": digest,
        "media_valid": True,
        "source_hash_matches": True,
        "quality": {"passed": True, "blockers": []},
    }


def _seed_v1(project_dir: Path) -> tuple[dict[str, str], str]:
    hashes: dict[str, str] = {}
    for shot_id in ("S1", "S2", "S3", "S4"):
        rid = f"{shot_id.lower()}-parent000001"
        out = project_dir / "working" / "prime_rlm" / "rollouts" / rid
        out.mkdir(parents=True, exist_ok=True)
        mp4 = out / f"{shot_id}.mp4"
        mp4.write_bytes(f"v1-{shot_id}-mp4".encode("utf-8"))
        digest = hashlib.sha256(mp4.read_bytes()).hexdigest()
        hashes[shot_id] = digest
        _write_json(
            out / "RECEIPT.json",
            {
                "rollout_id": rid,
                "shot_id": shot_id,
                "status": "succeeded",
                "output_hash": digest,
                "revision_number": 1,
                "motion_obligation": "PERFORMANCE" if shot_id == "S2" else "LOCAL",
                "renderer": "h3" if shot_id == "S2" else "local_compose",
            },
        )
        _write_json(out / "OBSERVATION.json", _obs(digest))
        _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "keyframes" / f"{shot_id}.png")
        _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / f"{shot_id}.png")
    composed = project_dir / "working" / "prime_rlm" / "composed"
    composed.mkdir(parents=True, exist_ok=True)
    v1 = composed / "scene_v1.mp4"
    v1.write_bytes(b"v1-composed-scene")
    parent_hash = hashlib.sha256(v1.read_bytes()).hexdigest()
    _write_json(
        composed / "PARENT_COMPOSE.json",
        {
            "parent_scene_hash": parent_hash,
            "shot_hashes": hashes,
            "composed_path": "working/prime_rlm/composed/scene_v1.mp4",
            "review_id": "2026-08-17T12:05:19.483108+00:00",
            "source_job": "vid-lights-out-scene-v1",
        },
    )
    return hashes, parent_hash


def _prepare_revise(tmp_path, monkeypatch) -> tuple[str, Path, dict[str, str], str]:
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    _write_json(
        project_dir / "JOB_SKELETON.json",
        {
            "status": REVISE_STATUS,
            "scene_id": REVISE_SCENE,
            "project_id": job_id,
            "h3_only": "S2",
            "foreman_proven": False,
            "frozen": False,
        },
    )
    _lock_lucien(project_dir)
    record_human_preference(job_id, "REVISE", caller="human", target=REVISE_SCENE)
    submit_scene_proposal(
        job_id,
        {
            "scene_id": REVISE_SCENE,
            "audience_state_change": "Tail stills and missing steam are the revise evidence.",
            "visual_intent": "Keep S1/S2. Revise S3/S4 only.",
            "duration_target": "15s",
            "shots": _lights_out_shots(),
        },
        caller="prime",
    )
    hashes, parent_hash = _seed_v1(project_dir)
    return job_id, project_dir, hashes, parent_hash


def _submit_s3_s4(job_id: str) -> None:
    submit_revision_proposal(
        job_id,
        {
            "affected_shots": ["S3", "S4"],
            "unchanged_shots": ["S1", "S2"],
            "revision_reason": "After 10s two stills look bad; pot smoke does not rise.",
            "revision_number": 2,
        },
        caller="prime",
    )


def test_revise_is_not_showpiece_or_lights_out():
    skel = {"status": REVISE_STATUS, "project_id": "vid-scene-revise-v1", "scene_id": REVISE_SCENE}
    proposal = {"scene_id": REVISE_SCENE}
    assert _is_revise(skel, proposal) is True
    assert _is_lights_out(skel, proposal) is False
    assert _is_showpiece(skel, proposal) is False


def test_revise_is_not_terminal_stop(tmp_path, monkeypatch):
    job_id, _project_dir, _hashes, _parent = _prepare_revise(tmp_path, monkeypatch)
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "submit_revision_proposal"
    assert "REVISE" in world["next_step"]["summary"]


def test_rejects_s2_in_affected(tmp_path, monkeypatch):
    job_id, _project_dir, _hashes, _parent = _prepare_revise(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="immutable_h3_shot"):
        submit_revision_proposal(
            job_id,
            {
                "affected_shots": ["S2", "S3", "S4"],
                "revision_reason": "whole scene",
                "revision_number": 2,
            },
            caller="prime",
        )


def test_targeted_revision_keeps_s1_s2_hashes_and_new_scene_hash(tmp_path, monkeypatch):
    job_id, project_dir, hashes, parent_hash = _prepare_revise(tmp_path, monkeypatch)
    _submit_s3_s4(job_id)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local_revised)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    monkeypatch.setattr("lib.compose_scene._concat_mp4s", _fake_concat_v2)
    monkeypatch.setattr("lib.compose_scene._see_mp4", _fake_see)

    h3_calls = []

    def _count_h3(inputs):
        h3_calls.append(inputs)
        raise AssertionError("H3 must not run during revision of LOCAL/NONE cuts")

    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _count_h3)

    for shot_id in ("S3", "S4"):
        world = open_job(job_id)["production_world"]
        assert world["next_step"]["action"] == "compile_cut"
        assert world["next_step"]["shot_id"] == shot_id
        compile_cut(job_id, shot_id, caller="prime")
        world = open_job(job_id)["production_world"]
        assert world["next_step"]["action"] == "dispatch_cut"
        assert world["next_step"]["shot_id"] == shot_id
        out = dispatch_cut(job_id, shot_id, caller="prime")
        assert out["status"] == "succeeded"
        assert out["revision_number"] == 2
        assert out["parent_output_hash"] == hashes[shot_id]
        assert out["output_hash"] != hashes[shot_id]
        assert out["renderer"] == "local_compose"

    assert h3_calls == []
    with pytest.raises(AdapterError, match="unchanged_shot_immutable"):
        dispatch_cut(job_id, "S2", caller="prime")
    with pytest.raises(AdapterError, match="unchanged_shot_immutable"):
        dispatch_cut(job_id, "S1", caller="prime")

    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "compose_scene"
    composed = compose_scene(job_id, caller="prime")
    assert composed["composed_hash"] != parent_hash
    assert composed["parent_scene_hash"] == parent_hash
    assert composed["shot_hashes"]["S1"] == hashes["S1"]
    assert composed["shot_hashes"]["S2"] == hashes["S2"]
    assert composed["shot_hashes"]["S3"] != hashes["S3"]
    assert composed["shot_hashes"]["S4"] != hashes["S4"]
    queue = json.loads(
        (project_dir / "working" / "prime_rlm" / "REVIEW_QUEUE.json").read_text(encoding="utf-8")
    )
    assert queue["revision_number"] == 2
    assert queue["affected_shots"] == ["S3", "S4"]
    assert "S2" not in queue["affected_shots"]
    assert (project_dir / "working" / "prime_rlm" / "composed" / "scene_v2.mp4").is_file()
    assert (project_dir / "working" / "prime_rlm" / "composed" / "scene_v1.mp4").is_file()
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_preference"
    summary = world["next_step"]["summary"].lower()
    assert "scene" in summary
    assert "not per-cut" in summary or "not cuts" in summary
    assert world["foreman_proven"] is False


def test_resume_open_job_does_not_redispatch_landed_revision_cut(tmp_path, monkeypatch):
    job_id, _project_dir, _hashes, _parent = _prepare_revise(tmp_path, monkeypatch)
    _submit_s3_s4(job_id)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _boom_h3)
    monkeypatch.setattr("lib.dispatch_cut._local_compose_still", _fake_local_revised)
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    compile_cut(job_id, "S3", caller="prime")
    first = dispatch_cut(job_id, "S3", caller="prime")
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "compile_cut"
    assert world["next_step"]["shot_id"] == "S4"
    with pytest.raises(AdapterError, match="rollout_already_landed"):
        dispatch_cut(job_id, "S3", caller="prime")
    assert first["output_hash"]


def test_cursor_cannot_submit_revision(tmp_path, monkeypatch):
    job_id, _project_dir, _hashes, _parent = _prepare_revise(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Cursor cannot impersonate"):
        submit_revision_proposal(
            job_id,
            {
                "affected_shots": ["S3", "S4"],
                "revision_reason": "x",
                "revision_number": 2,
            },
            caller="cursor",
        )


def test_launcher_flag_and_prompt_exist():
    script = Path(__file__).resolve().parents[2] / "tools" / "run_prime_foreman_session.py"
    text = script.read_text(encoding="utf-8")
    assert "--scene-revise" in text
    assert "FOREMAN_SCENE_REVISE_PROOF.md" in text
    prompt = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "FOREMAN_SCENE_REVISE_PROOF.md"
    assert prompt.is_file()
    body = prompt.read_text(encoding="utf-8")
    assert "vid-scene-revise-v1" in body
    assert "submit_revision_proposal" in body
    assert "Do not redispatch S2" in body or "Never dispatch S2" in body


def test_live_revise_job_seeded(monkeypatch):
    jobs = Path(r"C:\ContentStudio\jobs\vid-scene-revise-v1")
    if not (jobs / "project.json").is_file():
        pytest.skip("live revise job not on this machine")
    monkeypatch.setenv("OM_PRIME_ADAPTER_ROOT", r"C:\ContentStudio")
    monkeypatch.setenv("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs")
    parent = "606c7f5ac71354b1494af823dedbae8239e7a9e3b8af8b88117b7a40db1ef210"
    s2_hash = "1dabb032629cb96c2f2924f165b63492862d134e4393d356d88ef0b46bea61e5"
    s1_hash = "fbf712f393f794408d3dcfcde5286ece6e9813b51d5c0397941cd50c20f5b7ef"
    assert (jobs / "working" / "prime_rlm" / "composed" / "scene_v1.mp4").is_file()
    assert (jobs / "working" / "prime_rlm" / "composed" / "scene_v2.mp4").is_file()
    freeze = json.loads((jobs / "working" / "prime_rlm" / "JOB_FREEZE.json").read_text(encoding="utf-8"))
    assert freeze["frozen"] is True
    assert freeze["reason"] == "scene_revision_routing_proven"
    assert freeze["proven_status"] == "SCENE_REVISION_ROUTING_PROVEN"
    assert freeze["scene_revision_routing_proven"] is True
    assert freeze["scene_revision_effectiveness_proven"] is False
    s3_v2 = json.loads(
        (jobs / "working" / "prime_rlm" / "rollouts" / "s3-70773a93abae" / "RECEIPT.json").read_text(
            encoding="utf-8"
        )
    )
    assert s3_v2["mode"] == "still_hold"
    assert s3_v2["provider"] == "ffmpeg"
    revision = json.loads((jobs / "working" / "prime_rlm" / "SCENE_REVISION.json").read_text(encoding="utf-8"))
    assert revision["affected_shots"] == ["S3", "S4"]
    assert "S2" not in revision["affected_shots"]
    queue = json.loads((jobs / "working" / "prime_rlm" / "REVIEW_QUEUE.json").read_text(encoding="utf-8"))
    assert queue["parent_scene_hash"] == parent
    assert queue["composed_hash"] != parent
    assert queue["shot_hashes"]["S1"] == s1_hash
    assert queue["shot_hashes"]["S2"] == s2_hash
    assert queue["shot_hashes"]["S3"] != "dbaeddec830714a5f3a0302f0272eaec432710960fc78589a2b84e00fed873f0"
    assert queue["shot_hashes"]["S4"] != "4e07715db4bcf20a43d75785f0e6eeb8197da28b0e897966608e422e0a3c51fa"
    s2 = jobs / "working" / "prime_rlm" / "rollouts" / "s2-12824f9ec84a" / "S2.mp4"
    assert hashlib.sha256(s2.read_bytes()).hexdigest() == s2_hash
    s2_rollouts = list((jobs / "working" / "prime_rlm" / "rollouts").glob("s2-*/RECEIPT.json"))
    assert len(s2_rollouts) == 1
    job = open_job("vid-scene-revise-v1")
    world = job["production_world"]
    assert world["next_step"]["action"] == "scene_revision_routing_proven"
    assert world["next_step"]["scene_revision_effectiveness_proven"] is False
    assert world["foreman_proven"] is False
