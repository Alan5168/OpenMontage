from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_STUDIO = Path(__file__).resolve().parents[2] / "tools" / "studio.py"
_SPEC = importlib.util.spec_from_file_location("studio_launcher", _STUDIO)
studio = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(studio)


def _cfg(tmp_path: Path, monkeypatch) -> dict:
    root = tmp_path / "studio"
    repo = tmp_path / "om"
    jobs = root / "jobs"
    (repo / "lib").mkdir(parents=True)
    (repo / "integrations" / "prime-om-adapter" / "src").mkdir(parents=True)
    (repo / "tools").mkdir(parents=True)
    (jobs / "vid-demo").mkdir(parents=True)
    (jobs / "vid-demo" / "project.json").write_text("{}", encoding="utf-8")
    (jobs / "vid-demo" / "JOB_SKELETON.json").write_text(
        json.dumps({"status": "LIGHTS_OUT_SCENE_PROOF", "scene_id": "scene_lights_out"}),
        encoding="utf-8",
    )
    cfg_path = root / "studio.json"
    cfg_path.write_text(
        json.dumps(
            {
                "studio_root": str(root),
                "om_repo": str(repo),
                "jobs_dir": str(jobs),
                "current_job": "vid-demo",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONTENT_STUDIO_CONFIG", str(cfg_path))
    monkeypatch.chdir(root)
    cfg = studio.load_config()
    studio.apply_env(cfg)
    return cfg


def test_apply_env_hides_pythonpath(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTHONPATH", raising=False)
    cfg = _cfg(tmp_path, monkeypatch)
    env = studio.apply_env(cfg)
    assert "prime-om-adapter" in env["PYTHONPATH"]
    assert env["OM_PRIME_ADAPTER_ROOT"] == cfg["studio_root"]
    assert env["OPENMONTAGE_PROJECTS_DIR"] == cfg["jobs_dir"]


def test_run_argv_is_state_driven_lights_out(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    argv = studio._run_argv(cfg, "vid-demo", [])
    assert "--project-id" in argv
    assert "vid-demo" in argv
    assert "--lights-out" in argv
    assert "run_prime_foreman_session.py" in argv[1].replace("\\", "/")


def test_continue_refuses_when_not_waiting(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)

    def fake_open(job_id):
        return {"next_step": {"action": "dispatch_cut", "shot_id": "S2"}}

    monkeypatch.setattr(studio, "_open", fake_open)
    with pytest.raises(SystemExit, match="No human gate"):
        studio.cmd_prefer(cfg, "vid-demo", "CONTINUE_SCENE")


def test_scene_review_gate_kind():
    step = {
        "action": "wait_human_preference",
        "summary": "Composed scene is on the review queue. KEEP_WATCHING / SHIP.",
        "scene_id": "scene_lights_out",
    }
    assert studio._gate_kind(step) == "scene_review"


def test_run_refuses_second_prime_session(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "prime_running", lambda job_id: True)
    with pytest.raises(SystemExit, match="already running"):
        studio.cmd_run(cfg, "vid-demo", [], ask=False)
