"""OM-owned cut dispatch. Prime requests; OM authorizes and executes.

PERFORMANCE goes to H3 FL2VA/I2VA. NONE/LOCAL goes to ffmpeg still-hold /
local_compose. vid3 scene_b/B2 freeze-on-success stays harness-acceptance
only. Lights-out and showpiece must not freeze on the first mp4.
Prime cannot flip generate=false. No automatic retry.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from lib.freeze_hold import freeze_frame_max_seconds
from lib.h3_context_ir import SHIP_SECONDS, compile_h3_ir, ship_duration_seconds
from lib.h3_runtime import R2VA_RUNTIME_UNAVAILABLE, ref2va_runtime_available
from lib.keyframe_presentation import PRESENTATION_UNUSABLE, evaluate_keyframe_presentation
from lib.motion_obligation import ShotCompileError, compile_cut as compile_shot
from lib.motion_router import MotionRouterError, assert_transition
from lib.prerequisite import CHARACTER_ID, IDENTITY_MISSING, active_scene_proposal, character_locked
from lib.quality_observation import evaluate_quality_observation, last_extracted_still
from lib.reference_atom import compile_performance_h3_spec

LOCAL_COMPOSE_RENDERERS = frozenset({"local_compose", "ffmpeg", "still", "still_loop"})
LOCAL_OBLIGATIONS = frozenset({"NONE", "LOCAL"})
DEFAULT_LOCAL_HOLD_SECONDS = 2.5

DISPATCH_SCHEMA = "om-rollout-receipt/v1"
OBSERVATION_SCHEMA = "om-observation-summary/v1"
PROVEN_SCHEMA = "om-proven-status/v1"
FREEZE_SCHEMA = "om-job-freeze/v1"
THIS_KNIFE_SCENE = "scene_b"
THIS_KNIFE_SHOT = "B2"
START_STILL_MISSING = "canonical_start_ref_missing"
PROVEN_INTERFACE = "PRIME_PRODUCTION_INTERFACE_READY"
PROVEN_DISPATCH = "PRIME_PRODUCTION_DISPATCH_PROVEN"


class DispatchError(ValueError):
    """Illegal dispatch. Do not invoke the provider."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _resolve_media(project_dir: Path, ref: str | None) -> Path | None:
    if not ref or not str(ref).strip():
        return None
    raw = Path(str(ref).strip())
    for candidate in (raw, project_dir / raw):
        try:
            resolved = candidate.expanduser()
            if resolved.is_file():
                return resolved
        except OSError:
            continue
    return None


def _requested_duration_seconds(shot: dict[str, Any]) -> float:
    start = shot.get("start_seconds")
    end = shot.get("end_seconds")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start:
        seconds = float(end) - float(start)
    else:
        try:
            seconds = float(shot.get("duration_seconds") or SHIP_SECONDS)
        except (TypeError, ValueError):
            seconds = SHIP_SECONDS
    return min(15.0, max(4.0, seconds))


def _duration_seconds(shot: dict[str, Any]) -> float:
    return ship_duration_seconds(
        _requested_duration_seconds(shot),
        allow_long=bool(shot.get("h3_allow_long")),
    )


def _local_hold_seconds(shot: dict[str, Any]) -> float:
    """NONE/LOCAL still-hold. Cap at fiction_anime_episode freeze_frame_max_seconds."""
    start = shot.get("start_seconds")
    end = shot.get("end_seconds")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start:
        seconds = float(end) - float(start)
    else:
        try:
            seconds = float(shot.get("duration_seconds") or DEFAULT_LOCAL_HOLD_SECONDS)
        except (TypeError, ValueError):
            seconds = DEFAULT_LOCAL_HOLD_SECONDS
    cap = freeze_frame_max_seconds("fiction_anime_episode") or 3.5
    return min(cap, max(1.0, seconds))


def _local_compose_still(
    first: Path,
    output_path: Path,
    duration: float,
    metadata: str | None = None,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise DispatchError("ffmpeg is required for NONE/LOCAL local_compose")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-framerate",
        "24",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(first),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
    ]
    if metadata:
        cmd.extend(["-metadata", f"comment={metadata}"])
    cmd.append(str(output_path))
    subprocess.run(cmd, check=True)


def _start_frame(project_dir: Path, shot: dict[str, Any], shot_id: str) -> Path | None:
    visual = shot.get("visual_ref") if isinstance(shot.get("visual_ref"), dict) else {}
    for ref in (
        shot.get("start_frame_ref"),
        shot.get("first_frame"),
        visual.get("path") if str(visual.get("kind") or "").lower() == "local_image" else None,
    ):
        found = _resolve_media(project_dir, str(ref) if ref else None)
        if found is not None:
            return found
    start_dir = project_dir / "working" / "prime_rlm" / "start_frames"
    for suffix in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = start_dir / f"{shot_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def _last_frame(project_dir: Path, shot: dict[str, Any], shot_id: str) -> Path | None:
    found = _resolve_media(project_dir, str(shot.get("last_frame_ref") or shot.get("last_frame") or ""))
    if found is not None:
        return found
    end_dir = project_dir / "working" / "prime_rlm" / "end_frames"
    for suffix in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = end_dir / f"{shot_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def _identity_hash(project_dir: Path) -> tuple[str | None, str | None]:
    plan = _read_json(project_dir / "artifacts" / "scene_plan.json") or {}
    meta = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
    sheet = meta.get("master_sheet_path") or "bible/avery/master_sheet.png"
    path = _resolve_media(project_dir, str(sheet))
    if path is None:
        return None, str(sheet)
    return _sha256_file(path), str(sheet)


def job_frozen(project_dir: Path) -> dict[str, Any] | None:
    freeze = _read_json(project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json")
    if freeze and freeze.get("frozen") is True:
        return freeze
    return None


def proven_status(project_dir: Path) -> str:
    known = {
        PROVEN_INTERFACE,
        PROVEN_DISPATCH,
        "PRIME_FOREMAN_PROOF",
        "PRIME_FOREMAN_PROVEN",
        "LIGHTS_OUT_SCENE_PROOF",
        "SCENE_REVISE_PROPAGATION_PROOF",
        "SCENE_REVISION_ROUTING_PROVEN",
    }
    freeze = job_frozen(project_dir)
    if freeze and freeze.get("proven_status"):
        return str(freeze["proven_status"])
    proven = _read_json(project_dir / "working" / "prime_rlm" / "PROVEN_STATUS.json")
    if proven and proven.get("proven_status") in known:
        return str(proven["proven_status"])
    if freeze:
        return PROVEN_DISPATCH
    skeleton = _read_json(project_dir / "JOB_SKELETON.json") or {}
    status = str(skeleton.get("status") or "")
    if status in known:
        return status
    return PROVEN_INTERFACE


def observation_hash_bound(observation: dict[str, Any] | None) -> bool:
    if not isinstance(observation, dict):
        return False
    output_hash = str(observation.get("output_hash") or "")
    return bool(
        observation.get("media_valid")
        and observation.get("source_hash_matches")
        and output_hash
        and observation.get("output_path")
    )


def _promote_dispatch_proven(
    project_dir: Path,
    receipt: dict[str, Any],
    observation: dict[str, Any],
) -> None:
    proven = {
        "schema_version": PROVEN_SCHEMA,
        "proven_status": PROVEN_DISPATCH,
        "foreman_proven": False,
        "job_id": receipt.get("job_id"),
        "shot_id": receipt.get("shot_id"),
        "rollout_id": receipt.get("rollout_id"),
        "output_hash": receipt.get("output_hash"),
        "observation_path": receipt.get("observation_path"),
        "created_at": _utc_now(),
        "note": (
            "Harness acceptance: Prime → OM dispatch → H3 → real mp4 → hash-bound Observation. "
            "Not episode complete. Not APPROVED. Job is frozen."
        ),
    }
    freeze = {
        "schema_version": FREEZE_SCHEMA,
        "frozen": True,
        "reason": "harness_acceptance_complete",
        "proven_status": PROVEN_DISPATCH,
        "do_not": ["B3", "B4", "B5", "polish_demo", "continue_episode"],
        "return_to": "harness_backlog",
        "created_at": _utc_now(),
    }
    _atomic_write_json(project_dir / "working" / "prime_rlm" / "PROVEN_STATUS.json", proven)
    _atomic_write_json(project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json", freeze)
    skeleton_path = project_dir / "JOB_SKELETON.json"
    skeleton = _read_json(skeleton_path) or {}
    skeleton["status"] = PROVEN_DISPATCH
    skeleton["frozen"] = True
    skeleton["foreman_proven"] = False
    skeleton["waiting_on"] = [
        "Job frozen after B2 harness acceptance. Return to harness backlog. Do not continue B3/B4/B5."
    ]
    _atomic_write_json(skeleton_path, skeleton)


def latest_rollout(project_dir: Path, shot_id: str) -> dict[str, Any] | None:
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return None
    receipts = sorted(root.glob("*/RECEIPT.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in receipts:
        row = _read_json(path)
        if row and row.get("shot_id") == shot_id:
            return row
    return None


def landed_original_rollout(project_dir: Path, shot_id: str) -> dict[str, Any] | None:
    """A first-take mp4 that already exists. Observer failure is not a reason to render again."""
    row = latest_rollout(project_dir, shot_id)
    if not row or row.get("parent_rollout_id"):
        return None
    digest = str(row.get("output_hash") or "").strip()
    if not digest:
        return None
    rollout_id = str(row.get("rollout_id") or "")
    mp4 = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id / f"{shot_id}.mp4"
    if mp4.is_file():
        return row
    return None


def _see_mp4(mp4: Path, out_dir: Path) -> dict[str, Any]:
    from lib.creative_loop import see_mp4

    return see_mp4(mp4, out_dir)


def _invoke_h3(inputs: dict[str, Any]) -> Any:
    from tools.video.comfyui_video import ComfyUIVideo

    return ComfyUIVideo().execute(inputs)


def _observation_summary(
    *,
    rollout_id: str,
    output_path: Path,
    output_hash: str,
    see: dict[str, Any],
    see_dir: Path,
    root: Path,
) -> dict[str, Any]:
    packet = see.get("frame_packet") or {}
    temporal = see.get("temporal_motion_report") or {}
    audio = see.get("audio_event_map") or {}
    checks = packet.get("machine_checks") or {}
    media_valid = bool(checks.get("probe_ok")) and output_path.is_file()
    source_ok = str(temporal.get("source_sha256") or packet.get("source_sha256") or "") == output_hash
    motion_flag = str(temporal.get("local_character_motion") or "")
    audio_present = audio.get("first_sound_seconds") is not None
    return {
        "schema_version": OBSERVATION_SCHEMA,
        "rollout_id": rollout_id,
        "output_path": _rel(output_path, root),
        "output_hash": output_hash,
        "media_valid": media_valid,
        "duration_seconds": temporal.get("duration_seconds") or packet.get("duration_seconds"),
        "temporal_evidence_present": bool(temporal.get("longest_static_run") is not None and temporal.get("motion_type")),
        "longest_static_run": temporal.get("longest_static_run"),
        "character_motion_present": motion_flag == "present",
        "source_hash_matches": source_ok,
        "audio_present": audio_present,
        "motion_coverage": temporal.get("motion_coverage"),
        "judgment": "measurement_only",
        "performance_question": (
            "Did Lucien complete an observable approach performance? "
            "Existing SEE reports motion types and static runs; it does not answer that."
        ),
        "see_paths": {
            "dir": _rel(see_dir, root),
            "temporal_motion_report": _rel(see_dir / "temporal_motion_report.json", root),
            "frame_packet": _rel(see_dir / "frame_packet.json", root),
            "audio_event_map": _rel(see_dir / "audio_event_map.json", root),
        },
        "created_at": _utc_now(),
    }


def _presentation_framing(shot: dict[str, Any]) -> str:
    intent = " ".join(
        str(shot.get(key) or "")
        for key in ("performance_intent", "visual_intent", "framing", "shot_size")
    ).lower()
    if any(token in intent for token in ("full-body", "full body", "walks the length", "wide")):
        return "full_body"
    if "insert" in intent:
        return "insert"
    return "medium_close"


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def validate_execution_request(
    *,
    job_id: str,
    shot_id: str,
    project_dir: Path,
    caller: str,
) -> dict[str, Any]:
    if caller != "prime":
        raise DispatchError("dispatch_cut is a Prime production action; Cursor cannot impersonate Prime")
    if job_frozen(project_dir):
        raise DispatchError("job is frozen after harness acceptance; do not dispatch")
    from lib.scene_revision import dispatch_blocked_reason, is_revise_project

    if is_revise_project(project_dir):
        blocked = dispatch_blocked_reason(project_dir, shot_id)
        if blocked:
            raise DispatchError(blocked)
    else:
        landed = landed_original_rollout(project_dir, shot_id)
        if landed:
            raise DispatchError(
                "rollout_already_landed: "
                f"{landed.get('rollout_id')} hash {landed.get('output_hash')}. "
                "OBSERVATION_INCOMPLETE is not a reason to render again. "
                "complete_observation on the existing output hash. "
                "Bounded repair quota is for the work, not the observer."
            )

    proposal = active_scene_proposal(project_dir)
    if not proposal:
        raise DispatchError("scene proposal missing or invalid")
    scene_id = str(proposal.get("scene_id") or "")
    if proposal.get("generate") is True or proposal.get("status") == "APPROVED":
        raise DispatchError("scene proposal cannot generate or APPROVE")
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    shot = next((row for row in shots if str(row.get("id")) == shot_id), None)
    if shot is None:
        raise DispatchError(f"shot {shot_id} is not on the current scene proposal")

    request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
    request = _read_json(request_path)
    if not request:
        raise DispatchError(f"execution proposal missing: {shot_id}")
    if request.get("status") != "PROPOSAL":
        raise DispatchError("dispatch_cut accepts only an existing PROPOSAL")
    if request.get("caller") != "prime":
        raise DispatchError("execution proposal caller must be prime")
    if request.get("generate") is True:
        raise DispatchError("Prime cannot flip generate=false; OM owns authorization")
    if request.get("job_id") != job_id:
        raise DispatchError("execution proposal job_id mismatch")
    if request.get("shot_id") != shot_id:
        raise DispatchError("execution proposal shot_id mismatch")
    if request.get("approved") is True or request.get("status") == "APPROVED":
        raise DispatchError("dispatch cannot ship or APPROVE")

    pref = _read_json(project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json")
    if is_revise_project(project_dir):
        if not pref or pref.get("label") != "REVISE":
            raise DispatchError("revision dispatch_cut requires HumanPreference REVISE")
    elif not pref or pref.get("label") != "CONTINUE_SCENE":
        raise DispatchError("dispatch_cut requires HumanPreference CONTINUE_SCENE")
    if pref.get("target") not in {scene_id, f"scene:{scene_id}", shot_id}:
        raise DispatchError("HumanPreference target is not the current scene")
    if pref.get("caller") not in {"human", "pi"}:
        raise DispatchError("CONTINUE_SCENE must be Alan/Pi; Prime cannot forge it")

    scene_state = _read_json(project_dir / "working" / "scene_a" / "SCENE_STATE.json") or {}
    if scene_state.get("ship") is True:
        raise DispatchError("human ship is true; dispatch refused")

    proposal_path = project_dir / "working" / "prime_rlm" / "scene_proposals" / f"{scene_id}.json"
    current_hash = _sha256_file(proposal_path)
    stored_hash = (request.get("shot_ref") or {}).get("scene_plan_hash")
    if stored_hash and stored_hash != current_hash:
        raise DispatchError("stale execution proposal: scene hash changed")

    try:
        compiled = compile_shot(shot)
    except ShotCompileError as exc:
        raise DispatchError(str(exc)) from exc
    if compiled["motion_obligation"] != request.get("motion_obligation"):
        raise DispatchError("stale execution proposal: motion_obligation mismatch")
    if compiled["renderer"] != request.get("renderer"):
        raise DispatchError("stale execution proposal: renderer mismatch")
    obligation = compiled["motion_obligation"]
    if obligation == "PERFORMANCE":
        if compiled["renderer"] != "h3":
            raise DispatchError("only PERFORMANCE cuts dispatch to H3")
        if compiled["h3_mode"] not in {"fl2va", "i2va"} or request.get("h3_mode") not in {"fl2va", "i2va"}:
            raise DispatchError("PERFORMANCE must dispatch to H3 FL2VA/I2VA")
    elif obligation == "INTERACTION":
        if not ref2va_runtime_available():
            raise DispatchError(R2VA_RUNTIME_UNAVAILABLE)
        raise DispatchError(
            "INTERACTION prefers h3_ref2va. Runtime weights exist, but "
            "dispatch_cut does not invoke MiniMaxH3ReferenceToVideo yet. "
            "Isolated H3_REF2VA_MOTION_REFERENCE_PROOF only. Do not FL2VA this cut."
        )
    elif obligation in LOCAL_OBLIGATIONS:
        if compiled["renderer"] not in LOCAL_COMPOSE_RENDERERS:
            raise DispatchError("NONE/LOCAL must dispatch to local_compose")
    else:
        raise DispatchError(f"unsupported motion_obligation for dispatch: {obligation}")
    try:
        assert_transition("EXECUTION_PROPOSAL", "ROLLOUT", actor=caller)
    except MotionRouterError as exc:
        raise DispatchError(str(exc)) from exc

    first = _start_frame(project_dir, shot, shot_id)
    last = _last_frame(project_dir, shot, shot_id)
    ident_hash, ident_path = _identity_hash(project_dir)
    return {
        "request": request,
        "request_path": request_path,
        "request_hash": _sha256_file(request_path),
        "proposal": proposal,
        "proposal_hash": current_hash,
        "shot": shot,
        "compiled": compiled,
        "first_frame": first,
        "last_frame": last,
        "identity_hash": ident_hash,
        "identity_path": ident_path,
        "scene_id": scene_id,
    }


def _dispatch_local_hold(
    *,
    receipt: dict[str, Any],
    first: Path,
    shot: dict[str, Any],
    compiled: dict[str, Any],
    output_path: Path,
    out_dir: Path,
    root: Path,
    framing: str,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None,
) -> dict[str, Any]:
    duration = _local_hold_seconds(shot)
    receipt["provider"] = "ffmpeg"
    receipt["model"] = "local_compose_still_hold"
    receipt["mode"] = "still_hold"
    receipt["config"] = {
        "duration_seconds": duration,
        "freeze_frame_max_seconds": freeze_frame_max_seconds("fiction_anime_episode") or 3.5,
        "renderer": compiled["renderer"],
        "motion_obligation": compiled["motion_obligation"],
        "h3": False,
    }
    receipt["gpu_or_api_cost"] = {
        "usd": 0.0,
        "note": "ffmpeg still-hold / local_compose. Not H3.",
    }
    started = time.perf_counter()
    try:
        meta = None
        if receipt.get("revision_number"):
            meta = (
                f"om_revision_{receipt['revision_number']}_"
                f"parent_{str(receipt.get('parent_output_hash') or '')[:16]}"
            )
        if meta:
            _local_compose_still(first, output_path, duration, metadata=meta)
        else:
            _local_compose_still(first, output_path, duration)
    except Exception as exc:
        receipt["wall_time_seconds"] = round(time.perf_counter() - started, 3)
        receipt["status"] = "failed"
        receipt["error"] = f"local_compose_failed: {type(exc).__name__}: {exc}"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }
    receipt["wall_time_seconds"] = round(time.perf_counter() - started, 3)
    if not output_path.is_file():
        receipt["status"] = "failed"
        receipt["error"] = "local_compose produced no output"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }
    output_hash = _sha256_file(output_path)
    receipt["output_hash"] = output_hash
    receipt["output_path"] = _rel(output_path, root)
    see_dir = out_dir / "see"
    try:
        see = (see_fn or _see_mp4)(output_path, see_dir)
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = f"observation_failed: {type(exc).__name__}: {exc}"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }
    observation = _observation_summary(
        rollout_id=str(receipt.get("rollout_id") or ""),
        output_path=output_path,
        output_hash=output_hash,
        see=see,
        see_dir=see_dir,
        root=root,
    )
    packet = see.get("frame_packet") or {}
    observation["quality"] = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=see.get("temporal_motion_report") or {},
        start_still=first,
        last_still=last_extracted_still(packet),
        framing=framing,
    )
    observation_path = out_dir / "OBSERVATION.json"
    _atomic_write_json(observation_path, observation)
    receipt["status"] = "succeeded"
    receipt["observation_path"] = _rel(observation_path, root)
    receipt["error"] = None
    receipt["frozen"] = False
    receipt["note"] = (
        "OM-authorized NONE/LOCAL still-hold. ffmpeg local_compose. Not H3. Not APPROVED. "
        "Does not freeze the job."
    )
    _atomic_write_json(out_dir / "RECEIPT.json", receipt)
    return {
        **receipt,
        "observation": observation,
        "receipt_path": _rel(out_dir / "RECEIPT.json", root),
        "written": True,
    }


def dispatch_cut(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    invoke_h3: Callable[[dict[str, Any]], Any] | None = None,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validated = validate_execution_request(
        job_id=job_id,
        shot_id=shot_id,
        project_dir=project_dir,
        caller=caller,
    )
    rollout_id = f"{shot_id.lower()}-{uuid.uuid4().hex[:12]}"
    out_dir = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{shot_id}.mp4"
    first = validated["first_frame"]
    last = validated["last_frame"]
    compiled = validated["compiled"]
    shot = validated["shot"]
    scene_id = str(validated.get("scene_id") or THIS_KNIFE_SCENE)
    input_hashes = {
        "execution_request": validated["request_hash"],
        "scene_proposal": validated["proposal_hash"],
        "identity": validated["identity_hash"],
        "first_frame": _sha256_file(first) if first is not None else None,
        "last_frame": _sha256_file(last) if last is not None else None,
        "lucien_identity": _sha256_file(project_dir / "bible" / "lucien" / "master_sheet.png")
        if (project_dir / "bible" / "lucien" / "master_sheet.png").is_file()
        else None,
    }
    receipt: dict[str, Any] = {
        "schema_version": DISPATCH_SCHEMA,
        "action": "dispatch_cut",
        "rollout_id": rollout_id,
        "job_id": job_id,
        "shot_id": shot_id,
        "scene_id": scene_id,
        "caller": caller,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "authorized_by": "openmontage",
        "generate": False,
        "retry": False,
        "status": "blocked",
        "execution_request_hash": validated["request_hash"],
        "provider": "comfyui",
        "model": None,
        "mode": "fl2va",
        "motion_obligation": compiled["motion_obligation"],
        "renderer": compiled["renderer"],
        "input_hashes": input_hashes,
        "identity_path": validated["identity_path"],
        "seed": None,
        "config": None,
        "wall_time_seconds": None,
        "gpu_or_api_cost": {"usd": 0.0, "note": "local ComfyUI / 5070 Ti when available"},
        "output_hash": None,
        "output_path": None,
        "observation_path": None,
        "error": None,
        "created_at": _utc_now(),
        "note": "OM-authorized rollout. Prime requested execution. Not APPROVED.",
    }
    from lib.scene_revision import active_revision, parent_rollout_for_shot

    revision = active_revision(project_dir)
    if revision and shot_id in set(revision.get("affected_shots") or []):
        parent = parent_rollout_for_shot(project_dir, shot_id, revision)
        receipt["revision_number"] = revision.get("revision_number")
        receipt["parent_scene_hash"] = revision.get("parent_scene_hash")
        receipt["review_id"] = revision.get("review_id")
        if parent:
            receipt["parent_rollout_id"] = parent.get("rollout_id")
            receipt["parent_output_hash"] = parent.get("output_hash")

    ids = [str(x) for x in (shot.get("character_ids") or [])]
    if CHARACTER_ID in ids and not character_locked(project_dir):
        receipt["error"] = IDENTITY_MISSING
        receipt["status"] = "blocked"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }

    if first is None:
        receipt["error"] = START_STILL_MISSING
        receipt["status"] = "blocked"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }

    framing = _presentation_framing(shot)
    presentation = evaluate_keyframe_presentation(first, framing=framing)
    receipt["keyframe_presentation"] = {
        "usable": presentation.get("usable"),
        "blockers": presentation.get("blockers"),
        "framing": framing,
    }
    if compiled["motion_obligation"] == "PERFORMANCE" and presentation.get("usable") is not True:
        receipt["error"] = PRESENTATION_UNUSABLE
        receipt["status"] = "blocked"
        receipt["presentation_blockers"] = presentation.get("blockers")
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }

    if compiled["motion_obligation"] in LOCAL_OBLIGATIONS:
        return _dispatch_local_hold(
            receipt=receipt,
            first=first,
            shot=shot,
            compiled=compiled,
            output_path=output_path,
            out_dir=out_dir,
            root=root,
            framing=framing,
            see_fn=see_fn,
        )

    requested = _requested_duration_seconds(shot)
    duration = _duration_seconds(shot)
    spec = compile_performance_h3_spec(
        shot,
        first_frame=str(first),
        last_frame=str(last) if last is not None else None,
        duration_seconds=duration,
    )
    spec["h3_allow_long"] = bool(shot.get("h3_allow_long"))
    h3_ir = compile_h3_ir(spec)
    receipt["config"] = {
        "h3_ir_mode": h3_ir["mode"],
        "requested_mode": "fl2va",
        "requested_duration_seconds": requested,
        "duration_seconds": h3_ir["duration_seconds"],
        "duration_capped_to_ship_grid": (not spec["h3_allow_long"])
        and requested > SHIP_SECONDS,
        "h3_allow_long": spec["h3_allow_long"],
        "length": h3_ir["length"],
        "width": h3_ir["width"],
        "height": h3_ir["height"],
        "workflow_model": "minimax-h3",
        "clip_device": "cpu",
        "last_frame_present": last is not None,
    }
    inputs = {
        "operation": "image_to_video",
        "workflow_model": "minimax-h3",
        "h3_ir": spec,
        "reference_image_path": str(first),
        "output_path": str(output_path),
        "project_dir": str(project_dir),
    }
    if last is not None:
        inputs["last_frame_path"] = str(last)

    started = time.perf_counter()
    invoke = invoke_h3 or _invoke_h3
    result = invoke(inputs)
    wall = round(time.perf_counter() - started, 3)
    receipt["wall_time_seconds"] = wall
    success = bool(getattr(result, "success", False))
    data = getattr(result, "data", None) or {}
    receipt["model"] = getattr(result, "model", None) or data.get("model")
    receipt["seed"] = getattr(result, "seed", None) or data.get("seed")
    receipt["gpu_or_api_cost"] = {
        "usd": float(getattr(result, "cost_usd", 0.0) or 0.0),
        "tool_duration_seconds": getattr(result, "duration_seconds", None),
        "timing": (data.get("timing") or {}),
        "note": "local ComfyUI / 5070 Ti when available. wall_time is harness+Comfy, not GPU s/it.",
    }
    if not success or not output_path.is_file():
        receipt["status"] = "failed"
        receipt["error"] = getattr(result, "error", None) or "H3 produced no output"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }

    output_hash = _sha256_file(output_path)
    receipt["output_hash"] = output_hash
    receipt["output_path"] = _rel(output_path, root)
    see_dir = out_dir / "see"
    try:
        see = (see_fn or _see_mp4)(output_path, see_dir)
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = f"observation_failed: {type(exc).__name__}: {exc}"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }
    observation = _observation_summary(
        rollout_id=rollout_id,
        output_path=output_path,
        output_hash=output_hash,
        see=see,
        see_dir=see_dir,
        root=root,
    )
    packet = see.get("frame_packet") or {}
    observation["quality"] = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=see.get("temporal_motion_report") or {},
        start_still=first,
        last_still=last_extracted_still(packet),
        framing=framing,
    )
    observation_path = out_dir / "OBSERVATION.json"
    _atomic_write_json(observation_path, observation)
    receipt["status"] = "succeeded"
    receipt["observation_path"] = _rel(observation_path, root)
    receipt["error"] = None
    if (
        observation_hash_bound(observation)
        and scene_id == THIS_KNIFE_SCENE
        and shot_id == THIS_KNIFE_SHOT
    ):
        _promote_dispatch_proven(project_dir, receipt, observation)
        receipt["proven_status"] = PROVEN_DISPATCH
        receipt["frozen"] = True
    _atomic_write_json(out_dir / "RECEIPT.json", receipt)
    return {
        **receipt,
        "observation": observation,
        "receipt_path": _rel(out_dir / "RECEIPT.json", root),
        "written": True,
    }


def complete_observation(
    job_id: str,
    project_dir: Path,
    root: Path,
    rollout_id: str,
    *,
    caller: str,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind SEE onto an H3 mp4 that already landed. Does not invoke H3. Does not draw again."""
    if caller != "prime":
        raise DispatchError("complete_observation is a Prime production action; Cursor cannot impersonate Prime")
    if job_frozen(project_dir):
        raise DispatchError("job is frozen")
    out_dir = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    existing = _read_json(out_dir / "RECEIPT.json") or {}
    shot_id = str(existing.get("shot_id") or "")
    scene_id = str(existing.get("scene_id") or "")
    output_path = out_dir / f"{shot_id}.mp4"
    if not output_path.is_file():
        raise DispatchError(f"rollout has no mp4: {rollout_id}")
    if existing.get("status") == "succeeded" and existing.get("observation_path"):
        obs = _read_json(out_dir / "OBSERVATION.json") or {}
        if "passed" in (obs.get("quality") or {}):
            return existing
    output_hash = _sha256_file(output_path)
    expected = str(existing.get("output_hash") or "").strip()
    if expected and expected != output_hash:
        raise DispatchError(
            f"output_hash_mismatch: disk {output_hash} != receipt {expected}. "
            "Do not bind a different take."
        )
    receipt = dict(existing)
    receipt["output_hash"] = output_hash
    receipt["output_path"] = _rel(output_path, root)
    receipt["foreman_proven"] = False
    receipt["studio_v1"] = False
    receipt["first_take_acceptable"] = False
    receipt["content_fail"] = False
    see_dir = out_dir / "see"
    try:
        see = (see_fn or _see_mp4)(output_path, see_dir)
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = f"observation_failed: {type(exc).__name__}: {exc}"
        receipt["observation_incomplete"] = True
        receipt["quality_verdict"] = None
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return {
            **receipt,
            "receipt_path": _rel(out_dir / "RECEIPT.json", root),
            "written": True,
        }
    observation = _observation_summary(
        rollout_id=rollout_id,
        output_path=output_path,
        output_hash=output_hash,
        see=see,
        see_dir=see_dir,
        root=root,
    )
    scene = active_scene_proposal(project_dir) or {}
    shot = next(
        (row for row in (scene.get("shots") or []) if str(row.get("id")) == shot_id),
        {"id": shot_id},
    )
    first = _start_frame(project_dir, shot, shot_id)
    packet = see.get("frame_packet") or {}
    observation["quality"] = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=see.get("temporal_motion_report") or {},
        start_still=first,
        last_still=last_extracted_still(packet),
        framing=_presentation_framing(shot),
    )
    observation_path = out_dir / "OBSERVATION.json"
    _atomic_write_json(observation_path, observation)
    receipt["status"] = "succeeded"
    receipt["error"] = None
    receipt["observation_path"] = _rel(observation_path, root)
    receipt["note"] = (
        "OM completed Observation on an existing H3 mp4 after a post-provider crash. "
        "Not a second generate. Not APPROVED. Not PRIME_FOREMAN_PROVEN."
    )
    if (
        observation_hash_bound(observation)
        and scene_id == THIS_KNIFE_SCENE
        and shot_id == THIS_KNIFE_SHOT
    ):
        _promote_dispatch_proven(project_dir, receipt, observation)
        receipt["proven_status"] = PROVEN_DISPATCH
        receipt["frozen"] = True
    _atomic_write_json(out_dir / "RECEIPT.json", receipt)
    return {
        **receipt,
        "observation": observation,
        "receipt_path": _rel(out_dir / "RECEIPT.json", root),
        "written": True,
    }


def rejudge_bound_observation(project_dir: Path, rollout_id: str) -> dict[str, Any]:
    """Recompute quality from already-bound SEE. Does not invoke H3. Does not re-SEE."""
    out_dir = project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id
    observation = _read_json(out_dir / "OBSERVATION.json")
    if not observation:
        raise DispatchError(f"no Observation to rejudge: {rollout_id}")
    receipt = _read_json(out_dir / "RECEIPT.json") or {}
    shot_id = str(receipt.get("shot_id") or "")
    scene = active_scene_proposal(project_dir) or {}
    shot = next(
        (row for row in (scene.get("shots") or []) if str(row.get("id")) == shot_id),
        {"id": shot_id},
    )
    see_dir = out_dir / "see"
    temporal = _read_json(see_dir / "temporal_motion_report.json") or {}
    packet = _read_json(see_dir / "frame_packet.json") or {}
    existing_quality = observation.get("quality") if isinstance(observation.get("quality"), dict) else {}
    start_still = _existing_presentation_path(existing_quality, "start_presentation") or _start_frame(
        project_dir, shot, shot_id
    )
    last_still = _existing_presentation_path(existing_quality, "last_presentation") or last_extracted_still(
        packet
    )
    observation["quality"] = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=temporal,
        start_still=start_still,
        last_still=last_still,
        framing=_presentation_framing(shot),
    )
    observation["performance_question"] = (
        "Did the declared temporal beats happen? Motion class is not the answer. "
        "FULL_MOTION is not required for PERFORMANCE."
    )
    observation["quality_rejudged_at"] = _utc_now()
    _atomic_write_json(out_dir / "OBSERVATION.json", observation)
    return {
        "rollout_id": rollout_id,
        "output_hash": observation.get("output_hash"),
        "quality": observation["quality"],
        "resee": False,
        "dispatch": False,
        "written": True,
    }


def _existing_presentation_path(quality: dict[str, Any], key: str) -> Path | None:
    row = quality.get(key) if isinstance(quality.get(key), dict) else {}
    path = Path(str(row.get("path") or ""))
    return path if path.is_file() else None


def complete_orphan_rollout(
    job_id: str,
    project_dir: Path,
    root: Path,
    rollout_id: str,
    *,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return complete_observation(
        job_id, project_dir, root, rollout_id, caller="prime", see_fn=see_fn
    )
