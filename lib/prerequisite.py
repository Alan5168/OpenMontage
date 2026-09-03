"""Production prerequisites. BLOCKED is not a cue to retry H3.

A character who must appear, and whose identity is canonical, cannot
be invented to make a pipeline green. Human A/B/NEITHER locks identity.
B1 (NONE) is a keyframe; B2 (PERFORMANCE) starts from that keyframe.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CHARACTER_ID = "lucien_mercer"
SCENE_ID = "scene_b"
KEYFRAME_SHOT = "B1"
MOTION_SHOT = "B2"
IDENTITY_MISSING = "character_identity_lock_missing"
PLAN_SCHEMA = "om-prerequisite-plan/v1"
CANDIDATE_SCHEMA = "om-identity-candidates/v1"
LOCK_SCHEMA = "om-character-identity-lock/v1"
KEYFRAME_SCHEMA = "om-keyframe-receipt/v1"

LUCIEN_PLATE_PROMPT = (
    "Character identity plate only, not a scene. 2D-animated 1990s cel TV anime, "
    "limited palette, clean lineart, flat fills. Bust-up of Lucien Mercer against a "
    "flat neutral studio grey. Adult man, tall presence, short dark hair, dead-still "
    "black eyes like two dry wells, scarred knuckles if hands enter frame. Simple dark "
    "work shirt or chef jacket, not an oversized hoodie. Front-on or mild 3/4, full head "
    "in frame. No kitchen, no range flame, no other character, no cinematic lighting hero "
    "shot, no text, no watermark, no photoreal person, no smile."
)
LUCIEN_PLATE_PROMPT_B = (
    "Character identity plate only, not a scene. 2D-animated 1990s cel TV anime, "
    "limited palette, clean lineart. Same man as Lucien Mercer: tall, scarred knuckles, "
    "dead-still dark eyes, deliberate economy. Mild 3/4 turn, bust-up, full head, "
    "neutral grey field. Not Avery. Not a kitchen establishing shot. No location, "
    "no backlight silhouette, no text."
)


class PrerequisiteError(ValueError):
    """Illegal prerequisite action."""


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


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def active_scene_proposal(project_dir: Path) -> dict[str, Any] | None:
    pointer = _read_json(project_dir / "working" / "prime_rlm" / "scene_proposals" / "CURRENT.json")
    if pointer and str(pointer.get("scene_id") or "").strip():
        payload = _read_json(
            project_dir / "working" / "prime_rlm" / "scene_proposals" / f"{pointer['scene_id']}.json"
        )
        if payload:
            return payload
    return _read_json(project_dir / "working" / "prime_rlm" / "scene_proposals" / "scene_b.json")


def lucien_lock_path(project_dir: Path) -> Path:
    return project_dir / "working" / "identity" / "LUCIEN_LOCK.json"


def lucien_sheet_path(project_dir: Path) -> Path:
    return project_dir / "bible" / "lucien" / "master_sheet.png"


def character_locked(project_dir: Path, character_id: str = CHARACTER_ID) -> bool:
    if character_id != CHARACTER_ID:
        return False
    receipt = _read_json(lucien_lock_path(project_dir))
    sheet = lucien_sheet_path(project_dir)
    return bool(
        receipt
        and receipt.get("locked") is True
        and receipt.get("character_id") == character_id
        and receipt.get("locked_by") in {"human", "pi"}
        and sheet.is_file()
    )


def identity_candidates(project_dir: Path, character_id: str = CHARACTER_ID) -> dict[str, Any] | None:
    return _read_json(
        project_dir / "working" / "prime_rlm" / "identity_candidates" / f"{character_id}.json"
    )


def identity_preference(project_dir: Path) -> dict[str, Any] | None:
    return _read_json(project_dir / "working" / "prime_rlm" / "IDENTITY_PREFERENCE.json")


def prerequisite_plan(project_dir: Path) -> dict[str, Any] | None:
    return _read_json(project_dir / "working" / "prime_rlm" / "PREREQUISITE_PLAN.json")


def b1_keyframe_path(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "keyframes" / "B1.png"


def diagnose_prerequisites(project_dir: Path) -> dict[str, Any]:
    proposal = active_scene_proposal(project_dir) or {}
    skeleton = _read_json(project_dir / "JOB_SKELETON.json") or {}
    scene_id = str(proposal.get("scene_id") or skeleton.get("scene_id") or "")
    status = str(skeleton.get("status") or "")
    project_id = str(skeleton.get("project_id") or "")
    if (
        scene_id in {"scene_showpiece", "scene_foreman", "scene_lights_out"}
        or status == "LIGHTS_OUT_SCENE_PROOF"
        or project_id == "vid-lights-out-scene-v1"
    ):
        return _diagnose_showpiece(project_dir, proposal)
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    b1 = next((row for row in shots if str(row.get("id")) == KEYFRAME_SHOT), None)
    b2 = next((row for row in shots if str(row.get("id")) == MOTION_SHOT), None)
    missing: list[str] = []
    if not character_locked(project_dir):
        missing.append("lucien_identity_lock")
    b1_still = b1_keyframe_path(project_dir)
    if not b1_still.is_file():
        missing.append("B1_keyframe")
    start_ref = (b2 or {}).get("start_frame_ref") if b2 else None
    start_ok = bool(start_ref) and (
        Path(str(start_ref)).is_file() or (project_dir / str(start_ref)).is_file()
    )
    if not start_ok:
        missing.append("B2_start_frame")
    root = missing[0] if missing else None
    return {
        "from_error": "canonical_start_ref_missing",
        "missing": missing,
        "root": root,
        "next_action": "RESOLVE_PREREQUISITE" if missing else "wait_human_redispatch",
        "do_not": ["retry_h3", "invent_lucien", "write_B2_png_by_hand"],
        "dependency_plan": [
            "lock_lucien_identity",
            "produce_B1_keyframe",
            "use_B1_as_B2_start_frame",
            "redispatch_B2",
        ],
        "b1_motion_obligation": (b1 or {}).get("motion_obligation") or "NONE",
        "b2_motion_obligation": (b2 or {}).get("motion_obligation") or "PERFORMANCE",
        "note": "B1 is NONE still. B2 is PERFORMANCE from B1. Identity is a human lock.",
    }


def _diagnose_showpiece(project_dir: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    missing: list[str] = []
    if not character_locked(project_dir):
        missing.append("lucien_identity_lock")
    first_perf = next(
        (row for row in shots if str(row.get("motion_obligation") or "").upper() == "PERFORMANCE"),
        None,
    )
    if first_perf is not None:
        sid = str(first_perf.get("id") or "")
        start = first_perf.get("start_frame_ref")
        start_ok = bool(start) and (
            Path(str(start)).is_file() or (project_dir / str(start)).is_file()
        )
        still = project_dir / "working" / "prime_rlm" / "start_frames" / f"{sid}.png"
        key = project_dir / "working" / "prime_rlm" / "keyframes" / f"{sid}.png"
        if not start_ok and not still.is_file() and not key.is_file():
            missing.append(f"{sid}_readable_start")
    root = missing[0] if missing else None
    return {
        "from_error": None,
        "missing": missing,
        "root": root,
        "next_action": "produce_keyframe" if missing else "dispatch_or_observe",
        "do_not": [
            "identity_relock",
            "unbounded_h3",
            "redispatch_vid3_b2",
            "cursor_impersonate_prime",
        ],
        "dependency_plan": [
            "inherit_locked_identities",
            "produce_readable_PERFORMANCE_start",
            "dispatch_first_PERFORMANCE",
            "quality_observation",
            "one_bounded_repair",
            "human_ab",
        ],
        "note": "Showpiece proof unit is the first PERFORMANCE cut. EST silhouette must not be its start still.",
    }


def submit_prerequisite_plan(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    from_rollout_id: str | None = None,
) -> dict[str, Any]:
    if caller != "prime":
        raise PrerequisiteError("submit_prerequisite_plan is a Prime production action")
    diagnosis = diagnose_prerequisites(project_dir)
    record = {
        "schema_version": PLAN_SCHEMA,
        "action": "submit_prerequisite_plan",
        "status": "PROPOSAL",
        "job_id": job_id,
        "caller": caller,
        "canonical_owner": "openmontage",
        "generate": False,
        "from_rollout_id": from_rollout_id,
        "next_action": "RESOLVE_PREREQUISITE",
        "missing": diagnosis["missing"],
        "root": diagnosis["root"],
        "dependency_plan": diagnosis["dependency_plan"],
        "do_not": diagnosis["do_not"],
        "created_at": _utc_now(),
        "note": "Not APPROVED. Not a retry. Do not dispatch H3 until the chain is satisfied.",
    }
    path = project_dir / "working" / "prime_rlm" / "PREREQUISITE_PLAN.json"
    _atomic_write_json(path, record)
    return {**record, "written": True, "path": _rel(path, root)}


def _still_providers() -> list[Any]:
    """Identity/keyframe stills. Cloud txt2img first. Flux2 is not required."""
    from tools.base_tool import ToolStatus
    from tools.graphics.comfyui_image import ComfyUIImage
    from tools.graphics.dashscope_image import DashscopeImage
    from tools.graphics.doubao_seedream import DoubaoSeedream

    providers = []
    for cls in (DoubaoSeedream, DashscopeImage, ComfyUIImage):
        tool = cls()
        if tool.get_status() == ToolStatus.AVAILABLE:
            providers.append(tool)
    return providers


def _invoke_image(inputs: dict[str, Any]) -> Any:
    from tools.base_tool import ToolResult

    errors: list[str] = []
    for tool in _still_providers():
        result = tool.execute(inputs)
        if getattr(result, "success", False):
            return result
        errors.append(f"{tool.name}: {getattr(result, 'error', None) or 'failed'}")
    return ToolResult(
        success=False,
        error="; ".join(errors) or "no still image provider is available",
    )


def propose_identity_candidates(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    character_id: str = CHARACTER_ID,
    generate: bool = True,
    invoke_image: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    if caller != "prime":
        raise PrerequisiteError("propose_identity_candidates is a Prime production action")
    if character_id != CHARACTER_ID:
        raise PrerequisiteError("this knife only bootstraps lucien_mercer")
    if character_locked(project_dir, character_id):
        raise PrerequisiteError("lucien_mercer is already identity-locked")
    out_dir = project_dir / "bible" / "lucien" / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = {"A": LUCIEN_PLATE_PROMPT, "B": LUCIEN_PLATE_PROMPT_B}
    invoke = invoke_image or _invoke_image
    rows = []
    for label, prompt in prompts.items():
        dest = out_dir / f"{label}.png"
        row: dict[str, Any] = {
            "id": label,
            "prompt": prompt,
            "path": _rel(dest, project_dir),
            "hash": None,
            "status": "spec_only",
            "error": None,
        }
        if generate:
            result = invoke(
                {
                    "prompt": prompt,
                    "width": 2048,
                    "height": 2048,
                    "seed": 11011 if label == "A" else 22022,
                    "watermark": False,
                    "output_path": str(dest),
                    "project_dir": str(project_dir),
                }
            )
            if getattr(result, "success", False) and dest.is_file():
                row["status"] = "candidate"
                row["hash"] = _sha256_file(dest)
            else:
                row["status"] = "generation_failed"
                row["error"] = getattr(result, "error", None) or "identity candidate image missing"
        rows.append(row)
    record = {
        "schema_version": CANDIDATE_SCHEMA,
        "action": "propose_identity_candidates",
        "status": "PROPOSAL",
        "job_id": job_id,
        "character_id": character_id,
        "caller": caller,
        "canonical_owner": "openmontage",
        "generate": False,
        "approved": False,
        "candidates": rows,
        "human_gate": "A / B / NEITHER",
        "target": f"identity:{character_id}",
        "created_at": _utc_now(),
        "note": "Identity candidates only. Prime cannot lock. Not Avery. Not a B2 start frame.",
    }
    path = project_dir / "working" / "prime_rlm" / "identity_candidates" / f"{character_id}.json"
    _atomic_write_json(path, record)
    return {**record, "written": True, "path": _rel(path, root)}


def apply_identity_preference(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    label: str,
    caller: str,
    target: str,
) -> dict[str, Any]:
    """Human A/B locks Lucien. NEITHER does not. Prime cannot call this with caller=prime."""
    if caller not in {"human", "pi"}:
        raise PrerequisiteError("character identity lock is Alan/Pi only")
    if target not in {f"identity:{CHARACTER_ID}", CHARACTER_ID, "lucien"}:
        raise PrerequisiteError("identity preference target must be identity:lucien_mercer")
    token = str(label or "").strip().upper()
    pref_path = project_dir / "working" / "prime_rlm" / "IDENTITY_PREFERENCE.json"
    pref = {
        "schema_version": "om-human-preference/v1",
        "action": "record_human_preference",
        "job_id": job_id,
        "label": token,
        "target": f"identity:{CHARACTER_ID}",
        "caller": caller,
        "canonical_owner": "openmontage",
        "promoted_to_hard_rule": False,
        "approved": False,
        "created_at": _utc_now(),
    }
    _atomic_write_json(pref_path, pref)
    if token == "NEITHER":
        return {**pref, "locked": False, "written": True, "path": _rel(pref_path, root)}
    if token not in {"A", "B"}:
        raise PrerequisiteError("identity preference must be A, B, or NEITHER")
    pack = identity_candidates(project_dir)
    if not pack:
        raise PrerequisiteError(
            "no Lucien identity candidates to lock. "
            "Prime must propose_identity_candidates first. Do not pick A/B blindly."
        )
    chosen = next((row for row in pack.get("candidates") or [] if row.get("id") == token), None)
    if not chosen:
        raise PrerequisiteError(f"candidate {token} missing")
    src = Path(str(chosen.get("path") or ""))
    if not src.is_file():
        src = project_dir / str(chosen.get("path") or "")
    if not src.is_file():
        src = root / str(chosen.get("path") or "")
    if not src.is_file():
        raise PrerequisiteError(f"candidate {token} has no image; cannot lock a missing Lucien")
    dest = lucien_sheet_path(project_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    avery = project_dir / "bible" / "avery" / "master_sheet.png"
    avery_hash = _sha256_file(avery) if avery.is_file() else None
    lock = {
        "schema_version": LOCK_SCHEMA,
        "action": "lock_character_identity",
        "character_id": CHARACTER_ID,
        "locked": True,
        "locked_by": caller,
        "candidate": token,
        "path": _rel(dest, root),
        "hash": _sha256_file(dest),
        "avery_master_sheet_untouched": True,
        "avery_hash": avery_hash,
        "job_id": job_id,
        "created_at": _utc_now(),
        "note": "Lucien identity only. Does not replace Avery. Does not APPROVE B2. Not a scene still.",
    }
    _atomic_write_json(lucien_lock_path(project_dir), lock)
    plan_path = project_dir / "artifacts" / "scene_plan.json"
    plan = _read_json(plan_path)
    if isinstance(plan, dict):
        meta = plan.setdefault("metadata", {})
        if isinstance(meta, dict):
            locks = meta.setdefault("character_identity_locks", {})
            if isinstance(locks, dict):
                locks[CHARACTER_ID] = {
                    "path": "bible/lucien/master_sheet.png",
                    "locked": True,
                    "locked_by": caller,
                    "candidate": token,
                }
            _atomic_write_json(plan_path, plan)
    return {**pref, "locked": True, "lock": lock, "written": True, "path": _rel(pref_path, root)}


def produce_keyframe(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    invoke_image: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    if caller != "prime":
        raise PrerequisiteError("produce_keyframe is a Prime production action")
    if shot_id == KEYFRAME_SHOT:
        return _produce_b1_keyframe(job_id, project_dir, root, invoke_image=invoke_image)
    return _produce_proposal_keyframe(
        job_id, shot_id, project_dir, root, invoke_image=invoke_image
    )


def _produce_b1_keyframe(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    invoke_image: Callable[[dict[str, Any]], Any] | None,
) -> dict[str, Any]:
    if not character_locked(project_dir):
        raise PrerequisiteError("B1 keyframe requires a locked Lucien identity")
    proposal_path = project_dir / "working" / "prime_rlm" / "scene_proposals" / f"{SCENE_ID}.json"
    proposal = _read_json(proposal_path)
    if not proposal:
        raise PrerequisiteError("scene_b proposal missing")
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    b1 = next((row for row in shots if str(row.get("id")) == KEYFRAME_SHOT), None)
    if b1 is None:
        raise PrerequisiteError("B1 is not on the scene_b proposal")
    obligation = str(b1.get("motion_obligation") or "").upper()
    if obligation not in {"NONE", ""}:
        raise PrerequisiteError("B1 must remain NONE; do not send the keyframe to H3")
    dest = b1_keyframe_path(project_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    plate = lucien_sheet_path(project_dir)
    prompt = (
        "2D-animated 1990s cel TV anime still, 16:9 landscape. Client back kitchen, "
        "wide establishing, grease smoke, range flame backlight. Lucien Mercer as a "
        "tall unhurried silhouette at the far end of the kitchen, holding still, "
        "watching. Same man as the locked identity plate. Intentional hold, no walk, "
        "no camera push, no other character. Limited animation key pose, not a video."
    )
    result = (invoke_image or _invoke_image)(
        {
            "prompt": prompt,
            "width": 1920,
            "height": 1080,
            "output_path": str(dest),
            "project_dir": str(project_dir),
            "reference_note": str(plate),
        }
    )
    if not dest.is_file():
        raise PrerequisiteError(
            getattr(result, "error", None) or "B1 keyframe image was not written"
        )
    rel = _rel(dest, project_dir)
    for row in shots:
        if str(row.get("id")) == KEYFRAME_SHOT:
            row["start_frame_ref"] = rel
            row["visual_ref"] = {"kind": "local_image", "path": rel}
        if str(row.get("id")) == MOTION_SHOT:
            row["start_frame_ref"] = rel
            row["start_state"] = "B1.final"
            row["requires_character_identity"] = CHARACTER_ID
            row["visual_ref"] = {"kind": "local_image", "path": rel}
    proposal["shots"] = shots
    _atomic_write_json(proposal_path, proposal)
    request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / "B2.json"
    request = _read_json(request_path)
    if request:
        shot_ref = request.setdefault("shot_ref", {})
        if isinstance(shot_ref, dict):
            shot_ref["scene_plan_hash"] = _sha256_file(proposal_path)
            shot_ref["start_frame_ref"] = rel
            shot_ref["start_state"] = "B1.final"
        request["generate"] = False
        request["status"] = "PROPOSAL"
        _atomic_write_json(request_path, request)
    receipt = {
        "schema_version": KEYFRAME_SCHEMA,
        "action": "produce_keyframe",
        "status": "PROPOSAL",
        "job_id": job_id,
        "shot_id": KEYFRAME_SHOT,
        "motion_obligation": "NONE",
        "renderer": "image_keyframe",
        "h3": False,
        "path": rel,
        "hash": _sha256_file(dest),
        "bound_to": MOTION_SHOT,
        "lucien_identity_hash": _sha256_file(plate),
        "human_approved": False,
        "canonical_start_ref": True,
        "validation": {
            "media_valid": dest.is_file() and dest.stat().st_size > 32,
            "identity_lock_present": True,
            "shot_contract": "B1 NONE still",
            "human_gate": False,
        },
        "generate": False,
        "created_at": _utc_now(),
        "note": "B1 NONE keyframe is B2 start_frame_ref. Not H3. Not APPROVED. Do not auto-dispatch B2.",
    }
    receipt_path = project_dir / "working" / "prime_rlm" / "keyframes" / "B1_RECEIPT.json"
    _atomic_write_json(receipt_path, receipt)
    return {**receipt, "written": True, "receipt_path": _rel(receipt_path, root)}


def _produce_proposal_keyframe(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    invoke_image: Callable[[dict[str, Any]], Any] | None,
) -> dict[str, Any]:
    proposal = active_scene_proposal(project_dir)
    if not proposal:
        raise PrerequisiteError("scene proposal missing")
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    shot = next((row for row in shots if str(row.get("id")) == shot_id), None)
    if shot is None:
        raise PrerequisiteError(f"shot {shot_id} is not on the current scene proposal")
    ids = [str(x) for x in (shot.get("character_ids") or [])]
    if CHARACTER_ID in ids and not character_locked(project_dir):
        raise PrerequisiteError("PERFORMANCE/character still requires a locked Lucien identity")
    dest = project_dir / "working" / "prime_rlm" / "keyframes" / f"{shot_id}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    plate = lucien_sheet_path(project_dir)
    if "avery_sterling" in ids:
        avery = project_dir / "bible" / "avery" / "master_sheet.png"
        if avery.is_file():
            plate = avery
    intent = str(shot.get("visual_intent") or shot.get("performance_intent") or "").strip()
    obligation = str(shot.get("motion_obligation") or "").upper()
    silhouette_ok = obligation in {"NONE", ""}
    prompt = (
        "2D-animated 1990s cel TV anime still, 16:9 landscape. "
        f"{intent} "
        "Match the locked identity plate. "
    )
    if not silhouette_ok:
        prompt += (
            "Face, costume, and body structure must be readable. "
            "Not a far silhouette. Not a video. No text, no watermark."
        )
    else:
        prompt += "Intentional hold. Not a video. No text."
    result = (invoke_image or _invoke_image)(
        {
            "prompt": prompt.strip(),
            "width": 1920,
            "height": 1080,
            "output_path": str(dest),
            "project_dir": str(project_dir),
            "reference_note": str(plate) if plate.is_file() else "",
        }
    )
    if not dest.is_file():
        raise PrerequisiteError(getattr(result, "error", None) or f"{shot_id} keyframe was not written")
    from lib.keyframe_presentation import evaluate_keyframe_presentation

    framing = "medium_close"
    if "insert" in intent.lower():
        framing = "insert"
    elif any(token in intent.lower() for token in ("wide", "est", "full body", "full-body")):
        framing = "full_body"
    presentation = evaluate_keyframe_presentation(dest, framing=framing)
    receipt_path = project_dir / "working" / "prime_rlm" / "keyframes" / f"{shot_id}_RECEIPT.json"
    rel = _rel(dest, project_dir)
    if obligation == "PERFORMANCE" and presentation.get("usable") is not True:
        receipt = {
            "schema_version": KEYFRAME_SCHEMA,
            "action": "produce_keyframe",
            "status": "blocked",
            "job_id": job_id,
            "shot_id": shot_id,
            "h3": False,
            "path": rel,
            "hash": _sha256_file(dest),
            "human_approved": False,
            "canonical_start_ref": False,
            "keyframe_presentation": presentation,
            "error": "keyframe_presentation_unusable",
            "generate": False,
            "created_at": _utc_now(),
            "note": "PERFORMANCE start still failed presentation. Do not dispatch H3. Retry the still, do not bind a silhouette.",
        }
        _atomic_write_json(receipt_path, receipt)
        return {**receipt, "written": True, "receipt_path": _rel(receipt_path, root)}
    start_copy = project_dir / "working" / "prime_rlm" / "start_frames" / f"{shot_id}.png"
    start_copy.parent.mkdir(parents=True, exist_ok=True)
    if start_copy.resolve() != dest.resolve():
        shutil.copy2(dest, start_copy)
    for row in shots:
        if str(row.get("id")) == shot_id:
            row["start_frame_ref"] = rel
            row["visual_ref"] = {"kind": "local_image", "path": rel}
    proposal["shots"] = shots
    proposal_path = (
        project_dir
        / "working"
        / "prime_rlm"
        / "scene_proposals"
        / f"{proposal.get('scene_id')}.json"
    )
    _atomic_write_json(proposal_path, proposal)
    request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
    request = _read_json(request_path)
    if request:
        shot_ref = request.setdefault("shot_ref", {})
        if isinstance(shot_ref, dict):
            shot_ref["scene_plan_hash"] = _sha256_file(proposal_path)
            shot_ref["start_frame_ref"] = rel
        request["generate"] = False
        request["status"] = "PROPOSAL"
        _atomic_write_json(request_path, request)
    receipt = {
        "schema_version": KEYFRAME_SCHEMA,
        "action": "produce_keyframe",
        "status": "PROPOSAL",
        "job_id": job_id,
        "shot_id": shot_id,
        "motion_obligation": obligation or "NONE",
        "renderer": "image_keyframe",
        "h3": False,
        "path": rel,
        "hash": _sha256_file(dest),
        "bound_to": shot_id,
        "human_approved": False,
        "canonical_start_ref": True,
        "keyframe_presentation": {
            "usable": presentation.get("usable"),
            "blockers": presentation.get("blockers"),
        },
        "generate": False,
        "created_at": _utc_now(),
        "note": "Start still only. Not H3. Not APPROVED. PERFORMANCE stills must stay readable.",
    }
    _atomic_write_json(receipt_path, receipt)
    return {**receipt, "written": True, "receipt_path": _rel(receipt_path, root)}
