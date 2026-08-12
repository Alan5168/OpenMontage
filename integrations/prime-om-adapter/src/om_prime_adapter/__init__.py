"""Prime-callable OpenMontage adapter. OM is the only canonical writer."""

from __future__ import annotations

from typing import Any

from .adapter import (
    AdapterError,
    get_gate,
    load_stage_pack,
    open_job,
    query_casebook,
    record_lesson_candidate,
    resume_prime,
    submit_gate_decision,
    submit_stage_artifact,
)
from .context import build_context_variables, mark_stale, reload_context, slice_variable

__all__ = [
    "AdapterError",
    "open_job",
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
    "run",
]


def run(action: str, **kwargs: Any) -> Any:
    """Dispatch adapter actions for Prime IPython / CLI."""
    table = {
        "open_job": open_job,
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
    }
    if action not in table:
        raise AdapterError(f"Unknown action: {action}")
    return table[action](**kwargs)
