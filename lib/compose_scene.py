"""OM-owned scene concat + review queue. Prime requests; Cursor cannot.

Lights-out walks S1–S4, then concatenates succeeded mp4s, hashes the
composed output, binds SEE, and writes a scene-level REVIEW_QUEUE.
Does not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN. Does not freeze.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from lib.dispatch_cut import (
    _atomic_write_json,
    _observation_summary,
    _read_json,
    _rel,
    _see_mp4,
    job_frozen,
    landed_original_rollout,
    latest_rollout,
    observation_hash_bound,
)
from lib.quality_observation import evaluate_quality_observation, last_extracted_still

COMPOSE_SCHEMA = "om-scene-compose/v1"
REVIEW_QUEUE_SCHEMA = "om-review-queue/v1"
LIGHTS_OUT_SHOT_IDS = ("S1", "S2", "S3", "S4")
LIGHTS_OUT_SCENE = "scene_lights_out"


class ComposeError(ValueError):
    """Illegal compose_scene. Do not invent a review queue."""


def review_queue_path(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "REVIEW_QUEUE.json"


def composed_mp4_path(project_dir: Path, scene_id: str = LIGHTS_OUT_SCENE) -> Path:
    return project_dir / "working" / "prime_rlm" / "composed" / f"{scene_id}.mp4"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _concat_mp4s(paths: list[Path], output: Path, metadata: str | None = None) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ComposeError("ffmpeg is required for compose_scene")
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.parent / "concat.txt"
    lines = []
    for path in paths:
        posix = path.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{posix}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
    ]
    if metadata:
        cmd.extend(["-metadata", f"comment={metadata}"])
    cmd.append(str(output))
    subprocess.run(cmd, check=True)


def _shot_rollout_mp4(
    project_dir: Path,
    shot_id: str,
    revision: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]] | None:
    if revision is not None:
        from lib.scene_revision import shot_mp4_for_compose

        return shot_mp4_for_compose(project_dir, shot_id, revision)
    row = landed_original_rollout(project_dir, shot_id) or latest_rollout(project_dir, shot_id)
    if not row:
        return None
    rollout_id = str(row.get("rollout_id") or "")
    mp4 = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id / f"{shot_id}.mp4"
    if not mp4.is_file():
        return None
    return mp4, row


def compose_scene(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    scene_id: str = LIGHTS_OUT_SCENE,
    concat_fn: Callable[[list[Path], Path], None] | None = None,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if caller != "prime":
        raise ComposeError("compose_scene is a Prime production action; Cursor cannot impersonate Prime")
    if job_frozen(project_dir):
        raise ComposeError("job is frozen; do not compose")

    from lib.scene_revision import REVISE_STATUS, active_revision, is_revise_project

    revision = active_revision(project_dir) if is_revise_project(project_dir) else None
    queue_scene_id = str((revision or {}).get("scene_id") or scene_id or LIGHTS_OUT_SCENE)

    shot_hashes: dict[str, str | None] = {}
    mp4s: list[Path] = []
    missing: list[str] = []
    for shot_id in LIGHTS_OUT_SHOT_IDS:
        found = _shot_rollout_mp4(project_dir, shot_id, revision)
        if found is None:
            missing.append(shot_id)
            shot_hashes[shot_id] = None
            continue
        mp4, row = found
        obs = _read_json(mp4.parent / "OBSERVATION.json") or {}
        if "passed" not in (obs.get("quality") or {}):
            missing.append(shot_id)
            shot_hashes[shot_id] = str(row.get("output_hash") or "") or None
            continue
        mp4s.append(mp4)
        shot_hashes[shot_id] = str(row.get("output_hash") or _sha256_file(mp4))
    if missing or len(mp4s) != len(LIGHTS_OUT_SHOT_IDS):
        raise ComposeError(
            "compose_scene requires succeeded hash-bound Observations for "
            f"{list(LIGHTS_OUT_SHOT_IDS)}; missing {missing}"
        )

    output_name = "scene_v2" if revision else queue_scene_id
    output_path = composed_mp4_path(project_dir, output_name)
    if concat_fn is not None:
        concat_fn(mp4s, output_path)
    elif revision:
        meta = (
            f"om_revision_{revision['revision_number']}_"
            f"parent_{str(revision.get('parent_scene_hash') or '')[:16]}"
        )
        _concat_mp4s(mp4s, output_path, metadata=meta)
    else:
        _concat_mp4s(mp4s, output_path)
    if not output_path.is_file():
        raise ComposeError("compose_scene produced no mp4")
    output_hash = _sha256_file(output_path)
    if revision and output_hash == str(revision.get("parent_scene_hash") or ""):
        raise ComposeError("scene_v2_hash must differ from parent_scene_hash")
    see_dir = output_path.parent / "see"
    try:
        see = (see_fn or _see_mp4)(output_path, see_dir)
    except Exception as exc:
        raise ComposeError(f"observation_failed: {type(exc).__name__}: {exc}") from exc
    observation = _observation_summary(
        rollout_id=f"composed-{output_name}",
        output_path=output_path,
        output_hash=output_hash,
        see=see,
        see_dir=see_dir,
        root=root,
    )
    packet = see.get("frame_packet") or {}
    observation["quality"] = evaluate_quality_observation(
        contract={
            "id": queue_scene_id,
            "motion_obligation": "NONE",
            "visual_intent": "composed scene hold",
        },
        observation=observation,
        temporal=see.get("temporal_motion_report") or {},
        start_still=None,
        last_still=last_extracted_still(packet),
        framing="full_body",
    )
    observation_path = output_path.parent / "OBSERVATION.json"
    _atomic_write_json(observation_path, observation)
    queue: dict[str, Any] = {
        "schema_version": REVIEW_QUEUE_SCHEMA,
        "action": "compose_scene",
        "job_id": job_id,
        "scene_id": queue_scene_id,
        "shot_ids": list(LIGHTS_OUT_SHOT_IDS),
        "composed_path": _rel(output_path, root),
        "composed_hash": output_hash,
        "shot_hashes": shot_hashes,
        "observation_path": _rel(observation_path, root),
        "observation_bound": observation_hash_bound(observation),
        "caller": caller,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "generate": False,
        "stamped": False,
        "review_labels": ["KEEP_WATCHING", "SHIP", "DO_NOT_SHIP", "REVISE"],
        "created_at": _utc_now(),
        "note": "Scene-level review queue. Not APPROVED. Cursor did not generate.",
    }
    if revision:
        queue["parent_scene_hash"] = revision.get("parent_scene_hash")
        queue["review_id"] = revision.get("review_id")
        queue["affected_shots"] = list(revision.get("affected_shots") or [])
        queue["unchanged_shots"] = list(revision.get("unchanged_shots") or [])
        queue["revision_reason"] = revision.get("revision_reason")
        queue["revision_number"] = revision.get("revision_number")
        queue["proven_status"] = REVISE_STATUS
        queue["scene_revision_effectiveness_proven"] = False
        queue["waiting_on"] = (
            "Alan reviews scene_v2 only, not per-cut A/B. "
            "KEEP_WATCHING / SHIP / DO_NOT_SHIP / REVISE. "
            "A new hash is routing evidence, not proof the review reason was addressed. "
            "Do not stamp SCENE_REVISION_EFFECTIVENESS_PROVEN."
        )
    else:
        queue["proven_status"] = "LIGHTS_OUT_SCENE_PROOF"
        queue["lights_out_scene_production_proven"] = False
        queue["waiting_on"] = (
            "Alan reviews the composed scene only, not per-cut A/B. "
            "KEEP_WATCHING / SHIP / DO_NOT_SHIP / REVISE. "
            "Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN."
        )
    queue_path = review_queue_path(project_dir)
    _atomic_write_json(queue_path, queue)
    receipt = {
        "schema_version": COMPOSE_SCHEMA,
        "action": "compose_scene",
        "status": "succeeded",
        "job_id": job_id,
        "scene_id": queue_scene_id,
        "composed_path": _rel(output_path, root),
        "composed_hash": output_hash,
        "shot_hashes": shot_hashes,
        "review_queue_path": _rel(queue_path, root),
        "observation_path": _rel(observation_path, root),
        "stamped": False,
        "created_at": _utc_now(),
    }
    if revision:
        receipt["parent_scene_hash"] = revision.get("parent_scene_hash")
        receipt["revision_number"] = revision.get("revision_number")
        receipt["revision_reason"] = revision.get("revision_reason")
        receipt["affected_shots"] = list(revision.get("affected_shots") or [])
    _atomic_write_json(output_path.parent / "COMPOSE_RECEIPT.json", receipt)
    return {
        **receipt,
        "review_queue": queue,
        "observation": observation,
        "written": True,
    }

