"""Context-as-variable handles. Reload from OM/files; never store binaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adapter import (
    AdapterError,
    _job_dir,
    _read_json,
    _sha256_file,
    _utc_now,
    authorized_root,
    load_stage_pack,
    open_job,
    query_casebook,
)


def _handle(name: str, payload: Any, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "source_path": source.get("path") or source.get("checkpoint_path"),
        "source_hash": source.get("hash") or source.get("checkpoint_hash"),
        "loaded_at": source.get("loaded_at") or _utc_now(),
        "reload_method": source.get("reload_method") or "om_prime_adapter.reload_context",
        "stale": False,
        "value": payload,
    }


def build_context_variables(job_id: str, *, scenario_id: str | None = None) -> dict[str, Any]:
    job = open_job(job_id)
    scenario = scenario_id or job.get("scenario_id") or "comic-nonfiction-short-knowledge-zh"
    research = None
    try:
        research = load_stage_pack(job_id, "research")
    except AdapterError:
        pass
    architecture = None
    try:
        architecture = load_stage_pack(job_id, "content_architecture")
    except AdapterError:
        pass
    casebook = query_casebook(
        "accepted rejected music_covers_vo intent_prompt_result_mixed render_before_gate",
        scenario_id=scenario,
        job_id=job_id,
        limit=12,
    )
    claim_table = (research or {}).get("slice", {}).get("claims") or []
    qa_failures = [
        {
            "error_class": hit.get("error_class"),
            "summary": hit.get("summary"),
            "status": hit.get("status"),
            "repair": hit.get("repair"),
        }
        for hit in casebook.get("rejected_hits") or []
    ]
    run_metrics = {
        "parent_input_tokens": 0,
        "parent_output_tokens": 0,
        "child_input_tokens": 0,
        "child_output_tokens": 0,
        "total_tokens": 0,
        "wall_seconds": 0.0,
        "artifact_bytes": sum(int(ref.get("bytes") or 0) for ref in job.get("artifact_refs") or []),
        "repeated_full_file_injections": 0,
    }
    variables = {
        "om_job_ref": _handle("om_job_ref", job, {"path": job.get("project_dir"), "hash": job.get("checkpoint_hash"), "loaded_at": _utc_now(), "reload_method": "open_job"}),
        "claim_table": _handle("claim_table", claim_table, (research or {}).get("source") or job),
        "casebook_hits": _handle("casebook_hits", casebook.get("hits") or [], {"path": "runtime/prime-rlm-pilot/fixtures/casebook", "hash": None, "loaded_at": _utc_now(), "reload_method": "query_casebook"}),
        "qa_failures": _handle("qa_failures", qa_failures, {"path": "runtime/prime-rlm-pilot/fixtures/casebook", "hash": None, "loaded_at": _utc_now(), "reload_method": "query_casebook"}),
        "run_metrics": _handle("run_metrics", run_metrics, {"path": job.get("project_dir"), "hash": job.get("checkpoint_hash"), "loaded_at": _utc_now(), "reload_method": "build_context_variables"}),
        "stage_outputs": _handle(
            "stage_outputs",
            {
                "research": (research or {}).get("slice"),
                "content_architecture": (architecture or {}).get("slice"),
            },
            (architecture or research or {}).get("source") or job,
        ),
    }
    return {
        "schema_version": "om-prime-context/v1",
        "job_id": job_id,
        "scenario_id": scenario,
        "built_at": _utc_now(),
        "variables": variables,
        "reload_context": "om_prime_adapter.reload_context",
        "binary_variables": 0,
        "secret_variables": 0,
    }


def reload_context(ledger: dict[str, Any]) -> dict[str, Any]:
    job_id = ledger.get("job_id")
    if not job_id:
        raise AdapterError("ledger missing job_id")
    fresh = build_context_variables(job_id, scenario_id=ledger.get("scenario_id"))
    old_vars = ledger.get("variables") or {}
    for name, handle in (fresh.get("variables") or {}).items():
        previous = old_vars.get(name) or {}
        handle["replaced"] = previous.get("source_hash") != handle.get("source_hash")
    fresh["reloaded_at"] = _utc_now()
    fresh["previous_built_at"] = ledger.get("built_at")
    return fresh


def mark_stale(ledger: dict[str, Any]) -> dict[str, Any]:
    root = authorized_root()
    job_id = ledger["job_id"]
    project_dir = _job_dir(job_id, root)
    marker = project_dir / "project.json"
    current_hash = _sha256_file(marker) if marker.is_file() else None
    stale = []
    for name, handle in (ledger.get("variables") or {}).items():
        expected = handle.get("source_hash")
        if not expected:
            continue
        if name == "om_job_ref":
            job = open_job(job_id)
            if job.get("checkpoint_hash") != expected:
                handle["stale"] = True
                stale.append(name)
            continue
        source_path = handle.get("source_path")
        if not source_path:
            continue
        candidate = root / source_path
        if not candidate.is_file():
            candidate = project_dir / source_path.split("/")[-1]
        if candidate.is_file() and _sha256_file(candidate) != expected:
            handle["stale"] = True
            stale.append(name)
    ledger["stale_variables"] = stale
    ledger["marker_hash"] = current_hash
    ledger["checked_at"] = datetime.now(timezone.utc).isoformat()
    return ledger


def slice_variable(ledger: dict[str, Any], name: str, selector: dict[str, Any] | None = None) -> Any:
    handle = (ledger.get("variables") or {}).get(name)
    if not handle:
        raise AdapterError(f"Unknown variable: {name}")
    if handle.get("stale"):
        raise AdapterError(f"Variable {name} is stale; call reload_context")
    value = handle.get("value")
    selector = selector or {}
    if "index" in selector and isinstance(value, list):
        index = int(selector["index"])
        return value[index]
    if "error_class" in selector and isinstance(value, list):
        return [item for item in value if (item or {}).get("error_class") == selector["error_class"]]
    if "key" in selector and isinstance(value, dict):
        return value.get(selector["key"])
    if "fields" in selector and isinstance(value, dict):
        fields = selector["fields"]
        return {field: value.get(field) for field in fields}
    if name == "claim_table" and selector.get("usable_as"):
        return [item for item in value if item.get("usable_as") == selector["usable_as"]]
    return value
