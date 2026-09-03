"""Compile episode beat sheets onto the existing eight-column scene_plan table.

This is not a second ledger. Output is ``scene_plan.scenes[]`` — the Hosoda-style
Backlot table: S / C / 画面 / 内容·摄影·Prompt / 台词 / 秒数 / 音响.

``sound_intent`` already carries SE + BGM. The gap this fills is the Prompt
column: visual_intent stays human intent; t2i_prompt is the exact still prompt;
i2v_prompt is the exact H3/I2V prompt. Do not mix the three.

Does **not** dispatch. Does **not** write frozen job checkpoints.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from lib.anchor_registry import bind_anchors, layout_plate
from lib.h3_context_ir import compile_h3_ir
from lib.motion_obligation import assert_motion_obligation
from lib.sceneplan_contract import validate_eight_column_scene_plan
from lib.shot_director import (
    BENCHMARK_KEYFRAMES,
    annotate_bindings,
    classify_shot,
    compile_beat_actions,
    first_frame_readiness,
    lint_temporal_beats,
)

SCHEMA_SCENE = "1.0"
STYLE_STILL = (
    "Limited Japanese TV anime still, 1990s late-night TV, cel-shaded, vertical 9:16, "
    "one cinematic keyframe, not a collage, not a storyboard grid, no subtitles, "
    "no watermark, no photoreal live-action"
)
AVERY_LOOK = (
    "Avery Sterling: oversized black hoodie, ash-brown messy hair, pale grey-blue "
    "wet over-expressive eyes, slim, goes red under eye contact"
)
LUCIEN_LOOK = (
    "Lucien Mercer: short black hair, dead-still dark eyes, scarred knuckles, "
    "charcoal chef coat, moves like a man who knows where every knife is"
)
LUNCHBOX = "blue-and-silver thermal lunchbox, lid closed"

MACRO_RE = re.compile(
    r"(?i)(?:hard cut(?: to)?|cut to|flashback|push in|then (?:hard )?cut|"
    r"wide establishing|extreme close-up)"
)
DURATION_RE = re.compile(r"(?i)(?:held\s+)?(?:~)?(\d+(?:\.\d+)?)\s*s(?:econds?)?")
WORDS_PER_SECOND = 2.3
H3_MIN = 4.0
H3_MAX = 15.0

FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "drama_preproduction"
)
EP01_GOLDEN = FIXTURES / "blacklisted_chef_ep01_cuts.json"

FRAMING_TO_SHOT = {
    "full": "wide",
    "wide": "establishing",
    "medium_shot": "medium",
    "medium_close_up": "medium_close",
    "close_up": "close_up",
    "extreme_close_up": "extreme_close_up",
}

OBLIGATION_MAP = {
    "CHARACTER_PERFORMANCE": "PERFORMANCE",
    "CHARACTER_PERFORMANCE": "PERFORMANCE",
    "PROP_MOTION": "LOCAL",
    "PROP_MOTION": "LOCAL",
    "GRAPHIC": "LOCAL",
    "AMBIENT": "LOCAL",
    "AMBIENT": "LOCAL",
    "INTENTIONAL_HOLD": "NONE",
    "INTENTIONAL_HOLD": "NONE",
}
LOCO_MARKERS = ("run", "bolt", "sprint", "arriv", "gait", "footstep", "walk toward")
WALK_BANS = {"walk", "walk cycle", "walkcycle"}

TEMPORAL_KIND = {
    "CHARACTER_PERFORMANCE": "CHARACTER_PERFORMANCE",
    "PROP_MOTION": "PROP",
    "GRAPHIC": "GRAPHIC",
    "AMBIENT": "AMBIENT",
    "INTENTIONAL_HOLD": "HOLD",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def episode_obj(data: dict[str, Any]) -> dict[str, Any]:
    ep = data.get("episode") if isinstance(data.get("episode"), dict) else data
    if not isinstance(ep, dict) or not ep:
        raise ValueError("episode JSON must contain an episode object")
    return ep


def detect_macro_shot(visual: str) -> bool:
    blob = visual or ""
    if len(MACRO_RE.findall(blob)) >= 2:
        return True
    if re.search(r"(?i)cut to", blob) and re.search(
        r"(?i)(?:wide|push in|establishing|close)", blob
    ):
        return True
    return False


def word_seconds(text: str) -> float:
    words = re.findall(r"[A-Za-z0-9']+", text or "")
    if not words:
        return 0.0
    return round(len(words) / WORDS_PER_SECOND, 1)


def parse_held_seconds(text: str) -> float | None:
    matches = DURATION_RE.findall(text or "")
    if not matches:
        return None
    return float(matches[-1])


def _duration(cut: dict[str, Any]) -> float:
    return round(float(cut["end_seconds"]) - float(cut["start_seconds"]), 3)


def load_ep01_golden_cuts() -> list[dict[str, Any]]:
    return [_normalize_cut(cut) for cut in load_json(EP01_GOLDEN)["cuts"]]


def _normalize_cut(cut: dict[str, Any]) -> dict[str, Any]:
    """Accept both golden-file spellings so the compiler has one shape."""
    out = dict(cut)
    pairs = (
        ("cut_id", "cut_id"),
        ("character_ids", "character_ids"),
        ("composition_anchor", "composition_anchor"),
        ("scene_anchor", "scene_anchor"),
        ("prop_ids", "prop_ids"),
        ("hard_flags", "hard_flags"),
        ("h3_eligible", "h3_eligible"),
        ("start_seconds", "start_seconds"),
        ("end_seconds", "end_seconds"),
        ("beat_id", "beat_id"),
        ("scene_a_id", "scene_a_id"),
        ("audience_state_after", "audience_state_after"),
        ("motion_obligation", "motion_obligation"),
    )
    for left, right in pairs:
        if out.get(left) is None and out.get(right) is not None:
            out[left] = out[right]
        elif out.get(right) is None and out.get(left) is not None:
            out[right] = out[left]
    ids = []
    for cid in out.get("character_ids") or out.get("character_ids") or []:
        if cid in {"avery_sterling", "avery_sterling"}:
            ids.append("avery_sterling")
        elif cid in {"lucien_mercer", "lucien_mercer"}:
            ids.append("lucien_mercer")
        else:
            ids.append(cid)
    if ids:
        out["character_ids"] = ids
        out["character_ids"] = ids
    raw = str(out.get("motion_obligation") or out.get("motion_obligation") or "")
    obligation_alias = {
        "CHARACTER_PERFORMANCE": "CHARACTER_PERFORMANCE",
        "PROP_MOTION": "PROP_MOTION",
        "INTENTIONAL_HOLD": "INTENTIONAL_HOLD",
        "AMBIENT": "AMBIENT",
        "GRAPHIC": "GRAPHIC",
    }
    if raw in obligation_alias:
        out["motion_obligation"] = obligation_alias[raw]
        out["motion_obligation"] = raw if raw in OBLIGATION_MAP else obligation_alias[raw]
    return out


def _anchor_refs(cut: dict[str, Any]) -> list[str]:
    refs = ["STYLE_LIMITED_TV_ANIME_V1"]
    for key in ("composition_anchor", "scene_anchor"):
        val = cut.get(key)
        if val:
            refs.append(str(val))
    for cid in cut.get("character_ids") or []:
        if cid == "avery_sterling":
            refs.append("CHAR_AVERY_V1")
        elif cid == "lucien_mercer":
            refs.append("CHAR_LUCIEN_V1")
    refs.extend(str(p) for p in (cut.get("prop_ids") or []) if p)
    refs.append("SOUND_KITCHEN_HUM")
    # unique, stable order
    seen: set[str] = set()
    out: list[str] = []
    for item in refs:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _identity_line(cut: dict[str, Any]) -> str:
    ids = set(cut.get("character_ids") or [])
    parts: list[str] = []
    if "avery_sterling" in ids:
        parts.append(AVERY_LOOK)
    if "lucien_mercer" in ids:
        parts.append(LUCIEN_LOOK)
    props = set(cut.get("prop_ids") or [])
    if "PROP_LUNCHBOX_V1" in props:
        parts.append(LUNCHBOX)
    return ". ".join(parts)


def compile_t2i_prompt(cut: dict[str, Any]) -> str:
    """Exact still / layout prompt. Not visual_intent."""
    framing = str(cut.get("framing") or "medium_close_up").replace("_", " ")
    camera = cut.get("camera") or "locked-off static"
    loc = cut.get("scene_anchor") or "SCENE_BACK_KITCHEN_V2"
    comp = cut.get("composition_anchor") or ""
    identity = _identity_line(cut)
    avoid = cut.get("avoid") or []
    avoid_line = "; ".join(f"no {a}" for a in avoid[:8]) if avoid else "no subtitles"
    picture = " ".join(
        part.strip()
        for part in [str(cut.get("visual") or ""), identity]
        if part and part.strip()
    )
    return (
        f"{STYLE_STILL}. {framing}, {camera}. Composition {comp}. Location {loc}. "
        f"{picture}. Avoid: {avoid_line}."
    )


def _is_locomotion(cut: dict[str, Any]) -> bool:
    blob = f"{cut.get('action') or ''} {cut.get('visual') or ''} {' '.join(cut.get('hard_flags') or [])}".lower()
    return any(marker in blob for marker in LOCO_MARKERS)


def _compiled_obligation(cut: dict[str, Any]) -> str:
    raw = str(cut.get("motion_obligation") or "")
    if raw in {"PROP_MOTION", "PROP_MOTION"}:
        chars = cut.get("character_ids") or cut.get("character_ids")
        if (cut.get("h3_eligible") or cut.get("h3_eligible")) and chars:
            return "PERFORMANCE"
        return "LOCAL"
    return OBLIGATION_MAP.get(raw, "NONE")


def _route(cut: dict[str, Any], obligation: str) -> tuple[str, str, str, str | None]:
    raw = str(cut.get("motion_obligation") or "")
    visual = f"{cut.get('visual') or ''} {cut.get('action') or ''}".lower()
    if obligation == "PERFORMANCE":
        return "H3", "I2V_HARD", "local_h3_fl2va", None
    if obligation == "LOCAL":
        if "steam" in visual:
            fn = "steam_rise"
        elif "door" in visual or "thup" in visual:
            fn = "door_decay"
        elif raw == "GRAPHIC" or "hud" in visual or "glyph" in visual:
            fn = "hud_flicker"
        elif raw == "AMBIENT":
            fn = "ambient_loop"
        else:
            fn = "prop_overlay"
        return "PROGRAMMATIC", "LIMITED", "ffmpeg-overlay", fn
    return "HOLD", "LIMITED", "ffmpeg-hold", None


def _split_spans(duration: float, count: int) -> list[tuple[float, float]]:
    step = duration / count
    spans: list[tuple[float, float]] = []
    t = 0.0
    for i in range(count):
        t1 = duration if i == count - 1 else round(t + step, 2)
        spans.append((round(t, 2), t1))
        t = t1
    return spans


def _beat_actions(cut: dict[str, Any], obligation: str) -> list[str]:
    actions = compile_beat_actions(cut, obligation)
    lint_temporal_beats(cut, actions)
    return actions


def _temporal_beats(cut: dict[str, Any], obligation: str) -> list[dict[str, Any]]:
    raw = str(cut.get("motion_obligation") or "")
    kind = TEMPORAL_KIND.get(raw, "HOLD")
    dur = _duration(cut)
    if obligation == "NONE":
        return [
            {
                "kind": "HOLD",
                "t_start": 0.0,
                "t_end": dur,
                "action": str(cut.get("action") or "Hold the last frame."),
            }
        ]
    actions = _beat_actions(cut, obligation)
    return [
        {"kind": kind, "t_start": start, "t_end": end, "action": text}
        for (start, end), text in zip(_split_spans(dur, len(actions)), actions)
    ]


def _h3_shots(cut: dict[str, Any], beats: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    framing = str(cut.get("framing") or "medium close-up").replace("_", " ")
    camera = cut.get("camera") or "locked-off static"
    last = float(beats[-1]["t_end"]) if beats else duration
    scale = duration / last if last else 1.0
    shots = []
    for beat in beats:
        shots.append(
            {
                "t0": round(float(beat["t_start"]) * scale, 2),
                "t1": round(float(beat["t_end"]) * scale, 2),
                "framing": framing,
                "action": beat.get("action") or cut.get("action") or cut.get("visual"),
                "camera": camera,
            }
        )
    return shots


def _h3_avoid(cut: dict[str, Any], locomotion: bool) -> list[str]:
    avoid = list(cut.get("avoid") or [])
    if locomotion:
        avoid = [item for item in avoid if item.lower() not in WALK_BANS and "walk cycle" not in item.lower()]
    return avoid


def _assert_prompt_lint(cut: dict[str, Any], prompt: str, locomotion: bool) -> None:
    low = prompt.lower()
    if locomotion and ("walk cycle" in low or "does not walk" in low or "invent a walk" in low):
        raise ValueError(f"{cut.get('cut_id')}: locomotion prompt still bans walking")


def compile_i2v_prompt(
    cut: dict[str, Any],
    beats: list[dict[str, Any]] | None = None,
    *,
    locomotion: bool = False,
    first_frame: str | None = None,
) -> str | None:
    if not cut.get("h3_eligible") and _compiled_obligation(cut) != "PERFORMANCE":
        return None
    if _compiled_obligation(cut) != "PERFORMANCE":
        return None
    dur = max(H3_MIN, min(H3_MAX, _duration(cut)))
    beats = beats or _temporal_beats(cut, "PERFORMANCE")
    spec = _h3_ir_spec(cut, beats, locomotion=locomotion, first_frame=first_frame)
    prompt = compile_h3_ir(spec)["prompt"]
    _assert_prompt_lint(cut, prompt, locomotion)
    return prompt


def _h3_ir_spec(
    cut: dict[str, Any],
    beats: list[dict[str, Any]] | None = None,
    *,
    locomotion: bool = False,
    first_frame: str | None = None,
) -> dict[str, Any]:
    dur = max(H3_MIN, min(H3_MAX, _duration(cut)))
    beats = beats or _temporal_beats(cut, "PERFORMANCE")
    return {
        "mode": "fl2va",
        "style": "limited TV anime",
        "overview": cut.get("visual"),
        "duration_seconds": dur,
        "camera": cut.get("camera") or "locked-off static",
        "avoid": _h3_avoid(cut, locomotion),
        "audio": cut.get("audio") or [],
        "shots": _h3_shots(cut, beats, dur),
        "identity": {
            "character": ", ".join(cut.get("character_ids") or []) or "unspecified",
            "must": [p for p in [LUNCHBOX] if "PROP_LUNCHBOX_V1" in (cut.get("prop_ids") or [])],
            "must_not": _h3_avoid(cut, locomotion),
        },
        "locomotion": locomotion,
        "first_frame": first_frame,
        "ratio": "9:16",
        "width": 768,
        "height": 1376,
        "hosted_minimax_ir": False,
        "dispatch": False,
    }


def _sound_intent(cut: dict[str, Any]) -> dict[str, Any]:
    audio = [str(a) for a in (cut.get("audio") or [])]
    se: list[str] = []
    bgm = "none — kitchen diegetic"
    silence = False
    for item in audio:
        low = item.lower()
        if "music" in low or "sting" in low:
            if "no music" in low:
                bgm = "none"
            else:
                bgm = item
            continue
        if "silence" in low:
            silence = True
            continue
        if "v.o" in low or "line" in low:
            se.append(item)
            continue
        se.append(item)
    if not audio and not (cut.get("dialogue") or []):
        silence = True
        bgm = "held kitchen hum only" if "BACK_KITCHEN" in str(cut.get("scene_anchor") or "") else "none"
        if not se:
            se = ["room tone"]
    return {"se": se or ["room tone"], "bgm_mood": bgm, "silence": silence}


def _dialogue_text(cut: dict[str, Any]) -> str:
    lines = cut.get("dialogue") or []
    if not lines:
        return ""
    return " ".join(f"{row.get('speaker')}: {row.get('line')}" for row in lines)


def _layout_notes(cut: dict[str, Any]) -> str:
    shot = FRAMING_TO_SHOT.get(str(cut.get("framing") or ""), cut.get("framing") or "medium")
    camera = cut.get("camera") or "locked-off static"
    comp = cut.get("composition_anchor") or "unspecified composition"
    action = (cut.get("action") or "").strip()
    avoid = cut.get("avoid") or []
    bits = [
        f"{shot.replace('_', ' ')}; {camera}.",
        f"Bind {comp}.",
        action,
    ]
    if avoid:
        bits.append("Do not: " + "; ".join(avoid[:6]) + ".")
    return " ".join(b for b in bits if b)


def _animation_class(cut: dict[str, Any], obligation: str) -> str:
    if obligation == "PERFORMANCE":
        return "I2V_HARD"
    raw = str(cut.get("animation_class") or "LIMITED")
    if raw in {"LIMITED", "I2V_STANDARD", "I2V_HARD"}:
        return "LIMITED" if obligation != "PERFORMANCE" else raw
    return "LIMITED"


def cut_to_scene(cut: dict[str, Any]) -> dict[str, Any]:
    if detect_macro_shot(str(cut.get("visual") or "")):
        raise ValueError(
            f"{cut.get('cut_id')}: visual still describes multiple cameras; split the row"
        )
    obligation = _compiled_obligation(cut)
    route, animation_class, renderer, local_fn = _route(cut, obligation)
    beats = _temporal_beats(cut, obligation)
    locomotion = _is_locomotion(cut)
    refs = _anchor_refs(cut)
    bindings = annotate_bindings(bind_anchors(refs))
    plate = layout_plate(bindings)
    profile = classify_shot(cut)
    readiness = first_frame_readiness(
        cut, bindings, plate, require_h3=(route == "H3")
    )
    dialogue = _dialogue_text(cut)
    voice_ids = (
        [f"vo-{cut['cut_id']}"] if dialogue else [f"silence-{cut['cut_id']}"]
    )
    scene_a = cut.get("scene_a_id")
    flags = list(cut.get("hard_flags") or [])
    if scene_a:
        flags.append(f"scene_a:{scene_a}")
    if route == "H3" and not readiness.get("shot_ready"):
        flags.append("h3_first_frame_blocked")
    first_frame = readiness["path"] if readiness["shot_ready"] else None
    if plate:
        visual_ref = {"kind": "local_image", "path": plate["path"]}
    else:
        visual_ref = {
            "kind": "placeholder",
            "placeholder_reason": "No bound composition/character/scene plate on disk yet.",
        }
    scene: dict[str, Any] = {
        "id": cut["cut_id"],
        "type": "character_scene" if cut.get("character_ids") else "animation",
        "description": cut.get("visual") or cut.get("action") or cut["cut_id"],
        "script_section_id": str(cut.get("beat_id") or "beat"),
        "start_seconds": float(cut["start_seconds"]),
        "end_seconds": float(cut["end_seconds"]),
        "layout_notes": _layout_notes(cut),
        "visual_intent": str(cut.get("visual") or "").strip(),
        "t2i_prompt": compile_t2i_prompt(cut),
        "dialogue": dialogue,
        "voice_segment_ids": voice_ids,
        "sound_intent": _sound_intent(cut),
        "visual_ref": visual_ref,
        "motion_route": route,
        "animation_class": animation_class,
        "motion_obligation": obligation,
        "performance_intent": str(cut.get("action") or ""),
        "intentional_hold": obligation == "NONE",
        "renderer": renderer,
        "character_ids": list(cut.get("character_ids") or []),
        "shot_language": {
            "shot_size": FRAMING_TO_SHOT.get(str(cut.get("framing") or ""), "medium_close"),
            "camera_movement": "static",
            "lighting_key": "tungsten_warm"
            if "KITCHEN" in str(cut.get("scene_anchor") or "")
            else "low_key",
            "depth_of_field": "shallow"
            if "close" in str(cut.get("framing") or "")
            else "medium",
            "color_temperature": "warm",
        },
        "shot_intent": str(cut.get("action") or ""),
        "audience_state_change": str(cut.get("audience_state_after") or ""),
        "anchor_refs": refs,
        "anchor_bindings": bindings,
        "shot_profile": profile,
        "first_frame_readiness": readiness,
        "avoid": list(cut.get("avoid") or []),
        "temporal_beats": beats,
        "generation_status": "pending",
        "review_decision": "pending",
        "flags": flags,
    }
    if cut.get("character_variant"):
        from lib.character_variant import normalize_character_variant

        scene["character_variant"] = normalize_character_variant(
            cut["character_variant"], scene["character_ids"]
        )
    if local_fn:
        scene["local_motion_fn"] = local_fn
    if scene_a:
        scene["review_notes"] = (
            f"Maps to frozen Scene A {scene_a}. Do not redispatch that job. "
            "9:16 rewrite required; Scene A plates are 16:9 corpus."
        )
    if route == "H3":
        spec = _h3_ir_spec(cut, beats, locomotion=locomotion, first_frame=first_frame)
        scene["h3_ir"] = spec
        scene["i2v_prompt"] = compile_i2v_prompt(
            cut, beats, locomotion=locomotion, first_frame=first_frame
        )
    assert_motion_obligation(scene)
    return scene


def _coverage(ep: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    target = round(float(ep.get("duration_target_minutes") or 2.7) * 60.0, 1)
    picture = sum(
        float(s["end_seconds"]) - float(s["start_seconds"]) for s in scenes
    )
    uncovered = []
    for scene in scenes:
        text = scene.get("dialogue") or ""
        vs = word_seconds(text)
        pic = float(scene["end_seconds"]) - float(scene["start_seconds"])
        if vs > pic + 0.4:
            uncovered.append(
                {
                    "cut_id": scene["id"],
                    "voice_seconds_estimate": vs,
                    "picture_seconds": round(pic, 3),
                }
            )
    return {
        "target_duration_seconds": target,
        "visual_coverage_duration": round(picture, 3),
        "coverage_ratio_vs_target": round(picture / target, 3) if target else None,
        "uncovered_voice_segments": uncovered,
        "cut_count": len(scenes),
        "h3_cut_count": sum(1 for s in scenes if s.get("motion_route") == "H3"),
        "not_a_quality_verdict": True,
    }


def compile_scene_plan(episode_path: Path) -> dict[str, Any]:
    ep = episode_obj(load_json(episode_path))
    n = int(ep.get("episode_number") or 0)
    if n != 1:
        raise ValueError("only episode 01 has a golden one-camera split; do not heuristic-dispatch others")
    cuts = load_ep01_golden_cuts()
    scenes = [cut_to_scene(cut) for cut in cuts]
    prior = "The episode has not started."
    for scene in scenes:
        after = str(scene.get("audience_state_change") or "")
        scene["audience_state_before"] = prior
        prior = after or prior
    plan = {
        "version": SCHEMA_SCENE,
        "style_playbook": "anime-limited-tv",
        "scenes": scenes,
        "metadata": {
            "presentation_contract": "eight-column-v1",
            "total_duration_seconds": scenes[-1]["end_seconds"] if scenes else 0,
            "benchmark_cuts": ["E01_B1_B", "E01_B2_A", "E01_B2_E", "E01_B7_C"],
            "compiler_revision": "shot_specific_temporal_v1",
            "h3_benchmark_ready": False,
            "canonical_script": str(episode_path).replace("\\", "/"),
            "human_recording_variant": None,
            "source_relationship": "canonical",
            "draft": True,
            "checkpoint": False,
            "dispatch": False,
            "foreman_proven": False,
            "aspect_ratio": "9:16",
            "canvas_conflict": (
                "This YouTube job is 9:16. Frozen Scene A board is 16:9 corpus. "
                "Do not copy those plates without a vertical rewrite."
            ),
            "coverage": _coverage(ep, scenes),
        },
    }
    validate_eight_column_scene_plan(plan, require_review_decisions=False)
    return plan


def write_scene_plan(plan: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_benchmark_keyframe_packages(plan: dict[str, Any], out_dir: Path) -> Path:
    """Compile 9:16 shot-keyframe briefs. Does not produce_keyframe. Does not dispatch."""
    by_id = {scene["id"]: scene for scene in plan["scenes"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    packages = []
    for spec in BENCHMARK_KEYFRAMES:
        scene = by_id[spec["cut_id"]]
        pkg = {
            "cut_id": spec["cut_id"],
            "composition_id": spec["composition_id"],
            "title": spec["title"],
            "kind_required": "SHOT_KEYFRAME",
            "aspect": "9:16",
            "width": 768,
            "height": 1376,
            "must_show": spec["must_show"],
            "t2i_prompt": scene.get("t2i_prompt"),
            "visual_intent": scene.get("visual_intent"),
            "identity_refs": [
                row for row in scene.get("anchor_bindings") or []
                if row.get("role") == "IDENTITY_REFERENCE"
            ],
            "scene_refs": [
                row for row in scene.get("anchor_bindings") or []
                if row.get("role") == "SCENE_REFERENCE"
            ],
            "prop_refs": [
                row for row in scene.get("anchor_bindings") or []
                if row.get("role") == "PROP_REFERENCE"
            ],
            "composition_binding": next(
                (
                    row
                    for row in scene.get("anchor_bindings") or []
                    if row.get("id") == spec["composition_id"]
                ),
                None,
            ),
            "first_frame_readiness": scene.get("first_frame_readiness"),
            "produce_keyframe": False,
            "dispatch": False,
            "status": "awaiting_operator_still",
            "note": (
                "Cursor does not call produce_keyframe on a live job. "
                "These briefs are the 9:16 shot keyframes Prime/operator must generate "
                "before A/B/C/D H3 benchmark."
            ),
        }
        path = out_dir / f"{spec['cut_id']}.json"
        path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        packages.append({"cut_id": spec["cut_id"], "path": str(path).replace("\\", "/")})
    manifest = out_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "dispatch": False,
                "produce_keyframe": False,
                "compiler_revision": plan["metadata"].get("compiler_revision"),
                "packages": packages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile episode beats onto eight-column scene_plan. No dispatch."
    )
    parser.add_argument("--episode", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = compile_scene_plan(args.episode)
    write_scene_plan(plan, args.out)
    keyframe_dir = args.out.parent / "benchmark_keyframes"
    manifest = write_benchmark_keyframe_packages(plan, keyframe_dir)
    cov = plan["metadata"]["coverage"]
    print(
        json.dumps(
            {
                "cuts": cov["cut_count"],
                "h3_cuts": cov["h3_cut_count"],
                "coverage_ratio_vs_target": cov["coverage_ratio_vs_target"],
                "uncovered_voice": len(cov["uncovered_voice_segments"]),
                "out": str(args.out),
                "keyframe_briefs": str(manifest),
                "dispatch": False,
                "h3_benchmark_ready": False,
            }
        )
    )
    return 0


# Public aliases used by tests / callers.
load_ep01_golden_cuts = load_ep01_golden_cuts
cut_to_scene = cut_to_scene
compile_t2i_prompt = compile_t2i_prompt
detect_macro_shot = detect_macro_shot
compile_scene_plan = compile_scene_plan


if __name__ == "__main__":
    raise SystemExit(main())
