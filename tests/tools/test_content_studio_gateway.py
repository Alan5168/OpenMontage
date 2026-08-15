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
    board_payload,
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


def test_board_is_workshop_kanban_not_trae(tmp_path: Path):
    projects, _project_dir = _fixture_projects(tmp_path)
    board = board_payload(projects)
    assert board["workshop_gui"] == "openmontage-backlot"
    assert board["foreman"] == "prime-agent-tui"
    assert board["trae_is_studio_gui"] is False
    assert board["dsh_is_windows_foreman"] is False
    assert board["motion"]["cut_count"] == 2
    assert board["motion"]["class_counts"]["LIMITED"] == 2


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


def test_prime_resume_requires_project_pointer_and_mechanical_evidence(tmp_path: Path, monkeypatch):
    projects, project_dir = _fixture_projects(tmp_path)
    sessions = tmp_path / "prime-sessions"
    sessions.mkdir()
    # Unrelated newest session must NOT be used without a project pointer.
    unrelated = sessions / "unrelated-latest.jsonl"
    unrelated.write_text(json.dumps({"type": "session_info", "name": "unrelated"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("tools.content_studio_gateway.DEFAULT_PRIME_SESSION_DIR", sessions)
    monkeypatch.setattr("tools.content_studio_gateway.DEFAULT_PRIME_AGENT_DIR", tmp_path / "prime-agent")
    monkeypatch.setattr(
        "tools.content_studio_gateway.DEFAULT_PRIME_KERNEL_PYTHON",
        tmp_path / "Prime-kernel-venv" / "Scripts" / "python.exe",
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
    with pytest.raises(GatewayError, match="SESSION_POINTER.json is required"):
        prepare_prime_resume(projects, None)

    bound = sessions / "pilot-bound.jsonl"
    bound.write_text(
        json.dumps({"type": "session_info", "name": "pilot-bound"}) + "\n"
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
    pointer_dir = project_dir / "working" / "prime_rlm"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    (pointer_dir / "SESSION_POINTER.json").write_text(
        json.dumps(
            {
                "project_id": "fixture-sceneplan-gate",
                "session_file": str(bound.resolve()),
                "session_dir": str(sessions),
                "session_id": bound.stem,
                "session_sha256": _sha(bound),
                "agent_dir": str(tmp_path / "prime-agent"),
                "kernel_python": str(tmp_path / "Prime-kernel-venv" / "Scripts" / "python.exe"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    request = prepare_prime_resume(projects, None)
    assert request["session_file"] == str(bound.resolve())
    assert request["session_file"] != str(unrelated.resolve())
    assert request["global_latest_fallback"] is False
    assert request["kernel_python"].endswith("python.exe")

    with pytest.raises(GatewayError, match="Mechanical JSONL evidence"):
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
                    "session_file": request["session_file"],
                    "resumed": True,
                    "fake_json_echo": False,
                    "nonce": "nonce-fixture-001",
                }
            ),
        )

    # Append mechanical toolCall + clean toolResult JSON to the bound session.
    nonce = "nonce-fixture-001"
    job = request["project_id"]
    start_line = len(bound.read_text(encoding="utf-8").splitlines())
    with bound.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "toolCall", "name": "ipython", "arguments": {"code": "print(1)"}}
                        ],
                    },
                }
            )
            + "\n"
        )
        handle.write(
            json.dumps(
                {
                    "type": "message",
                    "message": {
                        "role": "toolResult",
                        "toolCallId": "call_1",
                        "toolName": "ipython",
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "nonce": nonce,
                                        "job_id": job,
                                        "variable_names": ["om_job_ref", "claim_table"],
                                        "reload_context": True,
                                    }
                                ),
                            }
                        ],
                        "details": {"status": "ok"},
                    },
                }
            )
            + "\n"
        )

    evidence = {
        "status": "PASS",
        "resumed": True,
        "fake_json_echo": False,
        "nonce": nonce,
        "expected_job_id": job,
        "session_file": request["session_file"],
        "start_line_0based": start_line,
        # Deliberately wrong event hashes — record must re-verify from disk.
        "evidence_line_range_1based": [2, 4],
        "ipython_tool_calls": [{"event_sha256": "a" * 64, "line_no_1based": 2}],
        "clean_ipython_tool_results": [{"event_sha256": "b" * 64, "line_no_1based": 3}],
        "nonce_events": [{"event_sha256": "c" * 64, "line_no_1based": 4}],
        "restored_variable": True,
        "reload_context_ok": True,
    }
    receipt = record_prime_resume(
        projects,
        None,
        request["request_id"],
        json.dumps(
            {
                "status": "PRIME_OM_RESUME_ACCEPTED",
                "session_file": request["session_file"],
                "nonce": nonce,
            }
        ),
        json.dumps(evidence),
    )
    assert receipt["schema_version"] == "om-prime-resume-receipt/v3"
    assert receipt["resumed"] is True
    assert receipt["resumed_evidence"]["nonce"] == nonce
    assert receipt["resumed_evidence"]["expected_job_id"] == job
    assert receipt["resumed_evidence"]["reverified_from_session_jsonl"] is True
    assert receipt["resumed_evidence"]["ipython_tool_call_sha256"] != "a" * 64
    assert receipt["global_latest_fallback"] is False

    cross = dict(evidence)
    cross["expected_job_id"] = "other-project"
    with pytest.raises(GatewayError, match="evidence.expected_job_id mismatch"):
        record_prime_resume(
            projects,
            None,
            request["request_id"],
            json.dumps({"status": "PRIME_OM_RESUME_ACCEPTED", "session_file": request["session_file"], "nonce": nonce}),
            json.dumps(cross),
        )

    bad_nonce = dict(evidence)
    with pytest.raises(GatewayError, match="evidence.nonce != acknowledgement.nonce"):
        record_prime_resume(
            projects,
            None,
            request["request_id"],
            json.dumps(
                {
                    "status": "PRIME_OM_RESUME_ACCEPTED",
                    "session_file": request["session_file"],
                    "nonce": "different-nonce",
                }
            ),
            json.dumps(bad_nonce),
        )


def test_prepare_resume_rejects_unrelated_latest_even_when_present(tmp_path: Path, monkeypatch):
    projects, project_dir = _fixture_projects(tmp_path)
    sessions = tmp_path / "prime-sessions"
    sessions.mkdir()
    (sessions / "zzz-newest-unrelated.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr("tools.content_studio_gateway.DEFAULT_PRIME_SESSION_DIR", sessions)
    gate = show_gate_payload(projects)
    apply_sceneplan_decisions(
        projects,
        None,
        gate["checkpoint"]["sha256"],
        [{"cut_id": "c01", "decision": "keep"}, {"cut_id": "c02", "decision": "keep"}],
    )
    assert not (project_dir / "working" / "prime_rlm" / "SESSION_POINTER.json").exists()
    with pytest.raises(GatewayError, match="Global latest-session fallback is forbidden"):
        prepare_prime_resume(projects, None)


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
