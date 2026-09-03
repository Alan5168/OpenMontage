"""Local H3 Context-IR substitute — a compiler, not MiniMax's hosted service.

MiniMax did not open-source H3-Context-IR. Official guidance: call the hosted
API, or follow Prompting Guidance and build your own preprocessor.

This module is the Studio preprocessor. It lives in OpenMontage, not in a
ComfyUI node. It does **not** call MiniMax cloud IR, does **not** ask a VLM
to "enhance" (that is how A5 grew a smile and a push-in), and does **not**
PASS/APPROVE anything.

Dialect authority is the vendored MiniMax skill
``vendor/minimax-h3/h3-prompt-writing`` (base-en.txt). This compiler
**translates** a ShotContract into that dialect. It does not direct the
shot. Ref2VA six-section rewrite is not in this function; see ref-en.txt.

Input: structured cut context (identity, shots, camera, audio, avoid).
Output: a prompt string H3-Base / MiniMaxH3ImageToVideo can eat, plus the
frame grid H3 snaps to (24 fps, length ≡ 5 mod 17).

ComfyUI stays dumb equipment: load keep-set weights, sample, save.
"""

from __future__ import annotations

from typing import Any

FPS = 24
# MiniMaxH3ImageToVideo snaps length so n % 17 == 5 (124 ≈ 5s).
_FRAME_MOD = 17
_FRAME_REM = 5
SHIP_SECONDS = 5.0
SHIP_FRAMES = 124  # frames_for_duration(5)

# Official MiniMax H3-Base field names (skills/h3-prompt-writing/references/base-en.txt).
OFFICIAL_CORE_FIELDS = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)
I2VA_ALIGN = (
    "For the target video, at 0.00 seconds into the target video, "
    "<Picture 1> (from [Shot 1]) is fully referenced."
)
R2VA_NOT_IN_BASE_COMPILER = (
    "R2VA_PROMPT_NOT_IN_BASE_COMPILER: Ref2VA uses the six-section rewrite in "
    "vendor/minimax-h3/h3-prompt-writing/references/ref-en.txt. "
    "Do not emit the three-field I2VA/T2VA prompt and call it R2VA. "
    "Ref2VA weights are a separate runtime gate in lib/h3_runtime.py."
)


def ship_duration_seconds(requested: float, *, allow_long: bool = False) -> float:
    """5070 Ti ship grid. 8s → 192 frames is superlinear; default cap is 5s.

    Set ``h3_allow_long`` on the spec/shot to keep 6–15s. Frozen jobs are not
    re-run; this only affects new compiles.
    """
    duration = float(requested)
    if duration < 4 or duration > 15:
        raise ValueError(f"H3 duration must be 4-15s, got {duration}")
    if allow_long:
        return duration
    return min(duration, SHIP_SECONDS)


def align_frame_count(n: int) -> int:
    n = max(5, int(n))
    while n % _FRAME_MOD != _FRAME_REM:
        n += 1
    return n


def frames_for_duration(seconds: float) -> int:
    return align_frame_count(round(float(seconds) * FPS))


def compile_h3_ir(spec: dict[str, Any]) -> dict[str, Any]:
    """Serialize a structured cut into an H3-Base prompt + canvas.

    Required-ish keys (all optional except that the result must be non-empty):
      overview, identity, shots[], camera, audio[], avoid[], duration_seconds,
      width, height, mode (i2va|t2va|fl2va|l2va|r2va), style
    """
    if not isinstance(spec, dict) or not spec:
        raise ValueError("h3_ir spec must be a non-empty object")

    requested = float(spec.get("duration_seconds") or SHIP_SECONDS)
    allow_long = bool(spec.get("h3_allow_long"))
    duration = ship_duration_seconds(requested, allow_long=allow_long)
    length = frames_for_duration(duration)
    width = int(spec.get("width") or 1344)
    height = int(spec.get("height") or 768)
    mode = str(spec.get("mode") or "i2va").strip().lower()
    if spec.get("last_frame") and mode == "i2va":
        mode = "fl2va"
    if mode not in {"i2va", "t2va", "fl2va", "l2va", "r2va"}:
        raise ValueError(f"unknown H3 mode: {mode}")
    if mode == "r2va":
        raise ValueError(R2VA_NOT_IN_BASE_COMPILER)

    prompt = _render_prompt(spec, duration)
    avoid = _list(spec.get("avoid"))
    return {
        "schema_version": "h3-context-ir/v0.2",
        "hosted_minimax_ir": False,
        "prompt_dialect": "minimax-h3-prompt-writing/base-en",
        "mode": mode,
        "prompt": prompt,
        "avoid": avoid,
        "requested_duration_seconds": requested,
        "duration_seconds": duration,
        "duration_capped_to_ship_grid": (not allow_long) and requested > SHIP_SECONDS,
        "h3_allow_long": allow_long,
        "length": length,
        "fps": FPS,
        "width": width,
        "height": height,
        "ratio": str(spec.get("ratio") or "16:9"),
        "first_frame": spec.get("first_frame"),
        "last_frame": spec.get("last_frame"),
        "camera_lock": spec.get("camera") or "locked-off static",
    }


def compile_from_scene(
    scene: dict[str, Any],
    *,
    style_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map an OM scene/cut dict onto compile_h3_ir."""
    if scene.get("h3_ir") and isinstance(scene["h3_ir"], dict):
        spec = dict(scene["h3_ir"])
        spec.setdefault("duration_seconds", scene.get("duration_seconds") or scene.get("duration"))
        spec.setdefault("first_frame", scene.get("first_frame") or scene.get("visual_ref"))
        spec.setdefault("last_frame", scene.get("last_frame"))
        if not spec.get("identity"):
            from lib.character_variant import identity_from_variant

            spec["identity"] = scene.get("identity") or identity_from_variant(scene) or spec.get("identity") or {}
        spec.setdefault("h3_allow_long", scene.get("h3_allow_long"))
        spec.setdefault(
            "experimental_reference_binding",
            scene.get("experimental_reference_binding"),
        )
        return compile_h3_ir(spec)

    sl = scene.get("shot_language") or {}
    movement = sl.get("camera_movement") or "static"
    camera = (
        "locked-off static"
        if movement in {"static", "", None}
        else str(movement)
    )
    spec = {
        "mode": "i2va",
        "style": (style_context or {}).get("visual_language", {}).get("aesthetic")
        or scene.get("style")
        or "limited TV anime",
        "overview": scene.get("description") or scene.get("intent") or "",
        "identity": scene.get("identity") or _identity_from_variant(scene) or {},
        "duration_seconds": scene.get("duration_seconds") or scene.get("duration") or 5,
        "width": scene.get("width") or 1344,
        "height": scene.get("height") or 768,
        "ratio": scene.get("ratio") or "16:9",
        "camera": camera,
        "shots": scene.get("shots")
        or [
            {
                "t0": 0.0,
                "t1": float(scene.get("duration_seconds") or scene.get("duration") or 5),
                "framing": sl.get("shot_size") or "medium_close",
                "action": scene.get("action") or scene.get("description") or "",
                "camera": camera,
            }
        ],
        "audio": scene.get("audio") or [],
        "avoid": scene.get("avoid") or [],
        "first_frame": scene.get("first_frame") or scene.get("visual_ref"),
        "last_frame": scene.get("last_frame"),
        "h3_allow_long": scene.get("h3_allow_long"),
        "experimental_reference_binding": scene.get("experimental_reference_binding"),
    }
    return compile_h3_ir(spec)


def _identity_from_variant(scene: dict[str, Any]) -> dict[str, Any]:
    from lib.character_variant import identity_from_variant

    return identity_from_variant(scene)


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(x).strip() for x in value if str(x).strip()]


def _render_prompt(spec: dict[str, Any], duration: float) -> str:
    """Official H3-Base I2VA/FL2VA grammar, not hosted Context-IR JSON."""
    mode = str(spec.get("mode") or "i2va").strip().lower()
    if spec.get("last_frame") and mode == "i2va":
        mode = "fl2va"
    duration_s = f"{duration:.2f}"
    parts: list[str] = []
    last_shot = max(1, len(spec.get("shots") or []) or 1)
    if mode == "r2va":
        raise ValueError(R2VA_NOT_IN_BASE_COMPILER)
    if mode == "fl2va":
        parts.append(
            "How the reference pictures align with the target video — "
            "Picture 1 (from Shot 1) aligns with the 0.00-second mark of the "
            f"target video; Picture 2 (from Shot {last_shot}) aligns with the "
            f"{duration_s}-second mark of the target video."
        )
        parts.append("")
    elif mode == "l2va":
        parts.append(
            "How the reference pictures align with the target video — "
            f"<Picture 1> (from [Shot {last_shot}]) aligns with the "
            f"{duration_s}-second mark of the target video."
        )
        parts.append("")
    elif mode != "t2va":
        parts.append(I2VA_ALIGN)
        parts.append("")

    parts.append(
        "integrated_multimodal_description: " + _multimodal_body(spec, duration)
    )
    parts.append("")
    parts.append("overall_soundscape: " + _soundscape(spec))
    parts.append("")
    music = str(
        spec.get("non_diegetic_music")
        or spec.get("non_diegetic_score")
        or ""
    ).strip()
    parts.append("non_diegetic_music: " + (music if music else "N/A"))
    return "\n".join(parts)


def _style_token(style: str) -> str:
    raw = (style or "limited TV anime").strip()
    lowered = raw.lower()
    if "anime" in lowered or "2d" in lowered:
        return f"2D-animated, {raw}" if "2d-animated" not in lowered else raw
    return raw


def _camera_sentence(camera: str) -> str:
    raw = (camera or "locked-off static").strip()
    lowered = raw.lower().replace("_", " ")
    if lowered in {"", "static", "locked-off static", "locked off static", "static shot"}:
        return "The camera holds a static shot."
    if "push" in lowered:
        return "The camera pushes in with small amplitude at slow speed."
    return f"The camera {raw}."


def _multimodal_body(spec: dict[str, Any], duration: float) -> str:
    style = _style_token(str(spec.get("style") or "limited TV anime"))
    identity = spec.get("identity") or {}
    ident = _identity_line(
        identity,
        experimental=bool(spec.get("experimental_reference_binding")),
    )
    overview = str(spec.get("overview") or "").strip()
    camera = str(spec.get("camera") or "locked-off static").strip()
    cam_sentence = _camera_sentence(camera)
    locked = cam_sentence.startswith("The camera holds a static shot")
    shots = spec.get("shots") or []
    if not shots:
        shots = [{
            "t0": 0,
            "t1": duration,
            "framing": "medium close-up",
            "action": "Only declared micro-motion. Hold the first-frame composition.",
            "camera": camera,
        }]

    if locked and len(shots) <= 1:
        first = shots[0]
        framing = first.get("framing") or "medium close-up"
        actions = " ".join(
            str(s.get("action") or "").strip() for s in shots if str(s.get("action") or "").strip()
        )
        body = f"[Shot 1] {style}, a {framing} begins from <Picture 1>."
        if ident:
            body += f" {ident}"
        if overview:
            body += f" {overview}"
        body += f" {actions} {cam_sentence}"
        body += " " + _negatives(spec)
        return body

    chunks: list[str] = []
    for i, shot in enumerate(shots, start=1):
        t0 = float(shot.get("t0") or 0)
        framing = shot.get("framing") or ""
        action = shot.get("action") or ""
        cam = _camera_sentence(str(shot.get("camera") or camera))
        if i == 1:
            bit = f"[Shot 1] {style}, a {framing} begins from <Picture 1>."
            if ident:
                bit += f" {ident}"
            if overview:
                bit += f" {overview}"
            bit += f" {action} {cam}"
            chunks.append(bit)
        else:
            stamp = _shot_timestamp(t0)
            t1 = float(shot.get("t1") or duration)
            if locked:
                chunks.append(
                    f"[Shot {i}] At {stamp}, same locked setup {t0:.2f}–{t1:.2f}s. {action}"
                )
            else:
                chunks.append(
                    f"[Shot {i}] At {stamp}, the camera cuts to a {framing}. {action} {cam}"
                )
    chunks.append(_negatives(spec))
    return " ".join(c.strip() for c in chunks if c.strip())


def _shot_timestamp(seconds: float) -> str:
    whole = int(seconds)
    frac = int(round((seconds - whole) * 1000))
    if frac == 1000:
        whole += 1
        frac = 0
    minutes, secs = divmod(whole, 60)
    return f"{minutes:02d}:{secs:02d}.{frac:03d}"


_NEGATIVE_PHRASES = {
    "glasses": "The subject does not wear glasses.",
    "smile": "The subject does not smile.",
    "grin": "The subject does not grin.",
    "teeth showing": "The mouth stays closed. Teeth are not visible.",
    "new face": "The subject's face does not change.",
    "camera push-in": "The camera does not push in.",
    "push-in": "The camera does not push in.",
    "pan": "The camera does not pan.",
    "cut to a new setup": "The camera does not cut to a new setup.",
    "open the lunchbox lid": "The lunchbox lid stays closed.",
    "open lid": "The lunchbox lid stays closed.",
    "walk cycle": "The subject does not walk.",
    "drop the box": "The lunchbox does not drop.",
    "redesign the room": "The room is not redesigned.",
}


def _negatives(spec: dict[str, Any]) -> str:
    identity = spec.get("identity") or {}
    banned = _list(identity.get("must_not")) + _list(spec.get("avoid"))
    seen: set[str] = set()
    bits: list[str] = []
    for item in banned:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        if key == "walk cycle" and _locomotion(spec):
            continue
        bits.append(_NEGATIVE_PHRASES.get(key, f"Do not introduce {item}."))
    if _locomotion(spec):
        bits.append(
            "The character, room, and prop states remain as in <Picture 1>. "
            "Do not invent a smile or a new prop state. "
            "Perform the declared temporal beats. Alternate legs. No skating."
        )
    else:
        bits.append(
            "The character, room, and prop states remain as in <Picture 1>. "
            "Do not invent a smile, a walk cycle, or a new prop state."
        )
    return " ".join(bits)


_LOCO_WORDS = (
    "walk",
    "run",
    "bolt",
    "sprint",
    "arriv",
    "gait",
    "footstep",
    "locomotion",
)


def _locomotion(spec: dict[str, Any]) -> bool:
    if "locomotion" in spec:
        return bool(spec.get("locomotion"))
    for shot in spec.get("shots") or []:
        if isinstance(shot, dict) and shot.get("atom_id") in {
            "one_step",
            "two_step_stop",
            "controlled_approach",
            "decelerate_stop",
        }:
            return True
    blob = " ".join(
        [
            str(spec.get("overview") or ""),
            str(spec.get("action") or ""),
            " ".join(str(s.get("action") or "") for s in (spec.get("shots") or []) if isinstance(s, dict)),
        ]
    ).lower()
    return any(word in blob for word in _LOCO_WORDS)


def _soundscape(spec: dict[str, Any]) -> str:
    audio = _list(spec.get("audio"))
    if not audio:
        return (
            "Quiet room tone only. No music sting. No new spoken dialogue. "
            "Breathing remains audible if the body is under threat."
        )
    joined = "; ".join(audio)
    return joined + ". No non-diegetic score. No new spoken dialogue."


def _identity_line(identity: Any, *, experimental: bool = False) -> str:
    if not identity:
        return ""
    if isinstance(identity, str):
        return f"The locked character is {identity}, matching <Picture 1>."
    name = identity.get("character") or identity.get("name") or ""
    must = _list(identity.get("must"))
    bits = []
    if name:
        bits.append(f"The locked character is {name}, matching <Picture 1>.")
    if must:
        bits.append("Appearance stays: " + ", ".join(must) + ".")
    if experimental:
        from lib.reference_binding import compile_bindings_stanza

        stanza = compile_bindings_stanza(identity.get("reference_bindings"))
        if stanza:
            bits.append(stanza)
    return " ".join(bits)


def main(argv: list[str] | None = None) -> int:
    import json
    import sys
    from pathlib import Path

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python lib/h3_context_ir.py <spec.json>", file=sys.stderr)
        return 2
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    print(json.dumps(compile_h3_ir(spec), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
