"""Mechanically verify persistent Prime resume from session .jsonl events.

Do not trust model-emitted resumed=true. Require ipython toolCall + clean
toolResult carrying a unique nonce and either restored variable evidence or a
successful reload_context for the expected job_id.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _sha_line(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _tool_name(obj: dict[str, Any]) -> str | None:
    for key in ("name", "toolName", "tool_name"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    tool = obj.get("tool")
    if isinstance(tool, dict):
        for key in ("name", "toolName"):
            value = tool.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _is_tool_call(obj: dict[str, Any]) -> bool:
    etype = str(obj.get("type") or "").lower()
    if "toolcall" in etype or etype in {"tool_use", "function_call"}:
        return True
    role = str(obj.get("role") or "").lower()
    return role == "tool" and "result" not in etype


def _is_tool_result(obj: dict[str, Any]) -> bool:
    etype = str(obj.get("type") or "").lower()
    if "toolresult" in etype or etype in {"tool_result", "function_result"}:
        return True
    return False


def _blob(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _has_error(obj: dict[str, Any]) -> bool:
    if obj.get("isError") is True or obj.get("is_error") is True:
        return True
    if obj.get("error"):
        return True
    text = _blob(obj).lower()
    return '"error":' in text and "traceback" in text


def verify_resume_events(
    session_file: str | Path,
    *,
    nonce: str,
    expected_job_id: str,
    start_line: int = 0,
) -> dict[str, Any]:
    """Verify newly appended events after ``start_line`` (0-based exclusive start)."""
    path = Path(session_file)
    if not path.is_file():
        return {"status": "FAIL", "reason": f"session missing: {path}"}
    if not nonce or len(nonce) < 8:
        return {"status": "FAIL", "reason": "nonce too weak"}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    slice_lines = lines[start_line:]
    ipython_calls: list[dict[str, Any]] = []
    ipython_results: list[dict[str, Any]] = []
    nonce_hits: list[dict[str, Any]] = []
    reload_or_var_hits: list[dict[str, Any]] = []

    for offset, line in enumerate(slice_lines):
        line_no = start_line + offset  # 0-based
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        for node in _walk(obj):
            name = _tool_name(node)
            if name == "ipython" and (_is_tool_call(node) or _is_tool_call(obj) or "toolCall" in str(obj.get("type") or "")):
                ipython_calls.append(
                    {
                        "line_no_0based": line_no,
                        "line_no_1based": line_no + 1,
                        "event_sha256": _sha_line(line),
                        "type": obj.get("type"),
                    }
                )
            if name == "ipython" and (_is_tool_result(node) or _is_tool_result(obj)):
                err = _has_error(node) or _has_error(obj)
                ipython_results.append(
                    {
                        "line_no_0based": line_no,
                        "line_no_1based": line_no + 1,
                        "event_sha256": _sha_line(line),
                        "has_error": err,
                        "type": obj.get("type"),
                    }
                )
            blob = _blob(node)
            if nonce in blob:
                nonce_hits.append(
                    {
                        "line_no_0based": line_no,
                        "line_no_1based": line_no + 1,
                        "event_sha256": _sha_line(line),
                    }
                )
            if expected_job_id and expected_job_id in blob:
                if "reload_context" in blob or "variable_names" in blob or "om_job_ref" in blob or "claim_table" in blob:
                    reload_or_var_hits.append(
                        {
                            "line_no_0based": line_no,
                            "line_no_1based": line_no + 1,
                            "event_sha256": _sha_line(line),
                            "kind": "reload_or_variable",
                        }
                    )

    # Also accept explicit success markers in tool results / assistant content.
    restored = False
    reload_ok = False
    for offset, line in enumerate(slice_lines):
        if nonce not in line:
            continue
        low = line.lower()
        if "reload_context" in low and expected_job_id in line:
            reload_ok = True
        if any(k in line for k in ("om_job_ref", "claim_table", "variable_names", "RESTORED_VAR")):
            if expected_job_id in line or "variable" in low:
                restored = True

    clean_results = [item for item in ipython_results if not item["has_error"]]
    status = "PASS"
    reasons: list[str] = []
    if not ipython_calls:
        status = "FAIL"
        reasons.append("missing_ipython_toolCall")
    if not clean_results:
        status = "FAIL"
        reasons.append("missing_ipython_toolResult_without_error")
    if not nonce_hits:
        status = "FAIL"
        reasons.append("missing_nonce_in_new_events")
    if not (restored or reload_ok or reload_or_var_hits):
        status = "FAIL"
        reasons.append("missing_restored_variable_or_reload_context_for_job")

    line_start = min((x["line_no_1based"] for x in ipython_calls + clean_results + nonce_hits), default=None)
    line_end = max((x["line_no_1based"] for x in ipython_calls + clean_results + nonce_hits), default=None)

    return {
        "status": status,
        "reason": "; ".join(reasons) if reasons else "ok",
        "session_file": str(path.resolve()),
        "nonce": nonce,
        "expected_job_id": expected_job_id,
        "start_line_0based": start_line,
        "end_line_0based": start_line + len(slice_lines) - 1 if slice_lines else start_line,
        "evidence_line_range_1based": [line_start, line_end] if line_start and line_end else None,
        "ipython_tool_calls": ipython_calls,
        "ipython_tool_results": ipython_results,
        "clean_ipython_tool_results": clean_results,
        "nonce_events": nonce_hits,
        "reload_or_variable_events": reload_or_var_hits,
        "restored_variable": restored,
        "reload_context_ok": reload_ok,
        "resumed": status == "PASS",
        "fake_json_echo": False,
    }


def synthesize_ack_from_evidence(request: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PRIME_OM_RESUME_ACCEPTED" if evidence.get("status") == "PASS" else "PRIME_OM_RESUME_REJECTED",
        "project_id": request.get("project_id"),
        "checkpoint_sha256": request.get("checkpoint_sha256"),
        "next_stage": request.get("next_stage"),
        "session_file": request.get("session_file"),
        "resumed": bool(evidence.get("resumed")),
        "fake_json_echo": False,
        "evidence_line_range_1based": evidence.get("evidence_line_range_1based"),
        "ipython_tool_call_sha256": (evidence.get("ipython_tool_calls") or [{}])[0].get("event_sha256"),
        "ipython_tool_result_sha256": (evidence.get("clean_ipython_tool_results") or [{}])[0].get("event_sha256"),
        "nonce": evidence.get("nonce"),
    }
