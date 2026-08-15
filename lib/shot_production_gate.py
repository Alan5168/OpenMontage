"""Fail-closed visual-constraint gate for the Limited Anime Studio.

A cut cannot leave planning — and cannot reach video_selector / H3 /
video_compose — until the job has a locked master sheet + animatic and
the cut itself has approved stills on disk. Stored `render_allowed: true`
cannot bypass missing files. No new pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PLANNING = "planning"
UNCLASSIFIED = "unclassified"

LIMITED_ANIME_PIPELINES = frozenset({"anime-hybrid"})
LIMITED_ANIME_PROFILES = frozenset({"fiction_anime_episode"})

MASTER_SHEET_UNLOCKED = "master_sheet_unlocked"
MASTER_SHEET_MISSING = "master_sheet_file_missing"
ANIMATIC_UNLOCKED = "animatic_unlocked"
ANIMATIC_MISSING = "animatic_file_missing"
PLACEHOLDER_REF = "visual_ref_placeholder"
VISUAL_REF_NOT_LOCAL = "visual_ref_not_local_image"
START_STILL_MISSING = "approved_start_still_missing"
END_STILL_MISSING = "approved_end_still_missing"
CHARACTER_IDS_MISSING = "character_ids_missing"
ANIMATION_CLASS_MISSING = "animation_class_missing"


class ShotGateError(ValueError):
    """Cut is still in planning; motion/render is illegal."""


def gate_applies(scene_plan: dict[str, Any] | None, scenes: list[Any] | None = None) -> bool:
    """True when this plan is on the Limited Anime Studio path."""
    plan = scene_plan if isinstance(scene_plan, dict) else {}
    meta = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
    rows = scenes if scenes is not None else plan.get("scenes") or []
    if meta.get("pipeline") in LIMITED_ANIME_PIPELINES:
        return True
    if meta.get("profile") in LIMITED_ANIME_PROFILES:
        return True
    if meta.get("limited_anime_studio") is True:
        return True
    if "render_allowed" in meta:
        return True
    return any(isinstance(row, dict) and row.get("animation_class") for row in rows)


def resolve_media_path(project_dir: Path | None, ref: str | None) -> Path | None:
    if not ref or not str(ref).strip():
        return None
    raw = Path(str(ref).strip())
    candidates = [raw]
    if project_dir is not None:
        candidates.append(Path(project_dir) / raw)
    for candidate in candidates:
        try:
            resolved = candidate.expanduser()
            if resolved.is_file():
                return resolved
        except OSError:
            continue
    return None


def job_blockers(scene_plan: dict[str, Any] | None, project_dir: Path | None = None) -> list[str]:
    plan = scene_plan if isinstance(scene_plan, dict) else {}
    meta = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
    blockers: list[str] = []
    sheet = meta.get("master_sheet_path")
    if not _locked(meta.get("master_sheet_locked")) and not sheet:
        blockers.append(MASTER_SHEET_UNLOCKED)
    elif resolve_media_path(project_dir, sheet) is None:
        blockers.append(MASTER_SHEET_MISSING if sheet else MASTER_SHEET_UNLOCKED)
    animatic = meta.get("animatic_path")
    if not _locked(meta.get("animatic_locked")) and not animatic:
        blockers.append(ANIMATIC_UNLOCKED)
    elif resolve_media_path(project_dir, animatic) is None:
        blockers.append(ANIMATIC_MISSING if animatic else ANIMATIC_UNLOCKED)
    return blockers


def evaluate_cut(
    scene: dict[str, Any],
    *,
    scene_plan: dict[str, Any] | None = None,
    project_dir: Path | None = None,
    job: list[str] | None = None,
) -> dict[str, Any]:
    """Return planning vs dispatch state for one cut. Never raises for missing stills."""
    cut_id = scene.get("id")
    planned_class = str(scene.get("animation_class") or "").strip().upper() or None
    plan = scene_plan if isinstance(scene_plan, dict) else {"scenes": [scene], "metadata": {}}
    applies = gate_applies(plan, [scene])
    ordered: list[str] = []
    if applies:
        blockers = list(job if job is not None else job_blockers(plan, project_dir))
        blockers.extend(_cut_blockers(scene, project_dir))
        seen: set[str] = set()
        for item in blockers:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
    production_ready = applies and planned_class is not None and not ordered
    return {
        "cut_id": cut_id,
        "planned_class": planned_class,
        "production_ready": production_ready,
        "blockers": ordered,
        "applies": applies,
    }


def evaluate_plan(scene_plan: dict[str, Any] | None, project_dir: Path | None = None) -> dict[str, Any]:
    plan = scene_plan if isinstance(scene_plan, dict) else {"scenes": []}
    scenes = [row for row in (plan.get("scenes") or []) if isinstance(row, dict)]
    job = job_blockers(plan, project_dir)
    cuts = [
        evaluate_cut(scene, scene_plan=plan, project_dir=project_dir, job=job)
        for scene in scenes
    ]
    dispatchable = [row["cut_id"] for row in cuts if row["production_ready"]]
    planning = [
        row["cut_id"]
        for row in cuts
        if row["planned_class"] and not row["production_ready"]
    ]
    unclassified = [row["cut_id"] for row in cuts if not row["planned_class"]]
    return {
        "applies": gate_applies(plan, scenes),
        "job_blockers": job,
        "cuts": cuts,
        "dispatchable_cut_ids": dispatchable,
        "planning_cut_ids": planning,
        "unclassified_cut_ids": unclassified,
        "render_allowed": bool(dispatchable),
    }


def assert_dispatch(
    scene_plan: dict[str, Any],
    *,
    project_dir: Path | None = None,
    cut_ids: list[str] | None = None,
) -> None:
    """Raise if the named cuts (or every non-omitted cut) cannot leave planning."""
    if not gate_applies(scene_plan):
        return
    scenes = [row for row in (scene_plan.get("scenes") or []) if isinstance(row, dict)]
    by_id = {str(row.get("id")): row for row in scenes if row.get("id")}
    if cut_ids is not None:
        missing = [cut_id for cut_id in cut_ids if cut_id not in by_id]
        if missing:
            raise ShotGateError(f"unknown cut_ids for dispatch: {missing}")
        targets = [by_id[cut_id] for cut_id in cut_ids]
    else:
        targets = [row for row in scenes if row.get("review_decision") != "omit"]
    job = job_blockers(scene_plan, project_dir)
    lines: list[str] = []
    for scene in targets:
        row = evaluate_cut(scene, scene_plan=scene_plan, project_dir=project_dir, job=job)
        if row["production_ready"]:
            continue
        label = row["cut_id"] or "?"
        detail = ",".join(row["blockers"] or [ANIMATION_CLASS_MISSING])
        lines.append(f"{label}:{detail}")
    if lines:
        raise ShotGateError(
            "visual-constraint gate blocked dispatch — shot stays in planning: "
            + "; ".join(lines)
        )


def motion_dispatch_error(inputs: dict[str, Any], *, cut_ids: list[str] | None = None) -> str | None:
    """Tool-facing helper. None means the caller may proceed."""
    plan = _coerce_plan(inputs.get("scene_plan"))
    project_dir = _project_dir_from(inputs)
    requested_cut = inputs.get("cut_id")
    ids = cut_ids
    if ids is None and requested_cut:
        ids = [str(requested_cut)]
    if plan is None:
        if inputs.get("animation_class") or requested_cut:
            return "visual-constraint gate blocked dispatch: scene_plan is required to leave planning"
        return None
    if not gate_applies(plan):
        return None
    try:
        assert_dispatch(plan, project_dir=project_dir, cut_ids=ids)
    except ShotGateError as exc:
        return str(exc)
    return None


def _coerce_plan(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict) and isinstance(raw.get("scenes"), list):
        return raw
    if isinstance(raw, list):
        return {"scenes": raw, "metadata": {}}
    return None


def _project_dir_from(inputs: dict[str, Any]) -> Path | None:
    for key in ("project_dir", "pipeline_dir", "projects_dir"):
        value = inputs.get(key)
        if value:
            return Path(str(value))
    return None


def _locked(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "locked"}


def _cut_blockers(scene: dict[str, Any], project_dir: Path | None) -> list[str]:
    blockers: list[str] = []
    planned = str(scene.get("animation_class") or "").strip()
    if not planned:
        blockers.append(ANIMATION_CLASS_MISSING)
    visual = scene.get("visual_ref") if isinstance(scene.get("visual_ref"), dict) else {}
    kind = str(visual.get("kind") or "").strip().lower()
    if kind in {"", "placeholder"}:
        blockers.append(PLACEHOLDER_REF)
    elif kind != "local_image":
        blockers.append(VISUAL_REF_NOT_LOCAL)
    start_ref = scene.get("start_frame_ref") or visual.get("path")
    if resolve_media_path(project_dir, start_ref) is None:
        blockers.append(START_STILL_MISSING)
    planned_class = planned.upper()
    if planned_class == "LIMITED":
        end_ref = scene.get("end_frame_ref")
        if resolve_media_path(project_dir, end_ref) is None:
            blockers.append(END_STILL_MISSING)
    if scene.get("type") == "character_scene":
        ids = scene.get("character_ids")
        if not isinstance(ids, list) or not [item for item in ids if str(item).strip()]:
            blockers.append(CHARACTER_IDS_MISSING)
    return blockers
