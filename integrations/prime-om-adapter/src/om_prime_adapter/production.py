"""Production world for Prime TUI. OM remains canonical; Prime only proposes."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.dispatch_cut import (
    DispatchError,
    complete_observation as om_complete_observation,
    dispatch_cut as om_dispatch_cut,
    job_frozen,
    latest_rollout,
    proven_status,
    _start_frame,
)
from lib.bounded_repair import (
    RepairError,
    child_repairs,
    dispatch_bounded_repair as om_dispatch_bounded_repair,
    propose_bounded_repair as om_propose_bounded_repair,
)
from lib.compose_scene import (
    ComposeError,
    compose_scene as om_compose_scene,
    review_queue_path,
)
from lib.scene_revision import (
    REVISE_SCENE,
    REVISE_STATUS,
    RevisionError,
    SHOT_ORDER as REVISE_SHOT_ORDER,
    active_revision,
    is_revise_skeleton,
    revision_rollout,
    validate_revision_proposal,
    write_revision,
)
from lib.keyframe_presentation import evaluate_keyframe_presentation
from lib.motion_obligation import ShotCompileError, compile_cut as compile_shot
from lib.motion_router import MotionRouterError, assert_transition
from lib.prerequisite import (
    CHARACTER_ID,
    PrerequisiteError,
    active_scene_proposal,
    apply_identity_preference,
    b1_keyframe_path,
    character_locked,
    diagnose_prerequisites,
    identity_candidates,
    identity_preference,
    produce_keyframe as om_produce_keyframe,
    propose_identity_candidates as om_propose_identity_candidates,
    prerequisite_plan,
    submit_prerequisite_plan as om_submit_prerequisite_plan,
)

from .security import AdapterError, display_rel, scan_secrets

PROPOSAL_SCHEMA = "om-execution-proposal/v1"
WORLD_SCHEMA = "om-production-world/v1"
SCENE_PROPOSAL_SCHEMA = "om-scene-proposal/v1"
HUMAN_PREF_SCHEMA = "om-human-preference/v1"
HUMAN_PREF_LABELS = frozenset(
    {
        "A",
        "B",
        "NEITHER",
        "KEEP_WATCHING",
        "STOP",
        "REVISE",
        "CONTINUE_SCENE",
        "ABANDON_SCENE",
        "SHIP",
        "DO_NOT_SHIP",
    }
)
STORY_REF_CANDIDATES = (
    ("working/source/episode_01.md", "episode_script"),
    ("working/source/episode_01.json", "episode_script_json"),
    ("working/source/series_bible.md", "series_bible"),
    ("working/source/episode_table.md", "episode_table"),
    ("working/source/SHOWPIECE_INTENT.md", "showpiece_intent"),
    ("working/source/FOREMAN_INTENT.md", "foreman_intent"),
    ("working/source/LIGHTS_OUT_INTENT.md", "lights_out_intent"),
    ("working/source/REVISE_INTENT.md", "revise_intent"),
    ("working/scene_a/SCENE_INTENT.md", "prior_scene_intent"),
    ("working/scene_a/HOUSE_RULES_COLD_OPEN.json", "house_rules"),
    ("working/corpus/SCENE_A_CORPUS.json", "corpus"),
)
RECEIPT_GLOBS = (
    "working/scene_a/*RECEIPT.json",
    "working/scene_a/**/*RECEIPT.json",
    "working/prime_rlm/execution_requests/*.json",
    "working/prime_rlm/rollouts/*/RECEIPT.json",
)
SEE_NAMES = (
    "temporal_motion_report.json",
    "limited_grammar_report.json",
    "audio_event_map.json",
    "frame_packet.json",
    "scene_eligibility.json",
)


def _atomic_write_json(path: Path, value: dict[str, Any] | list[Any]) -> None:
    scan_secrets(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_if(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _meta(path: Path, root: Path, *, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": display_rel(path, root),
        "hash": _sha256_file(path) if path.is_file() else None,
        "bytes": path.stat().st_size if path.is_file() else 0,
        "loaded_at": _utc_now(),
    }


def scene_plan_path(project_dir: Path) -> Path | None:
    for candidate in (
        project_dir / "artifacts" / "scene_plan.json",
        project_dir / "scene_plan.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def load_scene_plan(project_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    path = scene_plan_path(project_dir)
    if path is None:
        return None, None
    plan = _read_json_if(path)
    return path, plan


def _shot_slice(scene: dict[str, Any]) -> dict[str, Any]:
    compiled = None
    compile_error = None
    try:
        compiled = compile_shot(scene)
    except ShotCompileError as exc:
        compile_error = str(exc)
    return {
        "id": scene.get("id"),
        "visual_intent": scene.get("visual_intent") or scene.get("description"),
        "performance_intent": scene.get("performance_intent"),
        "animation_class": scene.get("animation_class"),
        "motion_obligation": (compiled or {}).get("motion_obligation") or scene.get("motion_obligation"),
        "review_decision": scene.get("review_decision"),
        "character_ids": scene.get("character_ids") or [],
        "renderer": scene.get("renderer"),
        "start_frame_ref": scene.get("start_frame_ref"),
        "compile_preview": compiled,
        "compile_error": compile_error,
    }


def _identity(project_dir: Path, plan: dict[str, Any] | None, root: Path) -> dict[str, Any]:
    meta = (plan or {}).get("metadata") if isinstance((plan or {}).get("metadata"), dict) else {}
    sheet = meta.get("master_sheet_path") or "bible/avery/master_sheet.png"
    raw = Path(str(sheet))
    candidates = [raw, project_dir / raw] if not raw.is_absolute() else [raw]
    existing = next((p for p in candidates if p.is_file()), None)
    return {
        "character": meta.get("master_sheet_character") or "avery_sterling",
        "locked": bool(meta.get("master_sheet_locked")),
        "path": str(sheet),
        "exists": existing is not None,
        "hash": _meta(existing, root, kind="identity")["hash"] if existing else None,
    }


def _openviking_pointers(job_id: str, root: Path) -> dict[str, Any]:
    ctx = root / "context" / "openviking" / "content-studio"
    if not ctx.is_dir():
        return {
            "available": False,
            "pointers": [],
            "invented": False,
            "note": "OpenViking context dir missing; pointers not invented",
        }
    needles = [job_id.lower(), "scene-a", "blacklisted-chef", "house-rules"]
    pointers: list[dict[str, Any]] = []
    try:
        files = sorted(ctx.rglob("*"))
    except OSError:
        files = []
    for path in files:
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".mp4", ".wav", ".webp"}:
            continue
        hay = path.as_posix().lower()
        if not any(n in hay for n in needles):
            continue
        try:
            rel = path.relative_to(ctx).as_posix()
        except ValueError:
            continue
        pointers.append(
            {
                "path": display_rel(path, root),
                "uri": f"viking://resources/content-studio/{rel}",
            }
        )
        if len(pointers) >= 12:
            break
    return {
        "available": True,
        "pointers": pointers,
        "invented": False,
        "note": None if pointers else "No matching OpenViking files; none invented",
    }


def _observations(project_dir: Path, root: Path) -> list[dict[str, Any]]:
    rows = []
    see_dir = project_dir / "working" / "scene_a" / "see"
    for name in SEE_NAMES:
        path = see_dir / name
        if path.is_file():
            rows.append(_meta(path, root, kind="observation"))
    rollouts = project_dir / "working" / "prime_rlm" / "rollouts"
    if rollouts.is_dir():
        for path in sorted(rollouts.glob("*/OBSERVATION.json")):
            rows.append(_meta(path, root, kind="observation"))
            if len(rows) >= 24:
                break
    return rows


def _rollouts(project_dir: Path, root: Path) -> list[dict[str, Any]]:
    rows = []
    seen: set[Path] = set()
    for pattern in RECEIPT_GLOBS:
        for path in project_dir.glob(pattern):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            rows.append(_meta(path, root, kind="rollout_receipt"))
            if len(rows) >= 24:
                return rows
    return rows


def _story_refs(project_dir: Path, root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel, kind in STORY_REF_CANDIDATES:
        path = project_dir / rel
        if path.is_file():
            rows.append(_meta(path, root, kind=kind))
    return rows


def _proposal_dir(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "scene_proposals"


def _current_scene_proposal(project_dir: Path) -> dict[str, Any] | None:
    return active_scene_proposal(project_dir)


def _skeleton_scene_id(project_dir: Path) -> str | None:
    skeleton = _read_json_if(project_dir / "JOB_SKELETON.json") or {}
    scene_id = str(skeleton.get("scene_id") or "").strip()
    return scene_id or None


def _preference_target(project_dir: Path, target: str | None) -> str | None:
    if target:
        return str(target)
    proposal = _current_scene_proposal(project_dir) or {}
    scene_id = str(proposal.get("scene_id") or "").strip()
    return scene_id or _skeleton_scene_id(project_dir)


def _latest_human_preference(project_dir: Path, *, target: str | None = None) -> dict[str, Any] | None:
    latest = _read_json_if(project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json")
    if latest and target and latest.get("target") not in {target, f"scene:{target}"}:
        return None
    return latest


SHOWPIECE_STATUSES = frozenset({"SHOWPIECE_DESIGNED", "PRIME_FOREMAN_PROOF", "PRIME_FOREMAN_PROVEN"})
SHOWPIECE_SCENE = "scene_showpiece"
FOREMAN_SCENE = "scene_foreman"
LIGHTS_OUT_STATUS = "LIGHTS_OUT_SCENE_PROOF"
LIGHTS_OUT_SCENE = "scene_lights_out"
LIGHTS_OUT_JOB = "vid-lights-out-scene-v1"
LIGHTS_OUT_SHOT_ORDER = ("S1", "S2", "S3", "S4")
LIGHTS_OUT_H3_SHOT = "S2"
REVISE_H3_SHOT = "S2"
SCENE_REVIEW_LABELS = frozenset({"KEEP_WATCHING", "SHIP", "DO_NOT_SHIP", "REVISE"})
SHOWPIECE_DO_NOT = [
    "S3",
    "S4",
    "S5",
    "S6",
    "AI_NATIVE_LIMITED_ANIME_STUDIO_V1",
    "continue_demo_in_this_job",
]


def _continued(project_dir: Path, scene_id: str) -> bool:
    pref = _latest_human_preference(project_dir, target=scene_id)
    return bool(pref) and pref.get("label") == "CONTINUE_SCENE"


def _revised(project_dir: Path, scene_id: str) -> bool:
    pref = _latest_human_preference(project_dir, target=scene_id)
    return bool(pref) and pref.get("label") == "REVISE"


def _is_revise(skeleton: dict[str, Any], proposal: dict[str, Any] | None) -> bool:
    return is_revise_skeleton(skeleton, proposal)


def _cut_gate_ok(
    project_dir: Path,
    scene_id: str,
    skeleton: dict[str, Any],
    proposal: dict[str, Any] | None,
) -> bool:
    if _is_revise(skeleton, proposal):
        return _revised(project_dir, scene_id or REVISE_SCENE)
    return _continued(project_dir, scene_id)


def _is_lights_out(skeleton: dict[str, Any], proposal: dict[str, Any] | None) -> bool:
    if _is_revise(skeleton, proposal):
        return False
    status = str((skeleton or {}).get("status") or "")
    scene_id = str(
        (proposal or {}).get("scene_id")
        or (skeleton or {}).get("scene_id")
        or ""
    )
    project_id = str((skeleton or {}).get("project_id") or "")
    return (
        status == LIGHTS_OUT_STATUS
        or scene_id == LIGHTS_OUT_SCENE
        or project_id == LIGHTS_OUT_JOB
    )


def _is_showpiece(skeleton: dict[str, Any], proposal: dict[str, Any] | None) -> bool:
    if _is_lights_out(skeleton, proposal) or _is_revise(skeleton, proposal):
        return False
    status = str((skeleton or {}).get("status") or "")
    scene_id = str((proposal or {}).get("scene_id") or "")
    return status in SHOWPIECE_STATUSES or scene_id in {SHOWPIECE_SCENE, FOREMAN_SCENE}


def _ab_pair_path(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "AB_PAIR.json"


def _read_ab_pair(project_dir: Path) -> dict[str, Any] | None:
    return _read_json_if(_ab_pair_path(project_dir))


def _freeze_showpiece(
    project_dir: Path,
    *,
    reason: str,
    proven_status_value: str,
    foreman_proven: bool,
    summary: str,
) -> dict[str, Any]:
    existing = job_frozen(project_dir)
    if existing:
        return existing
    freeze = {
        "schema_version": "om-job-freeze/v1",
        "frozen": True,
        "reason": reason,
        "proven_status": proven_status_value,
        "foreman_proven": foreman_proven,
        "studio_v1": False,
        "do_not": list(SHOWPIECE_DO_NOT),
        "return_to": "new_production_job_for_20_30s_demo",
        "created_at": _utc_now(),
        "note": summary,
    }
    _atomic_write_json(project_dir / "working" / "prime_rlm" / "JOB_FREEZE.json", freeze)
    if foreman_proven:
        _atomic_write_json(
            project_dir / "working" / "prime_rlm" / "PROVEN_STATUS.json",
            {
                "schema_version": "om-proven-status/v1",
                "proven_status": "PRIME_FOREMAN_PROVEN",
                "foreman_proven": True,
                "studio_v1": False,
                "created_at": _utc_now(),
                "note": summary,
            },
        )
    skeleton_path = project_dir / "JOB_SKELETON.json"
    skeleton = _read_json_if(skeleton_path) or {}
    if skeleton:
        skeleton["frozen"] = True
        skeleton["foreman_proven"] = foreman_proven
        skeleton["studio_v1"] = False
        if foreman_proven:
            skeleton["status"] = "PRIME_FOREMAN_PROVEN"
        skeleton["waiting_on"] = [
            summary,
            "Do not stamp AI_NATIVE_LIMITED_ANIME_STUDIO_V1.",
            "Do not continue S3-S6 in this job.",
        ]
        _atomic_write_json(skeleton_path, skeleton)
    return freeze


def _original_rollout(project_dir: Path, shot_id: str) -> dict[str, Any] | None:
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return None
    receipts = sorted(root.glob("*/RECEIPT.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in receipts:
        row = _read_json_if(path)
        if row and row.get("shot_id") == shot_id and not row.get("parent_rollout_id"):
            return row
    return None


def _ab_wait_step(
    project_dir: Path,
    *,
    scene_id: str,
    waiting: list[str],
    shot_id: str | None,
) -> dict[str, Any]:
    pair = _read_ab_pair(project_dir) or {}
    return {
        "action": "wait_human_preference",
        "summary": (
            "A = original S2 rollout. B = the single repaired S2 rollout. "
            "Each side carries rollout_id, output hash, Observation summary, "
            "and B's changed repair dimension. Alan: A / B / NEITHER. "
            "Do not rename candidates. Do not draw again."
        ),
        "scene_id": scene_id,
        "shot_id": shot_id or pair.get("shot_id"),
        "target": pair.get("target") or f"ab:{shot_id or 'S2'}",
        "ab_pair": pair or None,
        "A": pair.get("A"),
        "B": pair.get("B"),
        "foreman_proven": False,
        "studio_v1": False,
        "ship": False,
        "waiting_on": waiting,
    }


def _next_step_frozen(
    freeze: dict[str, Any],
    project_dir: Path,
    waiting: list[str],
) -> dict[str, Any]:
    reason = str(freeze.get("reason") or "")
    proven = proven_status(project_dir)
    if reason == "temporal_beat_realization_unresolved":
        return {
            "action": "temporal_beat_realization_unresolved",
            "summary": (
                "NO_VALID_BLOCKER_FROM_CURRENT_RULE; TEMPORAL_BEAT_REALIZATION_UNRESOLVED. "
                "PRIME_FOREMAN_PROOF is PAUSED / UNRESOLVED, not FAILED. "
                "Do not touch this S2. Do not invent FIRST_TAKE_ACCEPTABLE. "
                "Do not spend bounded repair. Do not build an eye classifier. "
                "Do not stamp PRIME_FOREMAN_PROVEN. Do not run S3-S6."
            ),
            "first_take_acceptable": False,
            "content_fail": False,
            "foreman_proven": False,
            "studio_v1": False,
            "proven_status": proven,
            "repair_quota_used": False,
            "ship": False,
            "waiting_on": waiting,
        }
    if reason == "first_take_acceptable":
        return {
            "action": "first_take_acceptable",
            "summary": (
                "First S2 take has no real contract blocker. Do not invent one. "
                "FIRST_TAKE_ACCEPTABLE. This job has not proven bounded repair. "
                "Do not stamp PRIME_FOREMAN_PROVEN. Job is frozen. Do not run S3-S6. "
                "Do not stamp AI_NATIVE_LIMITED_ANIME_STUDIO_V1."
            ),
            "foreman_proven": False,
            "studio_v1": False,
            "proven_status": proven,
            "ship": False,
            "waiting_on": waiting,
        }
    if reason == "prime_foreman_proven":
        return {
            "action": "return_to_content_production",
            "summary": (
                "Alan chose B. PRIME_FOREMAN_PROOF is satisfied. Job is frozen. "
                "Do not run S3-S6 here. A 20-30s edited/sounded demo is a new production job. "
                "Do not stamp AI_NATIVE_LIMITED_ANIME_STUDIO_V1."
            ),
            "foreman_proven": True,
            "studio_v1": False,
            "proven_status": proven,
            "ship": False,
            "waiting_on": waiting,
        }
    if reason in {"repair_did_not_improve", "capability_miss"}:
        return {
            "action": "stop_showpiece_proof_miss",
            "summary": str(
                freeze.get("note")
                or (
                    "Repair A/B did not satisfy PRIME_FOREMAN_PROOF. Job is frozen. "
                    "Do not manufacture another failure. Do not run S3-S6."
                )
            ),
            "foreman_proven": False,
            "studio_v1": False,
            "reason": reason,
            "proven_status": proven,
            "ship": False,
            "waiting_on": waiting,
        }
    if reason == "lights_out_execution_proven":
        return {
            "action": "lights_out_execution_proven",
            "summary": (
                "Lights-out execution is proven. Job is frozen. "
                "Do not polish S3/S4. Do not redispatch S2 H3. "
                "REVISE is evidence for vid-scene-revise-v1, not more generation here. "
                "Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN."
            ),
            "foreman_proven": False,
            "studio_v1": False,
            "proven_status": proven,
            "lights_out_scene_production_proven": False,
            "ship": False,
            "waiting_on": waiting,
        }
    if reason in {"scene_revision_routing_proven", "revision_propagation_proven"}:
        return {
            "action": "scene_revision_routing_proven",
            "summary": (
                "SCENE_REVISION_ROUTING_PROVEN. REVISE entered OM, Prime named S3/S4, "
                "S1/S2 H3 stayed on parent hashes, scene_v2 has a new hash and parent provenance. "
                "SCENE_REVISION_EFFECTIVENESS is NOT proven: V2 still-hold did not address "
                "'stills look bad / pot smoke does not rise'. "
                "new hash ≠ useful revision. rerendered cut ≠ feedback addressed. "
                "affected_shots correct ≠ repair correct. Job frozen. Do not polish this fixture. "
                "Do not stamp SCENE_REVISION_EFFECTIVENESS_PROVEN."
            ),
            "foreman_proven": False,
            "studio_v1": False,
            "proven_status": proven,
            "scene_revision_routing_proven": True,
            "scene_revision_effectiveness_proven": False,
            "ship": False,
            "waiting_on": waiting,
        }
    return {
        "action": "return_to_harness",
        "summary": (
            "B2 dispatch is proven. Job is frozen. Do not continue B3/B4/B5. "
            "Return to harness backlog. Do not polish the demo."
        ),
        "proven_status": proven,
        "ship": False,
        "waiting_on": waiting,
    }


def _next_step_showpiece(
    *,
    project_dir: Path,
    skeleton: dict[str, Any],
    proposal: dict[str, Any] | None,
    pref: dict[str, Any] | None,
) -> dict[str, Any]:
    proof_unit = str((skeleton or {}).get("proof_unit") or "S2")
    waiting = [
        f"PRIME_FOREMAN_PROOF on this job, proof_unit {proof_unit} only.",
        "No valid evidence → no quality verdict. Incomplete Observation is not FIRST_TAKE_ACCEPTABLE.",
        "PERFORMANCE does not require FULL_MOTION. Judge declared temporal beats.",
        "Missing beat probes are unresolved, not FIRST_TAKE_ACCEPTABLE and not a repair.",
        "Do not invent a blocker. Do not stamp PRIME_FOREMAN_PROVEN from tests or Cursor.",
        "Do not stamp AI_NATIVE_LIMITED_ANIME_STUDIO_V1.",
    ]
    scene_id = str(
        (proposal or {}).get("scene_id")
        or (skeleton or {}).get("scene_id")
        or SHOWPIECE_SCENE
    )
    shots = [row for row in ((proposal or {}).get("shots") or []) if isinstance(row, dict)]
    if not pref or pref.get("label") not in HUMAN_PREF_LABELS:
        return {
            "action": "wait_human_preference",
            "summary": f"Waiting. Alan: CONTINUE_SCENE / STOP / REVISE on {scene_id}.",
            "scene_id": scene_id,
            "shot_id": proof_unit,
            "ship": False,
            "waiting_on": waiting,
        }
    if pref.get("label") in {"STOP", "REVISE", "ABANDON_SCENE"}:
        return {
            "action": "revise_or_stop",
            "summary": f"HumanPreference {pref.get('label')}. Do not keep generating.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if pref.get("label") in {"A", "B", "NEITHER"}:
        pair = _read_ab_pair(project_dir)
        label = str(pref.get("label"))
        if pair and not job_frozen(project_dir):
            if label == "B":
                _freeze_showpiece(
                    project_dir,
                    reason="prime_foreman_proven",
                    proven_status_value="PRIME_FOREMAN_PROVEN",
                    foreman_proven=True,
                    summary="Alan chose B. Autonomous repair improved preference.",
                )
            elif label == "A":
                _freeze_showpiece(
                    project_dir,
                    reason="repair_did_not_improve",
                    proven_status_value="PRIME_FOREMAN_PROOF",
                    foreman_proven=False,
                    summary="Alan chose A. Repair did not improve preference. Proof is not satisfied.",
                )
            else:
                _freeze_showpiece(
                    project_dir,
                    reason="capability_miss",
                    proven_status_value="PRIME_FOREMAN_PROOF",
                    foreman_proven=False,
                    summary="Alan chose NEITHER. Record the missing capability. Stop.",
                )
            freeze = job_frozen(project_dir)
            if freeze:
                return _next_step_frozen(freeze, project_dir, waiting)
        return {
            "action": "stop_showpiece_ab_recorded",
            "summary": (
                "Alan recorded A/B/NEITHER without a locked original-vs-repair pair. "
                "That does not stamp PRIME_FOREMAN_PROVEN."
            ),
            "scene_id": scene_id,
            "label": pref.get("label"),
            "target": pref.get("target"),
            "foreman_proven": False,
            "studio_v1": False,
            "ship": False,
            "waiting_on": waiting,
        }
    if pref.get("label") != "CONTINUE_SCENE":
        return {
            "action": "wait_human_preference",
            "summary": f"HumanPreference {pref.get('label')} recorded. Not APPROVED.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if not shots:
        return {
            "action": "submit_scene_proposal",
            "summary": (
                "CONTINUE_SCENE. Prime may re-own the scene proposal "
                f"(caller=prime, generate=false), then only execute {proof_unit}."
            ),
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }

    repair_root = project_dir / "working" / "prime_rlm" / "repairs"
    for receipt in (
        (project_dir / "working" / "prime_rlm" / "rollouts").glob("*/RECEIPT.json")
        if (project_dir / "working" / "prime_rlm" / "rollouts").is_dir()
        else []
    ):
        row = _read_json_if(receipt)
        if row and row.get("awaiting_human_ab") is True:
            return _ab_wait_step(
                project_dir,
                scene_id=scene_id,
                waiting=waiting,
                shot_id=str(row.get("shot_id") or ""),
            )

    performance = [
        row
        for row in shots
        if str(row.get("motion_obligation") or "").upper() == "PERFORMANCE"
    ]
    wanted = str((skeleton or {}).get("proof_unit") or "S2")
    proof_shot = next((row for row in performance if str(row.get("id") or "") == wanted), None)
    if proof_shot is None:
        proof_shot = performance[0] if performance else None
    if proof_shot is None:
        return {
            "action": "repair_shot_contract",
            "summary": "Showpiece has no PERFORMANCE cut. That is a directing miss, not an H3 miss.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    shot_id = str(proof_shot.get("id") or "")
    request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
    rollout = _original_rollout(project_dir, shot_id) or latest_rollout(project_dir, shot_id)
    if rollout and rollout.get("status") in {"succeeded", "failed"}:
        obs_path = (
            project_dir
            / "working"
            / "prime_rlm"
            / "rollouts"
            / str(rollout.get("rollout_id") or "")
            / "OBSERVATION.json"
        )
        obs = _read_json_if(obs_path) or rollout.get("observation") or {}
        quality = obs.get("quality") or {}
        parent_id = str(rollout.get("rollout_id") or "")
        mp4_path = (
            project_dir / "working" / "prime_rlm" / "rollouts" / parent_id / f"{shot_id}.mp4"
        )
        if "passed" not in quality:
            if rollout.get("output_hash") or mp4_path.is_file():
                return {
                    "action": "observation_incomplete",
                    "bind_tool": "complete_observation",
                    "summary": (
                        "OBSERVATION_INCOMPLETE. No valid evidence → no quality verdict. "
                        "Incomplete Observation is not FIRST_TAKE_ACCEPTABLE and not content FAIL. "
                        f"Rebind SEE onto the same output hash {rollout.get('output_hash') or '(disk)'}. "
                        "Do not dispatch_cut. Do not produce_keyframe. Do not spend bounded repair on the observer."
                    ),
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "rollout_id": parent_id,
                    "output_hash": rollout.get("output_hash"),
                    "first_take_acceptable": False,
                    "content_fail": False,
                    "quality_verdict": None,
                    "ship": False,
                    "waiting_on": waiting,
                }
            return {
                "action": "report_rollout_failed",
                "summary": (
                    "S2 rollout has no Observation and no mp4. Do not invent a blocker. "
                    "Do not draw a second take unless OM says the first never landed."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "rollout_id": parent_id,
                "error": rollout.get("error"),
                "ship": False,
                "waiting_on": waiting,
            }
        children = child_repairs(project_dir, parent_id)
        repair_proposal = _read_json_if(repair_root / f"{parent_id}.json")
        if children:
            return _ab_wait_step(
                project_dir,
                scene_id=scene_id,
                waiting=waiting,
                shot_id=shot_id,
            )
        if repair_proposal and repair_proposal.get("status") == "PROPOSAL":
            action = str(repair_proposal.get("action") or "")
            if action in {"prompt", "temporal_reference"}:
                return {
                    "action": "dispatch_bounded_repair",
                    "summary": (
                        "Prime proposed one legal repair. Dispatch that reroll once. "
                        "Then A = original, B = that repair. Stop."
                    ),
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "parent_rollout_id": parent_id,
                    "repair_action": action,
                    "ship": False,
                    "waiting_on": waiting,
                }
            if action == "keyframe":
                return {
                    "action": "produce_keyframe",
                    "summary": "Repair is keyframe. Produce a readable PERFORMANCE start still. Do not H3 the silhouette.",
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "parent_rollout_id": parent_id,
                    "ship": False,
                    "waiting_on": waiting,
                }
        blockers = [
            blocker
            for blocker in (quality.get("blockers") or [])
            if blocker != "performance_not_full_motion"
        ]
        if blockers:
            return {
                "action": "propose_bounded_repair",
                "summary": (
                    "Observation named a real contract blocker. Propose exactly one legal repair, "
                    "dispatch it once, then A = original vs B = that repair. Do not invent extras. "
                    "Do not repair by increasing overall motion. Repair the missed beat."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "rollout_id": parent_id,
                "blockers": blockers,
                "ship": False,
                "waiting_on": waiting,
            }
        if (
            quality.get("beat_realization_unresolved")
            or "TEMPORAL_BEAT_REALIZATION_UNRESOLVED" in str(quality.get("verdict") or "")
            or "performance_not_full_motion" in (quality.get("blockers") or [])
        ):
            return {
                "action": "temporal_beat_realization_unresolved",
                "summary": (
                    "NO_VALID_BLOCKER_FROM_CURRENT_RULE; TEMPORAL_BEAT_REALIZATION_UNRESOLVED. "
                    "FULL_MOTION is not required for PERFORMANCE. "
                    "Do not reroll. Do not spend bounded repair on a verifier or missing probe. "
                    "Do not stamp FIRST_TAKE_ACCEPTABLE until declared beats are evidenced."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "rollout_id": parent_id,
                "output_hash": rollout.get("output_hash"),
                "unresolved_beats": list(quality.get("unresolved_beats") or []),
                "verdict": quality.get("verdict"),
                "first_take_acceptable": False,
                "content_fail": False,
                "foreman_proven": False,
                "studio_v1": False,
                "ship": False,
                "waiting_on": waiting,
            }
        freeze = _freeze_showpiece(
            project_dir,
            reason="first_take_acceptable",
            proven_status_value="PRIME_FOREMAN_PROOF",
            foreman_proven=False,
            summary=(
                "First S2 take has no real contract blocker. FIRST_TAKE_ACCEPTABLE. "
                "Bounded repair is not proven. Do not stamp PRIME_FOREMAN_PROVEN."
            ),
        )
        return {
            "action": "first_take_acceptable",
            "summary": (
                "First S2 take has no real contract blocker. Do not invent one. "
                "FIRST_TAKE_ACCEPTABLE. This job has not proven bounded repair. "
                "Do not stamp PRIME_FOREMAN_PROVEN. Freeze this job. Do not run S3-S6."
            ),
            "scene_id": scene_id,
            "shot_id": shot_id,
            "rollout_id": parent_id,
            "foreman_proven": False,
            "studio_v1": False,
            "freeze_reason": freeze.get("reason"),
            "ship": False,
            "waiting_on": waiting,
        }
    if rollout and rollout.get("status") == "blocked":
        if "keyframe_presentation_unusable" in str(rollout.get("error") or ""):
            return {
                "action": "produce_keyframe",
                "summary": "PERFORMANCE start is unusable. Produce a readable still before H3.",
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if rollout.get("error") == "character_identity_lock_missing":
            return {
                "action": "resolve_prerequisite",
                "summary": "Identity lock missing. Inherit the vid3 Lucien/Avery plates. Do not re-lock. Do not retry H3.",
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
    if not request_path.is_file():
        return {
            "action": "compile_cut",
            "summary": f"CONTINUE_SCENE. compile_cut({shot_id}) writes an execution proposal only.",
            "scene_id": scene_id,
            "shot_id": shot_id,
            "ship": False,
            "waiting_on": waiting,
        }
    still_ready = _start_frame(project_dir, proof_shot, shot_id) is not None
    if not still_ready:
        return {
            "action": "produce_keyframe",
            "summary": (
                f"Produce a readable {shot_id} start still (MCU/MS, identity visible). "
                "Do not use the B1 kitchen silhouette. Do not send a bad still to H3."
            ),
            "scene_id": scene_id,
            "shot_id": shot_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if not character_locked(project_dir):
        return {
            "action": "resolve_prerequisite",
            "summary": "Copy/inherit locked Lucien identity into this job. Do not generate a new identity pair.",
            "scene_id": scene_id,
            "shot_id": shot_id,
            "ship": False,
            "waiting_on": waiting,
        }
    return {
        "action": "dispatch_cut",
        "summary": (
            f"Prime may request dispatch_cut({shot_id}). OM authorizes H3. "
            "Readable keyframe required. ReferenceAtoms must be in the H3 spec. "
            "One rollout, then Observation. No unbounded retry. Do not invent a failure."
        ),
        "scene_id": scene_id,
        "shot_id": shot_id,
        "ship": False,
        "waiting_on": waiting,
    }



def _append_cut_note(project_dir: Path, shot_id: str, note: str, extra: dict[str, Any] | None = None) -> None:
    path = project_dir / "working" / "prime_rlm" / "SCENE_CUT_NOTES.json"
    payload = _read_json_if(path) or {
        "schema_version": "om-scene-cut-notes/v1",
        "notes": [],
    }
    row = {"shot_id": shot_id, "note": note, "at": _utc_now()}
    if extra:
        row.update(extra)
    notes = payload.setdefault("notes", [])
    if isinstance(notes, list):
        notes.append(row)
    _atomic_write_json(path, payload)


def _lights_out_waiting() -> list[str]:
    return [
        "LIGHTS_OUT_SCENE_PROOF. Alan records one CONTINUE_SCENE on scene_lights_out, then leaves.",
        "Prime walks S1 local → S2 H3 → S3 local → S4 local → compose_scene. No per-cut A/B.",
        "Cursor does not generate. Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN.",
        "Do not chase PRIME_FOREMAN_PROVEN. Do not touch frozen jobs.",
        "Incomplete Observation → complete_observation on the same output hash. Not FAIL. Not first-take. Not repair.",
    ]


def _revise_waiting() -> list[str]:
    return [
        "SCENE_REVISE_PROPAGATION_PROOF. REVISE is not a terminal stop.",
        "Prime names affected cuts from scene-level feedback. OM executes only those cuts.",
        "S1 and accepted S2 H3 stay on parent hashes. Do not redispatch S2.",
        "Compose scene_v2 with a new hash and parent_scene_hash. Return to scene-level review only.",
        "Cursor does not generate. Proof is revision propagation, not art.",
    ]


def _shot_by_id(shots: list[dict[str, Any]], shot_id: str) -> dict[str, Any] | None:
    return next((row for row in shots if str(row.get("id") or "") == shot_id), None)


def _keyframe_ready(project_dir: Path, shot: dict[str, Any], shot_id: str) -> bool:
    first = _start_frame(project_dir, shot, shot_id)
    if first is None:
        return False
    obligation = str(shot.get("motion_obligation") or "").upper()
    if obligation != "PERFORMANCE":
        return True
    framing = "medium_close"
    intent = " ".join(str(shot.get(key) or "") for key in ("performance_intent", "visual_intent", "framing"))
    if "insert" in intent.lower():
        framing = "insert"
    presentation = evaluate_keyframe_presentation(first, framing=framing)
    return presentation.get("usable") is True


def _observation_payload(project_dir: Path, rollout: dict[str, Any]) -> dict[str, Any]:
    rollout_id = str(rollout.get("rollout_id") or "")
    obs_path = (
        project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id / "OBSERVATION.json"
    )
    return _read_json_if(obs_path) or rollout.get("observation") or {}


def _next_step_lights_out(
    *,
    project_dir: Path,
    skeleton: dict[str, Any],
    proposal: dict[str, Any] | None,
    pref: dict[str, Any] | None,
) -> dict[str, Any]:
    waiting = _lights_out_waiting()
    scene_id = str(
        (proposal or {}).get("scene_id")
        or (skeleton or {}).get("scene_id")
        or LIGHTS_OUT_SCENE
    )
    freeze = job_frozen(project_dir)
    if freeze:
        return _next_step_frozen(freeze, project_dir, waiting)
    review = _read_json_if(review_queue_path(project_dir))
    if not pref or pref.get("label") not in HUMAN_PREF_LABELS:
        return {
            "action": "wait_human_preference",
            "summary": f"Waiting. Alan: CONTINUE_SCENE / STOP / REVISE on {scene_id}. Then leave. Cursor does not generate.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    label = str(pref.get("label") or "")
    if label in {"STOP", "ABANDON_SCENE"} or (label == "REVISE" and not review):
        return {
            "action": "revise_or_stop",
            "summary": f"HumanPreference {label}. Do not keep generating.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if review:
        if label in SCENE_REVIEW_LABELS:
            return {
                "action": "scene_review_recorded",
                "summary": (
                    f"Alan recorded {label} on the composed scene. "
                    "Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN. "
                    "Alan only reviews the scene, not cuts."
                ),
                "scene_id": scene_id,
                "label": label,
                "review_queue": review,
                "stamped": False,
                "lights_out_scene_production_proven": False,
                "foreman_proven": False,
                "studio_v1": False,
                "ship": False,
                "waiting_on": waiting,
            }
        return {
            "action": "wait_human_preference",
            "summary": (
                "Composed scene is on the review queue. Alan reviews the scene only "
                "(KEEP_WATCHING / SHIP / DO_NOT_SHIP / REVISE), not per-cut A/B. "
                "Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN."
            ),
            "scene_id": scene_id,
            "target": scene_id,
            "review_queue": review,
            "ship": False,
            "waiting_on": waiting,
        }
    if label != "CONTINUE_SCENE":
        return {
            "action": "wait_human_preference",
            "summary": f"HumanPreference {label} recorded. Not CONTINUE_SCENE.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    target = pref.get("target")
    if target not in {scene_id, f"scene:{scene_id}"}:
        return {
            "action": "wait_human_preference",
            "summary": f"CONTINUE_SCENE target must be {scene_id}.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    shots = [row for row in ((proposal or {}).get("shots") or []) if isinstance(row, dict)]
    ids = [str(row.get("id") or "") for row in shots]
    if set(ids) != set(LIGHTS_OUT_SHOT_ORDER):
        return {
            "action": "submit_scene_proposal",
            "summary": (
                "CONTINUE_SCENE. Prime may re-own the scene proposal "
                "(caller=prime, generate=false) with all four cuts S1–S4 as specified. "
                "S2 is the only H3 PERFORMANCE cut. S4 is HOLD/NONE, not PERFORMANCE."
            ),
            "scene_id": scene_id,
            "shot_ids": list(LIGHTS_OUT_SHOT_ORDER),
            "h3_only": LIGHTS_OUT_H3_SHOT,
            "generate": False,
            "ship": False,
            "waiting_on": waiting,
        }
    performance = [
        row
        for row in shots
        if str(row.get("motion_obligation") or "").upper() == "PERFORMANCE"
    ]
    if len(performance) != 1 or str(performance[0].get("id") or "") != LIGHTS_OUT_H3_SHOT:
        return {
            "action": "repair_shot_contract",
            "summary": "Lights-out allows exactly one H3 PERFORMANCE cut (S2). S4 must stay HOLD/NONE.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    s2 = _shot_by_id(shots, LIGHTS_OUT_H3_SHOT) or {}
    s2_atoms = [str(row) for row in (s2.get("reference_atoms") or []) if str(row).strip()]
    if s2_atoms != ["freeze_notice", "weight_shift"] or "eye_shift_hold" in s2_atoms:
        return {
            "action": "repair_shot_contract",
            "summary": (
                "S2 must declare reference_atoms exactly [freeze_notice, weight_shift]. "
                "Do not add eye_shift_hold. Do not omit the list (MCU inference would invent it)."
            ),
            "scene_id": scene_id,
            "shot_id": LIGHTS_OUT_H3_SHOT,
            "ship": False,
            "waiting_on": waiting,
        }
    if not character_locked(project_dir):
        return {
            "action": "resolve_prerequisite",
            "summary": (
                "Copy/inherit locked Lucien/Avery identity from vid3 / vid-foreman-head-turn-v1. "
                "do_not_relock. Do not propose_identity_candidates."
            ),
            "scene_id": scene_id,
            "do_not": ["propose_identity_candidates", "identity_relock"],
            "ship": False,
            "waiting_on": waiting,
        }

    for shot_id in LIGHTS_OUT_SHOT_ORDER:
        shot = _shot_by_id(shots, shot_id)
        if shot is None:
            return {
                "action": "submit_scene_proposal",
                "summary": f"Missing {shot_id} on the scene proposal. Re-own all four cuts S1–S4.",
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
        if not request_path.is_file():
            return {
                "action": "compile_cut",
                "summary": (
                    f"CONTINUE_SCENE. compile_cut({shot_id}) writes an execution proposal only. "
                    "No human between cuts."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if not _keyframe_ready(project_dir, shot, shot_id):
            mcu_note = ""
            if shot_id == LIGHTS_OUT_H3_SHOT:
                mcu_note = " S2 MCU must be a usable face MCU, not a B1 silhouette."
            return {
                "action": "produce_keyframe",
                "summary": (
                    f"Produce a start still for {shot_id}.{mcu_note} "
                    "Do not send a bad still to H3. Cursor does not generate."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        rollout = _original_rollout(project_dir, shot_id) or latest_rollout(project_dir, shot_id)
        mp4_path = None
        if rollout:
            parent_id = str(rollout.get("rollout_id") or "")
            mp4_path = (
                project_dir / "working" / "prime_rlm" / "rollouts" / parent_id / f"{shot_id}.mp4"
            )
        if rollout and rollout.get("status") == "blocked":
            if "keyframe_presentation_unusable" in str(rollout.get("error") or ""):
                return {
                    "action": "produce_keyframe",
                    "summary": f"{shot_id} start is unusable. Produce a readable still before dispatch.",
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "ship": False,
                    "waiting_on": waiting,
                }
            if rollout.get("error") == "character_identity_lock_missing":
                return {
                    "action": "resolve_prerequisite",
                    "summary": (
                        "Identity lock missing. Inherit the vid3 Lucien/Avery plates. "
                        "Do not re-lock. Do not propose_identity_candidates."
                    ),
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "do_not": ["propose_identity_candidates"],
                    "ship": False,
                    "waiting_on": waiting,
                }
        if rollout and rollout.get("status") in {"succeeded", "failed"}:
            obs = _observation_payload(project_dir, rollout)
            quality = obs.get("quality") or {}
            parent_id = str(rollout.get("rollout_id") or "")
            if "passed" not in quality:
                if rollout.get("output_hash") or (mp4_path is not None and mp4_path.is_file()):
                    return {
                        "action": "observation_incomplete",
                        "bind_tool": "complete_observation",
                        "summary": (
                            "OBSERVATION_INCOMPLETE. No valid evidence → no quality verdict. "
                            "Incomplete Observation is not FAIL and not first-take and not repair. "
                            f"Rebind SEE onto the same output hash {rollout.get('output_hash') or '(disk)'}. "
                            "Do not dispatch_cut. Do not produce_keyframe."
                        ),
                        "scene_id": scene_id,
                        "shot_id": shot_id,
                        "rollout_id": parent_id,
                        "output_hash": rollout.get("output_hash"),
                        "first_take_acceptable": False,
                        "content_fail": False,
                        "quality_verdict": None,
                        "ship": False,
                        "waiting_on": waiting,
                    }
                _append_cut_note(
                    project_dir,
                    shot_id,
                    "rollout_failed_no_mp4",
                    {"rollout_id": parent_id, "error": rollout.get("error")},
                )
                return {
                    "action": "cut_failed",
                    "summary": (
                        f"{shot_id} rollout failed with no mp4. Do not compose_scene. "
                        "Do not invent a quality blocker or a repair. Record the runtime failure."
                    ),
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "rollout_id": parent_id,
                    "error": rollout.get("error"),
                    "ship": False,
                    "waiting_on": waiting,
                }
            blockers = [
                blocker
                for blocker in (quality.get("blockers") or [])
                if blocker != "performance_not_full_motion"
            ]
            if blockers:
                _append_cut_note(
                    project_dir,
                    shot_id,
                    "measurable_blocker_recorded_scene_continues",
                    {"blockers": blockers, "rollout_id": parent_id},
                )
            continue
        renderer = "H3" if shot_id == LIGHTS_OUT_H3_SHOT else "local_compose"
        return {
            "action": "dispatch_cut",
            "summary": (
                f"Prime may request dispatch_cut({shot_id}). OM branches renderer "
                f"({renderer}). No human between cuts. Do not freeze on success."
            ),
            "scene_id": scene_id,
            "shot_id": shot_id,
            "ship": False,
            "waiting_on": waiting,
        }

    return {
        "action": "compose_scene",
        "summary": (
            "S1–S4 succeeded with bound Observations. Prime may request compose_scene. "
            "OM concatenates the four mp4s, hashes, SEE-binds, and writes REVIEW_QUEUE. "
            "Then stop at scene-level review. Do not stamp LIGHTS_OUT_SCENE_PRODUCTION_PROVEN."
        ),
        "scene_id": scene_id,
        "shot_ids": list(LIGHTS_OUT_SHOT_ORDER),
        "ship": False,
        "waiting_on": waiting,
    }


def _next_step_revise(
    *,
    project_dir: Path,
    skeleton: dict[str, Any],
    proposal: dict[str, Any] | None,
    pref: dict[str, Any] | None,
) -> dict[str, Any]:
    waiting = _revise_waiting()
    scene_id = str(
        (proposal or {}).get("scene_id")
        or (skeleton or {}).get("scene_id")
        or REVISE_SCENE
    )
    freeze = job_frozen(project_dir)
    if freeze:
        return _next_step_frozen(freeze, project_dir, waiting)
    if not pref or pref.get("label") not in HUMAN_PREF_LABELS:
        return {
            "action": "wait_human_preference",
            "summary": f"Waiting. Alan: REVISE on {scene_id} (scene-level). Cursor does not generate.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    label = str(pref.get("label") or "")
    if label in {"STOP", "ABANDON_SCENE"}:
        return {
            "action": "revise_or_stop",
            "summary": f"HumanPreference {label}. Do not keep generating.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    revision = active_revision(project_dir)
    review = _read_json_if(review_queue_path(project_dir))
    v2_ready = bool(
        review
        and revision
        and str(review.get("composed_hash") or "")
        and str(review.get("composed_hash") or "") != str(revision.get("parent_scene_hash") or "")
    )
    if v2_ready:
        pref_at = str(pref.get("created_at") or "")
        queue_at = str((review or {}).get("created_at") or "")
        fresh_review = bool(pref_at and queue_at and pref_at > queue_at)
        if fresh_review and label in SCENE_REVIEW_LABELS:
            return {
                "action": "scene_review_recorded",
                "summary": (
                    f"Alan recorded {label} on scene_v2. Revision propagation is the proof. "
                    "Do not polish. Alan only reviews the scene, not cuts."
                ),
                "scene_id": scene_id,
                "label": label,
                "review_queue": review,
                "parent_scene_hash": revision.get("parent_scene_hash"),
                "stamped": False,
                "foreman_proven": False,
                "studio_v1": False,
                "ship": False,
                "waiting_on": waiting,
            }
        return {
            "action": "wait_human_preference",
            "summary": (
                "scene_v2 is on the review queue. Alan reviews the scene only "
                "(KEEP_WATCHING / SHIP / DO_NOT_SHIP / REVISE), not per-cut A/B. "
                "V1 is immutable. Proof is revision propagation, not art."
            ),
            "scene_id": scene_id,
            "target": scene_id,
            "review_queue": review,
            "ship": False,
            "waiting_on": waiting,
        }
    if label != "REVISE":
        return {
            "action": "wait_human_preference",
            "summary": f"HumanPreference {label} recorded. Revision proof waits for REVISE on {scene_id}.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    target = pref.get("target")
    if target not in {scene_id, f"scene:{scene_id}"}:
        return {
            "action": "wait_human_preference",
            "summary": f"REVISE target must be {scene_id}.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    shots = [row for row in ((proposal or {}).get("shots") or []) if isinstance(row, dict)]
    ids = [str(row.get("id") or "") for row in shots]
    if set(ids) != set(REVISE_SHOT_ORDER):
        return {
            "action": "submit_scene_proposal",
            "summary": (
                "Scene proposal must still own S1–S4. Do not drop the H3 cut. "
                "Revision will not redispatch S2."
            ),
            "scene_id": scene_id,
            "shot_ids": list(REVISE_SHOT_ORDER),
            "generate": False,
            "ship": False,
            "waiting_on": waiting,
        }
    if revision is None:
        return {
            "action": "submit_revision_proposal",
            "summary": (
                "REVISE is recorded. Prime reads scene-level feedback plus current scene hashes "
                "and submits a thin revision proposal (affected_shots, unchanged_shots, "
                "revision_reason). Do not regenerate the whole scene. Do not include S2."
            ),
            "scene_id": scene_id,
            "parent_scene_hash": True,
            "ship": False,
            "waiting_on": waiting,
        }
    affected = [str(x) for x in (revision.get("affected_shots") or []) if str(x).strip()]
    if REVISE_H3_SHOT in affected:
        return {
            "action": "repair_revision_proposal",
            "summary": "Active revision lists S2 as affected. OM rejects H3 redispatch. Re-submit without S2.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if not character_locked(project_dir):
        return {
            "action": "resolve_prerequisite",
            "summary": (
                "Copy/inherit locked Lucien/Avery identity. do_not_relock. "
                "Do not propose_identity_candidates."
            ),
            "scene_id": scene_id,
            "do_not": ["propose_identity_candidates", "identity_relock"],
            "ship": False,
            "waiting_on": waiting,
        }
    rev_num = int(revision.get("revision_number") or 2)
    for shot_id in affected:
        shot = _shot_by_id(shots, shot_id)
        if shot is None:
            return {
                "action": "submit_scene_proposal",
                "summary": f"Missing {shot_id} on the scene proposal.",
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        request_path = project_dir / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
        if not request_path.is_file():
            return {
                "action": "compile_cut",
                "summary": (
                    f"REVISE. compile_cut({shot_id}) for an affected cut only. "
                    "Unchanged shots stay on parent hashes."
                ),
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if not _keyframe_ready(project_dir, shot, shot_id):
            return {
                "action": "produce_keyframe",
                "summary": f"Produce a start still for affected cut {shot_id}. Cursor does not generate.",
                "scene_id": scene_id,
                "shot_id": shot_id,
                "ship": False,
                "waiting_on": waiting,
            }
        rollout = revision_rollout(project_dir, shot_id, rev_num)
        mp4_path = None
        if rollout:
            parent_id = str(rollout.get("rollout_id") or "")
            mp4_path = (
                project_dir / "working" / "prime_rlm" / "rollouts" / parent_id / f"{shot_id}.mp4"
            )
        if rollout and rollout.get("status") == "blocked":
            if "keyframe_presentation_unusable" in str(rollout.get("error") or ""):
                return {
                    "action": "produce_keyframe",
                    "summary": f"{shot_id} start is unusable. Produce a readable still before dispatch.",
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "ship": False,
                    "waiting_on": waiting,
                }
            if rollout.get("error") == "character_identity_lock_missing":
                return {
                    "action": "resolve_prerequisite",
                    "summary": "Identity lock missing. Inherit plates. Do not re-lock.",
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "do_not": ["propose_identity_candidates"],
                    "ship": False,
                    "waiting_on": waiting,
                }
        if rollout and rollout.get("status") in {"succeeded", "failed"}:
            obs = _observation_payload(project_dir, rollout)
            quality = obs.get("quality") or {}
            parent_id = str(rollout.get("rollout_id") or "")
            if "passed" not in quality:
                if rollout.get("output_hash") or (mp4_path is not None and mp4_path.is_file()):
                    return {
                        "action": "observation_incomplete",
                        "bind_tool": "complete_observation",
                        "summary": (
                            "OBSERVATION_INCOMPLETE. Rebind SEE onto the same output hash "
                            f"{rollout.get('output_hash') or '(disk)'}. Do not dispatch_cut."
                        ),
                        "scene_id": scene_id,
                        "shot_id": shot_id,
                        "rollout_id": parent_id,
                        "output_hash": rollout.get("output_hash"),
                        "first_take_acceptable": False,
                        "content_fail": False,
                        "quality_verdict": None,
                        "ship": False,
                        "waiting_on": waiting,
                    }
                return {
                    "action": "cut_failed",
                    "summary": f"{shot_id} revision rollout failed with no mp4. Do not compose_scene.",
                    "scene_id": scene_id,
                    "shot_id": shot_id,
                    "rollout_id": parent_id,
                    "error": rollout.get("error"),
                    "ship": False,
                    "waiting_on": waiting,
                }
            continue
        return {
            "action": "dispatch_cut",
            "summary": (
                f"Prime may request dispatch_cut({shot_id}) for this revision only. "
                "Do not dispatch unchanged S1 or S2 H3."
            ),
            "scene_id": scene_id,
            "shot_id": shot_id,
            "affected_shots": affected,
            "unchanged_shots": list(revision.get("unchanged_shots") or []),
            "ship": False,
            "waiting_on": waiting,
        }
    return {
        "action": "compose_scene",
        "summary": (
            "Affected cuts succeeded. Prime may request compose_scene. "
            "OM concatenates parent S1/S2 with revised S3/S4 into scene_v2, "
            "writes a new scene hash with parent_scene_hash, and returns to scene-level review."
        ),
        "scene_id": scene_id,
        "shot_ids": list(REVISE_SHOT_ORDER),
        "affected_shots": affected,
        "unchanged_shots": list(revision.get("unchanged_shots") or []),
        "parent_scene_hash": revision.get("parent_scene_hash"),
        "ship": False,
        "waiting_on": waiting,
    }


def _next_step(
    *,
    project_dir: Path | None = None,
    scene_state: dict[str, Any] | None,
    skeleton: dict[str, Any] | None,
    shots: list[dict[str, Any]],
) -> dict[str, Any]:
    state = scene_state or {}
    skel = skeleton or {}
    waiting = [str(x) for x in (skel.get("waiting_on") or []) if str(x).strip()]
    proposal = _current_scene_proposal(project_dir) if project_dir else None
    pref = _latest_human_preference(project_dir) if project_dir else None
    if state.get("ship") is True:
        return {
            "action": "human_ship_locked",
            "summary": "Human ship is true. Prime cannot publish.",
            "ship": True,
            "waiting_on": waiting,
        }
    freeze = job_frozen(project_dir) if project_dir else None
    if freeze and project_dir is not None:
        return _next_step_frozen(freeze, project_dir, waiting)
    if _is_revise(skel, proposal) and project_dir is not None:
        return _next_step_revise(
            project_dir=project_dir,
            skeleton=skel,
            proposal=proposal,
            pref=pref,
        )
    if _is_lights_out(skel, proposal) and project_dir is not None:
        return _next_step_lights_out(
            project_dir=project_dir,
            skeleton=skel,
            proposal=proposal,
            pref=pref,
        )
    if _is_showpiece(skel, proposal) and project_dir is not None:
        return _next_step_showpiece(
            project_dir=project_dir,
            skeleton=skel,
            proposal=proposal,
            pref=pref,
        )
    if state.get("status") == "CORPUS" or state.get("do_not_polish_a4") is True:
        if proposal is None:
            return {
                "action": "propose_next_scene",
                "summary": (
                    "Scene A is corpus. Do not polish A4. "
                    "Prime must open_job, read story_refs, and submit_scene_proposal. "
                    "Do not split cuts until HumanPreference CONTINUE_SCENE."
                ),
                "ship": False,
                "waiting_on": waiting,
            }
        scene_id = str(proposal.get("scene_id") or "")
        shots_in_proposal = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
        if not pref or pref.get("label") not in HUMAN_PREF_LABELS:
            return {
                "action": "wait_human_preference",
                "summary": "Scene proposal is waiting. Alan: CONTINUE_SCENE / STOP / REVISE.",
                "scene_id": scene_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if pref.get("label") in {"STOP", "REVISE", "ABANDON_SCENE"}:
            return {
                "action": "revise_or_stop",
                "summary": f"HumanPreference {pref.get('label')}. Prime may repair the proposal; do not compile_cut.",
                "scene_id": scene_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if pref.get("label") == "CONTINUE_SCENE" and not shots_in_proposal:
            return {
                "action": "split_shots",
                "summary": "CONTINUE_SCENE. Prime may now split shots onto the proposal, then compile_cut.",
                "scene_id": scene_id,
                "ship": False,
                "waiting_on": waiting,
            }
        if pref.get("label") == "CONTINUE_SCENE" and shots_in_proposal:
            b2 = next((row for row in shots_in_proposal if str(row.get("id")) == "B2"), None)
            b2_request = (
                project_dir / "working" / "prime_rlm" / "execution_requests" / "B2.json"
                if project_dir
                else None
            )
            b2_ready = bool(b2_request and b2_request.is_file())
            b2_rollout = latest_rollout(project_dir, "B2") if project_dir and b2_ready else None
            provider_ran = bool(b2_rollout) and b2_rollout.get("status") in {"succeeded", "failed"}
            still_ready = bool(
                b2 is not None
                and project_dir
                and _start_frame(project_dir, b2, "B2") is not None
            )
            if b2 is not None and b2_ready and provider_ran:
                return {
                    "action": "read_observation",
                    "summary": (
                        "B2 rollout exists. Reopen the job, read the receipt and Observation, "
                        "describe succeeded/failed, and propose the next action. Do not auto-retry."
                    ),
                    "scene_id": scene_id,
                    "shot_id": "B2",
                    "rollout_id": b2_rollout.get("rollout_id"),
                    "ship": False,
                    "waiting_on": waiting,
                }
            diagnosis = diagnose_prerequisites(project_dir) if project_dir else {}
            lucien_ok = bool(project_dir and character_locked(project_dir))
            b1_ok = bool(project_dir and b1_keyframe_path(project_dir).is_file())
            if (
                b2_rollout
                and b2_rollout.get("status") == "blocked"
                and "keyframe_presentation_unusable" in str(b2_rollout.get("error") or "")
            ):
                return {
                    "action": "repair_keyframe_presentation",
                    "summary": (
                        "PERFORMANCE start still is unusable original art "
                        "(silhouette / identity / costume / composition). "
                        "Produce a readable start still before H3. "
                        "B1 EST may stay a silhouette. Do not retry H3 on the bad still."
                    ),
                    "scene_id": scene_id,
                    "shot_id": "B2",
                    "rollout_id": b2_rollout.get("rollout_id"),
                    "presentation_blockers": b2_rollout.get("presentation_blockers"),
                    "ship": False,
                    "waiting_on": waiting,
                }
            if b2 is not None and b2_ready and still_ready and lucien_ok and b1_ok:
                return {
                    "action": "wait_human_redispatch",
                    "summary": (
                        "B1 keyframe is bound as B2.start_frame_ref. Do not auto-retry H3. "
                        "Alan may later ask Prime to dispatch_cut(B2) once."
                    ),
                    "scene_id": scene_id,
                    "shot_id": "B2",
                    "ship": False,
                    "waiting_on": waiting,
                }
            if (
                b2 is not None
                and b2_ready
                and b2_rollout
                and b2_rollout.get("status") == "blocked"
            ):
                ident_pref = identity_preference(project_dir) if project_dir else None
                cands = identity_candidates(project_dir) if project_dir else None
                plan = prerequisite_plan(project_dir) if project_dir else None
                if not lucien_ok:
                    if ident_pref and ident_pref.get("label") == "NEITHER":
                        return {
                            "action": "propose_identity_candidates",
                            "summary": (
                                "Alan chose NEITHER. Prime may propose a new Lucien identity pair. "
                                "Do not retry H3. Do not invent a start frame."
                            ),
                            "scene_id": scene_id,
                            "character_id": CHARACTER_ID,
                            "prerequisite": diagnosis,
                            "ship": False,
                            "waiting_on": waiting,
                        }
                    if cands and any(
                        row.get("status") == "candidate" for row in (cands.get("candidates") or [])
                    ):
                        return {
                            "action": "wait_human_preference",
                            "summary": (
                                "Lucien identity candidates are waiting. Alan: A / B / NEITHER "
                                "on target identity:lucien_mercer. Prime cannot lock identity."
                            ),
                            "scene_id": scene_id,
                            "target": f"identity:{CHARACTER_ID}",
                            "prerequisite": diagnosis,
                            "ship": False,
                            "waiting_on": waiting,
                        }
                    if plan:
                        return {
                            "action": "propose_identity_candidates",
                            "summary": (
                                "B2 blocked because Lucien identity is not locked. "
                                "Prime may propose A/B identity candidates. Do not retry H3."
                            ),
                            "scene_id": scene_id,
                            "character_id": CHARACTER_ID,
                            "prerequisite": diagnosis,
                            "ship": False,
                            "waiting_on": waiting,
                        }
                    return {
                        "action": "resolve_prerequisite",
                        "summary": (
                            "B2 blocked at a production prerequisite, not an H3 failure. "
                            "Root is Lucien identity lock, then B1 NONE keyframe as B2 start_frame_ref. "
                            "Do not retry H3. Do not hand-write B2.png."
                        ),
                        "scene_id": scene_id,
                        "shot_id": "B2",
                        "prerequisite": diagnosis,
                        "ship": False,
                        "waiting_on": waiting,
                    }
                if lucien_ok and not b1_ok:
                    return {
                        "action": "produce_keyframe",
                        "summary": (
                            "Lucien identity is locked. Produce B1 as a NONE still and bind it "
                            "as B2.start_frame_ref. Do not send B1 to H3."
                        ),
                        "scene_id": scene_id,
                        "shot_id": "B1",
                        "prerequisite": diagnosis,
                        "ship": False,
                        "waiting_on": waiting,
                    }
                return {
                    "action": "resolve_prerequisite",
                    "summary": "B2 still missing a legal start state. Follow the prerequisite plan. Do not retry H3.",
                    "scene_id": scene_id,
                    "prerequisite": diagnosis,
                    "ship": False,
                    "waiting_on": waiting,
                }
            if b2 is not None and b2_ready:
                return {
                    "action": "dispatch_cut",
                    "summary": (
                        "CONTINUE_SCENE with B2 compiled. Prime may request dispatch_cut(B2). "
                        "OM authorizes and executes. Prime cannot set generate=true. No retry."
                    ),
                    "scene_id": scene_id,
                    "shot_id": "B2",
                    "ship": False,
                    "waiting_on": waiting,
                }
            return {
                "action": "compile_cut",
                "summary": "CONTINUE_SCENE with shot split. compile_cut writes execution proposals only.",
                "scene_id": scene_id,
                "shot_id": (b2 or shots_in_proposal[0]).get("id"),
                "ship": False,
                "waiting_on": waiting,
            }
        return {
            "action": "wait_human_preference",
            "summary": f"HumanPreference {pref.get('label')} recorded. Prime does not interpret it as APPROVED.",
            "scene_id": scene_id,
            "ship": False,
            "waiting_on": waiting,
        }
    if waiting:
        return {
            "action": "blocked",
            "summary": waiting[0],
            "ship": False,
            "waiting_on": waiting,
        }
    legal = [
        row["id"]
        for row in shots
        if row.get("id")
        and str(row.get("review_decision") or "").lower() != "omit"
        and not row.get("compile_error")
    ]
    return {
        "action": "compile_cut" if legal else "repair_shot_contract",
        "summary": (
            f"Next legal compile_cut: {legal[0]}"
            if legal
            else "No compile-legal shot. Repair ShotContract."
        ),
        "shot_id": legal[0] if legal else None,
        "ship": False,
        "waiting_on": waiting,
    }


def build_production_world(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    checkpoint: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_path, plan = load_scene_plan(project_dir)
    scenes = [row for row in ((plan or {}).get("scenes") or []) if isinstance(row, dict)]
    shots = [_shot_slice(row) for row in scenes]
    scene_state = _read_json_if(project_dir / "working" / "scene_a" / "SCENE_STATE.json")
    skeleton = _read_json_if(project_dir / "JOB_SKELETON.json")
    checkpoint_ids: list[str] = []
    if isinstance(checkpoint, dict):
        embedded = ((checkpoint.get("artifacts") or {}).get("scene_plan") or {}).get("scenes") or []
        checkpoint_ids = [str(row.get("id")) for row in embedded if isinstance(row, dict) and row.get("id")]
    artifact_ids = [str(row.get("id")) for row in scenes if row.get("id")]
    mismatch = bool(checkpoint_ids) and set(checkpoint_ids) != set(artifact_ids)
    world = {
        "schema_version": WORLD_SCHEMA,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "scene_state": {
            "path": "working/scene_a/SCENE_STATE.json" if scene_state else None,
            "status": (scene_state or {}).get("status"),
            "role": (scene_state or {}).get("role"),
            "human_lock": (scene_state or {}).get("human_lock"),
            "ship": (scene_state or {}).get("ship"),
            "director_review_eligible": (scene_state or {}).get("director_review_eligible"),
            "do_not_polish_a4": (scene_state or {}).get("do_not_polish_a4"),
            "master": (scene_state or {}).get("master"),
            "cut_ids": (scene_state or {}).get("cut_ids"),
        }
        if scene_state
        else None,
        "job_skeleton": {
            "status": (skeleton or {}).get("status"),
            "pipeline": (skeleton or {}).get("pipeline"),
            "profile": (skeleton or {}).get("profile"),
            "render_allowed": (skeleton or {}).get("render_allowed"),
            "waiting_on": (skeleton or {}).get("waiting_on") or [],
        }
        if skeleton
        else None,
        "scene_plan_ref": _meta(plan_path, root, kind="scene_plan") if plan_path else None,
        "shot_contracts": shots,
        "identity": _identity(project_dir, plan, root),
        "character_identities": {
            "avery_sterling": _identity(project_dir, plan, root),
            "lucien_mercer": {
                "character": CHARACTER_ID,
                "locked": character_locked(project_dir),
                "path": "bible/lucien/master_sheet.png",
                "exists": (project_dir / "bible" / "lucien" / "master_sheet.png").is_file(),
            },
        },
        "prerequisite": diagnose_prerequisites(project_dir),
        "identity_candidates": identity_candidates(project_dir),
        "observations": _observations(project_dir, root),
        "rollouts": _rollouts(project_dir, root),
        "openviking": _openviking_pointers(job_id, root),
        "human_lock": {
            "human_lock": (scene_state or {}).get("human_lock"),
            "ship": (scene_state or {}).get("ship"),
            "lock_decision": (scene_state or {}).get("lock_decision"),
            "scene_a_human_lock": ((plan or {}).get("metadata") or {}).get("scene_a_human_lock"),
        },
        "story_refs": _story_refs(project_dir, root),
        "scene_proposal": {
            "scene_id": (_current_scene_proposal(project_dir) or {}).get("scene_id"),
            "status": (_current_scene_proposal(project_dir) or {}).get("status"),
            "shot_count": len((_current_scene_proposal(project_dir) or {}).get("shots") or []),
        }
        if _current_scene_proposal(project_dir)
        else None,
        "human_preference": _latest_human_preference(project_dir),
        "proven_status": proven_status(project_dir),
        "foreman_proven": bool((skeleton or {}).get("foreman_proven"))
        or bool((job_frozen(project_dir) or {}).get("foreman_proven")),
        "studio_v1": False,
        "checkpoint_vs_artifacts": {
            "checkpoint_cut_ids": checkpoint_ids,
            "artifact_cut_ids": artifact_ids,
            "match": not mismatch,
            "prefer": "artifacts/scene_plan.json",
            "note": (
                "Checkpoint scene_plan is stale; production shots come from artifacts/scene_plan.json."
                if mismatch
                else None
            ),
        },
        "blockers": list((skeleton or {}).get("waiting_on") or []),
        "next_step": _next_step(
            project_dir=project_dir,
            scene_state=scene_state,
            skeleton=skeleton,
            shots=shots,
        ),
    }
    scan_secrets(world)
    return world


def submit_scene_proposal(
    job_id: str,
    proposal: dict[str, Any],
    project_dir: Path,
    root: Path,
    *,
    caller: str,
) -> dict[str, Any]:
    if caller != "prime":
        raise AdapterError("submit_scene_proposal is a Prime production action")
    scene_id = str(proposal.get("scene_id") or "").strip()
    if not scene_id or "/" in scene_id or "\\" in scene_id or scene_id in {".", ".."}:
        raise AdapterError("scene_id is required and must be a simple id")
    if scene_id.lower() in {"scene_a", "a", "c001"}:
        raise AdapterError("Scene A / c001 are corpus or scrap; propose the next fiction scene")
    required = ("audience_state_change", "visual_intent", "duration_target")
    missing = [key for key in required if not str(proposal.get(key) or "").strip()]
    if missing:
        raise AdapterError(f"scene proposal missing {missing}")
    shots = [row for row in (proposal.get("shots") or []) if isinstance(row, dict)]
    skeleton = _read_json_if(project_dir / "JOB_SKELETON.json") or {}
    if shots and not _cut_gate_ok(project_dir, scene_id, skeleton, {"scene_id": scene_id}):
        raise AdapterError("shot split requires HumanPreference CONTINUE_SCENE or REVISE; do not list cuts yet")
    if proposal.get("generate") is True or proposal.get("status") == "APPROVED":
        raise AdapterError("scene proposal cannot generate or APPROVE")
    record = {
        "schema_version": SCENE_PROPOSAL_SCHEMA,
        "action": "submit_scene_proposal",
        "status": "PROPOSAL",
        "job_id": job_id,
        "scene_id": scene_id,
        "caller": caller,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "generate": False,
        "audience_state_change": proposal.get("audience_state_change"),
        "visual_intent": proposal.get("visual_intent"),
        "performance_intent": proposal.get("performance_intent"),
        "camera_intent": proposal.get("camera_intent"),
        "duration_target": proposal.get("duration_target"),
        "frozen": proposal.get("frozen") or [],
        "free": proposal.get("free") or [],
        "shots": shots,
        "story_ref_hashes": proposal.get("story_ref_hashes") or [],
        "created_at": _utc_now(),
        "note": "Scene intent proposal only. Not canonical scene_plan. Not APPROVED.",
    }
    scan_secrets(record)
    out_dir = _proposal_dir(project_dir)
    out_path = out_dir / f"{scene_id}.json"
    _atomic_write_json(out_path, record)
    _atomic_write_json(out_dir / "CURRENT.json", {"scene_id": scene_id, "path": display_rel(out_path, root)})
    return {
        **record,
        "written": True,
        "proposal_path": display_rel(out_path, root),
        "proposal_hash": _sha256_file(out_path),
    }


def submit_revision_proposal(
    job_id: str,
    proposal: dict[str, Any],
    project_dir: Path,
    root: Path,
    *,
    caller: str,
) -> dict[str, Any]:
    if caller != "prime":
        raise AdapterError("submit_revision_proposal is a Prime production action; Cursor cannot impersonate Prime")
    if proposal.get("generate") is True:
        raise AdapterError("Prime cannot flip generate=true")
    skeleton = _read_json_if(project_dir / "JOB_SKELETON.json") or {}
    scene_proposal = _current_scene_proposal(project_dir) or {}
    if not _is_revise(skeleton, scene_proposal):
        raise AdapterError("submit_revision_proposal is only for SCENE_REVISE_PROPAGATION_PROOF")
    scene_id = str(scene_proposal.get("scene_id") or skeleton.get("scene_id") or REVISE_SCENE)
    if not _revised(project_dir, scene_id):
        raise AdapterError("submit_revision_proposal requires HumanPreference REVISE")
    if job_frozen(project_dir):
        raise AdapterError("job is frozen; do not revise")
    try:
        record = validate_revision_proposal(
            project_dir=project_dir,
            proposal=proposal,
            skeleton=skeleton,
            scene_proposal=scene_proposal,
        )
        payload = write_revision(project_dir, job_id=job_id, record=record, caller=caller)
    except RevisionError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    out_path = project_dir / "working" / "prime_rlm" / "SCENE_REVISION.json"
    return {
        **payload,
        "written": True,
        "path": display_rel(out_path, root),
    }


def record_human_preference(
    job_id: str,
    label: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    target: str | None = None,
) -> dict[str, Any]:
    if caller not in {"human", "pi"}:
        raise AdapterError("HumanPreference is Alan/Pi only; Prime cannot forge CONTINUE_SCENE")
    token = str(label or "").strip().upper()
    if token not in HUMAN_PREF_LABELS:
        raise AdapterError(f"unknown HumanPreference label: {label!r}")
    resolved_target = _preference_target(project_dir, target)
    if str(resolved_target or "").startswith("identity:") or str(resolved_target or "") in {
        CHARACTER_ID,
        "lucien",
    }:
        try:
            payload = apply_identity_preference(
                job_id,
                project_dir,
                root,
                label=token,
                caller=caller,
                target=str(resolved_target),
            )
        except PrerequisiteError as exc:
            raise AdapterError(str(exc)) from exc
        log_path = project_dir / "working" / "prime_rlm" / "human_preferences.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({k: payload.get(k) for k in ("schema_version", "action", "job_id", "label", "target", "caller", "created_at") if k in payload}, ensure_ascii=False) + "\n")
        scan_secrets(payload)
        return payload
    record = {
        "schema_version": HUMAN_PREF_SCHEMA,
        "action": "record_human_preference",
        "job_id": job_id,
        "label": token,
        "target": resolved_target,
        "caller": caller,
        "canonical_owner": "openmontage",
        "promoted_to_hard_rule": False,
        "approved": False,
        "created_at": _utc_now(),
    }
    scan_secrets(record)
    pref_path = project_dir / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json"
    pair = _read_ab_pair(project_dir)
    if pair and token in {"A", "B", "NEITHER"}:
        if token == "B":
            freeze = _freeze_showpiece(
                project_dir,
                reason="prime_foreman_proven",
                proven_status_value="PRIME_FOREMAN_PROVEN",
                foreman_proven=True,
                summary="Alan chose B. Autonomous repair improved preference.",
            )
        elif token == "A":
            freeze = _freeze_showpiece(
                project_dir,
                reason="repair_did_not_improve",
                proven_status_value="PRIME_FOREMAN_PROOF",
                foreman_proven=False,
                summary="Alan chose A. Repair did not improve preference. Proof is not satisfied.",
            )
        else:
            freeze = _freeze_showpiece(
                project_dir,
                reason="capability_miss",
                proven_status_value="PRIME_FOREMAN_PROOF",
                foreman_proven=False,
                summary="Alan chose NEITHER. Record the missing capability. Stop.",
            )
        record["ab_pair"] = {"A": pair.get("A"), "B": pair.get("B")}
        record["foreman_proven"] = token == "B"
        record["studio_v1"] = False
        record["freeze_reason"] = freeze.get("reason")
    _atomic_write_json(pref_path, record)
    log_path = project_dir / "working" / "prime_rlm" / "human_preferences.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {**record, "written": True, "path": display_rel(pref_path, root)}


def get_human_preference(project_dir: Path) -> dict[str, Any] | None:
    return _latest_human_preference(project_dir)


def compile_cut_proposal(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    write: bool,
) -> dict[str, Any]:
    if caller != "prime":
        raise AdapterError("compile_cut is a Prime production action; Cursor cannot impersonate Prime")
    plan_path, plan = load_scene_plan(project_dir)
    scenes = [row for row in ((plan or {}).get("scenes") or []) if isinstance(row, dict)]
    by_id = {str(row.get("id")): row for row in scenes if row.get("id")}
    source = "artifacts/scene_plan.json"
    proposal = _current_scene_proposal(project_dir) or {}
    scene_id = str(proposal.get("scene_id") or "")
    skeleton = _read_json_if(project_dir / "JOB_SKELETON.json") or {}
    if _is_lights_out(skeleton, proposal) and not _continued(project_dir, scene_id or LIGHTS_OUT_SCENE):
        raise AdapterError("lights-out compile_cut requires HumanPreference CONTINUE_SCENE")
    if _is_revise(skeleton, proposal) and not _revised(project_dir, scene_id or REVISE_SCENE):
        raise AdapterError("revision compile_cut requires HumanPreference REVISE")
    for row in proposal.get("shots") or []:
        if isinstance(row, dict) and str(row.get("id")) == shot_id:
            if not _cut_gate_ok(project_dir, scene_id, skeleton, proposal):
                raise AdapterError(
                    f"Unknown shot_id {shot_id!r} in canonical scene_plan; "
                    "new-scene compile_cut requires HumanPreference CONTINUE_SCENE or REVISE"
                )
            by_id[shot_id] = row
            source = f"scene_proposal:{scene_id}"
            plan_path = _proposal_dir(project_dir) / f"{scene_id}.json"
            break
    if shot_id not in by_id:
        if scene_id and not _cut_gate_ok(project_dir, scene_id, skeleton, proposal):
            raise AdapterError(
                f"Unknown shot_id {shot_id!r} in canonical scene_plan; "
                "new-scene compile_cut requires HumanPreference CONTINUE_SCENE or REVISE"
            )
        raise AdapterError(f"Unknown shot_id: {shot_id}")
    scene = by_id[shot_id]
    if str(scene.get("review_decision") or "").strip().lower() == "omit":
        raise AdapterError(f"shot {shot_id} is omitted; compile_cut refused")
    try:
        compiled = compile_shot(scene)
    except ShotCompileError as exc:
        raise AdapterError(str(exc)) from exc
    try:
        assert_transition("SHOT_CONTRACT", "EXECUTION_PROPOSAL", actor=caller)
    except MotionRouterError as exc:
        raise AdapterError(str(exc)) from exc
    proposal = {
        "schema_version": PROPOSAL_SCHEMA,
        "action": "compile_cut",
        "status": "PROPOSAL",
        "job_id": job_id,
        "shot_id": shot_id,
        "caller": caller,
        "canonical_owner": "openmontage",
        "prime_may_write_project_state": False,
        "generate": False,
        "motion_obligation": compiled["motion_obligation"],
        "dispatch_class": compiled["dispatch_class"],
        "renderer": compiled["renderer"],
        "h3_mode": compiled["h3_mode"],
        "h3_mode_label": compiled["h3_mode_label"],
        "h3_default": compiled["h3_default"],
        "compile": compiled,
        "shot_ref": {
            "id": shot_id,
            "visual_intent": scene.get("visual_intent") or scene.get("description"),
            "animation_class": scene.get("animation_class"),
            "scene_plan_path": display_rel(plan_path, root) if plan_path else source,
            "scene_plan_hash": _sha256_file(plan_path) if plan_path and plan_path.is_file() else None,
            "source": source,
        },
        "created_at": _utc_now(),
        "note": "Execution request only. Does not generate media. Does not APPROVE.",
    }
    scan_secrets(proposal)
    if not write:
        proposal["written"] = False
        return proposal
    out_dir = project_dir / "working" / "prime_rlm" / "execution_requests"
    out_path = out_dir / f"{shot_id}.json"
    _atomic_write_json(out_path, proposal)
    log_path = project_dir / "working" / "prime_rlm" / "execution_request_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"shot_id": shot_id, "hash": _sha256_file(out_path), "at": _utc_now()}, ensure_ascii=False)
            + "\n"
        )
    return {
        **proposal,
        "written": True,
        "proposal_path": display_rel(out_path, root),
        "proposal_hash": _sha256_file(out_path),
    }


def dispatch_cut_request(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    generate: bool | None = None,
    invoke_h3=None,
    see_fn=None,
) -> dict[str, Any]:
    if generate is True:
        raise AdapterError("Prime cannot flip generate=false; OM owns authorization")
    try:
        payload = om_dispatch_cut(
            job_id,
            shot_id,
            project_dir,
            root,
            caller=caller,
            invoke_h3=invoke_h3,
            see_fn=see_fn,
        )
    except DispatchError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def compose_scene_request(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    see_fn=None,
    concat_fn=None,
) -> dict[str, Any]:
    try:
        payload = om_compose_scene(
            job_id,
            project_dir,
            root,
            caller=caller,
            see_fn=see_fn,
            concat_fn=concat_fn,
        )
    except ComposeError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def complete_observation(
    job_id: str,
    rollout_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    see_fn=None,
) -> dict[str, Any]:
    try:
        payload = om_complete_observation(
            job_id,
            project_dir,
            root,
            rollout_id,
            caller=caller,
            see_fn=see_fn,
        )
    except DispatchError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def submit_prerequisite_plan(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    from_rollout_id: str | None = None,
) -> dict[str, Any]:
    try:
        payload = om_submit_prerequisite_plan(
            job_id, project_dir, root, caller=caller, from_rollout_id=from_rollout_id
        )
    except PrerequisiteError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def propose_identity_candidates(
    job_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    generate: bool = True,
    invoke_image=None,
) -> dict[str, Any]:
    try:
        payload = om_propose_identity_candidates(
            job_id,
            project_dir,
            root,
            caller=caller,
            generate=generate,
            invoke_image=invoke_image,
        )
    except PrerequisiteError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def produce_keyframe(
    job_id: str,
    shot_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    invoke_image=None,
) -> dict[str, Any]:
    try:
        payload = om_produce_keyframe(
            job_id, shot_id, project_dir, root, caller=caller, invoke_image=invoke_image
        )
    except PrerequisiteError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def propose_bounded_repair(
    job_id: str,
    parent_rollout_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    try:
        payload = om_propose_bounded_repair(
            project_dir,
            parent_rollout_id,
            caller=caller,
            actions=actions,
        )
    except RepairError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload


def dispatch_bounded_repair(
    job_id: str,
    parent_rollout_id: str,
    project_dir: Path,
    root: Path,
    *,
    caller: str,
    invoke_h3=None,
    see_fn=None,
) -> dict[str, Any]:
    try:
        payload = om_dispatch_bounded_repair(
            project_dir,
            root,
            parent_rollout_id,
            caller=caller,
            invoke_h3=invoke_h3,
            see_fn=see_fn,
        )
    except RepairError as exc:
        raise AdapterError(str(exc)) from exc
    scan_secrets(payload)
    return payload
