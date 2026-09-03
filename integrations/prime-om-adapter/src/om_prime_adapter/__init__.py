"""Prime-callable OpenMontage adapter. OM is the only canonical writer."""

from __future__ import annotations

from typing import Any

from .adapter import (
    AdapterError,
    compile_cut,
    complete_observation,
    compose_scene,
    dispatch_bounded_repair,
    dispatch_cut,
    get_gate,
    get_human_preference,
    load_stage_pack,
    open_job,
    produce_keyframe,
    propose_bounded_repair,
    propose_identity_candidates,
    query_casebook,
    record_human_preference,
    record_lesson_candidate,
    resume_prime,
    submit_gate_decision,
    submit_prerequisite_plan,
    submit_revision_proposal,
    submit_scene_proposal,
    submit_stage_artifact,
)
from .context import build_context_variables, mark_stale, reload_context, slice_variable
from .openviking import openviking_health, read_openviking, search_openviking

__all__ = [
    "AdapterError",
    "open_job",
    "compile_cut",
    "complete_observation",
    "compose_scene",
    "dispatch_cut",
    "dispatch_bounded_repair",
    "submit_prerequisite_plan",
    "propose_identity_candidates",
    "propose_bounded_repair",
    "produce_keyframe",
    "submit_scene_proposal",
    "submit_revision_proposal",
    "record_human_preference",
    "get_human_preference",
    "load_stage_pack",
    "query_casebook",
    "submit_stage_artifact",
    "record_lesson_candidate",
    "get_gate",
    "submit_gate_decision",
    "resume_prime",
    "build_context_variables",
    "reload_context",
    "mark_stale",
    "slice_variable",
    "openviking_health",
    "search_openviking",
    "read_openviking",
    "run",
]


def run(action: str, **kwargs: Any) -> Any:
    """Dispatch adapter actions for Prime IPython / CLI."""
    table = {
        "open_job": open_job,
        "compile_cut": compile_cut,
        "complete_observation": complete_observation,
        "compose_scene": compose_scene,
        "dispatch_cut": dispatch_cut,
        "dispatch_bounded_repair": dispatch_bounded_repair,
        "submit_prerequisite_plan": submit_prerequisite_plan,
        "propose_identity_candidates": propose_identity_candidates,
        "propose_bounded_repair": propose_bounded_repair,
        "produce_keyframe": produce_keyframe,
        "submit_scene_proposal": submit_scene_proposal,
        "submit_revision_proposal": submit_revision_proposal,
        "record_human_preference": record_human_preference,
        "get_human_preference": get_human_preference,
        "load_stage_pack": load_stage_pack,
        "query_casebook": query_casebook,
        "submit_stage_artifact": submit_stage_artifact,
        "record_lesson_candidate": record_lesson_candidate,
        "get_gate": get_gate,
        "submit_gate_decision": submit_gate_decision,
        "resume_prime": resume_prime,
        "build_context_variables": build_context_variables,
        "reload_context": reload_context,
        "mark_stale": mark_stale,
        "slice_variable": slice_variable,
        "openviking_health": openviking_health,
        "search_openviking": search_openviking,
        "read_openviking": read_openviking,
    }
    if action not in table:
        raise AdapterError(f"Unknown action: {action}")
    return table[action](**kwargs)
