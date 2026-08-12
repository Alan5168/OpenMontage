from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.prime_resume_evidence import verify_resume_events


def _tool_call_line(code: str = "print(1)") -> str:
    return json.dumps(
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "toolCall", "name": "ipython", "arguments": {"code": code}}],
            },
        }
    )


def _tool_result_line(payload: dict | str, *, status: str = "ok") -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return json.dumps(
        {
            "type": "message",
            "message": {
                "role": "toolResult",
                "toolCallId": "call_1",
                "toolName": "ipython",
                "content": [{"type": "text", "text": text}],
                "details": {"status": status},
            },
        }
    )


def test_verify_resume_events_requires_clean_toolresult_json(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    job = "fixture-pi-resume-e2e"
    lines = [
        json.dumps({"type": "session_info", "name": "old"}),
        _tool_call_line(),
        _tool_result_line(
            {
                "nonce": nonce,
                "job_id": job,
                "variable_names": ["om_job_ref", "claim_table"],
                "reload_context": True,
            }
        ),
    ]
    session.write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = verify_resume_events(session, nonce=nonce, expected_job_id=job, start_line=1)
    assert evidence["status"] == "PASS"
    assert evidence["job_id"] == job
    assert evidence["variable_names"]
    assert evidence["reload_context_ok"] is True
    assert evidence["prompt_or_toolCall_text_ignored"] is True


def test_verify_fails_when_only_prompt_or_toolcall_has_markers(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    job = "fixture-pi-resume-e2e"
    prompt_payload = {
        "nonce": nonce,
        "job_id": job,
        "variable_names": ["om_job_ref"],
        "reload_context": True,
    }
    lines = [
        json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": json.dumps(prompt_payload)}],
                },
            }
        ),
        _tool_call_line(code=json.dumps(prompt_payload)),
        _tool_result_line(""),  # clean but empty — no JSON payload
    ]
    session.write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = verify_resume_events(session, nonce=nonce, expected_job_id=job, start_line=0)
    assert evidence["status"] == "FAIL"
    assert "missing_clean_toolResult_json" in evidence["reason"]


def test_verify_fails_on_job_id_mismatch_inside_toolresult(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    lines = [
        _tool_call_line(),
        _tool_result_line(
            {
                "nonce": nonce,
                "job_id": "pilot-ai-content-os-state-machine-zh-v1",
                "variable_names": ["om_job_ref"],
                "reload_context": True,
            }
        ),
    ]
    session.write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = verify_resume_events(
        session, nonce=nonce, expected_job_id="fixture-pi-resume-e2e", start_line=0
    )
    assert evidence["status"] == "FAIL"


def test_verify_fails_without_ipython(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    session.write_text(
        json.dumps({"type": "message", "message": {"role": "assistant", "content": nonce}}) + "\n",
        encoding="utf-8",
    )
    evidence = verify_resume_events(
        session, nonce=nonce, expected_job_id="fixture-pi-resume-e2e", start_line=0
    )
    assert evidence["status"] == "FAIL"
    assert "missing_ipython_toolCall" in evidence["reason"]
