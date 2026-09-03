"""Thin scene-revision record. Prime names affected cuts; OM owns hashes.

REVISE is not a terminal stop on SCENE_REVISE_PROPAGATION_PROOF.
Accepted H3 / PERFORMANCE shots are immutable. V1 hashes stay on disk.

Routing ≠ effectiveness. new hash ≠ useful revision.
rerendered cut ≠ feedback addressed. affected_shots correct ≠ repair correct.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REVISION_SCHEMA = "om-scene-revision/v1"
REVISE_STATUS = "SCENE_REVISE_PROPAGATION_PROOF"
REVISE_SCENE = "scene_revise"
REVISE_JOB = "vid-scene-revise-v1"
SHOT_ORDER = ("S1", "S2", "S3", "S4")
IMMUTABLE_H3_SHOT = "S2"
PARENT_COMPOSE_NAME = "PARENT_COMPOSE.json"


class RevisionError(ValueError):
    """Illegal revision proposal or dispatch."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _latest_rollout(project_dir: Path, shot_id: str) -> dict[str, Any] | None:
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return None
    receipts = sorted(root.glob("*/RECEIPT.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in receipts:
        row = _read_json(path)
        if row and row.get("shot_id") == shot_id:
            return row
    return None


def revision_path(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "SCENE_REVISION.json"


def parent_compose_path(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "composed" / PARENT_COMPOSE_NAME


def is_revise_project(project_dir: Path) -> bool:
    skeleton = _read_json(project_dir / "JOB_SKELETON.json") or {}
    return is_revise_skeleton(skeleton, None)


def is_revise_skeleton(skeleton: dict[str, Any] | None, proposal: dict[str, Any] | None) -> bool:
    status = str((skeleton or {}).get("status") or "")
    scene_id = str(
        (proposal or {}).get("scene_id")
        or (skeleton or {}).get("scene_id")
        or ""
    )
    project_id = str((skeleton or {}).get("project_id") or "")
    return (
        status == REVISE_STATUS
        or scene_id == REVISE_SCENE
        or project_id == REVISE_JOB
    )


def active_revision(project_dir: Path) -> dict[str, Any] | None:
    row = _read_json(revision_path(project_dir))
    if not row or row.get("schema_version") != REVISION_SCHEMA:
        return None
    return row


def read_parent_compose(project_dir: Path) -> dict[str, Any]:
    row = _read_json(parent_compose_path(project_dir)) or {}
    if not row.get("parent_scene_hash"):
        raise RevisionError("PARENT_COMPOSE.json missing parent_scene_hash")
    return row


def immutable_shot_ids(skeleton: dict[str, Any] | None, proposal: dict[str, Any] | None) -> set[str]:
    locked = {IMMUTABLE_H3_SHOT}
    h3_only = str((skeleton or {}).get("h3_only") or "").strip()
    if h3_only:
        locked.add(h3_only)
    for row in (proposal or {}).get("shots") or []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("id") or "")
        obligation = str(row.get("motion_obligation") or "").upper()
        renderer = str(row.get("renderer") or "").lower()
        if shot_id and (obligation == "PERFORMANCE" or renderer == "h3"):
            locked.add(shot_id)
    return locked


def _norm_shot_ids(values: Any) -> list[str]:
    out: list[str] = []
    for item in values or []:
        token = str(item or "").strip()
        if token and token not in out:
            out.append(token)
    return out


def validate_revision_proposal(
    *,
    project_dir: Path,
    proposal: dict[str, Any],
    skeleton: dict[str, Any] | None,
    scene_proposal: dict[str, Any] | None,
) -> dict[str, Any]:
    affected = _norm_shot_ids(proposal.get("affected_shots"))
    if not affected:
        raise RevisionError("revision proposal requires affected_shots")
    unknown = [shot_id for shot_id in affected if shot_id not in SHOT_ORDER]
    if unknown:
        raise RevisionError(f"unknown affected_shots: {unknown}")
    locked = immutable_shot_ids(skeleton, scene_proposal)
    overlap = [shot_id for shot_id in affected if shot_id in locked]
    if overlap:
        raise RevisionError(
            "immutable_h3_shot: "
            f"{overlap} cannot be redispatched because LOCAL/scene feedback. "
            "Accepted PERFORMANCE/H3 stays on the parent hash."
        )
    if set(affected) == set(SHOT_ORDER):
        raise RevisionError("whole-scene regenerate is not industrial revision")
    unchanged = _norm_shot_ids(proposal.get("unchanged_shots"))
    for shot_id in SHOT_ORDER:
        if shot_id not in affected and shot_id not in unchanged:
            unchanged.append(shot_id)
    for shot_id in locked:
        if shot_id not in unchanged:
            unchanged.append(shot_id)
        if shot_id in affected:
            raise RevisionError(f"immutable shot listed as affected: {shot_id}")
    reason = str(proposal.get("revision_reason") or "").strip()
    if not reason:
        raise RevisionError("revision_reason is required")
    try:
        revision_number = int(proposal.get("revision_number") or 2)
    except (TypeError, ValueError) as exc:
        raise RevisionError("revision_number must be an integer") from exc
    if revision_number < 2:
        raise RevisionError("revision_number starts at 2")
    parent = read_parent_compose(project_dir)
    pref = _read_json(project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json") or {}
    review_id = str(
        proposal.get("review_id")
        or pref.get("created_at")
        or parent.get("review_id")
        or ""
    ).strip()
    if not review_id:
        raise RevisionError("review_id missing (HumanPreference created_at)")
    return {
        "affected_shots": affected,
        "unchanged_shots": unchanged,
        "immutable_shots": sorted(locked),
        "revision_reason": reason,
        "revision_number": revision_number,
        "parent_scene_hash": str(parent["parent_scene_hash"]),
        "parent_shot_hashes": dict(parent.get("shot_hashes") or {}),
        "review_id": review_id,
        "scene_id": str(
            (scene_proposal or {}).get("scene_id")
            or (skeleton or {}).get("scene_id")
            or REVISE_SCENE
        ),
    }


def write_revision(
    project_dir: Path,
    *,
    job_id: str,
    record: dict[str, Any],
    caller: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": REVISION_SCHEMA,
        "action": "submit_revision_proposal",
        "status": "ACTIVE",
        "job_id": job_id,
        "scene_id": record["scene_id"],
        "parent_scene_hash": record["parent_scene_hash"],
        "parent_shot_hashes": record["parent_shot_hashes"],
        "review_id": record["review_id"],
        "affected_shots": record["affected_shots"],
        "unchanged_shots": record["unchanged_shots"],
        "immutable_shots": record["immutable_shots"],
        "revision_reason": record["revision_reason"],
        "revision_number": record["revision_number"],
        "caller": caller,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "generate": False,
        "created_at": _utc_now(),
        "note": "Thin revision record. Prime named affected cuts. OM owns execution and hashes. V1 is immutable.",
    }
    _atomic_write_json(revision_path(project_dir), payload)
    return payload


def rollout_by_output_hash(
    project_dir: Path,
    shot_id: str,
    output_hash: str | None,
) -> dict[str, Any] | None:
    digest = str(output_hash or "").strip()
    if not digest:
        return None
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return None
    for path in sorted(root.glob("*/RECEIPT.json")):
        row = _read_json(path)
        if (
            row
            and row.get("shot_id") == shot_id
            and str(row.get("output_hash") or "") == digest
        ):
            return row
    return None


def revision_rollout(
    project_dir: Path,
    shot_id: str,
    revision_number: int,
) -> dict[str, Any] | None:
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return None
    receipts = sorted(root.glob("*/RECEIPT.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in receipts:
        row = _read_json(path)
        if (
            row
            and row.get("shot_id") == shot_id
            and int(row.get("revision_number") or 0) == int(revision_number)
            and row.get("output_hash")
        ):
            return row
    return None


def parent_rollout_for_shot(
    project_dir: Path,
    shot_id: str,
    revision: dict[str, Any],
) -> dict[str, Any] | None:
    digest = str((revision.get("parent_shot_hashes") or {}).get(shot_id) or "")
    found = rollout_by_output_hash(project_dir, shot_id, digest)
    if found:
        return found
    row = _latest_rollout(project_dir, shot_id)
    if row and not row.get("parent_rollout_id") and int(row.get("revision_number") or 1) == 1:
        return row
    return None


def dispatch_blocked_reason(project_dir: Path, shot_id: str) -> str | None:
    """None means dispatch may proceed. String is the DispatchError."""
    revision = active_revision(project_dir)
    if not revision:
        return None
    locked = set(revision.get("immutable_shots") or [])
    unchanged = set(revision.get("unchanged_shots") or [])
    affected = set(revision.get("affected_shots") or [])
    if shot_id in locked or shot_id in unchanged:
        return (
            f"unchanged_shot_immutable: {shot_id} is not in affected_shots. "
            "Do not redispatch S2 H3 or any unnamed cut."
        )
    if shot_id not in affected:
        return f"shot {shot_id} is not in the active revision affected_shots"
    existing = revision_rollout(project_dir, shot_id, int(revision["revision_number"]))
    if existing and existing.get("output_hash"):
        return (
            "rollout_already_landed: "
            f"{existing.get('rollout_id')} hash {existing.get('output_hash')} "
            f"for revision {revision['revision_number']}. "
            "Do not generate again."
        )
    return None


def shot_mp4_for_compose(
    project_dir: Path,
    shot_id: str,
    revision: dict[str, Any] | None,
) -> tuple[Path, dict[str, Any]] | None:
    if revision is None:
        row = _latest_rollout(project_dir, shot_id)
    elif shot_id in set(revision.get("unchanged_shots") or []) or shot_id in set(
        revision.get("immutable_shots") or []
    ):
        row = parent_rollout_for_shot(project_dir, shot_id, revision)
    else:
        row = revision_rollout(project_dir, shot_id, int(revision["revision_number"]))
    if not row:
        return None
    rollout_id = str(row.get("rollout_id") or "")
    mp4 = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id / f"{shot_id}.mp4"
    if not mp4.is_file():
        return None
    return mp4, row
