from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.limited_grammar import evaluate_limited_grammar
from schemas.artifacts import validate_artifact


def _report(*types_and_times):
    segs = []
    motion = {}
    for i, (t0, t1, kind) in enumerate(types_and_times, start=1):
        segs.append({"t_start": t0, "t_end": t1, "motion_type": kind})
        motion[f"segment_{i}"] = kind
    return {"segments": segs, "motion_type": motion}


def test_overlay_static_is_not_executed():
    cuts = [{
        "id": "A1", "t_start": 0, "t_end": 2.5,
        "temporal_intent": "overlay_information_change",
    }]
    out = evaluate_limited_grammar(cuts, _report((0, 2.5, "STATIC_HOLD")))
    assert not out["ok"]
    assert out["findings"][0]["failure_class"] == "overlay_grammar_not_executed"


def test_intentional_hold_is_legal():
    cuts = [{
        "id": "A2", "t_start": 2.5, "t_end": 4.5,
        "temporal_intent": "intentional_hold",
    }]
    out = evaluate_limited_grammar(cuts, _report((2.5, 4.5, "STATIC_HOLD")))
    assert out["ok"]


def test_est_missing_character():
    cuts = [{
        "id": "A4", "t_start": 12, "t_end": 17,
        "temporal_intent": "camera_only",
        "character_ids": ["avery_sterling"],
        "plate_kind": "environment_only",
        "characters_offscreen": False,
    }]
    out = evaluate_limited_grammar(cuts, _report((12, 17, "LIMITED_LOCAL_MOTION")))
    assert out["findings"][0]["failure_class"] == "character_missing_from_est"
    off = dict(cuts[0], characters_offscreen=True)
    assert evaluate_limited_grammar([off], _report((12, 17, "LIMITED_LOCAL_MOTION")))["ok"]


def test_source_loop_stretch_requires_cycle_flag():
    cuts = [{
        "id": "A5", "t_start": 17, "t_end": 25,
        "temporal_intent": "limited_local_motion",
        "source_seconds": 5.0,
        "cycle_allowed": False,
    }]
    out = evaluate_limited_grammar(cuts, _report((17, 25, "LIMITED_LOCAL_MOTION")))
    assert out["findings"][0]["failure_class"] == "source_loop_stretch"
    cycled = dict(cuts[0], cycle_allowed=True)
    assert evaluate_limited_grammar([cycled], _report((17, 25, "LIMITED_LOCAL_MOTION")))["ok"]


if __name__ == "__main__":
    test_overlay_static_is_not_executed()
    test_intentional_hold_is_legal()
    test_est_missing_character()
    test_source_loop_stretch_requires_cycle_flag()
    validate_artifact("limited_grammar_report", evaluate_limited_grammar(
        [{
            "id": "A2", "t_start": 2.5, "t_end": 4.5,
            "temporal_intent": "intentional_hold",
        }],
        _report((2.5, 4.5, "STATIC_HOLD")),
    ))
    print("ok")
