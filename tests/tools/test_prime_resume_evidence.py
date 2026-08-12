from __future__ import annotations

import json
from pathlib import Path

from tools.prime_resume_evidence import verify_resume_events


def test_verify_resume_events_requires_ipython_nonce_and_job(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    job = "pilot-ai-content-os-state-machine-zh-v1"
    lines = [
        json.dumps({"type": "session_info", "name": "old"}),
        json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "toolCall", "name": "ipython", "arguments": {"code": "print(1)"}}],
                },
            }
        ),
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
                                    "om_job_ref": {"project_id": job},
                                }
                            ),
                        }
                    ],
                    "details": {"status": "ok"},
                },
            }
        ),
    ]
    session.write_text("\n".join(lines) + "\n", encoding="utf-8")
    evidence = verify_resume_events(session, nonce=nonce, expected_job_id=job, start_line=1)
    assert evidence["status"] == "PASS"
    assert evidence["resumed"] is True
    assert evidence["ipython_tool_calls"]
    assert evidence["clean_ipython_tool_results"]
    assert evidence["nonce_events"]
    assert evidence["evidence_line_range_1based"]


def test_verify_resume_events_fails_without_ipython(tmp_path: Path):
    session = tmp_path / "s.jsonl"
    nonce = "resume-nonce-abc12345"
    session.write_text(
        json.dumps({"type": "message", "message": {"role": "assistant", "content": nonce}}) + "\n",
        encoding="utf-8",
    )
    evidence = verify_resume_events(
        session, nonce=nonce, expected_job_id="pilot-ai-content-os-state-machine-zh-v1", start_line=0
    )
    assert evidence["status"] == "FAIL"
    assert "missing_ipython_toolCall" in evidence["reason"]
