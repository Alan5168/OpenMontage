from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from lib.checkpoint import init_project, write_checkpoint
from tools.content_studio_gateway import (
    GatewayError,
    apply_sceneplan_decisions,
    prepare_prime_resume,
    record_prime_resume,
    resolve_project,
    show_gate_payload,
    status_payload,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scene_plan(decision: str = "pending") -> dict:
    return {
        "version": "1.0",
        "style_playbook": "premium-minimalist",
        "scenes": [
            {
                "id": "c01",
                "type": "animation",
                "description": "A gate closes in front of a result card.",
                "visual_intent": "让观众一眼看懂结果不等于放行。",
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "script_section_id": "s01",
                "dialogue": "结果不是放行。",
                "sound_intent": {"se": ["gate click"], "bgm_mood": "restrained"},
                "t2i_prompt": "textless editorial gate and result card",
                "visual_ref": {"kind": "api_image", "path": "review/c01.png"},
                "review_decision": decision,
            },
            {
                "id": "c02",
                "type": "diagram",
                "description": "The same gate shows an empty evidence socket.",
                "visual_intent": "延续机位，突出证据槽为空。",
                "start_seconds": 3.0,
                "end_seconds": 7.0,
                "script_section_id": "s02",
                "dialogue": "缺证据就不开门。",
                "sound_intent": {"se": ["muted denial"], "bgm_mood": "restrained"},
                "reuse": {"source_cut_id": "c01", "kind": "same_layout"},
                "review_decision": decision,
            },
        ],
    }


def _fixture_projects(tmp_path: Path) -> tuple[Path, Path]:
    projects = tmp_path / "jobs"
    project_id = "fixture-sceneplan-gate"
    project_dir = projects / project_id
    init_project(
        project_id,
        title="Fixture",
        pipeline_type="unknown",
        pipeline_dir=projects,
        style_playbook="premium-minimalist",
    )
    plan = _scene_plan()
    (project_dir / "artifacts").mkdir(exist_ok=True)
    (project_dir / "artifacts" / "scene_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_checkpoint(
        projects,
        project_id,
        "scene_plan",
        "awaiting_human",
        {"scene_plan": plan},
        pipeline_type="unknown",
        style_playbook="premium-minimalist",
        human_approval_required=True,
        human_approved=False,
    )
    return projects, project_dir


def test_current_project_is_derived_from_awaiting_human_state(tmp_path: Path):
    projects, project_dir = _fixture_projects(tmp_path)
    other = projects / "older"
    other.mkdir()
    (other / "project.json").write_text(
        json.dumps({"project_id": "older", "title": "Older"}), encoding="utf-8"
    )
    selected = resolve_project(projects)
    assert selected["project_dir"] == project_dir
    assert selected["awaiting_human"] is True


def test_show_gate_separates_result_intent_and_prompt(tmp_path: Path):
    projects, _project_dir = _fixture_projects(tmp_path)
    gate = show_gate_payload(projects)
    assert gate["columns"] == [
        "scene_number",
        "cut_id",
        "image_result",
        "visual_intent",
        "prompt",
        "dialogue",
        "duration",
        "sound",
    ]
    assert gate["cut_count"] == 2
    assert gate["cuts"][0]["visual_intent"] == "让观众一眼看懂结果不等于放行。"
    assert gate["cuts"][0]["prompt"] == "textless editorial gate and result card"
    assert gate["cuts"][1]["prompt_source_cut_id"] == "c01"


def test_stale_hash_and_invalid_cut_fail_closed(tmp_path: Path):
    projects, _project_dir = _fixture_projects(tmp_path)
    with pytest.raises(GatewayError, match="Stale"):
        apply_sceneplan_decisions(
            projects,
            None,
            "0" * 64,
            [{"cut_id": "c01", "decision": "keep"}],
        )
    gate = show_gate_payload(projects)
    with pytest.raises(GatewayError, match="Unknown cut_id"):
        apply_sceneplan_decisions(
            projects,
            None,
            gate["checkpoint"]["sha256"],
            [{"cut_id": "c99", "decision": "keep"}],
        )


def test_partial_change_stays_at_gate_and_invalidates_result(tmp_path: Path):
    projects, project_dir = _fixture_projects(tmp_path)
    gate = show_gate_payload(projects)
    result = apply_sceneplan_decisions(
        projects,
        None,
        gate["checkpoint"]["sha256"],
        [
            {
                "cut_id": "c01",
                "decision": "change",
                "visual_intent": "让卡片先碎裂，再显示门禁。",
                "prompt": "textless shattered result card before a red gate",
                "note": "先碎后挡，冲突更清楚。",
            }
        ],
    )
    assert result["status"] == "AWAITING_BOUNDED_CHANGES"
    checkpoint = json.loads((project_dir / "checkpoint_scene_plan.json").read_text())
    assert checkpoint["status"] == "awaiting_human"
    changed = checkpoint["artifacts"]["scene_plan"]["scenes"][0]
    assert "visual_ref" not in changed
    assert "needs_layout_regeneration" in changed["flags"]
    assert list((project_dir / "history").glob("artifact_scene_plan_*.json"))


def test_full_approval_archives_old_hash_and_survives_reload(tmp_path: Path):
    projects, project_dir = _fixture_projects(tmp_path)
    gate = show_gate_payload(projects)
    result = apply_sceneplan_decisions(
        projects,
        None,
        gate["checkpoint"]["sha256"],
        [
            {"cut_id": "c01", "decision": "keep", "note": "保留。"},
            {"cut_id": "c02", "decision": "keep", "note": "复用成立。"},
        ],
    )
    assert result["status"] == "APPROVED"
    assert result["prime_resume_allowed"] is True
    assert result["old_checkpoint_sha256"] != result["new_checkpoint_sha256"]
    checkpoint = json.loads((project_dir / "checkpoint_scene_plan.json").read_text())
    assert checkpoint["status"] == "completed"
    assert checkpoint["human_approved"] is True
    assert checkpoint["metadata"]["pi_entry"]["no_mac_relay"] is True
    reloaded = show_gate_payload(projects)
    assert {cut["decision"] for cut in reloaded["cuts"]} == {"keep"}
    assert list((project_dir / "history").glob("checkpoint_scene_plan_*.json"))


def test_prime_resume_request_and_receipt_are_bound_to_checkpoint(tmp_path: Path, monkeypatch):
    projects, project_dir = _fixture_projects(tmp_path)
    sessions = tmp_path / "prime-sessions"
    sessions.mkdir()
    session_file = sessions / "fixture-director.jsonl"
    session_file.write_text(
        json.dumps({"type": "session_info", "name": "fixture-director"}) + "\n"
        + json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "usage": {"input": 10, "output": 4, "totalTokens": 14, "cost": {"total": 0.0}},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "tools.content_studio_gateway.DEFAULT_PRIME_SESSION_DIR",
        sessions,
    )
    monkeypatch.setattr(
        "tools.content_studio_gateway.DEFAULT_PRIME_AGENT_DIR",
        tmp_path / "prime-agent",
    )
    gate = show_gate_payload(projects)
    apply_sceneplan_decisions(
        projects,
        None,
        gate["checkpoint"]["sha256"],
        [
            {"cut_id": "c01", "decision": "keep"},
            {"cut_id": "c02", "decision": "omit", "note": "信息重复。"},
        ],
    )
    request = prepare_prime_resume(projects, None)
    assert request["schema_version"] == "om-prime-resume-request/v2"
    assert request["session_file"].endswith(".jsonl")
    assert "--no-session" in request["forbidden_flags"]
    response = json.dumps(
        {
            "status": "PRIME_OM_RESUME_ACCEPTED",
            "project_id": request["project_id"],
            "checkpoint_sha256": request["checkpoint_sha256"],
            "next_stage": request["next_stage"],
            "session_file": request["session_file"],
            "resumed": True,
            "fake_json_echo": False,
        }
    )
    receipt = record_prime_resume(projects, None, request["request_id"], response)
    assert receipt["status"] == "PASS"
    assert receipt["schema_version"] == "om-prime-resume-receipt/v2"
    assert receipt["resumed"] is True
    assert receipt["fake_json_echo"] is False
    assert receipt["usage_ledger"]["aggregate_tokens"]["total"] == 14
    assert receipt["provider"] == "bailian"
    assert receipt["model"] == "qwen3.8-max"
    assert receipt["production_started"] is False
    assert status_payload(projects, None)["prime_resume_receipt"]["status"] == "PASS"

    with pytest.raises(GatewayError, match="acknowledgement mismatch"):
        record_prime_resume(
            projects,
            None,
            request["request_id"],
            json.dumps(
                {
                    "status": "PRIME_OM_RESUME_ACCEPTED",
                    "project_id": request["project_id"],
                    "checkpoint_sha256": request["checkpoint_sha256"],
                    "next_stage": request["next_stage"],
                }
            ),
        )


def test_independent_t2i_mothers_cannot_be_approved(tmp_path: Path):
    projects, project_dir = _fixture_projects(tmp_path)
    plan = _scene_plan()
    plan["scenes"][1].pop("reuse")
    plan["scenes"][1]["t2i_prompt"] = "different camera different world"
    (project_dir / "artifacts" / "scene_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_checkpoint(
        projects,
        "fixture-sceneplan-gate",
        "scene_plan",
        "awaiting_human",
        {"scene_plan": plan},
        pipeline_type="unknown",
        style_playbook="premium-minimalist",
        human_approval_required=True,
        human_approved=False,
    )
    gate = show_gate_payload(projects)
    assert gate["visual_continuity"]["status"] == "FAIL"
    with pytest.raises(GatewayError, match="Visual continuity hard gate"):
        apply_sceneplan_decisions(
            projects,
            None,
            gate["checkpoint"]["sha256"],
            [
                {"cut_id": "c01", "decision": "keep"},
                {"cut_id": "c02", "decision": "keep"},
            ],
        )
