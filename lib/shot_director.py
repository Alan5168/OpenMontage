"""Shot-specific temporal beats and first-frame readiness.

PERFORMANCE does not inherit a generic Avery-fear template.
Beats must be observable in the current framing. Character master sheets
are identity references, not FL2VA first frames.
"""

from __future__ import annotations

from typing import Any

AVERY_FEAR_SIGNATURE = "Completely frozen against the set. Only shallow breath."

_ACTOR = {
    "avery_sterling": "Avery",
    "avery_sterling": "Avery",
    "lucien_mercer": "Lucien",
    "lucien_mercer": "Lucien",
}

_HAND_MARKERS = ("finger", "knuckle", "handle", "grip", "hand", "fist")
_EYE_MARKERS = ("eye", "gaze", "wells", "stare")
_LOCO_MARKERS = ("arriv", "run", "bolt", "sprint", "gait", "footstep", "walk toward")
_STEAM_MARKERS = ("steam",)
_DOOR_MARKERS = ("door", "thup")

_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "ECU_HAND": ("knee", "knees", "shoulder", "gaze", "eyes stay", "chest rises", "shallow breath"),
    "ECU_EYES": ("knee", "knees", "grip", "finger", "handle", "shoulder"),
    "PROP_ONLY": ("chest", "knee", "shoulder", "breath", "grip", "eyes", "avery", "lucien"),
    "GRAPHIC": ("chest", "knee", "shoulder", "breath", "grip"),
}


class ShotDirectorError(ValueError):
    """Temporal or first-frame contract failed. Do not dispatch."""


def _character_ids(cut: dict[str, Any]) -> list[str]:
    return [str(c) for c in (cut.get("character_ids") or cut.get("character_ids") or [])]


def actor_names(cut: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for cid in _character_ids(cut):
        label = _ACTOR.get(str(cid), str(cid))
        if label not in names:
            names.append(label)
    return names


def _blob(cut: dict[str, Any]) -> str:
    flags = cut.get("hard_flags") or cut.get("hard_flags") or []
    return f"{cut.get('visual') or ''} {cut.get('action') or ''} {' '.join(flags)}".lower()


def classify_shot(cut: dict[str, Any]) -> dict[str, str]:
    framing = str(cut.get("framing") or "")
    blob = _blob(cut)
    chars = _character_ids(cut)
    raw = str(cut.get("motion_obligation") or "")
    dialogue = cut.get("dialogue") or []

    if raw == "GRAPHIC" or "hud" in blob or "glyph" in blob:
        return {"framing_class": "GRAPHIC", "action_type": "graphic", "visible_subject": "hud"}
    if (raw == "AMBIENT" or (not chars and any(m in blob for m in _STEAM_MARKERS))):
        return {"framing_class": "PROP_ONLY", "action_type": "ambient", "visible_subject": "steam"}
    if raw == "PROP_MOTION" and not (cut.get("h3_eligible") and chars):
        subject = "door" if any(m in blob for m in _DOOR_MARKERS) else "prop"
        return {"framing_class": "PROP_ONLY", "action_type": "prop_local", "visible_subject": subject}
    if raw == "INTENTIONAL_HOLD":
        if framing == "extreme_close_up" and any(m in blob for m in _HAND_MARKERS):
            return {"framing_class": "ECU_HAND", "action_type": "hold", "visible_subject": "hands"}
        if framing == "extreme_close_up" and any(m in blob for m in _EYE_MARKERS):
            return {"framing_class": "ECU_EYES", "action_type": "hold", "visible_subject": "eyes"}
        return {"framing_class": "HOLD", "action_type": "hold", "visible_subject": "locked_frame"}

    if framing == "extreme_close_up":
        if any(m in blob for m in _HAND_MARKERS):
            return {"framing_class": "ECU_HAND", "action_type": "micro_performance", "visible_subject": "hands"}
        if any(m in blob for m in _EYE_MARKERS):
            return {"framing_class": "ECU_EYES", "action_type": "micro_performance", "visible_subject": "eyes"}
        if any(m in blob for m in _STEAM_MARKERS) or "lunchbox" in blob:
            return {"framing_class": "PROP_ONLY", "action_type": "ambient", "visible_subject": "lunchbox"}

    if "arriv" in blob:
        return {"framing_class": "WIDE_LOCO", "action_type": "locomotion", "visible_subject": "full_body"}
    if any(m in blob for m in ("bolt", "sprint", "run toward", "run to")) or (
        "run" in blob and not any(m in blob for m in ("does not run", "doesn't run", "not run"))
    ):
        return {"framing_class": "WIDE_LOCO", "action_type": "locomotion", "visible_subject": "full_body"}

    if len(chars) >= 2:
        if dialogue:
            return {"framing_class": "TWO_SHOT", "action_type": "dialogue", "visible_subject": "two_shot"}
        return {"framing_class": "TWO_SHOT", "action_type": "blocking", "visible_subject": "two_shot"}

    if (
        framing in {"medium_close_up", "close_up"}
        and chars in (["avery_sterling"], ["avery_sterling"])
        and any(w in blob for w in ("cooler", "pressed", "can't", "cannot", "doesn't move", "does not move"))
    ):
        return {"framing_class": "MCU_BODY", "action_type": "body_tension", "visible_subject": "avery_torso"}

    if chars in (["lucien_mercer"], ["lucien_mercer"]):
        return {"framing_class": "SINGLE", "action_type": "lucien_micro", "visible_subject": "lucien"}
    if chars in (["avery_sterling"], ["avery_sterling"]):
        return {"framing_class": "SINGLE", "action_type": "avery_declared", "visible_subject": "avery"}
    return {"framing_class": "SINGLE", "action_type": "declared", "visible_subject": "subject"}


def _loco_beats(cut: dict[str, Any]) -> list[str]:
    blob = _blob(cut)
    negative_run = any(m in blob for m in ("does not run", "doesn't run", "do not run", "not run"))
    if ("bolt" in blob or "sprint" in blob or "run" in blob) and not negative_run:
        return [
            "Avery starts planted. Weight shifts into the bolt.",
            "Avery sprints toward the swinging door. Real run cycle, alternate legs, no slide.",
            "Avery nearly clips the prep-cook silhouette. Keep running.",
            "Avery commits through the door path. No heroic slow-mo.",
            "Avery leaves this composition. He does not look back.",
        ]
    return [
        "Far-end silhouette resolves as Lucien, backlit. Avery stays pinned small at the cooler.",
        "Lucien's weight shifts. First unhurried step into the kitchen.",
        "Lucien continues a controlled approach. Avery does not run.",
        "Lucien decelerates. Foot plants at the declared distance.",
        "Lucien settles. Watch only. No smile, no close.",
    ]


def _two_shot_beats(cut: dict[str, Any]) -> list[str]:
    dialogue = cut.get("dialogue") or []
    blob = _blob(cut)
    if dialogue:
        first = dialogue[0] if isinstance(dialogue[0], dict) else {"speaker": "speaker", "line": str(dialogue[0])}
        line = first.get("line") or ""
        return [
            "Both hold the ten-foot two-shot. Avery pinned. Lucien watching. Mouths closed.",
            f"Avery starts the line. Mouth motion only as needed for: {line}",
            "Lucien holds and listens. Does not close the gap. Does not answer.",
            "Avery aborts the line. Body stays on his mark.",
            "Both hold the silence. Ten-foot geometry holds. No handshake.",
        ]
    if "stop" in blob or "ten feet" in blob or "watches" in blob:
        return [
            "Lucien plants ten feet off. Avery stays pinned at the cooler.",
            "Lucien watches Avery. He does not attack. He does not close the gap.",
            "Avery does not step forward. Lunchbox still in his hands.",
            "Lucien's weight settles. The ten-foot line holds.",
            "Both hold. Watch, not violence.",
        ]
    if "clap" in blob or "slips" in blob or "drop" in blob:
        return [
            "Avery and Lucien still ten feet apart. Lunchbox in Avery's hands.",
            "Avery's arm shoots up. The box slips.",
            "The lunchbox hits tile between Avery and Lucien. CLAP. Lid stays sealed.",
            "Neither Avery nor Lucien lunges. Food does not explode.",
            "Hold the box on the floor between Avery and Lucien.",
        ]
    visual = str(cut.get("visual") or "").strip()
    action = str(cut.get("action") or "").strip()
    return [
        f"Both already in the declared two-shot. {visual}",
        f"Avery and Lucien play only the declared action: {action}",
        "Neither Avery nor Lucien steals extra blocking.",
        "Avery and Lucien keep the ten-foot relationship unless the visual names a close.",
        "Both hold the end pose. No handshake.",
    ]


def _ecu_hand_beats(cut: dict[str, Any]) -> list[str]:
    blob = _blob(cut)
    names = {n.lower() for n in actor_names(cut)}
    if "knuckle" in blob and "lucien" in names:
        return [
            "Lucien's scarred knuckles already in frame. No face.",
            "Hands at rest. Light catches the scars.",
            "No fist clench into a punch.",
            "Hold the knuckles. No new body.",
        ]
    return [
        "Fingers already locked on the thermal lunchbox handle. Lid closed.",
        "Tremble travels through the knuckles. The box does not drop.",
        "Grip tightens a millimeter. Steam only at the seam.",
        "Hold the grip. Lid stays sealed.",
    ]


def _ecu_eye_beats(cut: dict[str, Any]) -> list[str]:
    names = actor_names(cut)
    who = names[0] if names else "The subject"
    return [
        f"{who}'s eyes already locked in frame. Dry. No blink burst.",
        f"{who} does not smile. Does not tear. Almost no motion.",
        "A micro still. Gaze does not dart off-axis.",
        f"Hold {who}'s eyes. No other body part enters.",
    ]


def _mcu_body_beats() -> list[str]:
    return [
        AVERY_FEAR_SIGNATURE,
        "Avery's chest rises faster. Grip on the lunchbox tightens slightly.",
        "Avery's knees soften. Shoulders contract. Eyes stay fixed forward.",
        "One unstable breath. Micro tremble only. Mouth stays closed.",
        "Avery freezes again on the same closed-mouth MCU pose.",
    ]


def _lucien_micro_beats(cut: dict[str, Any]) -> list[str]:
    blob = _blob(cut)
    action = str(cut.get("action") or "").strip()
    visual = str(cut.get("visual") or "").strip()
    if "look" in blob and "down" in blob:
        return [
            "Lucien already in frame. Head starts level.",
            "Lucien's head tilts down toward the sealed lunchbox at his feet.",
            "Lucien's eyes find the lid. He does not open it.",
            "Lucien holds the look down. No smile.",
        ]
    if "door" in blob or "lifts" in blob:
        return [
            "Lucien already looking down. Face still.",
            "Lucien's gaze lifts, slow, toward the door Avery just left.",
            "Lucien holds on the empty door. No chase.",
            "Lucien's face does not soften into a smile.",
        ]
    if "eye" in blob or "crack" in blob:
        return [
            "Lucien's eyes already dead-still in frame.",
            "A hairline shift behind the eyes. Not anger yet. Not a name.",
            "Hold the crack. No grin. No tears.",
            "Lucien does not look away.",
        ]
    return [
        f"Lucien already in the declared pose. {visual}",
        f"Lucien plays only: {action}",
        "No Avery physiology. No extra locomotion.",
        "Lucien holds the end of the declared action.",
    ]


def _avery_declared_beats(cut: dict[str, Any]) -> list[str]:
    blob = _blob(cut)
    visual = str(cut.get("visual") or "").strip()
    action = str(cut.get("action") or "").strip()
    if "couscous" in blob or "smoothing" in blob:
        return [
            "Avery's hands already over the open lunchbox. Face not required if framing hides it.",
            "Avery smooths plain couscous over the lavish plate.",
            "The lid stays in play as a cover, not a spill.",
            "Avery holds the disguise. No smile.",
        ]
    if "drawstring" in blob or "snag" in blob or "hood" in blob:
        return [
            "Avery already in the doorway path. Hoodie on.",
            f"Avery plays the snag: {action}",
            "The drawstring catches. Avery's ears may flash. No new hairstyle.",
            "Avery holds the caught beat. No comedy face redesign.",
        ]
    if "spine" in blob or "half-turned" in blob or "shoulders shaking" in blob:
        return [
            "Avery's back already half-turned. Lunchbox still in play if framed.",
            "Avery forces his spine straight. Shoulders still shaking.",
            "Avery does not sprint yet unless the visual names the bolt.",
            "Hold the half-turn. Mouth closed.",
        ]
    return [
        f"Avery already in the declared start pose. {visual}",
        f"Avery plays only the declared action: {action}",
        "Do not invent knees, a walk, or a new prop state unless the visual names them.",
        "Avery holds the end pose. No smile.",
    ]


def compile_beat_actions(cut: dict[str, Any], obligation: str) -> list[str]:
    profile = classify_shot(cut)
    framing = profile["framing_class"]
    action_type = profile["action_type"]
    blob = _blob(cut)

    if obligation == "LOCAL" or framing == "GRAPHIC":
        if "steam" in blob:
            return [
                "Steam already leaking at the sealed seam. Lid closed.",
                "A wisp curls upward. No lid pop. Box does not slide.",
                "Steam thins but keeps rising.",
                "Hold the last curl. Meal still intact.",
            ]
        if any(m in blob for m in _DOOR_MARKERS):
            return [
                "Door already swinging from the exit. Empty doorway.",
                "First thup. Arc decays.",
                "Second thup, smaller.",
                "Door stills. No one returns.",
            ]
        if framing == "GRAPHIC" or "hud" in blob:
            return [
                "Black. Glyph off.",
                "Flicker on. Text assembling letter by letter.",
                "Glyph holds, still glitching. No face.",
            ]
        return [
            "Declared local motion already in frame.",
            "Continue only that overlay.",
            "Do not invent a character performance.",
        ]

    if action_type == "hold" or obligation == "NONE":
        return [str(cut.get("action") or "Hold the last frame.")]

    if framing == "WIDE_LOCO" or action_type == "locomotion":
        return _loco_beats(cut)
    if framing == "TWO_SHOT":
        return _two_shot_beats(cut)
    if framing == "ECU_HAND":
        return _ecu_hand_beats(cut)
    if framing == "ECU_EYES":
        return _ecu_eye_beats(cut)
    if framing == "MCU_BODY":
        return _mcu_body_beats()
    if action_type == "lucien_micro":
        return _lucien_micro_beats(cut)
    if action_type == "avery_declared":
        return _avery_declared_beats(cut)
    visual = str(cut.get("visual") or "").strip()
    action = str(cut.get("action") or "").strip()
    who = ", ".join(actor_names(cut)) or "The subject"
    return [
        f"{who} already in the declared start pose. {visual}",
        f"Play only: {action}",
        "No borrowed physiology from another cut.",
        f"{who} holds the end of the declared action.",
    ]


def lint_temporal_beats(cut: dict[str, Any], actions: list[str]) -> None:
    profile = classify_shot(cut)
    framing = profile["framing_class"]
    joined = " ".join(actions).lower()
    cut_id = cut.get("cut_id") or cut.get("cut_id") or cut.get("id") or "<cut>"

    if framing == "MCU_BODY":
        if AVERY_FEAR_SIGNATURE.lower() not in joined:
            raise ShotDirectorError(f"{cut_id}: Avery MCU lost its body-tension beats")
    elif AVERY_FEAR_SIGNATURE.lower() in joined:
        raise ShotDirectorError(
            f"{cut_id}: Avery fear template leaked into {framing}/{profile['action_type']}"
        )

    for token in _FORBIDDEN.get(framing, ()):
        if token in joined:
            raise ShotDirectorError(
                f"{cut_id}: {token!r} is not observable in {framing} ({profile['visible_subject']})"
            )

    if framing == "TWO_SHOT":
        for i, line in enumerate(actions):
            low = line.lower()
            if "avery" not in low and "lucien" not in low and "both" not in low:
                raise ShotDirectorError(f"{cut_id}: two-shot beat {i} does not name an actor: {line}")

    if framing == "WIDE_LOCO":
        if not any(w in joined for w in ("step", "gait", "plant", "settle", "sprint", "run", "arriv", "bolt")):
            raise ShotDirectorError(f"{cut_id}: locomotion beats have no displacement")


def first_frame_readiness(
    cut: dict[str, Any],
    bindings: list[dict[str, Any]],
    plate: dict[str, Any] | None,
    *,
    require_h3: bool,
) -> dict[str, Any]:
    """Character/scene/prop plates are references. FL2VA needs a 9:16 shot keyframe."""
    comp_id = str(cut.get("composition_anchor") or cut.get("composition_anchor") or "")
    comp = next((row for row in bindings if row.get("id") == comp_id), None)
    plate_kind = str((plate or {}).get("kind") or "")
    aspect_note = str((plate or {}).get("aspect_note") or "")
    sixteen_nine = "16:9" in aspect_note
    blockers: list[str] = []
    role = "MISSING"

    if not comp_id:
        blockers.append("no composition_anchor")
    elif not comp or comp.get("status") != "bound":
        blockers.append(f"required {comp_id} unresolved")

    if plate_kind == "character":
        role = "IDENTITY_REFERENCE"
        blockers.append("character master sheet is IDENTITY_REFERENCE, not SHOT_KEYFRAME")
    elif plate_kind == "scene":
        role = "SCENE_REFERENCE"
        blockers.append("scene plate is SCENE_REFERENCE, not SHOT_KEYFRAME")
    elif plate_kind == "prop":
        role = "PROP_REFERENCE"
        blockers.append("prop plate is PROP_REFERENCE, not SHOT_KEYFRAME")
    elif plate_kind == "composition":
        role = "COMPOSITION_REFERENCE"
        if sixteen_nine:
            blockers.append("composition plate is 16:9 corpus, not a 9:16 SHOT_KEYFRAME")
        else:
            blockers.append("composition plate is not marked as 9:16 SHOT_KEYFRAME")
    elif require_h3:
        blockers.append("no first-frame plate")

    if sixteen_nine and "16:9" not in " ".join(blockers):
        blockers.append("bound plate is 16:9 Scene A corpus; 9:16 shot keyframe missing")

    if require_h3:
        blockers.append("H3 FL2VA blocked until first_frame.kind=SHOT_KEYFRAME at 9:16")

    from lib.character_variant import start_frame_is_variant_still, still_refs_of

    plate_path = str((plate or {}).get("path") or "").replace("\\", "/").strip()
    variant_stills = still_refs_of(
        cut.get("character_variant") if isinstance(cut.get("character_variant"), dict) else None
    )
    if start_frame_is_variant_still(cut) or (plate_path and plate_path in variant_stills):
        if role == "MISSING":
            role = "IDENTITY_REFERENCE"
        blockers.append("character_variant.still_refs are IDENTITY_REFERENCE, not SHOT_KEYFRAME")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for item in blockers:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    payload = {
        "role": role if plate else "MISSING",
        "shot_ready": False,
        "path": (plate or {}).get("path"),
        "composition_id": comp_id or None,
        "aspect": "16:9" if sixteen_nine else None,
        "blockers": unique,
        "h3_dispatch_allowed": False,
    }
    payload["shot_ready"] = payload["shot_ready"]
    payload["h3_dispatch_allowed"] = payload["h3_dispatch_allowed"]
    payload["blockers"] = payload["blockers"]
    return payload


def annotate_bindings(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_by_kind = {
        "character": "IDENTITY_REFERENCE",
        "scene": "SCENE_REFERENCE",
        "prop": "PROP_REFERENCE",
        "composition": "COMPOSITION_REFERENCE",
        "style": "STYLE_REFERENCE",
        "sound": "SOUND_REFERENCE",
    }
    out = []
    for row in bindings:
        item = dict(row)
        item["role"] = role_by_kind.get(str(row.get("kind") or ""), "UNSPECIFIED")
        out.append(item)
    return out


BENCHMARK_KEYFRAMES = (
    {
        "cut_id": "E01_B1_B",
        "composition_id": "COMP_AVERY_COOLER_MCU",
        "title": "Avery cooler MCU",
        "must_show": "Avery pressed to cooler, lunchbox in both hands, 9:16 MCU, mouth closed",
    },
    {
        "cut_id": "E01_B2_A",
        "composition_id": "COMP_LUCIEN_BACKLIT_KITCHEN",
        "title": "Lucien arriving, Avery small at cooler",
        "must_show": "9:16 kitchen wide. Lucien resolving far, backlit. Avery pinned small at cooler.",
    },
    {
        "cut_id": "E01_B2_E",
        "composition_id": "COMP_TWO_SHOT_TEN_FEET",
        "title": "Ten-foot two-shot",
        "must_show": "9:16 two-shot, Avery and Lucien ten feet apart, lunchbox on Avery",
    },
    {
        "cut_id": "E01_B7_C",
        "composition_id": "COMP_LUNCHBOX_ON_TILE",
        "title": "Lunchbox-on-tile ECU",
        "must_show": "9:16 ECU sealed lunchbox on tile, steam at seam, no faces",
    },
)

# Import aliases — drama_preproduction and tests use both namings.
classify_shot = classify_shot
compile_beat_actions = compile_beat_actions
lint_temporal_beats = lint_temporal_beats
first_frame_readiness = first_frame_readiness
annotate_bindings = annotate_bindings
BENCHMARK_KEYFRAMES = BENCHMARK_KEYFRAMES
AVERY_FEAR_SIGNATURE = AVERY_FEAR_SIGNATURE
ShotDirectorError = ShotDirectorError
actor_names = actor_names
