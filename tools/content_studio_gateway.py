#!/usr/bin/env python3
"""Pi-facing gateway for OpenMontage project recovery and human gates.

This module deliberately stores no session or "current project" state. Every
read derives from OpenMontage project markers, checkpoints, artifacts, and
history. Every scene-plan mutation goes through lib.checkpoint.write_checkpoint.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.checkpoint import get_pipeline_stages, validate_checkpoint, write_checkpoint
from lib.motion_router import MotionRouterError, summarize_scenes
from backlot.state import load_board_state
from tools.prime_session_path import SessionPathError, resolve_session_jsonl
from tools.prime_usage_ledger import summarize_session_usage
from tools.prime_resume_evidence import verify_resume_events
from tools.sceneplan_continuity import evaluate_visual_continuity


GATE_DECISIONS = {"keep", "change", "merge", "omit"}
DEFAULT_PRIME_SESSION_DIR = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_SESSION_DIR",
        r"C:\ContentStudio\runtime\prime-rlm-pilot\sessions",
    )
)
DEFAULT_PRIME_AGENT_DIR = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_AGENT_DIR",
        r"C:\ContentStudio\runtime\prime-rlm-pilot\agent",
    )
)
DEFAULT_PRIME_KERNEL_PYTHON = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_KERNEL_PYTHON",
        r"C:\ContentStudio\runtime\Prime-kernel-venv\Scripts\python.exe",
    )
)
OM_PRIME_ADAPTER_SKILL = REPO_ROOT / "integrations" / "prime-om-adapter"
SCENEPLAN_COLUMNS = [
    "scene_number",
    "cut_id",
    "image_result",
    "visual_intent",
    "prompt",
    "dialogue",
    "duration",
    "sound",
]


class GatewayError(RuntimeError):
    pass


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
        raise GatewayError(f"Cannot read valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayError(f"Expected a JSON object: {path}")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _checkpoint_paths(project_dir: Path) -> list[Path]:
    return sorted(
        project_dir.glob("checkpoint_*.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )


def _project_summary(project_dir: Path) -> dict[str, Any] | None:
    marker_path = project_dir / "project.json"
    if not marker_path.is_file():
        return None
    marker = _read_json(marker_path)
    checkpoints = []
    for path in _checkpoint_paths(project_dir):
        try:
            checkpoint = _read_json(path)
            validate_checkpoint(checkpoint)
        except Exception:
            continue
        checkpoints.append((path, checkpoint))
    awaiting = [item for item in checkpoints if item[1].get("status") == "awaiting_human"]
    active = awaiting[0] if awaiting else (checkpoints[0] if checkpoints else None)
    last_activity = max(
        [marker_path.stat().st_mtime_ns]
        + [path.stat().st_mtime_ns for path, _checkpoint in checkpoints]
    )
    return {
        "project_id": marker.get("project_id") or project_dir.name,
        "title": marker.get("title") or project_dir.name,
        "pipeline_type": marker.get("pipeline_type"),
        "project_dir": project_dir,
        "active_checkpoint_path": active[0] if active else None,
        "active_checkpoint": active[1] if active else None,
        "awaiting_human": bool(awaiting),
        "last_activity_ns": last_activity,
    }


def list_project_summaries(projects_dir: Path) -> list[dict[str, Any]]:
    if not projects_dir.is_dir():
        return []
    projects = []
    for entry in projects_dir.iterdir():
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        summary = _project_summary(entry)
        if summary:
            projects.append(summary)
    projects.sort(
        key=lambda item: (item["awaiting_human"], item["last_activity_ns"]),
        reverse=True,
    )
    return projects


def resolve_project(projects_dir: Path, project_id: str | None = None) -> dict[str, Any]:
    if project_id:
        project_dir = projects_dir / project_id
        summary = _project_summary(project_dir)
        if not summary:
            raise GatewayError(f"OpenMontage project not found: {project_id}")
        return summary
    projects = list_project_summaries(projects_dir)
    if not projects:
        raise GatewayError(f"No OpenMontage projects found under {projects_dir}")
    return projects[0]


def _sceneplan_checkpoint(project_dir: Path) -> tuple[Path, dict[str, Any]]:
    path = project_dir / "checkpoint_scene_plan.json"
    if not path.is_file():
        raise GatewayError(f"Sceneplan checkpoint missing: {path}")
    checkpoint = _read_json(path)
    validate_checkpoint(checkpoint)
    if checkpoint.get("stage") != "scene_plan":
        raise GatewayError("checkpoint_scene_plan.json has the wrong stage")
    return path, checkpoint


def _sceneplan_artifact(project_dir: Path, checkpoint: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    embedded = (checkpoint.get("artifacts") or {}).get("scene_plan")
    if not isinstance(embedded, dict):
        raise GatewayError("Sceneplan checkpoint does not embed artifacts.scene_plan")
    artifact_path = project_dir / "artifacts" / "scene_plan.json"
    if not artifact_path.is_file():
        raise GatewayError(f"Canonical sceneplan artifact missing: {artifact_path}")
    artifact = _read_json(artifact_path)
    if artifact != embedded:
        raise GatewayError(
            "Canonical sceneplan artifact and checkpoint copy diverge; repair OM state before approval"
        )
    scenes = artifact.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise GatewayError("Sceneplan has no scenes")
    return artifact_path, artifact


def _scene_map(scene_plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping = {}
    for scene in scene_plan["scenes"]:
        cut_id = scene.get("id")
        if not isinstance(cut_id, str) or not cut_id or cut_id in mapping:
            raise GatewayError("Sceneplan cut IDs must be unique non-empty strings")
        mapping[cut_id] = scene
    return mapping


def _resolved_layout(scene: dict[str, Any], scenes: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    current = scene
    visited = {scene["id"]}
    source_cut_id = None
    while isinstance(current.get("reuse"), dict):
        source_cut_id = current["reuse"].get("source_cut_id")
        if source_cut_id not in scenes or source_cut_id in visited:
            raise GatewayError(f"Invalid or cyclic reuse pointer from {scene['id']}")
        visited.add(source_cut_id)
        current = scenes[source_cut_id]
    return current.get("visual_ref"), source_cut_id


def _resolved_prompt(scene: dict[str, Any], scenes: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
    current = scene
    visited = {scene["id"]}
    source_cut_id = None
    while not current.get("t2i_prompt") and isinstance(current.get("reuse"), dict):
        source_cut_id = current["reuse"].get("source_cut_id")
        if source_cut_id not in scenes or source_cut_id in visited:
            raise GatewayError(f"Invalid or cyclic reuse pointer from {scene['id']}")
        visited.add(source_cut_id)
        current = scenes[source_cut_id]
    return current.get("t2i_prompt"), source_cut_id


def _display_path(project_dir: Path, raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    try:
        path = Path(raw_path)
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except (OSError, ValueError):
        return raw_path


def current_payload(projects_dir: Path, project_id: str | None = None) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    checkpoint = project["active_checkpoint"]
    return {
        "schema_version": "content-studio-pi-gateway/v1",
        "action": "current",
        "selection_policy": "awaiting_human_first_then_latest_om_checkpoint",
        "project_id": project["project_id"],
        "title": project["title"],
        "pipeline_type": project["pipeline_type"],
        "active_stage": checkpoint.get("stage") if checkpoint else None,
        "status": checkpoint.get("status") if checkpoint else None,
        "awaiting_human": project["awaiting_human"],
    }


def show_gate_payload(projects_dir: Path, project_id: str | None = None) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    project_dir = project["project_dir"]
    checkpoint_path, checkpoint = _sceneplan_checkpoint(project_dir)
    artifact_path, scene_plan = _sceneplan_artifact(project_dir, checkpoint)
    scenes = _scene_map(scene_plan)
    cuts = []
    for scene in scene_plan["scenes"]:
        visual_ref, visual_source = _resolved_layout(scene, scenes)
        prompt, prompt_source = _resolved_prompt(scene, scenes)
        duration = round(float(scene["end_seconds"]) - float(scene["start_seconds"]), 3)
        cuts.append(
            {
                "scene_number": scene.get("script_section_id"),
                "cut_id": scene["id"],
                "image_result": {
                    "kind": (visual_ref or {}).get("kind") if visual_ref else "missing",
                    "path": _display_path(project_dir, (visual_ref or {}).get("path")),
                    "source_cut_id": visual_source,
                    "output_hash": (scene.get("image_provenance") or {}).get("output_hash"),
                },
                "visual_intent": scene.get("visual_intent") or scene.get("description") or scene.get("shot_intent"),
                "prompt": prompt,
                "prompt_source_cut_id": prompt_source,
                "dialogue": scene.get("dialogue", ""),
                "duration": {
                    "start_seconds": scene["start_seconds"],
                    "end_seconds": scene["end_seconds"],
                    "duration_seconds": duration,
                },
                "sound": scene.get("sound_intent"),
                "decision": scene.get("review_decision", "pending"),
                "decision_note": scene.get("review_notes"),
            }
        )
    return {
        "schema_version": "content-studio-sceneplan-gate/v1",
        "action": "show_sceneplan_gate",
        "project_id": project["project_id"],
        "title": project["title"],
        "entry_channel_required": "human",
        "workshop_gui": "openmontage-backlot",
        "foreman": "prime-agent-tui",
        "checkpoint": {
            "stage": checkpoint["stage"],
            "status": checkpoint["status"],
            "human_approved": checkpoint.get("human_approved", False),
            "sha256": _sha256_file(checkpoint_path),
        },
        "artifact": {
            "relative_path": artifact_path.relative_to(project_dir).as_posix(),
            "sha256": _sha256_file(artifact_path),
        },
        "columns": SCENEPLAN_COLUMNS,
        "allowed_decisions": sorted(GATE_DECISIONS),
        "cut_count": len(cuts),
        "cuts": cuts,
        "visual_continuity": evaluate_visual_continuity(scene_plan),
    }


def _read_json_if(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _see_board(project_dir: Path) -> dict[str, Any]:
    """Surface temporal/grammar measurement. Missing report means SEE is incomplete."""
    artifacts = Path(project_dir) / "artifacts"
    scene_a = Path(project_dir) / "working" / "scene_a"
    temporal = (
        _read_json_if(artifacts / "temporal_motion_report.json")
        or _read_json_if(scene_a / "TEMPORAL_MOTION_REPORT.json")
        or _read_json_if(scene_a / "see" / "temporal_motion_report.json")
    )
    grammar = (
        _read_json_if(artifacts / "limited_grammar_report.json")
        or _read_json_if(scene_a / "LIMITED_GRAMMAR_REPORT.json")
        or _read_json_if(scene_a / "see" / "limited_grammar_report.json")
    )
    payload: dict[str, Any] = {
        "temporal_report_present": temporal is not None,
        "incomplete": temporal is None,
    }
    if temporal:
        payload["motion_coverage"] = temporal.get("motion_coverage")
        payload["longest_static_run"] = temporal.get("longest_static_run")
        payload["motion_type"] = temporal.get("motion_type")
        payload["duration_seconds"] = temporal.get("duration_seconds")
    if grammar:
        payload["limited_grammar_ok"] = grammar.get("ok")
        payload["limited_grammar_finding_count"] = grammar.get("finding_count")
        payload["limited_grammar_classes"] = [
            row.get("failure_class") for row in (grammar.get("findings") or []) if isinstance(row, dict)
        ]
    return payload


def _ship_board(project_dir: Path, *, planning_render_allowed: bool) -> dict[str, Any]:
    """Planning dispatch is not ship. Only SCENE_STATE.ship is a human green light."""
    skeleton = _read_json_if(Path(project_dir) / "JOB_SKELETON.json") or {}
    scene = _read_json_if(Path(project_dir) / "working" / "scene_a" / "SCENE_STATE.json") or {}
    see = _see_board(project_dir)
    human_ship = scene.get("ship") is True
    return {
        "allowed": human_ship,
        "human_ship": human_ship,
        "job_render_allowed": skeleton.get("render_allowed") is True,
        "planning_render_allowed": bool(planning_render_allowed),
        "planning_render_allowed_is_not_ship": True,
        "see_complete": see.get("temporal_report_present") is True and not see.get("incomplete"),
        "limited_grammar_ok": see.get("limited_grammar_ok"),
        "reason": "Planning render_allowed is not a production green light. Scene A is not proven shippable.",
    }


def board_payload(projects_dir: Path, project_id: str | None = None) -> dict[str, Any]:
    """Workshop kanban. This is the studio GUI; Trae is not."""
    project = resolve_project(projects_dir, project_id)
    state = load_board_state(project["project_dir"])
    storyboard = state.get("storyboard") or {}
    artifact = (state.get("artifacts") or {}).get("scene_plan") or {}
    if not isinstance(artifact, dict):
        artifact = {}
    scenes = artifact.get("scenes") if isinstance(artifact.get("scenes"), list) else None
    if not scenes and isinstance(storyboard, dict):
        scenes = storyboard.get("scenes") or []
    try:
        motion = summarize_scenes(
            scenes or [],
            scene_plan=artifact if artifact.get("scenes") else {"scenes": scenes or [], "metadata": {}},
            project_dir=project["project_dir"],
        )
    except MotionRouterError as exc:
        raise GatewayError(str(exc)) from exc
    waiting = []
    if isinstance(artifact, dict):
        waiting = list((artifact.get("metadata") or {}).get("waiting_on") or [])
    if isinstance(storyboard, dict) and storyboard.get("waiting_on"):
        waiting = list(storyboard.get("waiting_on") or waiting)
    return {
        "schema_version": "content-studio-board/v1",
        "action": "board",
        "workshop_gui": "openmontage-backlot",
        "foreman": "prime-agent-tui",
        "trae_is_studio_gui": False,
        "dsh_is_windows_foreman": False,
        "project_id": project["project_id"],
        "title": project["title"],
        "pipeline_type": project["pipeline_type"],
        "awaiting_human": project["awaiting_human"],
        "waiting_on": waiting,
        "stages": state.get("stages") or [],
        "motion": motion,
        "see": _see_board(project["project_dir"]),
        "ship": _ship_board(
            project["project_dir"],
            planning_render_allowed=bool(motion.get("render_allowed")),
        ),
        "storyboard": storyboard,
    }


def lock_visuals(
    projects_dir: Path,
    project_id: str | None,
    *,
    master_sheet: Path,
    i_am_human: bool,
    animatic: Path | None = None,
) -> dict[str, Any]:
    """Human identity lock. Does not approve cuts, freeze camera, or enable H3."""
    from lib.shot_production_gate import evaluate_plan

    if not i_am_human:
        raise GatewayError("lock-visuals is human-only; pass --i-am-human")
    sheet = Path(master_sheet).expanduser()
    if not sheet.is_file():
        raise GatewayError(f"master sheet missing: {sheet}")
    reel = Path(animatic).expanduser() if animatic else None
    if reel is not None and not reel.is_file():
        raise GatewayError(f"animatic missing: {reel}")

    project = resolve_project(projects_dir, project_id)
    project_dir = project["project_dir"]
    checkpoint_path, checkpoint = _sceneplan_checkpoint(project_dir)
    artifact_path, original = _sceneplan_artifact(project_dir, checkpoint)
    scene_plan = copy.deepcopy(original)
    meta = scene_plan.setdefault("metadata", {})
    if not isinstance(meta, dict):
        raise GatewayError("scene_plan.metadata must be an object")
    meta["master_sheet_path"] = str(sheet.resolve())
    meta["master_sheet_locked"] = True
    if reel is not None:
        meta["animatic_path"] = str(reel.resolve())
        meta["animatic_locked"] = True

    old_bytes = artifact_path.read_bytes()
    next_artifacts = copy.deepcopy(checkpoint.get("artifacts") or {})
    next_artifacts["scene_plan"] = scene_plan
    next_review = copy.deepcopy(checkpoint.get("review") or {})
    next_metadata = copy.deepcopy(checkpoint.get("metadata") or {})
    next_metadata["visual_locks"] = {
        "locked_by": "human",
        "timestamp": _utc_now(),
        "master_sheet_path": meta["master_sheet_path"],
        "animatic_path": meta.get("animatic_path"),
        "locks": "identity",
    }
    try:
        _atomic_write_json(artifact_path, scene_plan)
        write_checkpoint(
            projects_dir,
            project["project_id"],
            "scene_plan",
            checkpoint.get("status") or "awaiting_human",
            next_artifacts,
            pipeline_type=checkpoint.get("pipeline_type"),
            style_playbook=checkpoint.get("style_playbook"),
            checkpoint_policy=checkpoint.get("checkpoint_policy", "guided"),
            human_approval_required=checkpoint.get("human_approval_required", True),
            human_approved=bool(checkpoint.get("human_approved")),
            review=next_review,
            cost_snapshot=checkpoint.get("cost_snapshot"),
            metadata=next_metadata,
        )
    except Exception:
        artifact_path.write_bytes(old_bytes)
        raise

    overview = evaluate_plan(scene_plan, project_dir)
    return {
        "schema_version": "content-studio-lock-visuals/v1",
        "action": "lock-visuals",
        "status": "JOB_VISUALS_LOCKED",
        "project_id": project["project_id"],
        "master_sheet_path": meta["master_sheet_path"],
        "animatic_path": meta.get("animatic_path"),
        "job_blockers": overview["job_blockers"],
        "dispatchable_cut_ids": overview["dispatchable_cut_ids"],
        "planning_cut_ids": overview["planning_cut_ids"],
        "render_allowed": overview["render_allowed"],
        "note": "Identity locked. Cuts still need an approved source still; camera/motion stay open until SEE.",
    }


def _append_review_note(scene: dict[str, Any], note: str) -> None:
    clean = note.strip()
    if not clean:
        return
    existing = str(scene.get("review_notes") or "").strip()
    scene["review_notes"] = f"{existing}\nWindows Pi: {clean}".strip()


def _apply_one_decision(scene: dict[str, Any], decision: dict[str, Any], scenes: dict[str, dict[str, Any]]) -> None:
    action = decision.get("decision")
    if action not in GATE_DECISIONS:
        raise GatewayError(f"Invalid decision for {scene['id']}: {action!r}")
    note = str(decision.get("note") or "")
    scene["review_decision"] = action
    _append_review_note(scene, note)

    if action == "change":
        visual_intent = decision.get("visual_intent")
        prompt = decision.get("prompt")
        if not note and not visual_intent and not prompt:
            raise GatewayError(f"change requires a note, visual_intent, or prompt: {scene['id']}")
        if visual_intent:
            scene["visual_intent"] = str(visual_intent)
        if prompt:
            scene["t2i_prompt"] = str(prompt)
        scene.pop("reuse", None)
        scene.pop("visual_ref", None)
        scene.pop("image_provenance", None)
        flags = list(scene.get("flags") or [])
        if "needs_layout_regeneration" not in flags:
            flags.append("needs_layout_regeneration")
        scene["flags"] = flags
    elif action == "merge":
        target = decision.get("merge_target_id")
        if target not in scenes or target == scene["id"]:
            raise GatewayError(f"merge requires another existing cut as merge_target_id: {scene['id']}")
        scene["merge_target_id"] = target
    else:
        scene.pop("merge_target_id", None)


def apply_sceneplan_decisions(
    projects_dir: Path,
    project_id: str | None,
    expected_checkpoint_sha256: str,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    project_dir = project["project_dir"]
    checkpoint_path, checkpoint = _sceneplan_checkpoint(project_dir)
    old_checkpoint_hash = _sha256_file(checkpoint_path)
    if old_checkpoint_hash != expected_checkpoint_sha256:
        raise GatewayError(
            "Stale Sceneplan Gate: checkpoint changed after display; reopen the gate before deciding"
        )
    if checkpoint.get("status") not in {"awaiting_human", "completed"}:
        raise GatewayError(f"Sceneplan Gate is not reviewable: {checkpoint.get('status')}")
    artifact_path, original_scene_plan = _sceneplan_artifact(project_dir, checkpoint)
    scene_plan = copy.deepcopy(original_scene_plan)
    scenes = _scene_map(scene_plan)

    if not isinstance(decisions, list) or not decisions:
        raise GatewayError("At least one explicit cut decision is required")
    seen = set()
    for decision in decisions:
        cut_id = decision.get("cut_id")
        if cut_id not in scenes:
            raise GatewayError(f"Unknown cut_id: {cut_id!r}")
        if cut_id in seen:
            raise GatewayError(f"Duplicate cut decision: {cut_id}")
        seen.add(cut_id)
        _apply_one_decision(scenes[cut_id], decision, scenes)

    unresolved = [
        scene["id"]
        for scene in scene_plan["scenes"]
        if scene.get("review_decision", "pending") in {"pending", "change"}
    ]
    approved = not unresolved
    status = "completed" if approved else "awaiting_human"
    continuity = evaluate_visual_continuity(scene_plan)
    if approved and continuity["status"] != "PASS":
        raise GatewayError(
            "Visual continuity hard gate blocked approval: "
            f"{continuity.get('reason')} [{continuity.get('verdict_tag')}]"
        )

    old_artifact_bytes = artifact_path.read_bytes()
    old_artifact_hash = _sha256_bytes(old_artifact_bytes)
    timestamp = _utc_now()
    history_dir = project_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"artifact_scene_plan_{old_artifact_hash[:16]}_{timestamp.replace(':', '').replace('+', '_')}.json"
    history_path.write_bytes(old_artifact_bytes)

    decision_digest = hashlib.sha256(
        json.dumps(decisions, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    decision_log = {
        "version": "1.0",
        "project_id": project["project_id"],
        "decisions": [
            {
                "decision_id": f"pi-sceneplan-{decision_digest[:16]}",
                "stage": "scene_plan",
                "category": "visual_accuracy_check",
                "subject": "Windows Pi direct Sceneplan Gate",
                "options_considered": [
                    {
                        "option_id": "windows_pi_cut_decisions",
                        "label": "Apply Alan's direct cut decisions",
                        "score": 1.0,
                        "reason": json.dumps(decisions, ensure_ascii=False, sort_keys=True),
                    },
                    {
                        "option_id": "leave_gate_unchanged",
                        "label": "Leave the gate unchanged",
                        "score": 0.0,
                        "reason": "Available only when Alan has not made a decision.",
                        "rejected_because": "Alan supplied explicit cut decisions in Windows Pi.",
                    },
                ],
                "selected": "windows_pi_cut_decisions",
                "reason": "Alan decided directly in Windows Pi; no Mac relay.",
                "user_visible": True,
                "user_approved": True,
                "confidence": 1.0,
            }
        ],
    }

    next_artifacts = copy.deepcopy(checkpoint.get("artifacts") or {})
    next_artifacts["scene_plan"] = scene_plan
    next_artifacts["decision_log"] = decision_log
    next_review = copy.deepcopy(checkpoint.get("review") or {})
    next_review["status"] = "WINDOWS_PI_APPROVED" if approved else "WINDOWS_PI_CHANGES_PENDING"
    next_review["human_decision"] = {
        "status": "approved" if approved else "partial_or_change_requested",
        "entry_channel": "Windows Pi",
        "decisions": decisions,
        "unresolved_cut_ids": unresolved,
        "timestamp": timestamp,
    }
    next_metadata = copy.deepcopy(checkpoint.get("metadata") or {})
    next_metadata["pi_entry"] = {
        "gateway": "content-studio-pi-gateway/v1",
        "entry_channel": "Windows Pi",
        "no_mac_relay": True,
        "timestamp": timestamp,
    }

    try:
        _atomic_write_json(artifact_path, scene_plan)
        next_review["canonical_scene_plan_sha256"] = _sha256_file(artifact_path)
        write_checkpoint(
            projects_dir,
            project["project_id"],
            "scene_plan",
            status,
            next_artifacts,
            pipeline_type=checkpoint.get("pipeline_type"),
            style_playbook=checkpoint.get("style_playbook"),
            checkpoint_policy=checkpoint.get("checkpoint_policy", "guided"),
            human_approval_required=True,
            human_approved=approved,
            review=next_review,
            cost_snapshot=checkpoint.get("cost_snapshot"),
            metadata=next_metadata,
        )
    except Exception:
        artifact_path.write_bytes(old_artifact_bytes)
        raise

    return {
        "schema_version": "content-studio-sceneplan-decision/v1",
        "status": "APPROVED" if approved else "AWAITING_BOUNDED_CHANGES",
        "project_id": project["project_id"],
        "entry_channel": "Windows Pi",
        "no_mac_relay": True,
        "decisions_applied": decisions,
        "unresolved_cut_ids": unresolved,
        "old_checkpoint_sha256": old_checkpoint_hash,
        "new_checkpoint_sha256": _sha256_file(checkpoint_path),
        "old_artifact_sha256": old_artifact_hash,
        "new_artifact_sha256": _sha256_file(artifact_path),
        "artifact_history_path": history_path.relative_to(project_dir).as_posix(),
        "prime_resume_allowed": approved,
        "visual_continuity": continuity,
    }


def _resolve_persistent_session(project_dir: Path) -> dict[str, Any]:
    """Locate the project-bound Prime .jsonl path. Never fall back to global latest."""
    pointer_path = project_dir / "working" / "prime_rlm" / "SESSION_POINTER.json"
    if not pointer_path.is_file():
        raise GatewayError(
            "Project-bound working/prime_rlm/SESSION_POINTER.json is required. "
            "Global latest-session fallback is forbidden. Create a Director session "
            "for this project and write the pointer before resume."
        )
    pointer = _read_json(pointer_path)
    session_file = pointer.get("session_file") or pointer.get("session_path")
    if not session_file:
        raise GatewayError("SESSION_POINTER.json missing session_file")
    project_id = pointer.get("project_id")
    marker = _read_json(project_dir / "project.json")
    expected_project_id = marker.get("project_id") or project_dir.name
    if project_id and project_id != expected_project_id:
        raise GatewayError(
            f"SESSION_POINTER project_id mismatch: {project_id!r} != {expected_project_id!r}"
        )
    session_dir_value = pointer.get("session_dir")
    session_dir = Path(session_dir_value) if session_dir_value else DEFAULT_PRIME_SESSION_DIR
    try:
        resolved = resolve_session_jsonl(session_file, session_dir=session_dir)
    except SessionPathError as exc:
        raise GatewayError(str(exc)) from exc
    kernel = pointer.get("kernel_python") or str(DEFAULT_PRIME_KERNEL_PYTHON)
    return {
        "session_file": str(resolved),
        "session_dir": str(session_dir),
        "session_id": pointer.get("session_id") or resolved.stem,
        "session_sha256": pointer.get("session_sha256") or _sha256_file(resolved),
        "pointer_path": str(pointer_path),
        "agent_dir": str(pointer.get("agent_dir") or DEFAULT_PRIME_AGENT_DIR),
        "kernel_python": str(kernel),
        "project_id": expected_project_id,
        "checkpoint_sha256_at_bind": pointer.get("checkpoint_sha256"),
    }


def prepare_prime_resume(projects_dir: Path, project_id: str | None) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    project_dir = project["project_dir"]
    checkpoint_path, checkpoint = _sceneplan_checkpoint(project_dir)
    if checkpoint.get("status") != "completed" or not checkpoint.get("human_approved"):
        raise GatewayError("Prime resume is blocked until the Windows Pi Sceneplan Gate is approved")
    stages = get_pipeline_stages(checkpoint.get("pipeline_type"))
    try:
        next_stage = stages[stages.index("scene_plan") + 1]
    except (ValueError, IndexError):
        raise GatewayError("Cannot resolve the stage after scene_plan")
    checkpoint_hash = _sha256_file(checkpoint_path)
    session = _resolve_persistent_session(project_dir)
    request_id = hashlib.sha256(
        f"{project['project_id']}:{checkpoint_hash}:{session['session_sha256']}:{_utc_now()}".encode("utf-8")
    ).hexdigest()[:20]
    request = {
        "schema_version": "om-prime-resume-request/v2",
        "status": "READY_FOR_PERSISTENT_PRIME",
        "request_id": request_id,
        "project_id": project["project_id"],
        "pipeline_type": checkpoint.get("pipeline_type"),
        "approved_stage": "scene_plan",
        "checkpoint_sha256": checkpoint_hash,
        "next_stage": next_stage,
        "entry_channel": "Windows Pi",
        "provider": "bailian",
        "model": "qwen3.8-max",
        "resume_mode": "persistent_jsonl",
        "session_file": session["session_file"],
        "session_dir": session["session_dir"],
        "session_id": session["session_id"],
        "session_sha256": session["session_sha256"],
        "agent_dir": session["agent_dir"],
        "kernel_python": session["kernel_python"],
        "pointer_path": session["pointer_path"],
        "skill_path": str(OM_PRIME_ADAPTER_SKILL),
        "forbidden_flags": ["--no-session", "--no-tools"],
        "global_latest_fallback": False,
        "instruction": (
            "Resume the existing Prime session from session_file. Prove IPython state "
            "revival or reload. Acknowledge the OM checkpoint. Do not start assets/render. "
            "Do not use --no-session or --no-tools."
        ),
        "created_at": _utc_now(),
    }
    request_path = project_dir / "working" / "pi_entry" / "PRIME_RESUME_REQUEST.json"
    _atomic_write_json(request_path, request)
    return request


def record_prime_resume(
    projects_dir: Path,
    project_id: str | None,
    request_id: str,
    prime_response: str,
    evidence_json: str | None = None,
) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    project_dir = project["project_dir"]
    request_path = project_dir / "working" / "pi_entry" / "PRIME_RESUME_REQUEST.json"
    request = _read_json(request_path)
    if request.get("request_id") != request_id:
        raise GatewayError("Prime resume request_id mismatch")
    if not evidence_json:
        raise GatewayError(
            "Mechanical JSONL evidence is required; model self-report resumed=true is insufficient"
        )
    try:
        submitted = json.loads(evidence_json)
    except json.JSONDecodeError as exc:
        raise GatewayError("Invalid evidence JSON") from exc

    try:
        acknowledgement = (
            json.loads(prime_response.strip()) if prime_response.strip().startswith("{") else {}
        )
    except json.JSONDecodeError as exc:
        raise GatewayError("Invalid Prime acknowledgement JSON") from exc

    submitted_job = submitted.get("expected_job_id")
    if submitted_job != request["project_id"]:
        raise GatewayError(
            f"evidence.expected_job_id mismatch: {submitted_job!r} != {request['project_id']!r}"
        )

    submitted_session = submitted.get("session_file")
    if not submitted_session:
        raise GatewayError("evidence.session_file required")
    if Path(str(submitted_session)).resolve() != Path(str(request["session_file"])).resolve():
        raise GatewayError("evidence.session_file != request.session_file")

    submitted_nonce = submitted.get("nonce")
    ack_nonce = acknowledgement.get("nonce")
    if not submitted_nonce or submitted_nonce != ack_nonce:
        raise GatewayError("evidence.nonce != acknowledgement.nonce")

    if acknowledgement.get("session_file") not in {None, request["session_file"]}:
        if Path(str(acknowledgement.get("session_file"))).resolve() != Path(
            str(request["session_file"])
        ).resolve():
            raise GatewayError("Prime acknowledgement session_file mismatch")

    start_line = submitted.get("start_line_0based")
    if not isinstance(start_line, int) or start_line < 0:
        raise GatewayError("evidence.start_line_0based required for re-verification")

    # Never trust caller-submitted PASS; re-verify toolResult JSONL on disk.
    evidence = verify_resume_events(
        request["session_file"],
        nonce=str(submitted_nonce),
        expected_job_id=str(request["project_id"]),
        start_line=start_line,
    )
    if evidence.get("status") != "PASS" or not evidence.get("resumed"):
        raise GatewayError(f"Resume evidence re-verification failed: {evidence.get('reason')}")
    if evidence.get("expected_job_id") != request["project_id"]:
        raise GatewayError("Re-verified evidence.expected_job_id mismatch")
    if Path(str(evidence.get("session_file"))).resolve() != Path(str(request["session_file"])).resolve():
        raise GatewayError("Re-verified evidence.session_file mismatch")
    if evidence.get("nonce") != acknowledgement.get("nonce"):
        raise GatewayError("Re-verified evidence.nonce != acknowledgement.nonce")

    usage = summarize_session_usage(request["session_file"])
    call_sha = evidence["ipython_tool_calls"][0]["event_sha256"]
    result_events = evidence.get("accepted_tool_result_events") or evidence.get("clean_ipython_tool_results")
    result_sha = result_events[0]["event_sha256"]
    receipt = {
        "schema_version": "om-prime-resume-receipt/v3",
        "status": "PASS",
        "request_id": request_id,
        "project_id": request["project_id"],
        "checkpoint_sha256": request["checkpoint_sha256"],
        "next_stage": request["next_stage"],
        "provider": "bailian",
        "model": "qwen3.8-max",
        "resume_mode": "persistent_jsonl",
        "session_file": request["session_file"],
        "session_dir": request["session_dir"],
        "session_id": request["session_id"],
        "session_sha256": request["session_sha256"],
        "kernel_python": request.get("kernel_python"),
        "pointer_path": request.get("pointer_path"),
        "resumed": True,
        "fake_json_echo": False,
        "resumed_evidence": {
            "nonce": evidence["nonce"],
            "expected_job_id": evidence["expected_job_id"],
            "job_id": evidence.get("job_id"),
            "variable_names": evidence.get("variable_names") or [],
            "evidence_line_range_1based": evidence["evidence_line_range_1based"],
            "ipython_tool_call_sha256": call_sha,
            "ipython_tool_result_sha256": result_sha,
            "restored_variable": bool(evidence.get("restored_variable")),
            "reload_context_ok": bool(evidence.get("reload_context_ok")),
            "reverified_from_session_jsonl": True,
            "verifier": "tools.prime_resume_evidence.verify_resume_events",
        },
        "forbidden_flags_absent": True,
        "global_latest_fallback": False,
        "usage_ledger": {
            "parent_tokens": usage["parent_tokens"],
            "child_tokens": usage["child_tokens"],
            "aggregate_tokens": usage["aggregate_tokens"],
            "provider_cost_or_plan_usage": usage["provider_cost_or_plan_usage"],
            "wall_seconds": usage["wall_seconds"],
            "status": usage["status"],
        },
        "prime_response_sha256": _sha256_bytes(prime_response.encode("utf-8")),
        "entry_channel": "Windows Pi",
        "no_mac_relay": True,
        "production_started": False,
        "recorded_at": _utc_now(),
    }
    receipt_path = project_dir / "working" / "pi_entry" / "PRIME_RESUME_RECEIPT.json"
    _atomic_write_json(receipt_path, receipt)
    return receipt


def status_payload(projects_dir: Path, project_id: str | None) -> dict[str, Any]:
    project = resolve_project(projects_dir, project_id)
    gate = show_gate_payload(projects_dir, project["project_id"])
    receipt_path = project["project_dir"] / "working" / "pi_entry" / "PRIME_RESUME_RECEIPT.json"
    return {
        "schema_version": "content-studio-pi-status/v1",
        "project": current_payload(projects_dir, project["project_id"]),
        "sceneplan_gate": {
            "status": gate["checkpoint"]["status"],
            "checkpoint_sha256": gate["checkpoint"]["sha256"],
            "decisions": {cut["cut_id"]: cut["decision"] for cut in gate["cuts"]},
        },
        "prime_resume_receipt": _read_json(receipt_path) if receipt_path.is_file() else None,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs")),
    )
    parser.add_argument("--project-id")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("current")
    sub.add_parser("show-gate")
    sub.add_parser("board")
    lock_parser = sub.add_parser("lock-visuals")
    lock_parser.add_argument("--master-sheet", type=Path, required=True)
    lock_parser.add_argument("--animatic", type=Path, required=False)
    lock_parser.add_argument("--i-am-human", action="store_true")
    apply_parser = sub.add_parser("apply-sceneplan")
    apply_parser.add_argument("--expected-checkpoint-sha256", required=True)
    apply_parser.add_argument("--decisions-json", required=True)
    sub.add_parser("prepare-resume")
    record_parser = sub.add_parser("record-resume")
    record_parser.add_argument("--request-id", required=True)
    record_parser.add_argument("--prime-response", required=True)
    record_parser.add_argument("--evidence-json", required=True)
    sub.add_parser("status")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "current":
            payload = current_payload(args.projects_dir, args.project_id)
        elif args.command == "show-gate":
            payload = show_gate_payload(args.projects_dir, args.project_id)
        elif args.command == "board":
            payload = board_payload(args.projects_dir, args.project_id)
        elif args.command == "lock-visuals":
            payload = lock_visuals(
                args.projects_dir,
                args.project_id,
                master_sheet=args.master_sheet,
                animatic=args.animatic,
                i_am_human=args.i_am_human,
            )
        elif args.command == "apply-sceneplan":
            decisions = json.loads(args.decisions_json)
            payload = apply_sceneplan_decisions(
                args.projects_dir,
                args.project_id,
                args.expected_checkpoint_sha256,
                decisions,
            )
        elif args.command == "prepare-resume":
            payload = prepare_prime_resume(args.projects_dir, args.project_id)
        elif args.command == "record-resume":
            payload = record_prime_resume(
                args.projects_dir,
                args.project_id,
                args.request_id,
                args.prime_response,
                args.evidence_json,
            )
        else:
            payload = status_payload(args.projects_dir, args.project_id)
    except (GatewayError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
