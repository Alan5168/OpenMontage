"""Bounded repair: see a bad take, recut once, then A/B.

Foreman is not proven by calling H3. Foreman is proven by:
Rollout 1 → quality Observation → repair proposal → one reroll → Observation 2 → Human A/B.

This module never stamps PRIME_FOREMAN_PROVEN. Alan choosing B after a real
repair does that. Do not invent a blocker so a repair can be exercised.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from lib.dispatch_cut import (
    job_frozen,
    _atomic_write_json,
    _invoke_h3,
    _read_json,
    _rel,
    _see_mp4,
    _sha256_file,
    _utc_now,
)
from lib.h3_context_ir import compile_h3_ir
from lib.prerequisite import active_scene_proposal
from lib.quality_observation import evaluate_quality_observation, last_extracted_still
from lib.reference_atom import compile_performance_h3_spec

REPAIR_SCHEMA = "om-bounded-repair/v1"
LEGAL_REPAIRS = frozenset({"prompt", "temporal_reference", "keyframe", "abandon"})
MAX_REROLLS = 1
BOUND_REACHED = "repair_bound_reached"
NOTHING_TO_REPAIR = "quality_passed_nothing_to_repair"


class RepairError(ValueError):
    """Illegal repair proposal or reroll."""


def _repairs_dir(project_dir: Path) -> Path:
    return project_dir / "working" / "prime_rlm" / "repairs"


def _rollout_dir(project_dir: Path, rollout_id: str) -> Path:
    return project_dir / "working" / "prime_rlm" / "rollouts" / rollout_id


def default_actions(quality: dict[str, Any]) -> list[str]:
    blockers = list(quality.get("blockers") or [])
    if not blockers:
        return []
    if "identity_weak" in blockers or "body_silhouette_only" in str(quality):
        return ["keyframe"]
    if any("eye_shift" in blocker for blocker in blockers):
        return ["prompt"]
    if "gait_failure" in blockers:
        return ["temporal_reference"]
    if any(blocker.endswith("_not_realized") for blocker in blockers):
        return ["prompt"]
    if "character_did_not_move" in blockers:
        return ["prompt"]
    if "identity_drift" in blockers or "face_or_costume_disappear" in blockers:
        return ["prompt"]
    return ["abandon"]


def child_repairs(project_dir: Path, parent_rollout_id: str) -> list[dict[str, Any]]:
    found = []
    root = project_dir / "working" / "prime_rlm" / "rollouts"
    if not root.is_dir():
        return found
    for receipt_path in root.glob("*/RECEIPT.json"):
        row = _read_json(receipt_path)
        if row and row.get("parent_rollout_id") == parent_rollout_id:
            found.append(row)
    return found


def propose_bounded_repair(
    project_dir: Path,
    parent_rollout_id: str,
    *,
    caller: str,
    actions: list[str] | None = None,
    quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if caller != "prime":
        raise RepairError("propose_bounded_repair is a Prime production action; Cursor cannot impersonate Prime")
    if job_frozen(project_dir):
        raise RepairError("job is frozen; do not repair a frozen harness-acceptance job")
    parent = _read_json(_rollout_dir(project_dir, parent_rollout_id) / "RECEIPT.json")
    if not parent:
        raise RepairError(f"parent rollout missing: {parent_rollout_id}")
    observation = _read_json(_rollout_dir(project_dir, parent_rollout_id) / "OBSERVATION.json") or {}
    quality = quality or observation.get("quality") or {}
    if quality.get("beat_realization_unresolved"):
        raise RepairError(
            "temporal_beat_realization_unresolved: not a content FAIL; "
            "do not spend the bounded repair quota on a missing probe"
        )
    if quality.get("passed") is True:
        raise RepairError(NOTHING_TO_REPAIR)
    if "passed" not in quality:
        raise RepairError(
            "observation_incomplete: no quality verdict; "
            "bounded repair quota is for the work, not the observer"
        )
    if not (quality.get("blockers") or []):
        raise RepairError("quality observation missing blockers; refuse to invent a repair")
    if len(child_repairs(project_dir, parent_rollout_id)) >= MAX_REROLLS:
        raise RepairError(BOUND_REACHED)
    chosen = list(actions or default_actions(quality))
    if not chosen:
        raise RepairError(NOTHING_TO_REPAIR)
    illegal = [row for row in chosen if row not in LEGAL_REPAIRS]
    if illegal:
        raise RepairError(f"illegal repair: {illegal}; legal={sorted(LEGAL_REPAIRS)}")
    if len(chosen) != 1:
        raise RepairError("bounded repair is one action, then A/B; do not stack departments")
    action = chosen[0]
    payload = {
        "schema_version": REPAIR_SCHEMA,
        "status": "PROPOSAL",
        "caller": caller,
        "parent_rollout_id": parent_rollout_id,
        "shot_id": parent.get("shot_id"),
        "action": action,
        "legal_repairs": sorted(LEGAL_REPAIRS),
        "max_rerolls": MAX_REROLLS,
        "retry": action in {"prompt", "temporal_reference"},
        "generate": False,
        "blockers": list(quality.get("blockers") or []),
        "quality_passed": False,
        "foreman_proven": False,
        "created_at": _utc_now(),
        "note": (
            "One bounded recut. keyframe waits for a readable still. "
            "abandon ends the take. prompt/temporal_reference may reroll H3 once. "
            "Not PRIME_FOREMAN_PROVEN unless a real blocker existed and Alan chooses B."
        ),
    }
    path = _repairs_dir(project_dir) / f"{parent_rollout_id}.json"
    _atomic_write_json(path, payload)
    return {**payload, "written": True, "proposal_path": str(path)}


def _observation_brief(observation: dict[str, Any] | None) -> str:
    quality = (observation or {}).get("quality") or {}
    blockers = [str(row) for row in (quality.get("blockers") or []) if str(row).strip()]
    if blockers:
        return "blockers: " + ", ".join(blockers)
    if quality.get("passed") is True:
        return "no contract blocker"
    return str(quality.get("note") or "observation recorded")


def write_ab_pair(
    project_dir: Path,
    *,
    parent_rollout_id: str,
    child_rollout_id: str,
    repair_dimension: str,
) -> dict[str, Any]:
    """A = original rollout. B = the single repaired rollout. No renamed candidates."""
    parent = _read_json(_rollout_dir(project_dir, parent_rollout_id) / "RECEIPT.json") or {}
    child = _read_json(_rollout_dir(project_dir, child_rollout_id) / "RECEIPT.json") or {}
    parent_obs = _read_json(_rollout_dir(project_dir, parent_rollout_id) / "OBSERVATION.json") or {}
    child_obs = _read_json(_rollout_dir(project_dir, child_rollout_id) / "OBSERVATION.json") or {}
    shot_id = str(parent.get("shot_id") or child.get("shot_id") or "")
    payload = {
        "schema_version": "om-ab-pair/v1",
        "shot_id": shot_id,
        "target": f"ab:{shot_id}",
        "A": {
            "role": "original",
            "rollout_id": parent_rollout_id,
            "output_hash": parent.get("output_hash"),
            "observation_summary": _observation_brief(parent_obs),
            "repair_dimension": None,
        },
        "B": {
            "role": "repaired",
            "rollout_id": child_rollout_id,
            "output_hash": child.get("output_hash"),
            "observation_summary": _observation_brief(child_obs),
            "repair_dimension": repair_dimension,
        },
        "foreman_proven": False,
        "studio_v1": False,
        "note": (
            "A = original S2 rollout. B = the single repaired S2 rollout. "
            "Do not rename two new candidates. Do not draw a third take."
        ),
        "created_at": _utc_now(),
    }
    path = project_dir / "working" / "prime_rlm" / "AB_PAIR.json"
    _atomic_write_json(path, payload)
    return payload


def dispatch_bounded_repair(
    project_dir: Path,
    root: Path,
    parent_rollout_id: str,
    *,
    caller: str,
    invoke_h3: Callable[[dict[str, Any]], Any] | None = None,
    see_fn: Callable[[Path, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute one legal repair. Does not stamp PRIME_FOREMAN_PROVEN."""
    if caller != "prime":
        raise RepairError("dispatch_bounded_repair is a Prime production action; Cursor cannot impersonate Prime")
    if job_frozen(project_dir):
        raise RepairError("job is frozen; do not repair a frozen harness-acceptance job")
    proposal = _read_json(_repairs_dir(project_dir) / f"{parent_rollout_id}.json")
    if not proposal or proposal.get("status") != "PROPOSAL":
        raise RepairError("repair proposal missing; propose_bounded_repair first")
    if len(child_repairs(project_dir, parent_rollout_id)) >= MAX_REROLLS:
        raise RepairError(BOUND_REACHED)
    action = str(proposal.get("action") or "")
    parent = _read_json(_rollout_dir(project_dir, parent_rollout_id) / "RECEIPT.json") or {}
    shot_id = str(parent.get("shot_id") or proposal.get("shot_id") or "")
    if action == "abandon":
        payload = {
            "schema_version": REPAIR_SCHEMA,
            "status": "abandoned",
            "parent_rollout_id": parent_rollout_id,
            "shot_id": shot_id,
            "action": "abandon",
            "foreman_proven": False,
            "created_at": _utc_now(),
        }
        path = _repairs_dir(project_dir) / f"{parent_rollout_id}.result.json"
        _atomic_write_json(path, payload)
        return payload
    if action == "keyframe":
        payload = {
            "schema_version": REPAIR_SCHEMA,
            "status": "blocked",
            "error": "repair_requires_readable_keyframe",
            "parent_rollout_id": parent_rollout_id,
            "shot_id": shot_id,
            "action": "keyframe",
            "next_step": "produce a PERFORMANCE-readable start still, then compile again",
            "foreman_proven": False,
            "created_at": _utc_now(),
        }
        path = _repairs_dir(project_dir) / f"{parent_rollout_id}.result.json"
        _atomic_write_json(path, payload)
        return payload
    if action not in {"prompt", "temporal_reference"}:
        raise RepairError(f"cannot dispatch repair action {action}")

    scene = active_scene_proposal(project_dir) or {}
    shot = next(
        (row for row in (scene.get("shots") or []) if str(row.get("id")) == shot_id),
        {"id": shot_id, "performance_intent": "controlled approach, then stop"},
    )
    first_path = None
    for candidate in (
        project_dir / "working" / "prime_rlm" / "start_frames" / f"{shot_id}.png",
        project_dir / str(shot.get("start_frame_ref") or ""),
    ):
        if candidate.is_file():
            first_path = candidate
            break
    if first_path is None:
        raise RepairError("repair reroll needs a start still")

    from lib.keyframe_presentation import PRESENTATION_UNUSABLE, evaluate_keyframe_presentation

    presentation = evaluate_keyframe_presentation(first_path, framing="medium_close")
    if presentation.get("usable") is not True:
        raise RepairError(PRESENTATION_UNUSABLE + ": " + ", ".join(presentation.get("blockers") or []))

    duration = float((parent.get("config") or {}).get("duration_seconds") or 5.0)
    spec = compile_performance_h3_spec(
        shot,
        first_frame=str(first_path),
        last_frame=None,
        duration_seconds=duration,
    )
    if action == "prompt":
        spec["overview"] = (
            str(spec.get("overview") or "")
            + " Keep identity and costume from Picture 1. Do not lose the face."
        ).strip()
    h3_ir = compile_h3_ir(spec)
    child_id = f"{shot_id.lower()}-r1-{os.urandom(4).hex()}"
    out_dir = _rollout_dir(project_dir, child_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{shot_id}.mp4"
    inputs = {
        "operation": "image_to_video",
        "workflow_model": "minimax-h3",
        "h3_ir": spec,
        "reference_image_path": str(first_path),
        "output_path": str(output_path),
        "project_dir": str(project_dir),
        "parent_rollout_id": parent_rollout_id,
        "repair_action": action,
    }
    result = (invoke_h3 or _invoke_h3)(inputs)
    success = bool(getattr(result, "success", False))
    receipt = {
        "schema_version": "om-rollout-receipt/v1",
        "action": "dispatch_bounded_repair",
        "rollout_id": child_id,
        "parent_rollout_id": parent_rollout_id,
        "shot_id": shot_id,
        "caller": caller,
        "retry": True,
        "repair_action": action,
        "status": "succeeded" if success and output_path.is_file() else "failed",
        "generate": False,
        "foreman_proven": False,
        "output_path": _rel(output_path, root) if output_path.is_file() else None,
        "output_hash": _sha256_file(output_path) if output_path.is_file() else None,
        "created_at": _utc_now(),
        "note": "Bounded reroll 1/1. Not APPROVED. Not PRIME_FOREMAN_PROVEN.",
    }
    if receipt["status"] != "succeeded":
        receipt["error"] = getattr(result, "error", None) or "H3 produced no output"
        _atomic_write_json(out_dir / "RECEIPT.json", receipt)
        return receipt

    see_dir = out_dir / "see"
    see = (see_fn or _see_mp4)(output_path, see_dir)
    from lib.dispatch_cut import _observation_summary

    observation = _observation_summary(
        rollout_id=child_id,
        output_path=output_path,
        output_hash=receipt["output_hash"],
        see=see,
        see_dir=see_dir,
        root=root,
    )
    packet = see.get("frame_packet") or {}
    quality = evaluate_quality_observation(
        contract=shot,
        observation=observation,
        temporal=see.get("temporal_motion_report") or {},
        start_still=first_path,
        last_still=last_extracted_still(packet),
        framing="medium_close",
    )
    observation["quality"] = quality
    observation["parent_rollout_id"] = parent_rollout_id
    observation_path = out_dir / "OBSERVATION.json"
    _atomic_write_json(observation_path, observation)
    receipt["observation_path"] = _rel(observation_path, root)
    receipt["quality_passed"] = bool(quality.get("passed"))
    receipt["awaiting_human_ab"] = True
    _atomic_write_json(out_dir / "RECEIPT.json", receipt)
    proposal["status"] = "DISPATCHED"
    proposal["child_rollout_id"] = child_id
    _atomic_write_json(_repairs_dir(project_dir) / f"{parent_rollout_id}.json", proposal)
    ab_pair = write_ab_pair(
        project_dir,
        parent_rollout_id=parent_rollout_id,
        child_rollout_id=child_id,
        repair_dimension=action,
    )
    return {
        **receipt,
        "observation": observation,
        "awaiting_human_ab": True,
        "ab_pair": ab_pair,
        "foreman_proven": False,
        "studio_v1": False,
        "written": True,
    }
