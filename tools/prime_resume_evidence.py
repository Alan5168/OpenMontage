"""Mechanically verify persistent Prime resume from session .jsonl events.

Evidence may ONLY come from error-free ipython toolResult payloads.
Prompt text and toolCall arguments never count as resume proof.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha_line(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _blob(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


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
    return "toolcall" in etype or etype in {"tool_use", "function_call"}


def _is_tool_result(obj: dict[str, Any]) -> bool:
    etype = str(obj.get("type") or "").lower()
    if "toolresult" in etype or etype in {"tool_result", "function_result"}:
        return True
    role = str(obj.get("role") or "").lower()
    return role in {"toolresult", "tool_result"}


def _has_error(obj: dict[str, Any]) -> bool:
    if obj.get("isError") is True or obj.get("is_error") is True:
        return True
    details = obj.get("details")
    if isinstance(details, dict) and str(details.get("status") or "").lower() == "error":
        return True
    text = _blob(obj).lower()
    return '"status": "error"' in text or '"status":"error"' in text


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = item.get("line_no_0based")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _content_texts(node: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    content = node.get("content")
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    texts.append(text)
    text = node.get("text")
    if isinstance(text, str):
        texts.append(text)
    return texts


def _parse_json_objects(texts: list[str]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for text in texts:
        candidate = text.strip()
        if not candidate:
            continue
        # Prefer whole-string JSON; also accept a trailing JSON object.
        for blob in (candidate, candidate[candidate.find("{") :] if "{" in candidate else ""):
            if not blob.startswith("{"):
                continue
            try:
                obj = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                payloads.append(obj)
                break
    return payloads


def _payload_passes(payload: dict[str, Any], *, nonce: str, expected_job_id: str) -> bool:
    if payload.get("nonce") != nonce:
        return False
    if payload.get("job_id") != expected_job_id:
        return False
    if payload.get("reload_context") is not True:
        return False
    names = payload.get("variable_names")
    if not isinstance(names, list) or not names:
        return False
    return True


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
    if not expected_job_id:
        return {"status": "FAIL", "reason": "expected_job_id required"}

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    slice_lines = lines[start_line:]
    ipython_calls: list[dict[str, Any]] = []
    ipython_results: list[dict[str, Any]] = []
    accepted_payloads: list[dict[str, Any]] = []
    accepted_result_events: list[dict[str, Any]] = []

    for offset, line in enumerate(slice_lines):
        line_no = start_line + offset
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue

        message = obj.get("message") if isinstance(obj.get("message"), dict) else None
        candidates: list[dict[str, Any]] = [obj]
        if message is not None:
            candidates.append(message)
            content = message.get("content")
            if isinstance(content, list):
                candidates.extend(item for item in content if isinstance(item, dict))

        for node in candidates:
            name = _tool_name(node)
            if name == "ipython" and _is_tool_call(node):
                ipython_calls.append(
                    {
                        "line_no_0based": line_no,
                        "line_no_1based": line_no + 1,
                        "event_sha256": _sha_line(line),
                        "type": obj.get("type"),
                        "role": (message or {}).get("role"),
                    }
                )
            if name == "ipython" and _is_tool_result(node):
                err = _has_error(node) or (_has_error(message) if message else False) or _has_error(obj)
                event = {
                    "line_no_0based": line_no,
                    "line_no_1based": line_no + 1,
                    "event_sha256": _sha_line(line),
                    "has_error": err,
                    "type": obj.get("type"),
                    "role": (message or {}).get("role"),
                }
                ipython_results.append(event)
                if err:
                    continue
                # Only clean toolResult text/JSON counts as resume evidence.
                for payload in _parse_json_objects(_content_texts(node) + (_content_texts(message) if message else [])):
                    if _payload_passes(payload, nonce=nonce, expected_job_id=expected_job_id):
                        accepted_payloads.append(payload)
                        accepted_result_events.append(event)

    ipython_calls = _dedupe(ipython_calls)
    ipython_results = _dedupe(ipython_results)
    clean_results = [item for item in ipython_results if not item["has_error"]]
    accepted_result_events = _dedupe(accepted_result_events)

    status = "PASS"
    reasons: list[str] = []
    if not ipython_calls:
        status = "FAIL"
        reasons.append("missing_ipython_toolCall")
    if not clean_results:
        status = "FAIL"
        reasons.append("missing_ipython_toolResult_without_error")
    if not accepted_payloads:
        status = "FAIL"
        reasons.append(
            "missing_clean_toolResult_json_with_exact_nonce_job_id_reload_context_and_variable_names"
        )

    line_refs = ipython_calls + accepted_result_events
    line_start = min((x["line_no_1based"] for x in line_refs), default=None)
    line_end = max((x["line_no_1based"] for x in line_refs), default=None)
    winning = accepted_payloads[0] if accepted_payloads else {}

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
        "accepted_tool_result_events": accepted_result_events,
        "accepted_payload": winning or None,
        "variable_names": list(winning.get("variable_names") or []),
        "job_id": winning.get("job_id"),
        "reload_context_ok": bool(winning.get("reload_context") is True),
        "restored_variable": bool(winning.get("variable_names")),
        "nonce_events": accepted_result_events,
        "resumed": status == "PASS",
        "fake_json_echo": False,
        "prompt_or_toolCall_text_ignored": True,
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
        "ipython_tool_result_sha256": (evidence.get("accepted_tool_result_events") or evidence.get("clean_ipython_tool_results") or [{}])[
            0
        ].get("event_sha256"),
        "nonce": evidence.get("nonce"),
    }
