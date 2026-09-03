"""Small PERFORMANCE directing atoms. Not a reference library.

ContentIR → keyframe → temporal reference → H3.
A one-line 'walks ominously' is not a temporal reference.
"""

from __future__ import annotations

import re
from typing import Any

REFERENCE_ATOM_SCHEMA = "om-reference-atom/v1"

ATOMS: dict[str, dict[str, Any]] = {
    "freeze_notice": {
        "id": "freeze_notice",
        "action": (
            "Hold. The body does not travel. Eyes register the other person. "
            "Weight stays planted. No walk cycle yet."
        ),
        "locomotion": False,
    },
    "breath_tension": {
        "id": "breath_tension",
        "action": (
            "Chest and shoulders show one restrained breath. Face stays readable. "
            "No smile. No walk."
        ),
        "locomotion": False,
    },
    "weight_shift": {
        "id": "weight_shift",
        "action": (
            "Weight shifts onto the leading foot. Hips prepare. "
            "The trailing foot has not yet taken a full traveling step."
        ),
        "locomotion": False,
    },
    "one_step": {
        "id": "one_step",
        "action": (
            "One controlled step only. Alternate legs. No opposite-arm same-leg swing. "
            "Then the traveling foot plants."
        ),
        "locomotion": True,
    },
    "two_step_stop": {
        "id": "two_step_stop",
        "action": (
            "Two short steps, then a complete stop. Feet plant. "
            "Do not continue into a long walk cycle."
        ),
        "locomotion": True,
    },
    "controlled_approach": {
        "id": "controlled_approach",
        "action": (
            "Controlled approach: alternate left and right legs, opposite-arm swing, "
            "unhurried. The figure grows in frame. No skating. No same-side gait."
        ),
        "locomotion": True,
    },
    "decelerate_stop": {
        "id": "decelerate_stop",
        "action": (
            "Decelerate. Last half-step. Stop. Hold eye contact. "
            "Feet planted. Do not keep walking."
        ),
        "locomotion": True,
    },
    "eye_shift_hold": {
        "id": "eye_shift_hold",
        "action": (
            "Eyes shift, then hold. Mouth state unchanged. Shoulders settle. "
            "Almost no travel."
        ),
        "locomotion": False,
    },
}

_DEFAULT_APPROACH = (
    ("freeze_notice", 1.0),
    ("weight_shift", 2.0),
    ("controlled_approach", 3.0),
    ("decelerate_stop", 2.0),
)

_LOCO_POS = re.compile(r"\b(walks|walking|walk|approaches|approach|locomotion|stride|steps?)\b")
_LOCO_NEG = re.compile(r"\bno locomotion\b|\bno walk\b|\bdoes not walk\b|\bnot a walk\b|\bno walk cycle\b")


def atom(atom_id: str) -> dict[str, Any]:
    row = ATOMS.get(atom_id)
    if row is None:
        raise ValueError(f"unknown ReferenceAtom: {atom_id}")
    return dict(row)


def locomotion_declared(text: str) -> bool:
    lowered = (text or "").lower()
    if _LOCO_NEG.search(lowered) and not re.search(r"\b(walks|walking|approaches)\b", lowered):
        return False
    return bool(_LOCO_POS.search(lowered))


def infer_atom_ids(shot: dict[str, Any]) -> list[str]:
    declared = shot.get("reference_atoms") or shot.get("temporal_reference")
    if isinstance(declared, list) and declared:
        ids = []
        for row in declared:
            if isinstance(row, str):
                ids.append(row)
            elif isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
        if ids:
            return ids
    intent = " ".join(
        str(shot.get(key) or "")
        for key in ("performance_intent", "visual_intent", "action")
    )
    if locomotion_declared(intent):
        if "one step" in intent.lower() or "one-step" in intent.lower():
            return ["freeze_notice", "one_step", "decelerate_stop"]
        if "two step" in intent.lower() or "two-step" in intent.lower():
            return ["weight_shift", "two_step_stop"]
        return [row[0] for row in _DEFAULT_APPROACH]
    return ["freeze_notice", "breath_tension", "eye_shift_hold"]


def compile_temporal_reference(
    shot: dict[str, Any],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    duration = max(4.0, min(15.0, float(duration_seconds)))
    ids = infer_atom_ids(shot)
    weights = []
    for atom_id in ids:
        spec = atom(atom_id)
        default = next((span for key, span in _DEFAULT_APPROACH if key == atom_id), 1.0)
        weights.append((spec, float(default)))
    total = sum(span for _, span in weights) or 1.0
    shots = []
    t = 0.0
    locomotion = False
    for spec, span in weights:
        length = duration * (span / total)
        t1 = min(duration, t + length)
        shots.append(
            {
                "t0": round(t, 3),
                "t1": round(t1, 3),
                "framing": shot.get("framing") or _framing(shot),
                "action": spec["action"],
                "atom_id": spec["id"],
            }
        )
        locomotion = locomotion or bool(spec["locomotion"])
        t = t1
    if shots:
        shots[-1]["t1"] = round(duration, 3)
    return {
        "schema_version": REFERENCE_ATOM_SCHEMA,
        "atom_ids": ids,
        "shots": shots,
        "locomotion": locomotion or locomotion_declared(
            str(shot.get("performance_intent") or shot.get("visual_intent") or "")
        ),
        "duration_seconds": duration,
        "note": "Provider-neutral beats. Not a motion library. Ref2VA can replace atoms later.",
    }


def compile_performance_h3_spec(
    shot: dict[str, Any],
    *,
    first_frame: str | None,
    last_frame: str | None,
    duration_seconds: float,
) -> dict[str, Any]:
    temporal = compile_temporal_reference(shot, duration_seconds=duration_seconds)
    avoid = ["smile", "push-in", "png loop", "ken burns as walk"]
    if not temporal["locomotion"]:
        avoid.append("walk cycle")
    return {
        "mode": "fl2va" if last_frame else "i2va",
        "duration_seconds": temporal["duration_seconds"],
        "first_frame": first_frame,
        "last_frame": last_frame,
        "overview": shot.get("visual_intent") or shot.get("performance_intent") or "",
        "identity": _identity_for_performance(shot),
        "camera": "locked-off static",
        "style": "limited TV anime",
        "avoid": avoid,
        "locomotion": temporal["locomotion"],
        "temporal_reference": temporal,
        "shots": temporal["shots"],
    }


def _identity_for_performance(shot: dict[str, Any]) -> dict[str, Any]:
    from lib.character_variant import identity_from_variant

    ident = identity_from_variant(shot)
    if ident.get("name"):
        return ident
    return {"name": (shot.get("character_ids") or ["lucien_mercer"])[0]}


def _framing(shot: dict[str, Any]) -> str:
    raw = str(shot.get("shot_size") or shot.get("framing") or "").lower()
    if raw in {"mcu", "medium_close", "medium close-up", "close_up"}:
        return "medium close-up"
    if raw in {"ms", "medium", "medium_shot"}:
        return "medium shot"
    if "insert" in raw:
        return "insert"
    if locomotion_declared(str(shot.get("performance_intent") or shot.get("visual_intent") or "")):
        return "full body"
    return "medium close-up"
