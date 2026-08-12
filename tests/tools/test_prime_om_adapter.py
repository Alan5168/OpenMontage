from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from lib.checkpoint import init_project, write_checkpoint
from tests.contracts.test_phase0_contracts import sample_artifact

ADAPTER_SRC = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "src"
sys.path.insert(0, str(ADAPTER_SRC))

from om_prime_adapter import (  # noqa: E402
    AdapterError,
    build_context_variables,
    get_gate,
    load_stage_pack,
    mark_stale,
    open_job,
    query_casebook,
    record_lesson_candidate,
    reload_context,
    resume_prime,
    slice_variable,
    submit_gate_decision,
    submit_stage_artifact,
)


SCENARIO = "comic-nonfiction-short-knowledge-zh"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _architecture() -> dict:
    return {
        "version": "1.0",
        "audience_problem": "把一次模型输出当成内容生产完成。",
        "thesis": "可靠的内容生产靠阶段门禁，而不是更强模型。",
        "viewer_change": "观众能区分烟雾结果与可发布成片。",
        "hooks": [
            {"text": "有输出不等于过门", "promise": "先看检查点"},
            {"text": "音乐不能盖住口播", "promise": "混音合同可测"},
            {"text": "意图、prompt、结果必须分列", "promise": "八列 sceneplan"},
        ],
        "structure": {
            "opening_promise": "先冻结失败，再谈生成。",
            "evidence_or_conflict": ["缺前置检查点不能前进", "未批准 Gate 不能渲染"],
            "turn": "门禁不是负担，是唯一可信完成定义。",
            "payoff": "同一失败不再整片重做。",
            "takeaway": "没有人工 Gate，就没有发布。",
        },
        "visual_opportunities": [
            {
                "beat": "opening",
                "opportunity": "textless gate closing in front of a result card",
                "provider_decided": False,
            }
        ],
    }


def _write_casebook(root: Path) -> None:
    casebook = root / "runtime" / "prime-rlm-pilot" / "fixtures" / "casebook"
    casebook.mkdir(parents=True, exist_ok=True)
    accepted = {
        "case_id": "PH7-D2-vo-bgm-accepted",
        "scenario_id": SCENARIO,
        "status": "accepted",
        "error_class": "music_covers_vo",
        "summary": "BGM 0.26 + two-pass loudnorm keeps vo_bgm_diff at 9.7dB without rerendering video.",
        "repair": "audio-only remux; never touch burned captions or video elementary stream",
        "evidence_paths": ["reports/windows-content-studio-shared-harness-v1/evidence/PH7-D2/REVIEW_PACK.md"],
        "tags": ["audio", "bgm", "vo", "loudnorm"],
        "before": {"vo_bgm_diff_db": 7.9, "bgm_volume": 0.32, "gate": "FAIL"},
        "after": {"vo_bgm_diff_db": 9.7, "bgm_volume": 0.26, "gate": "PASS"},
    }
    rejected = {
        "case_id": "PH7-D2-vo-bgm-rejected",
        "scenario_id": SCENARIO,
        "status": "rejected",
        "error_class": "music_covers_vo",
        "summary": "Music covering voice-over; old poster-only gate missed the finished video.",
        "repair": None,
        "evidence_paths": ["reports/windows-content-studio-shared-harness-v1/evidence/PH7-D2/audio_l0_bad_final.json"],
        "tags": ["audio", "bgm", "false-pass"],
        "before": {"vo_bgm_diff_db": 7.9, "lufs": -27.4, "gate": "false_pass"},
        "after": None,
    }
    mixed = {
        "case_id": "sceneplan-intent-prompt-result-mixed",
        "scenario_id": SCENARIO,
        "status": "rejected",
        "error_class": "intent_prompt_result_mixed",
        "summary": "Sceneplan collapsed visual intent, exact API prompt and generated result into one column.",
        "repair": "Keep eight-column contract: result / intent / prompt stay independent.",
        "evidence_paths": ["reports/windows-openmontage-localized-content-studio-v1/SCENEPLAN_8COL_CONTRACT.md"],
        "tags": ["sceneplan", "eight-column"],
    }
    render_early = {
        "case_id": "render-before-gate",
        "scenario_id": SCENARIO,
        "status": "rejected",
        "error_class": "render_before_gate",
        "summary": "Render started before Windows Pi Sceneplan Gate.",
        "repair": "Canonical checkpoint stays awaiting_human until Pi writes decisions.",
        "evidence_paths": ["reports/windows-openmontage-localized-content-studio-v1/PASS_ALAN_WINDOWS_ENTRY_REPORT.json"],
        "tags": ["gate", "render"],
    }
    (casebook / "accepted_music_covers_vo.json").write_text(json.dumps(accepted, ensure_ascii=False, indent=2), encoding="utf-8")
    (casebook / "rejected_music_covers_vo.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")
    (casebook / "rejected_intent_prompt_mixed.json").write_text(json.dumps(mixed, ensure_ascii=False, indent=2), encoding="utf-8")
    (casebook / "rejected_render_before_gate.json").write_text(json.dumps(render_early, ensure_ascii=False, indent=2), encoding="utf-8")


def _fixture_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    root = tmp_path / "ContentStudio"
    jobs = root / "jobs"
    job_id = "fixture-prime-rlm-historical"
    monkeypatch.setenv("OM_PRIME_ADAPTER_ROOT", str(root))
    monkeypatch.setenv("OPENMONTAGE_PROJECTS_DIR", str(jobs))
    init_project(
        job_id,
        title="Prime RLM historical fixture",
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
    (project_dir / "artifacts" / "research_brief.json").write_text(
        json.dumps(research, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_checkpoint(
        jobs,
        job_id,
        "research",
        "completed",
        {"research_brief": research},
        pipeline_type="unknown",
        style_playbook="premium-minimalist",
    )
    _write_casebook(root)
    return root, job_id


def test_open_job_is_read_only_and_hash_backed(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    first = open_job(job_id)
    second = open_job(job_id)
    assert first["canonical_owner"] == "openmontage"
    assert first["prime_may_write_project_state"] is False
    assert first["checkpoint_hash"]
    assert first["checkpoint_hash"] == second["checkpoint_hash"]
    assert first["artifact_refs"]


def test_load_stage_pack_returns_slice_not_media(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    pack = load_stage_pack(job_id, "research")
    assert pack["artifact_name"] == "research_brief"
    assert pack["source"]["hash"]
    assert pack["body"] is None
    assert pack["slice"]["claims"]
    assert all("claim" in item for item in pack["slice"]["claims"])


def test_query_casebook_returns_accepted_and_rejected(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    hits = query_casebook("music covering voice-over", SCENARIO, error_class="music_covers_vo", job_id=job_id)
    assert hits["accepted_hits"]
    assert hits["rejected_hits"]
    assert hits["accepted_hits"][0]["error_class"] == "music_covers_vo"
    assert hits["rejected_hits"][0]["status"] == "rejected"


def test_submit_stage_artifact_writes_through_om_validator(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    result = submit_stage_artifact(
        job_id,
        stage="proposal",
        artifact_name="proposal_packet",
        artifact=sample_artifact("proposal_packet"),
        caller="prime",
    )
    assert result["status"] == "WRITTEN"
    assert result["canonical_owner"] == "openmontage"
    project_dir = tmp_path / "ContentStudio" / "jobs" / job_id
    assert (project_dir / "artifacts" / "proposal_packet.json").is_file()
    assert (project_dir / "checkpoint_proposal.json").is_file()


def test_wrong_stage_write_is_rejected(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="denied for this Prime adapter"):
        submit_stage_artifact(
            job_id,
            stage="compose",
            artifact_name="render_report",
            artifact=sample_artifact("render_report"),
            caller="prime",
        )
    with pytest.raises(AdapterError, match="OM validator rejected write|PREREQUISITE"):
        submit_stage_artifact(
            job_id,
            stage="script",
            artifact_name="script",
            artifact=sample_artifact("script"),
            caller="pi",
        )


def test_human_gated_stage_cannot_be_completed_by_prime(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Windows Pi"):
        submit_stage_artifact(
            job_id,
            stage="scene_plan",
            artifact_name="scene_plan",
            artifact=sample_artifact("scene_plan"),
            caller="prime",
        )


def test_path_traversal_job_id_is_rejected(tmp_path, monkeypatch):
    _fixture_root(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Illegal job_id|escapes authorized root"):
        open_job("../secrets")


def test_secret_scan_rejects_token_payload(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    bad = sample_artifact("proposal_packet")
    bad["api_key"] = "sk-testsecretvalue"
    with pytest.raises(AdapterError, match="Secret-like"):
        submit_stage_artifact(
            job_id,
            stage="proposal",
            artifact_name="proposal_packet",
            artifact=bad,
            caller="prime",
        )


def test_prime_cannot_submit_gate_decision(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    with pytest.raises(AdapterError, match="Windows Pi only"):
        submit_gate_decision(job_id, [{"cut_id": "c01", "decision": "keep"}], caller="prime")


def test_record_lesson_candidate_is_job_local(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    result = record_lesson_candidate(
        job_id,
        {
            "error_class": "music_covers_vo",
            "summary": "Keep vo_bgm_diff in [9,10] dB with audio-only remux.",
            "evidence_paths": ["evidence/PH7-D2/REVIEW_PACK.md"],
            "status": "candidate",
            "scenario_id": SCENARIO,
            "repair": "bgm_volume 0.32 -> 0.26",
        },
    )
    ledger = tmp_path / "ContentStudio" / "jobs" / job_id / "working" / "lessons_candidates.jsonl"
    assert result["status"] == "RECORDED"
    assert ledger.is_file()
    line = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert line["promoted_to_global"] is False


def test_resume_prime_writes_pointer_not_gate(tmp_path, monkeypatch):
    root, job_id = _fixture_root(tmp_path, monkeypatch)
    before = open_job(job_id)
    result = resume_prime(job_id, "content-director__comic-nonfiction-short-knowledge-zh__v1")
    after = open_job(job_id)
    assert result["om_still_canonical"] is True
    assert after["checkpoint_hash"] == before["checkpoint_hash"]
    receipt = root / "jobs" / job_id / "working" / "prime_rlm" / "SESSION_RECEIPT.json"
    assert receipt.is_file()


def test_context_variables_reload_and_stale(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    ledger = build_context_variables(job_id, scenario_id=SCENARIO)
    names = set(ledger["variables"])
    assert {"om_job_ref", "claim_table", "casebook_hits", "qa_failures", "run_metrics"} <= names
    claim = slice_variable(ledger, "claim_table", {"index": 0})
    assert "claim" in claim
    same = reload_context(ledger)
    assert same["variables"]["claim_table"]["value"]
    project_dir = tmp_path / "ContentStudio" / "jobs" / job_id
    marker = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    marker["title"] = "Changed title"
    (project_dir / "project.json").write_text(json.dumps(marker, indent=2), encoding="utf-8")
    research_path = project_dir / "artifacts" / "research_brief.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    research["topic"] = "Changed topic"
    research_path.write_text(json.dumps(research, indent=2), encoding="utf-8")
    stale = mark_stale(ledger)
    assert "claim_table" in stale["stale_variables"] or stale["variables"]["claim_table"]["stale"] is True
    with pytest.raises(AdapterError, match="stale"):
        stale["variables"]["claim_table"]["stale"] = True
        slice_variable(stale, "claim_table", {"index": 0})


def test_get_gate_does_not_mutate(tmp_path, monkeypatch):
    _root, job_id = _fixture_root(tmp_path, monkeypatch)
    before = _sha(tmp_path / "ContentStudio" / "jobs" / job_id / "checkpoint_research.json")
    gate = get_gate(job_id)
    after = _sha(tmp_path / "ContentStudio" / "jobs" / job_id / "checkpoint_research.json")
    assert gate["prime_may_submit_gate"] is False
    assert before == after
