"""LIMITED temporal grammar preflight — OM contract, not taste.

Catches three Phase-1 holes without re-rendering the film:

1. overlay_information_change that measures as STATIC_HOLD → overlay never executed
2. character required on EST but plate is environment_only → coverage hole
3. local-motion cut longer than source without cycle_allowed → silent loop stretch

STATIC_HOLD is still legal when the cut declares intentional_hold.
"""

from __future__ import annotations

from typing import Any

OVERLAY_INTENTS = frozenset({"overlay_information_change"})
HOLD_INTENTS = frozenset({"intentional_hold"})
LOCAL_INTENTS = frozenset({"limited_local_motion", "limited_local_plus_camera"})
STRETCH_RATIO = 1.15


def evaluate_limited_grammar(
    cuts: list[dict[str, Any]],
    temporal_report: dict[str, Any],
) -> dict[str, Any]:
    segments = list(temporal_report.get("segments") or [])
    findings: list[dict[str, Any]] = []
    for cut in cuts:
        if not isinstance(cut, dict):
            continue
        findings.extend(_eval_cut(cut, segments))
    repair_items = [
        {
            "t_start": row["t_start"],
            "t_end": row["t_end"],
            "action": row["repair"],
            "scope": "segment",
            "notes": row["why"],
        }
        for row in findings
    ]
    return {
        "version": "limited-grammar-report/v0.1",
        "ok": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "repair_plan": {
            "version": "repair-plan/v0.1",
            "items": repair_items,
        }
        if repair_items
        else None,
        "judgment": "contract_only",
        "note": "Does not decide if a legal hold is good. Prime does that.",
    }


def _eval_cut(cut: dict[str, Any], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cut_id = str(cut.get("id") or "?")
    t0 = float(cut.get("t_start") or 0)
    t1 = float(cut.get("t_end") or t0)
    intent = str(cut.get("temporal_intent") or "").strip()
    overlapped = _overlap(t0, t1, segments)
    types = {str(seg.get("motion_type")) for seg in overlapped}
    out: list[dict[str, Any]] = []

    if intent in OVERLAY_INTENTS and types and types <= {"STATIC_HOLD"}:
        out.append(_finding(
            cut_id, t0, t1, "overlay_grammar_not_executed",
            "declared overlay_information_change but OM measured STATIC_HOLD for the whole cut",
            "rebuild overlay so type-on/glyph change is temporally measurable (larger HUD, not a still card)",
        ))

    if intent in HOLD_INTENTS and types <= {"STATIC_HOLD", ""}:
        pass

    chars = [c for c in (cut.get("character_ids") or []) if c]
    plate = str(cut.get("plate_kind") or "")
    offscreen = bool(cut.get("characters_offscreen"))
    if chars and plate == "environment_only" and not offscreen:
        out.append(_finding(
            cut_id, t0, t1, "character_missing_from_est",
            f"cut lists {chars} but plate_kind=environment_only and characters_offscreen is false",
            "composite character into EST, or set characters_offscreen=true if they are meant to be absent",
        ))

    source = cut.get("source_seconds")
    cycle = bool(cut.get("cycle_allowed"))
    try:
        source_f = float(source)
    except (TypeError, ValueError):
        source_f = None
    dur = max(0.0, t1 - t0)
    if intent in LOCAL_INTENTS and source_f and not cycle and dur > source_f * STRETCH_RATIO:
        out.append(_finding(
            cut_id, t0, t1, "source_loop_stretch",
            f"cut {dur:.2f}s exceeds source {source_f:.2f}s without cycle_allowed",
            "trim the cut, get a longer temporal source, or explicitly set cycle_allowed for a blink/breath cycle",
        ))
    return out


def _overlap(t0: float, t1: float, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hit = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        a = float(seg.get("t_start") or 0)
        b = float(seg.get("t_end") or a)
        if b > t0 and a < t1:
            hit.append(seg)
    return hit


def _finding(cut_id: str, t0: float, t1: float, failure_class: str, why: str, repair: str) -> dict[str, Any]:
    return {
        "cut_id": cut_id,
        "t_start": round(t0, 3),
        "t_end": round(t1, 3),
        "failure_class": failure_class,
        "why": why,
        "repair": repair,
    }
