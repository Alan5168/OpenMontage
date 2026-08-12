"""OpenMontage adapter used by Prime IPython. OM remains the only writer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

OM_REPO = Path(__file__).resolve().parents[4]
if str(OM_REPO) not in sys.path:
    sys.path.insert(0, str(OM_REPO))

from lib.checkpoint import (  # noqa: E402
    CANONICAL_STAGE_ARTIFACTS,
    STAGES,
    CheckpointValidationError,
    get_pipeline_stages,
    validate_checkpoint,
    write_checkpoint,
)
from schemas.artifacts import validate_artifact  # noqa: E402

from .schemas import JOB_REF_SCHEMA, LESSON_SCHEMA, STAGE_PACK_SCHEMA
from .security import (
    AdapterError,
    authorized_root,
    casebook_dir,
    display_rel,
    jobs_dir,
    reject_media_payload,
    resolve_authorized,
    scan_secrets,
)

SCHEMA_VERSION = "om-prime-adapter/v1"
PI_CALLER = "pi"
PRIME_CALLER = "prime"
WRITE_DENIED_STAGES = {"assets", "edit", "compose", "publish", "publish_package"}
HUMAN_GATED_STAGES = {"script", "scene_plan", "final_gate"}
TOKEN_RE = re.compile(r"[a-z0-9_]+", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError(f"Cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"Expected JSON object: {path}")
    scan_secrets(value)
    return value


def _atomic_write_json(path: Path, value: dict[str, Any] | list[Any]) -> None:
    scan_secrets(value)
    reject_media_payload(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _job_dir(job_id: str, root: Path | None = None) -> Path:
    if not job_id or job_id in {".", ".."} or "/" in job_id or "\\" in job_id:
        raise AdapterError(f"Illegal job_id: {job_id!r}")
    root = root or authorized_root()
    return resolve_authorized(jobs_dir(root) / job_id, root=root)


def _checkpoint_paths(project_dir: Path) -> list[Path]:
    return sorted(
        project_dir.glob("checkpoint_*.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )


def _active_checkpoint(project_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    awaiting = []
    readable = []
    for path in _checkpoint_paths(project_dir):
        try:
            checkpoint = _read_json(path)
            validate_checkpoint(checkpoint)
        except Exception:
            continue
        readable.append((path, checkpoint))
        if checkpoint.get("status") == "awaiting_human":
            awaiting.append((path, checkpoint))
    if awaiting:
        return awaiting[0]
    if readable:
        return readable[0]
    return None, None


def _source_meta(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": display_rel(path, root),
        "hash": _sha256_file(path) if path.is_file() else None,
        "bytes": path.stat().st_size if path.is_file() else 0,
        "loaded_at": _utc_now(),
        "reload_method": "om_prime_adapter.reload_context",
    }


def open_job(job_id: str) -> dict[str, Any]:
    root = authorized_root()
    project_dir = _job_dir(job_id, root)
    marker_path = project_dir / "project.json"
    if not marker_path.is_file():
        raise AdapterError(f"Unknown job: {job_id}")
    marker = _read_json(marker_path)
    checkpoint_path, checkpoint = _active_checkpoint(project_dir)
    artifact_refs = []
    artifacts_dir = project_dir / "artifacts"
    if artifacts_dir.is_dir():
        for path in sorted(artifacts_dir.glob("*.json")):
            artifact_refs.append(_source_meta(path, root))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "action": "open_job",
        "job_id": marker.get("project_id") or job_id,
        "title": marker.get("title"),
        "scenario_id": marker.get("scenario_id") or marker.get("style_playbook"),
        "pipeline_type": marker.get("pipeline_type") or (checkpoint or {}).get("pipeline_type"),
        "style_playbook": marker.get("style_playbook"),
        "stage": (checkpoint or {}).get("stage"),
        "status": (checkpoint or {}).get("status"),
        "human_approved": (checkpoint or {}).get("human_approved"),
        "checkpoint_path": display_rel(checkpoint_path, root) if checkpoint_path else None,
        "checkpoint_hash": _sha256_file(checkpoint_path) if checkpoint_path else None,
        "project_dir": display_rel(project_dir, root),
        "authorized_root": str(root),
        "artifact_refs": artifact_refs,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
    }
    jsonschema.validate(payload, JOB_REF_SCHEMA)
    scan_secrets(payload)
    return payload


def load_stage_pack(job_id: str, stage: str, *, include_body: bool = False) -> dict[str, Any]:
    root = authorized_root()
    project_dir = _job_dir(job_id, root)
    artifact_name = CANONICAL_STAGE_ARTIFACTS.get(stage)
    if not artifact_name:
        raise AdapterError(f"Unknown stage: {stage}")
    artifact_path = project_dir / "artifacts" / f"{artifact_name}.json"
    if not artifact_path.is_file():
        raise AdapterError(f"Stage artifact missing: {stage}/{artifact_name}")
    artifact = _read_json(artifact_path)
    validate_artifact(artifact_name, artifact)
    source = _source_meta(artifact_path, root)
    slice_ = _stage_slice(stage, artifact_name, artifact)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "action": "load_stage_pack",
        "job_id": job_id,
        "stage": stage,
        "artifact_name": artifact_name,
        "source": source,
        "slice": slice_,
        "body": artifact if include_body else None,
        "include_body": include_body,
    }
    jsonschema.validate(payload, STAGE_PACK_SCHEMA)
    return payload


def _stage_slice(stage: str, artifact_name: str, artifact: dict[str, Any]) -> dict[str, Any]:
    if artifact_name == "research_brief":
        return {
            "topic": artifact.get("topic"),
            "claims": [
                {
                    "claim": item.get("claim"),
                    "source_url": item.get("source_url") or item.get("source_name"),
                    "usable_as": item.get("usable_as"),
                }
                for item in (artifact.get("data_points") or [])[:8]
            ],
            "misconceptions": (artifact.get("audience_insights") or {}).get("misconceptions", [])[:4],
        }
    if artifact_name == "content_architecture":
        return {
            "thesis": artifact.get("thesis"),
            "hooks": artifact.get("hooks"),
            "takeaway": (artifact.get("structure") or {}).get("takeaway"),
            "visual_opportunities": artifact.get("visual_opportunities"),
        }
    if artifact_name == "scene_plan":
        scenes = []
        for scene in artifact.get("scenes") or []:
            scenes.append(
                {
                    "id": scene.get("id"),
                    "visual_intent": scene.get("visual_intent") or scene.get("description"),
                    "prompt": scene.get("t2i_prompt"),
                    "image_result_kind": (scene.get("visual_ref") or {}).get("kind"),
                    "dialogue": scene.get("dialogue"),
                    "review_decision": scene.get("review_decision"),
                }
            )
        return {"scene_count": len(scenes), "scenes": scenes}
    if artifact_name == "script":
        return {
            "title": artifact.get("title"),
            "total_duration_seconds": artifact.get("total_duration_seconds"),
            "section_ids": [section.get("id") for section in artifact.get("sections") or []],
        }
    return {"keys": sorted(artifact.keys())}


def query_casebook(
    query: str,
    scenario_id: str,
    error_class: str | None = None,
    *,
    job_id: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    root = authorized_root()
    search_dirs = [casebook_dir(root)]
    if job_id:
        search_dirs.insert(0, _job_dir(job_id, root) / "casebook")
    cases: list[dict[str, Any]] = []
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                case = _read_json(path)
            except AdapterError:
                continue
            if case.get("scenario_id") and case.get("scenario_id") != scenario_id:
                continue
            if error_class and case.get("error_class") != error_class:
                continue
            score = _case_score(query, case)
            if score <= 0 and error_class is None:
                continue
            cases.append(
                {
                    **{k: v for k, v in case.items() if k != "full_transcript"},
                    "source": _source_meta(path, root),
                    "score": score,
                }
            )
    cases.sort(key=lambda item: (-float(item.get("score") or 0), item.get("case_id") or ""))
    accepted = [item for item in cases if item.get("status") == "accepted"]
    rejected = [item for item in cases if item.get("status") == "rejected"]
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "query_casebook",
        "query": query,
        "scenario_id": scenario_id,
        "error_class": error_class,
        "hits": cases[:limit],
        "accepted_hits": accepted[:limit],
        "rejected_hits": rejected[:limit],
        "hit_count": len(cases[:limit]),
    }


def _case_score(query: str, case: dict[str, Any]) -> float:
    haystack = " ".join(
        [
            str(case.get("case_id") or ""),
            str(case.get("error_class") or ""),
            str(case.get("summary") or ""),
            str(case.get("repair") or ""),
            " ".join(str(item) for item in (case.get("tags") or [])),
        ]
    ).lower()
    tokens = TOKEN_RE.findall(query.lower())
    if not tokens:
        return 1.0 if case.get("error_class") else 0.0
    hits = sum(1 for token in tokens if token in haystack)
    bonus = 2.0 if case.get("error_class") and case["error_class"] in query.lower() else 0.0
    return hits + bonus


def submit_stage_artifact(
    job_id: str,
    stage: str,
    artifact_name: str,
    artifact: dict[str, Any],
    *,
    status: str = "completed",
    caller: str = PRIME_CALLER,
    human_approved: bool = False,
) -> dict[str, Any]:
    root = authorized_root()
    if caller not in {PRIME_CALLER, PI_CALLER}:
        raise AdapterError("Unknown caller")
    if stage in WRITE_DENIED_STAGES:
        raise AdapterError(f"Stage {stage!r} is denied for this Prime adapter; OM owns media/render")
    if stage in HUMAN_GATED_STAGES and caller != PI_CALLER:
        raise AdapterError(f"Stage {stage!r} requires Windows Pi / human Gate; Prime cannot complete it")
    scan_secrets(artifact)
    reject_media_payload(artifact)
    expected = CANONICAL_STAGE_ARTIFACTS.get(stage)
    if expected and artifact_name != expected:
        raise AdapterError(f"Wrong artifact for stage {stage}: expected {expected}, got {artifact_name}")
    validate_artifact(artifact_name, artifact)
    project_dir = _job_dir(job_id, root)
    marker = _read_json(project_dir / "project.json")
    pipeline_type = marker.get("pipeline_type")
    legal = list(get_pipeline_stages(pipeline_type)) if pipeline_type else list(STAGES)
    if not pipeline_type or pipeline_type == "unknown":
        legal = list(STAGES)
    if stage not in legal:
        raise AdapterError(f"Stage {stage!r} is not in pipeline {pipeline_type}")
    if stage in legal:
        predecessors = legal[: legal.index(stage)]
        missing = []
        for predecessor in predecessors:
            if not (project_dir / f"checkpoint_{predecessor}.json").is_file():
                missing.append(predecessor)
        if missing:
            raise AdapterError(
                f"OM validator rejected write: PREREQUISITE VIOLATION missing {missing} before {stage}"
            )
    artifact_path = project_dir / "artifacts" / f"{artifact_name}.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    previous_bytes = artifact_path.read_bytes() if artifact_path.is_file() else None
    try:
        _atomic_write_json(artifact_path, artifact)
        checkpoint_path = write_checkpoint(
            jobs_dir(root),
            job_id,
            stage,
            status,
            {artifact_name: artifact},
            pipeline_type=pipeline_type,
            style_playbook=marker.get("style_playbook"),
            human_approval_required=stage in HUMAN_GATED_STAGES,
            human_approved=bool(human_approved) if stage in HUMAN_GATED_STAGES else human_approved,
        )
    except (CheckpointValidationError, jsonschema.ValidationError, ValueError) as exc:
        if previous_bytes is None and artifact_path.exists():
            artifact_path.unlink()
        elif previous_bytes is not None:
            artifact_path.write_bytes(previous_bytes)
        raise AdapterError(f"OM validator rejected write: {exc}") from exc
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "submit_stage_artifact",
        "status": "WRITTEN",
        "job_id": job_id,
        "stage": stage,
        "artifact_name": artifact_name,
        "artifact_hash": _sha256_file(artifact_path),
        "checkpoint_hash": _sha256_file(Path(checkpoint_path)),
        "caller": caller,
        "canonical_owner": "openmontage",
    }


def record_lesson_candidate(job_id: str, lesson: dict[str, Any]) -> dict[str, Any]:
    root = authorized_root()
    jsonschema.validate(lesson, LESSON_SCHEMA)
    scan_secrets(lesson)
    project_dir = _job_dir(job_id, root)
    ledger_path = project_dir / "working" / "lessons_candidates.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        **lesson,
        "job_id": job_id,
        "recorded_at": _utc_now(),
        "scope": "job_local_candidate",
        "promoted_to_global": False,
    }
    scan_secrets(record)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "record_lesson_candidate",
        "status": "RECORDED",
        "job_id": job_id,
        "ledger": display_rel(ledger_path, root),
        "error_class": lesson.get("error_class"),
    }


def get_gate(job_id: str) -> dict[str, Any]:
    root = authorized_root()
    project_dir = _job_dir(job_id, root)
    checkpoint_path, checkpoint = _active_checkpoint(project_dir)
    if checkpoint_path is None or checkpoint is None:
        raise AdapterError("No readable checkpoint")
    artifact_name = CANONICAL_STAGE_ARTIFACTS.get(checkpoint.get("stage") or "", "")
    artifact_path = project_dir / "artifacts" / f"{artifact_name}.json" if artifact_name else None
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "get_gate",
        "job_id": job_id,
        "stage": checkpoint.get("stage"),
        "status": checkpoint.get("status"),
        "human_approved": checkpoint.get("human_approved"),
        "human_approval_required": checkpoint.get("human_approval_required"),
        "checkpoint_hash": _sha256_file(checkpoint_path),
        "artifact_hash": _sha256_file(artifact_path) if artifact_path and artifact_path.is_file() else None,
        "pi_only_write": checkpoint.get("stage") in HUMAN_GATED_STAGES,
        "prime_may_submit_gate": False,
    }


def submit_gate_decision(
    job_id: str,
    decisions: list[dict[str, Any]],
    *,
    caller: str,
) -> dict[str, Any]:
    if caller != PI_CALLER:
        raise AdapterError("submit_gate_decision is Windows Pi only; Prime cannot forge a human Gate")
    scan_secrets(decisions)
    # Pi remains the only writer for Gate mutations; this adapter only refuses Prime.
    raise AdapterError(
        "Gate mutation stays on tools.content_studio_gateway / Windows Pi. "
        "This adapter will not write human decisions."
    )


def resume_prime(job_id: str, session_id: str) -> dict[str, Any]:
    root = authorized_root()
    if not session_id or "/" in session_id or "\\" in session_id:
        raise AdapterError(f"Illegal session_id: {session_id!r}")
    project_dir = _job_dir(job_id, root)
    job = open_job(job_id)
    receipt = {
        "schema_version": "om-prime-session-receipt/v1",
        "job_id": job_id,
        "session_id": session_id,
        "checkpoint_hash": job.get("checkpoint_hash"),
        "stage": job.get("stage"),
        "status": job.get("status"),
        "canonical_owner": "openmontage",
        "prime_state_authority": False,
        "recorded_at": _utc_now(),
    }
    receipt_path = project_dir / "working" / "prime_rlm" / "SESSION_RECEIPT.json"
    _atomic_write_json(receipt_path, receipt)
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "resume_prime",
        "status": "POINTER_WRITTEN",
        "job_id": job_id,
        "session_id": session_id,
        "receipt": display_rel(receipt_path, root),
        "receipt_hash": _sha256_file(receipt_path),
        "om_still_canonical": True,
    }
