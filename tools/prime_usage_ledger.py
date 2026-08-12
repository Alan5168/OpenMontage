"""Summarize parent/child/total token usage from a Prime session .jsonl.

Does not invent numbers. Missing fields stay marked missing.
When child_usage_attributed events exist, assistant message.usage is treated as
aggregate (may already fold child tokens); child_tokens are the explicit
childUsage breakout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _empty_bucket() -> dict[str, Any]:
    return {"input": 0, "output": 0, "total": 0, "missing": True}


def _add_usage(bucket: dict[str, Any], usage: dict[str, Any] | None) -> None:
    if not isinstance(usage, dict):
        return
    inp = usage.get("input")
    out = usage.get("output")
    total = usage.get("totalTokens")
    if total is None:
        total = usage.get("total")
    if inp is None and out is None and total is None:
        return
    bucket["missing"] = False
    try:
        if inp is not None:
            bucket["input"] += int(inp)
        if out is not None:
            bucket["output"] += int(out)
        if total is not None:
            bucket["total"] += int(total)
        elif inp is not None and out is not None:
            bucket["total"] += int(inp) + int(out)
    except (TypeError, ValueError):
        return


def _add_cost(cost_bucket: dict[str, Any], usage: dict[str, Any] | None) -> None:
    if not isinstance(usage, dict):
        return
    cost = usage.get("cost")
    if not isinstance(cost, dict):
        return
    total = cost.get("total")
    if total is None:
        return
    try:
        cost_bucket["total"] = float(cost_bucket.get("total") or 0) + float(total)
        cost_bucket["missing"] = False
    except (TypeError, ValueError):
        return


def summarize_session_usage(session_file: str | Path) -> dict[str, Any]:
    path = Path(session_file)
    assistant = _empty_bucket()
    child = _empty_bucket()
    aggregate_from_attr = _empty_bucket()
    cost = {"total": 0.0, "missing": True}
    events = 0
    child_events = 0
    if not path.is_file():
        return {
            "session_file": str(path),
            "parent_tokens": _empty_bucket(),
            "child_tokens": _empty_bucket(),
            "aggregate_tokens": _empty_bucket(),
            "provider_cost_or_plan_usage": None,
            "wall_seconds": None,
            "events_scanned": 0,
            "status": "MISSING_SESSION",
        }

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        events += 1
        etype = obj.get("type")
        if etype == "child_usage_attributed":
            child_events += 1
            _add_usage(child, obj.get("childUsage") or obj.get("child_usage"))
            _add_usage(aggregate_from_attr, obj.get("aggregateUsage") or obj.get("aggregate_usage"))
            _add_cost(cost, obj.get("aggregateUsage") or obj.get("childUsage"))
            continue
        message = obj.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            _add_usage(assistant, message["usage"])
            _add_cost(cost, message["usage"])
        elif isinstance(obj.get("usage"), dict):
            _add_usage(assistant, obj["usage"])
            _add_cost(cost, obj["usage"])

    if child_events:
        # Assistant usage already folds child in Prime; expose child as breakout.
        aggregate = assistant if not assistant["missing"] else aggregate_from_attr
        parent = {
            "input": max(0, aggregate["input"] - child["input"]),
            "output": max(0, aggregate["output"] - child["output"]),
            "total": max(0, aggregate["total"] - child["total"]),
            "missing": aggregate["missing"],
            "note": "derived_as_aggregate_minus_child",
        }
    else:
        parent = assistant
        aggregate = {
            "input": parent["input"] + child["input"],
            "output": parent["output"] + child["output"],
            "total": parent["total"] + child["total"],
            "missing": parent["missing"] and child["missing"],
        }

    return {
        "session_file": str(path.resolve()),
        "parent_tokens": parent,
        "child_tokens": child,
        "aggregate_tokens": aggregate,
        "provider_cost_or_plan_usage": None if cost["missing"] else {"total_cost": cost["total"]},
        "wall_seconds": None,
        "events_scanned": events,
        "child_usage_events": child_events,
        "status": "OK" if not aggregate.get("missing", True) else "MISSING_USAGE_FIELDS",
    }
