from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lib.checkpoint import init_project, write_checkpoint
from tests.contracts.test_phase0_contracts import sample_artifact

ADAPTER_SRC = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "src"
sys.path.insert(0, str(ADAPTER_SRC))

from om_prime_adapter import (  # noqa: E402
    AdapterError,
    compile_cut,
    complete_observation,
    dispatch_bounded_repair,
    dispatch_cut,
    open_job,
    produce_keyframe,
    propose_bounded_repair,
    propose_identity_candidates,
    record_human_preference,
    submit_prerequisite_plan,
    submit_scene_proposal,
)


SCENARIO = "comic-nonfiction-short-knowledge-zh"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_readable_mcu_png(path: Path) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 720), (150, 150, 155))
    draw = ImageDraw.Draw(image)
    draw.ellipse((520, 80, 760, 380), fill=(210, 170, 145))
    draw.rectangle((500, 360, 780, 700), fill=(40, 42, 48))
    draw.rectangle((560, 400, 600, 430), fill=(180, 160, 90))
    image.save(path)


def _write_silhouette_png(path: Path) -> None:
    from PIL import Image, ImageDraw

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 720), (32, 36, 42))
    draw = ImageDraw.Draw(image)
    draw.rectangle((560, 220, 720, 500), fill=(255, 140, 40))
    draw.rectangle((632, 250, 648, 430), fill=(4, 4, 6))
    image.save(path)


def _studio_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, Path]:
    root = tmp_path / "ContentStudio"
    jobs = root / "jobs"
    job_id = "vid3-prime-entry-fixture"
    monkeypatch.setenv("OM_PRIME_ADAPTER_ROOT", str(root))
    monkeypatch.setenv("OPENMONTAGE_PROJECTS_DIR", str(jobs))
    init_project(
        job_id,
        title="Prime production entry fixture",
        pipeline_type="unknown",
        pipeline_dir=jobs,
        style_playbook="premium-minimalist",
    )
    project_dir = jobs / job_id
    marker_path = project_dir / "project.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["scenario_id"] = SCENARIO
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    research = sample_artifact("research_brief")
    _write_json(project_dir / "artifacts" / "research_brief.json", research)
    write_checkpoint(
        jobs,
        job_id,
        "research",
        "completed",
        {"research_brief": research},
        pipeline_type="unknown",
        style_playbook="premium-minimalist",
    )
    sheet = project_dir / "bible" / "avery" / "master_sheet.png"
    sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.write_bytes(b"identity-lock")
    plan = {
        "version": "1.0",
        "style_playbook": "premium-minimalist",
        "scenes": [
            {
                "id": "A1",
                "visual_intent": "HUD wakes on black",
                "animation_class": "LIMITED",
                "character_ids": [],
                "review_decision": "keep",
            },
            {
                "id": "A5",
                "visual_intent": "Threat sits in the body. Mouth closed.",
                "animation_class": "I2V_HARD",
                "character_ids": ["avery_sterling"],
                "review_decision": "candidate",
            },
            {
                "id": "WALK",
                "visual_intent": "Avery walks toward cooler",
                "performance_intent": "Avery walks toward cooler",
                "motion_obligation": "PERFORMANCE",
                "character_ids": ["avery_sterling"],
                "review_decision": "candidate",
            },
            {
                "id": "BAD",
                "visual_intent": "Avery walks toward cooler",
                "motion_obligation": "PERFORMANCE",
                "animation_class": "LIMITED",
                "renderer": "local_compose",
                "character_ids": ["avery_sterling"],
            },
            {
                "id": "c001",
                "visual_intent": "Jesse scrap",
                "animation_class": "LIMITED",
                "review_decision": "omit",
                "character_ids": ["jesse"],
            },
        ],
        "metadata": {
            "pipeline": "anime-hybrid",
            "profile": "fiction_anime_episode",
            "master_sheet_path": str(sheet),
            "master_sheet_locked": True,
            "master_sheet_character": "avery_sterling",
            "scene_a_human_lock": True,
        },
    }
    _write_json(project_dir / "artifacts" / "scene_plan.json", plan)
    _write_json(
        project_dir / "working" / "scene_a" / "SCENE_STATE.json",
        {
            "schema_version": "content-studio-scene-state/v1",
            "project_id": job_id,
            "scene_id": "scene_a",
            "status": "CORPUS",
            "human_lock": True,
            "ship": False,
            "director_review_eligible": False,
            "do_not_polish_a4": True,
            "master": None,
            "cut_ids": ["A1", "A5"],
        },
    )
    _write_json(
        project_dir / "JOB_SKELETON.json",
        {
            "schema_version": "content-studio-vid3-job-skeleton/v1",
            "project_id": job_id,
            "status": "HARNESS_BUILD",
            "render_allowed": False,
            "waiting_on": ["Scene A is corpus. Do not polish A4."],
        },
    )
    _write_json(
        project_dir / "working" / "scene_a" / "see" / "temporal_motion_report.json",
        {"version": "temporal-motion-report/v0.1", "motion_coverage": 0.1},
    )
    return root, job_id, project_dir


def test_open_job_reads_artifacts_not_stale_checkpoint(tmp_path, monkeypatch):
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    job = open_job(job_id)
    world = job["production_world"]
    ids = [row["id"] for row in world["shot_contracts"]]
    assert ids == ["A1", "A5", "WALK", "BAD", "c001"]
    assert world["scene_state"]["status"] == "CORPUS"
    assert world["identity"]["exists"] is True
    assert world["next_step"]["action"] == "propose_next_scene"
    assert "CONTINUE_SCENE" in world["next_step"]["summary"]
    assert "polish A4" in world["next_step"]["summary"]
    assert job["prime_may_write_project_state"] is False
    assert world["proven_status"] == "PRIME_PRODUCTION_INTERFACE_READY"
    assert world["foreman_proven"] is False
    assert world["observations"]
    assert world["openviking"]["invented"] is False


def test_compile_cut_performance_writes_h3_fl2va_proposal(tmp_path, monkeypatch):
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    before = _sha(project_dir / "artifacts" / "scene_plan.json")
    state_before = (project_dir / "working" / "scene_a" / "SCENE_STATE.json").read_text(encoding="utf-8")
    out = compile_cut(job_id, "WALK", caller="prime")
    assert out["status"] == "PROPOSAL"
    assert out["generate"] is False
    assert out["motion_obligation"] == "PERFORMANCE"
    assert out["renderer"] == "h3"
    assert out["h3_mode"] == "fl2va"
    assert out["written"] is True
    assert _sha(project_dir / "artifacts" / "scene_plan.json") == before
    assert (project_dir / "working" / "scene_a" / "SCENE_STATE.json").read_text(encoding="utf-8") == state_before
    stored = json.loads((project_dir / "working" / "prime_rlm" / "execution_requests" / "WALK.json").read_text(encoding="utf-8"))
    assert stored["generate"] is False
    assert stored["canonical_owner"] == "openmontage"


def test_compile_cut_a5_legacy_i2v_hard_is_fl2va(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    out = compile_cut(job_id, "A5", caller="prime")
    assert out["motion_obligation"] == "PERFORMANCE"
    assert out["h3_mode"] == "fl2va"
    assert out["dispatch_class"] == "I2V_HARD"


def test_compile_cut_local_hud_is_not_h3(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    out = compile_cut(job_id, "A1", caller="prime")
    assert out["motion_obligation"] == "LOCAL"
    assert out["renderer"] == "local_compose"
    assert out["h3_default"] is False
    assert out["h3_mode"] is None


def test_compile_cut_rejects_performance_on_local_compose(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="PERFORMANCE cannot be satisfied"):
        compile_cut(job_id, "BAD", caller="prime")
    assert not (_project_dir / "working" / "prime_rlm" / "execution_requests" / "BAD.json").exists()


def test_cursor_cannot_impersonate_prime_compile(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Cursor cannot impersonate"):
        compile_cut(job_id, "A5", caller="cursor")


def test_omitted_shot_cannot_compile(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="omitted"):
        compile_cut(job_id, "c001", caller="prime")


def test_scene_proposal_cannot_include_shots_before_continue(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="CONTINUE_SCENE"):
        submit_scene_proposal(
            job_id,
            {
                "scene_id": "scene_b",
                "audience_state_change": "viewer meets the other man",
                "visual_intent": "a figure at the far end of the kitchen",
                "duration_target": "25s",
                "shots": [{"id": "B1", "visual_intent": "don't list this yet"}],
            },
            caller="prime",
        )


def test_prime_cannot_forge_continue(tmp_path, monkeypatch):
    _root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Alan/Pi only"):
        record_human_preference(job_id, "CONTINUE_SCENE", caller="prime")


def test_continue_then_shot_split_then_compile(tmp_path, monkeypatch):
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    first = submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_b",
            "audience_state_change": "viewer asks whether Avery can go through with this",
            "visual_intent": "another presence enters the kitchen",
            "duration_target": "25s",
        },
        caller="prime",
    )
    assert first["generate"] is False
    assert first["shots"] == []
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_preference"
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_b")
    second = submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_b",
            "audience_state_change": "viewer asks whether Avery can go through with this",
            "visual_intent": "another presence enters the kitchen",
            "duration_target": "25s",
            "shots": [
                {
                    "id": "B1",
                    "visual_intent": "Avery walks two steps then stops",
                    "performance_intent": "Avery walks two steps then stops",
                    "motion_obligation": "PERFORMANCE",
                    "character_ids": ["avery_sterling"],
                }
            ],
        },
        caller="prime",
    )
    assert second["shots"][0]["id"] == "B1"
    out = compile_cut(job_id, "B1", caller="prime")
    assert out["motion_obligation"] == "PERFORMANCE"
    assert out["h3_mode"] == "fl2va"
    assert out["generate"] is False
    assert (project_dir / "working" / "prime_rlm" / "execution_requests" / "B1.json").is_file()


def test_tui_open_job_command(tmp_path, monkeypatch):
    root, job_id, _project_dir = _studio_job(tmp_path, monkeypatch)
    script = Path(__file__).resolve().parents[2] / "tools" / "run_prime_production_tui.py"
    env = os.environ.copy()
    env["OM_PRIME_ADAPTER_ROOT"] = str(root)
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(ADAPTER_SRC),
            str(Path(__file__).resolve().parents[2]),
            env.get("PYTHONPATH", ""),
        ]
    )
    proc = subprocess.run(
        [sys.executable, str(script), "--project-id", job_id, "--command", "open_job"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["job_id"] == job_id
    assert payload["next_step"]["action"] == "propose_next_scene"
    assert "A5" in payload["shot_ids"]


def test_foreman_launcher_uses_rpc_not_print_dash_p():
    import importlib.util

    script = Path(__file__).resolve().parents[2] / "tools" / "run_prime_foreman_session.py"
    spec = importlib.util.spec_from_file_location("prime_foreman_session", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cmd = mod.build_rpc_command(
        "vid3-blacklisted-chef-90s-v1",
        resume=None,
        chain=("bailian/qwen3.8-max", "minimax/MiniMax-M3"),
    )
    assert "--mode" in cmd and "rpc" in cmd
    assert "-p" not in cmd
    assert "--no-session" not in cmd
    assert "--no-tools" not in cmd
    assert "--models" in cmd


def test_tui_prefer_a_without_identity_is_refused():
    import importlib.util

    script = Path(__file__).resolve().parents[2] / "tools" / "run_prime_production_tui.py"
    spec = importlib.util.spec_from_file_location("prime_production_tui", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(mod.AdapterError, match="prefer A identity"):
        mod.resolve_prefer_args(["prefer", "A"])
    label, target = mod.resolve_prefer_args(["prefer", "A", "identity"])
    assert label == "A"
    assert target == "identity:lucien_mercer"


def _prepare_b2(tmp_path, monkeypatch, *, start_still: bool) -> tuple[str, Path]:
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_b",
            "audience_state_change": "viewer asks whether Avery can go through with this",
            "visual_intent": "Lucien walks the kitchen",
            "duration_target": "25s",
        },
        caller="prime",
    )
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_b")
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_b",
            "audience_state_change": "viewer asks whether Avery can go through with this",
            "visual_intent": "Lucien walks the kitchen",
            "duration_target": "25s",
            "shots": [
                {
                    "id": "B1",
                    "visual_intent": "Lucien resolves at the far end and holds",
                    "intentional_hold": True,
                    "motion_obligation": "NONE",
                    "animation_class": "LIMITED",
                    "character_ids": ["lucien_mercer"],
                    "start_seconds": 0.0,
                    "end_seconds": 4.0,
                    "review_decision": "candidate",
                },
                {
                    "id": "B2",
                    "visual_intent": "Lucien Mercer walks the length of the kitchen toward Avery",
                    "performance_intent": "unhurried approach, full-body locomotion",
                    "motion_obligation": "PERFORMANCE",
                    "animation_class": "I2V_HARD",
                    "character_ids": ["lucien_mercer"],
                    "start_seconds": 4.0,
                    "end_seconds": 12.0,
                    "review_decision": "candidate",
                },
            ],
        },
        caller="prime",
    )
    compile_cut(job_id, "B2", caller="prime")
    if start_still:
        still = project_dir / "working" / "prime_rlm" / "start_frames" / "B2.png"
        _write_readable_mcu_png(still)
    return job_id, project_dir


def _lock_lucien(project_dir: Path) -> None:
    sheet = project_dir / "bible" / "lucien" / "master_sheet.png"
    sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.write_bytes(b"lucien-identity-plate")
    _write_json(
        project_dir / "working" / "identity" / "LUCIEN_LOCK.json",
        {
            "schema_version": "om-character-identity-lock/v1",
            "character_id": "lucien_mercer",
            "locked": True,
            "locked_by": "human",
            "candidate": "A",
            "path": "bible/lucien/master_sheet.png",
        },
    )


def _fake_image(calls: list):
    from tools.base_tool import ToolResult

    def invoke(inputs):
        calls.append(inputs)
        out = Path(inputs["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"img")
        return ToolResult(success=True, data={"provider": "comfyui"}, artifacts=[str(out)])

    return invoke


def _fake_h3(calls: list):
    from tools.base_tool import ToolResult

    def invoke(inputs):
        calls.append(inputs)
        out = Path(inputs["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-h3-mp4")
        return ToolResult(
            success=True,
            data={"provider": "comfyui", "model": "minimax-h3", "seed": 7},
            artifacts=[str(out)],
            cost_usd=0.0,
            duration_seconds=11.0,
            seed=7,
            model="minimax-h3",
        )

    return invoke


def _fake_see(mp4: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(mp4.read_bytes()).hexdigest()
    packet = {
        "source_sha256": digest,
        "duration_seconds": 8.0,
        "machine_checks": {"probe_ok": True},
    }
    temporal = {
        "source_sha256": digest,
        "duration_seconds": 8.0,
        "longest_static_run": 0.4,
        "motion_type": {"segment_1": "FULL_MOTION"},
        "local_character_motion": "present",
        "motion_coverage": 0.82,
    }
    audio = {"first_sound_seconds": 0.2}
    (out_dir / "temporal_motion_report.json").write_text("{}", encoding="utf-8")
    (out_dir / "frame_packet.json").write_text("{}", encoding="utf-8")
    (out_dir / "audio_event_map.json").write_text("{}", encoding="utf-8")
    return {
        "frame_packet": packet,
        "temporal_motion_report": temporal,
        "audio_event_map": audio,
    }


def _fake_see_limited(mp4: Path, out_dir: Path) -> dict:
    payload = _fake_see(mp4, out_dir)
    payload["temporal_motion_report"]["motion_type"] = {
        "segment_1": "LIMITED_LOCAL_MOTION",
        "segment_2": "STATIC_HOLD",
        "segment_3": "CAMERA_ONLY",
    }
    payload["temporal_motion_report"]["longest_static_run"] = 0.9
    return payload


def _fake_see_eye_absent(mp4: Path, out_dir: Path) -> dict:
    payload = _fake_see_limited(mp4, out_dir)
    payload["temporal_motion_report"]["eye_shift"] = "absent"
    return payload


def _fake_see_camera_only(mp4: Path, out_dir: Path) -> dict:
    payload = _fake_see(mp4, out_dir)
    payload["temporal_motion_report"]["motion_type"] = {"segment_1": "CAMERA_ONLY"}
    payload["temporal_motion_report"]["local_character_motion"] = "absent"
    payload["temporal_motion_report"]["longest_static_run"] = 0.0
    return payload


def _fake_see_beats_proven(mp4: Path, out_dir: Path) -> dict:
    payload = _fake_see_limited(mp4, out_dir)
    payload["temporal_motion_report"]["eye_shift"] = "present"
    return payload


def _prepare_showpiece_s2(tmp_path, monkeypatch) -> tuple[str, Path]:
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_showpiece",
            "audience_state_change": "Lucien occupies the kitchen in MCU",
            "visual_intent": "MCU breath, not an 8s walk",
            "duration_target": "26s",
        },
        caller="prime",
    )
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_showpiece")
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_showpiece",
            "audience_state_change": "Lucien occupies the kitchen in MCU",
            "visual_intent": "MCU breath, not an 8s walk",
            "duration_target": "26s",
            "shots": [
                {
                    "id": "S2",
                    "visual_intent": "MCU Lucien. Face, collar, eyes, breath.",
                    "performance_intent": "eyes shift, one restrained breath, hold. No locomotion.",
                    "motion_obligation": "PERFORMANCE",
                    "animation_class": "I2V_HARD",
                    "character_ids": ["lucien_mercer"],
                    "framing": "medium_close",
                    "reference_atoms": ["freeze_notice", "breath_tension", "eye_shift_hold"],
                    "start_seconds": 4.0,
                    "end_seconds": 10.0,
                    "review_decision": "candidate",
                }
            ],
        },
        caller="prime",
    )
    compile_cut(job_id, "S2", caller="prime")
    _lock_lucien(project_dir)
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S2.png")
    return job_id, project_dir


def _prepare_foreman_s1(tmp_path, monkeypatch) -> tuple[str, Path]:
    _root, job_id, project_dir = _studio_job(tmp_path, monkeypatch)
    _write_json(
        project_dir / "JOB_SKELETON.json",
        {
            "status": "PRIME_FOREMAN_PROOF",
            "proof_unit": "S1",
            "foreman_proven": False,
            "frozen": False,
        },
    )
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_foreman",
            "audience_state_change": "Lucien occupies the kitchen with a readable head/hand beat",
            "visual_intent": "MCU freeze, head turn, stop. No eye contract.",
            "duration_target": "8s",
        },
        caller="prime",
    )
    record_human_preference(job_id, "CONTINUE_SCENE", caller="human", target="scene_foreman")
    submit_scene_proposal(
        job_id,
        {
            "scene_id": "scene_foreman",
            "audience_state_change": "Lucien occupies the kitchen with a readable head/hand beat",
            "visual_intent": "MCU freeze, head turn, stop. No eye contract.",
            "duration_target": "8s",
            "shots": [
                {
                    "id": "S1",
                    "visual_intent": "MCU Lucien. Face, collar, hands in frame.",
                    "performance_intent": "freeze, raise or turn the head, clench a hand, stop. No locomotion.",
                    "motion_obligation": "PERFORMANCE",
                    "animation_class": "I2V_HARD",
                    "character_ids": ["lucien_mercer"],
                    "framing": "medium_close",
                    "reference_atoms": ["freeze_notice", "weight_shift"],
                    "start_seconds": 0.0,
                    "end_seconds": 8.0,
                    "review_decision": "candidate",
                }
            ],
        },
        caller="prime",
    )
    compile_cut(job_id, "S1", caller="prime")
    _lock_lucien(project_dir)
    _write_readable_mcu_png(project_dir / "working" / "prime_rlm" / "start_frames" / "S1.png")
    return job_id, project_dir


def test_next_step_after_b2_compile_is_dispatch(tmp_path, monkeypatch):
    job_id, _project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "dispatch_cut"
    assert world["next_step"]["shot_id"] == "B2"


def test_dispatch_cut_b2_writes_rollout_and_observation(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=True)
    _lock_lucien(project_dir)
    state_before = (project_dir / "working" / "scene_a" / "SCENE_STATE.json").read_text(encoding="utf-8")
    proposal_before = json.loads(
        (project_dir / "working" / "prime_rlm" / "execution_requests" / "B2.json").read_text(encoding="utf-8")
    )
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    out = dispatch_cut(job_id, "B2", caller="prime")
    assert out["status"] == "succeeded"
    assert out["mode"] == "fl2va"
    assert out["provider"] == "comfyui"
    assert out["model"] == "minimax-h3"
    assert out["execution_request_hash"]
    assert out["input_hashes"]["first_frame"]
    assert out["output_hash"]
    assert out["observation"]["character_motion_present"] is True
    assert out["observation"]["source_hash_matches"] is True
    assert "approach" in out["observation"]["performance_question"].lower()
    assert calls and calls[0]["workflow_model"] == "minimax-h3"
    stored = json.loads(
        (project_dir / "working" / "prime_rlm" / "execution_requests" / "B2.json").read_text(encoding="utf-8")
    )
    assert stored["generate"] is False
    assert stored["status"] == "PROPOSAL"
    assert stored == proposal_before
    assert (project_dir / "working" / "scene_a" / "SCENE_STATE.json").read_text(encoding="utf-8") == state_before
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "return_to_harness"
    assert world["proven_status"] == "PRIME_PRODUCTION_DISPATCH_PROVEN"
    assert (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    assert [row["atom_id"] for row in calls[0]["h3_ir"]["shots"]] == [
        "freeze_notice",
        "weight_shift",
        "controlled_approach",
        "decelerate_stop",
    ]
    assert calls[0]["h3_ir"]["locomotion"] is True
    with pytest.raises(AdapterError, match="frozen"):
        dispatch_cut(job_id, "B2", caller="prime")


def test_see_crash_after_mp4_still_writes_receipt(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=True)
    _lock_lucien(project_dir)
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))

    def boom(mp4, out_dir):
        raise ModuleNotFoundError("No module named 'PIL'")

    monkeypatch.setattr("lib.dispatch_cut._see_mp4", boom)
    out = dispatch_cut(job_id, "B2", caller="prime")
    assert out["status"] == "failed"
    assert out["output_hash"]
    assert "observation_failed" in (out["error"] or "")
    assert (project_dir / "working" / "prime_rlm" / "rollouts" / out["rollout_id"] / "RECEIPT.json").is_file()
    world = open_job(job_id)["production_world"]
    assert world["proven_status"] != "PRIME_PRODUCTION_DISPATCH_PROVEN"


def test_dispatch_cut_blocks_on_lucien_identity_before_h3(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=True)
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    out = dispatch_cut(job_id, "B2", caller="prime")
    assert out["status"] == "blocked"
    assert out["error"] == "character_identity_lock_missing"
    assert calls == []
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "resolve_prerequisite"
    assert world["next_step"]["prerequisite"]["root"] == "lucien_identity_lock"


def test_dispatch_cut_missing_start_still_after_identity_lock(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    _lock_lucien(project_dir)
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    out = dispatch_cut(job_id, "B2", caller="prime")
    assert out["status"] == "blocked"
    assert out["error"] == "canonical_start_ref_missing"
    assert calls == []
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "produce_keyframe"
    assert world["next_step"]["shot_id"] == "B1"


def test_dispatch_cut_blocks_silhouette_start_before_h3(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    _lock_lucien(project_dir)
    still = project_dir / "working" / "prime_rlm" / "start_frames" / "B2.png"
    _write_silhouette_png(still)
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    out = dispatch_cut(job_id, "B2", caller="prime")
    assert out["status"] == "blocked"
    assert out["error"] == "keyframe_presentation_unusable"
    assert "body_silhouette_only" in (out.get("presentation_blockers") or [])
    assert calls == []
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "repair_keyframe_presentation"


def test_dispatch_cut_rejects_generate_true_and_cursor(tmp_path, monkeypatch):
    job_id, _project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=True)
    with pytest.raises(AdapterError, match="cannot flip generate"):
        dispatch_cut(job_id, "B2", caller="prime", generate=True)
    with pytest.raises(AdapterError, match="Cursor cannot impersonate"):
        dispatch_cut(job_id, "B2", caller="cursor")
    with pytest.raises(AdapterError, match="execution proposal missing|only PERFORMANCE"):
        dispatch_cut(job_id, "B1", caller="prime")


def test_dispatch_cut_rejects_stale_proposal_hash(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=True)
    path = project_dir / "working" / "prime_rlm" / "scene_proposals" / "scene_b.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["visual_intent"] = "changed after compile"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(AdapterError, match="stale execution proposal"):
        dispatch_cut(job_id, "B2", caller="prime")


def test_prerequisite_identity_then_b1_keyframe_binds_b2(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    avery_before = (project_dir / "bible" / "avery" / "master_sheet.png").read_bytes()
    dispatch_cut(job_id, "B2", caller="prime")
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "resolve_prerequisite"
    plan = submit_prerequisite_plan(job_id, caller="prime")
    assert plan["root"] == "lucien_identity_lock"
    assert "retry_h3" in plan["do_not"]
    continue_pref = json.loads(
        (project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json").read_text(encoding="utf-8")
    )
    assert continue_pref["label"] == "CONTINUE_SCENE"
    calls: list = []
    monkeypatch.setattr("lib.prerequisite._invoke_image", _fake_image(calls))
    cands = propose_identity_candidates(job_id, caller="prime")
    assert {row["id"] for row in cands["candidates"]} == {"A", "B"}
    assert all(row["status"] == "candidate" for row in cands["candidates"])
    with pytest.raises(AdapterError, match="Alan/Pi only"):
        record_human_preference(job_id, "A", caller="prime", target="identity:lucien_mercer")
    locked = record_human_preference(job_id, "A", caller="human", target="identity:lucien_mercer")
    assert locked["locked"] is True
    assert (project_dir / "bible" / "lucien" / "master_sheet.png").is_file()
    assert (project_dir / "bible" / "avery" / "master_sheet.png").read_bytes() == avery_before
    scene_pref = json.loads(
        (project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json").read_text(encoding="utf-8")
    )
    assert scene_pref["label"] == "CONTINUE_SCENE"
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "produce_keyframe"
    key = produce_keyframe(job_id, "B1", caller="prime")
    assert key["h3"] is False
    assert key["bound_to"] == "B2"
    scene_b = json.loads(
        (project_dir / "working" / "prime_rlm" / "scene_proposals" / "scene_b.json").read_text(encoding="utf-8")
    )
    b2 = next(row for row in scene_b["shots"] if row["id"] == "B2")
    assert "keyframes/B1.png" in b2["start_frame_ref"].replace("\\", "/")
    assert b2["start_state"] == "B1.final"
    assert not (project_dir / "working" / "prime_rlm" / "start_frames" / "B2.png").exists()
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_redispatch"


def test_cannot_lock_identity_without_candidates(tmp_path, monkeypatch):
    job_id, _project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    with pytest.raises(AdapterError, match="propose_identity_candidates first"):
        record_human_preference(job_id, "A", caller="human", target="identity:lucien_mercer")


def test_neither_does_not_lock_lucien(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_b2(tmp_path, monkeypatch, start_still=False)
    dispatch_cut(job_id, "B2", caller="prime")
    submit_prerequisite_plan(job_id, caller="prime")
    monkeypatch.setattr("lib.prerequisite._invoke_image", _fake_image([]))
    propose_identity_candidates(job_id, caller="prime")
    out = record_human_preference(job_id, "NEITHER", caller="human", target="identity:lucien_mercer")
    assert out["locked"] is False
    assert not (project_dir / "bible" / "lucien" / "master_sheet.png").is_file()
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "propose_identity_candidates"


def test_identity_stills_prefer_volcengine_not_flux2(monkeypatch, tmp_path):
    from tools.base_tool import ToolResult, ToolStatus

    from lib.prerequisite import _invoke_image

    called: list[str] = []

    class FakeSeedream:
        name = "doubao_seedream"

        def get_status(self):
            return ToolStatus.AVAILABLE

        def execute(self, inputs):
            called.append(self.name)
            path = Path(inputs["output_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"seedream-plate")
            return ToolResult(success=True, artifacts=[str(path)])

    class Boom:
        name = "must-not-run"

        def get_status(self):
            return ToolStatus.AVAILABLE

        def execute(self, inputs):
            raise AssertionError("Flux2/ComfyUI must not run when Seedream is available")

    monkeypatch.setenv("ARK_AGENTPLAN_API_KEY", "test-only")
    monkeypatch.delenv("BAILIAN_TOKENPLAN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setattr("tools.graphics.doubao_seedream.DoubaoSeedream", FakeSeedream)
    monkeypatch.setattr("tools.graphics.dashscope_image.DashscopeImage", Boom)
    monkeypatch.setattr("tools.graphics.comfyui_image.ComfyUIImage", Boom)
    dest = tmp_path / "A.png"
    result = _invoke_image({"prompt": "Lucien plate", "output_path": str(dest), "width": 1024, "height": 1024})
    assert result.success is True
    assert called == ["doubao_seedream"]
    assert dest.read_bytes() == b"seedream-plate"


def test_showpiece_s2_dispatch_does_not_freeze_the_job(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "dispatch_cut"
    assert world["next_step"]["shot_id"] == "S2"
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    out = dispatch_cut(job_id, "S2", caller="prime")
    assert out["status"] == "succeeded"
    assert out.get("frozen") is not True
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    assert [row["atom_id"] for row in calls[0]["h3_ir"]["shots"]] == [
        "freeze_notice",
        "breath_tension",
        "eye_shift_hold",
    ]
    assert calls[0]["h3_ir"]["locomotion"] is False
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "temporal_beat_realization_unresolved"
    assert world["next_step"]["first_take_acceptable"] is False
    assert world["next_step"]["content_fail"] is False
    assert "eye_shift_hold" in world["next_step"]["unresolved_beats"]
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    assert world["foreman_proven"] is False
    assert world["studio_v1"] is False
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "temporal_beat_realization_unresolved"


def test_showpiece_missing_observation_does_not_invent_first_take(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    rollout_id = "s2-orphanobs01"
    out = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    out.mkdir(parents=True)
    (out / "S2.mp4").write_bytes(b"fake-s2-mp4")
    digest = hashlib.sha256(b"fake-s2-mp4").hexdigest()
    _write_json(
        out / "RECEIPT.json",
        {
            "rollout_id": rollout_id,
            "shot_id": "S2",
            "status": "failed",
            "output_hash": digest,
            "error": "observation_failed: frame extract produced empty file at t=6.542",
        },
    )
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "observation_incomplete"
    assert world["next_step"]["bind_tool"] == "complete_observation"
    assert world["next_step"]["first_take_acceptable"] is False
    assert world["next_step"]["content_fail"] is False
    assert world["next_step"]["quality_verdict"] is None
    assert world["next_step"]["rollout_id"] == rollout_id
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see)
    bound = complete_observation(job_id, rollout_id, caller="prime")
    assert bound["status"] == "succeeded"
    assert bound.get("frozen") is not True
    quality = json.loads((out / "OBSERVATION.json").read_text(encoding="utf-8"))["quality"]
    assert "passed" in quality
    assert "performance_not_full_motion" not in (quality.get("blockers") or [])
    world = open_job(job_id)["production_world"]
    if quality.get("beat_realization_unresolved"):
        assert world["next_step"]["action"] == "temporal_beat_realization_unresolved"
        assert world["next_step"]["first_take_acceptable"] is False
        assert world["next_step"]["content_fail"] is False
    elif quality.get("passed") is True:
        assert world["next_step"]["action"] == "first_take_acceptable"
    else:
        assert world["next_step"]["action"] == "propose_bounded_repair"


def test_showpiece_does_not_rerender_when_observation_incomplete(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    rollout_id = "s2-10869730e0b7"
    out = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    out.mkdir(parents=True)
    (out / "S2.mp4").write_bytes(b"locked-s2-mp4")
    _write_json(
        out / "RECEIPT.json",
        {
            "rollout_id": rollout_id,
            "shot_id": "S2",
            "status": "failed",
            "output_hash": "9373e305cefd2ab398bbb22d53e2f4b196560ae99894794197c70a926cf54628",
            "error": "observation_failed: schema invalid",
        },
    )
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    with pytest.raises(AdapterError, match="rollout_already_landed"):
        dispatch_cut(job_id, "S2", caller="prime")
    assert calls == []


def test_showpiece_real_blocker_asks_repair_not_invented_ab(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    calls: list = []
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3(calls))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_eye_absent)
    out = dispatch_cut(job_id, "S2", caller="prime")
    assert out["status"] == "succeeded"
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "propose_bounded_repair"
    assert world["next_step"]["blockers"] == ["eye_shift_not_realized"]
    assert world["foreman_proven"] is False


def test_showpiece_limited_local_without_eye_probe_is_unresolved_not_repair(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_limited)
    out = dispatch_cut(job_id, "S2", caller="prime")
    assert out["status"] == "succeeded"
    quality = out["observation"]["quality"]
    assert "performance_not_full_motion" not in quality["blockers"]
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "temporal_beat_realization_unresolved"
    assert not (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").is_file()


def test_showpiece_beats_proven_first_take_does_not_stamp_foreman(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_beats_proven)
    out = dispatch_cut(job_id, "S2", caller="prime")
    assert out["status"] == "succeeded"
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "first_take_acceptable"
    freeze = json.loads(
        (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["reason"] == "first_take_acceptable"
    assert freeze["foreman_proven"] is False
    assert freeze["proven_status"] != "PRIME_FOREMAN_PROVEN"


def test_showpiece_alan_b_stamps_foreman_not_studio_v1(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_eye_absent)
    parent = dispatch_cut(job_id, "S2", caller="prime")
    assert parent["status"] == "succeeded"
    propose_bounded_repair(job_id, parent["rollout_id"], caller="prime")
    monkeypatch.setattr("lib.bounded_repair._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.bounded_repair._see_mp4", _fake_see)
    child = dispatch_bounded_repair(job_id, parent["rollout_id"], caller="prime")
    assert child["status"] == "succeeded"
    pair = json.loads((project_dir / "working" / "prime_rlm" / "AB_PAIR.json").read_text(encoding="utf-8"))
    assert pair["A"]["rollout_id"] == parent["rollout_id"]
    assert pair["B"]["rollout_id"] == child["rollout_id"]
    assert pair["B"]["repair_dimension"]
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "wait_human_preference"
    assert world["next_step"]["A"]["rollout_id"] == parent["rollout_id"]
    assert world["next_step"]["B"]["rollout_id"] == child["rollout_id"]
    recorded = record_human_preference(job_id, "B", caller="human", target=pair["target"])
    assert recorded["foreman_proven"] is True
    assert recorded["studio_v1"] is False
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "return_to_content_production"
    assert world["foreman_proven"] is True
    assert world["studio_v1"] is False
    assert world["proven_status"] == "PRIME_FOREMAN_PROVEN"
    freeze = json.loads(
        (project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["reason"] == "prime_foreman_proven"
    assert "S3" in freeze["do_not"]
    assert "AI_NATIVE_LIMITED_ANIME_STUDIO_V1" in freeze["do_not"]


def test_showpiece_unresolved_pause_is_not_first_take_or_b2_harness_return(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_showpiece_s2(tmp_path, monkeypatch)
    _write_json(
        project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json",
        {
            "schema_version": "om-job-freeze/v1",
            "frozen": True,
            "reason": "temporal_beat_realization_unresolved",
            "proven_status": "PRIME_FOREMAN_PROOF",
            "foreman_proven": False,
            "studio_v1": False,
            "repair_quota_used": False,
        },
    )
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "temporal_beat_realization_unresolved"
    assert world["next_step"]["first_take_acceptable"] is False
    assert world["next_step"]["content_fail"] is False
    assert world["next_step"]["repair_quota_used"] is False
    assert world["foreman_proven"] is False
    assert world["next_step"]["action"] != "first_take_acceptable"
    assert world["next_step"]["action"] != "return_to_harness"


def test_foreman_measurable_take_first_take_without_eye_probe(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_foreman_s1(tmp_path, monkeypatch)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_limited)
    out = dispatch_cut(job_id, "S1", caller="prime")
    assert out["status"] == "succeeded"
    quality = out["observation"]["quality"]
    assert "eye_shift_hold" not in quality["checks"]
    assert "performance_not_full_motion" not in quality["blockers"]
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "first_take_acceptable"
    assert world["foreman_proven"] is False


def test_foreman_camera_only_asks_repair_not_eye_fail(tmp_path, monkeypatch):
    job_id, project_dir = _prepare_foreman_s1(tmp_path, monkeypatch)
    monkeypatch.setattr("lib.dispatch_cut._invoke_h3", _fake_h3([]))
    monkeypatch.setattr("lib.dispatch_cut._see_mp4", _fake_see_camera_only)
    out = dispatch_cut(job_id, "S1", caller="prime")
    assert out["status"] == "succeeded"
    world = open_job(job_id)["production_world"]
    assert world["next_step"]["action"] == "propose_bounded_repair"
    blockers = world["next_step"]["blockers"]
    assert "weight_shift_not_realized" in blockers or "character_did_not_move" in blockers
    assert "eye_shift_not_realized" not in blockers
    assert world["foreman_proven"] is False


