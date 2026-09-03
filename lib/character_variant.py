"""Phase × costume slot on a ShotContract.

Job CHARACTER_CARDS already store this tree. The field on scene_plan.scenes[]
is the cut-level bind. Stills here are IDENTITY_REFERENCE, never SHOT_KEYFRAME.

Stolen as a gate, not a factory: moyin/StarReel/ArcReel keep wardrobe on the
character record. Do not copy those UIs, MCP servers, or AGPL trees.
"""

from __future__ import annotations

from typing import Any

VARIANT_STILL_AS_START = "character_variant_still_used_as_start_frame"
VARIANT_ID_NOT_IN_CAST = "character_variant_id_not_in_character_ids"
WORLD_LOCK_HOLDS_WARDROBE = "world_lock_holds_character_wardrobe"

BANNED_WORLD_LOCK_KEYS = frozenset(
    {
        "wardrobe",
        "costume",
        "hair",
        "face",
        "appearance",
        "character_look",
        "must_show",
        "portrait",
        "character_wardrobe",
        "character_hair",
    }
)

_VIEW_ENUM = frozenset(
    {"front_3q", "full_body", "front_face", "profile_left", "profile_right"}
)


class CharacterVariantError(ValueError):
    """Illegal character_variant. Do not dispatch."""


def _norm_path(path: Any) -> str:
    return str(path or "").replace("\\", "/").strip()


def still_refs_of(variant: dict[str, Any] | None) -> list[str]:
    if not isinstance(variant, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in variant.get("still_refs") or []:
        key = _norm_path(item)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def normalize_character_variant(
    raw: Any,
    character_ids: list[Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CharacterVariantError("character_variant must be an object")
    character_id = str(raw.get("character_id") or "").strip()
    if not character_id:
        raise CharacterVariantError("character_variant.character_id is required")
    ids = [str(item).strip() for item in (character_ids or []) if str(item).strip()]
    if ids and character_id not in ids:
        raise CharacterVariantError(
            f"{VARIANT_ID_NOT_IN_CAST}: {character_id!r} not in {ids}"
        )
    view = str(raw.get("view") or "").strip()
    if view and view not in _VIEW_ENUM:
        raise CharacterVariantError(
            f"character_variant.view must be one of {sorted(_VIEW_ENUM)}; got {view!r}"
        )
    payload: dict[str, Any] = {"character_id": character_id}
    for key in ("phase", "costume", "must_show"):
        value = str(raw.get(key) or "").strip()
        if value:
            payload[key] = value
    if view:
        payload["view"] = view
    refs = still_refs_of(raw)
    if refs:
        payload["still_refs"] = refs
    return payload


def identity_from_variant(scene: dict[str, Any] | None) -> dict[str, Any]:
    """H3 identity block. Picture 1 remains the shot keyframe, not still_refs."""
    scene = scene if isinstance(scene, dict) else {}
    raw = scene.get("character_variant")
    if not isinstance(raw, dict):
        return {}
    name = str(raw.get("character_id") or "").strip()
    if not name:
        ids = [str(item).strip() for item in (scene.get("character_ids") or []) if str(item).strip()]
        name = ids[0] if ids else ""
    if not name:
        return {}
    must: list[str] = []
    if raw.get("phase"):
        must.append(f"phase {raw['phase']}")
    if raw.get("costume"):
        must.append(str(raw["costume"]))
    if raw.get("must_show"):
        must.append(str(raw["must_show"]))
    payload: dict[str, Any] = {"name": name}
    if must:
        payload["must"] = must
    if scene.get("experimental_reference_binding"):
        from lib.reference_binding import bindings_from_owner

        bindings = bindings_from_owner(owner=name, still_refs=still_refs_of(raw))
        if bindings:
            payload["reference_bindings"] = bindings
    return payload


def start_frame_is_variant_still(scene: dict[str, Any] | None) -> bool:
    scene = scene if isinstance(scene, dict) else {}
    start = _norm_path(scene.get("start_frame_ref"))
    visual = scene.get("visual_ref") if isinstance(scene.get("visual_ref"), dict) else {}
    start = start or _norm_path(visual.get("path"))
    if not start:
        return False
    return start in still_refs_of(scene.get("character_variant"))


def cut_variant_blockers(scene: dict[str, Any] | None) -> list[str]:
    scene = scene if isinstance(scene, dict) else {}
    raw = scene.get("character_variant")
    if raw is None:
        return []
    blockers: list[str] = []
    try:
        normalize_character_variant(raw, scene.get("character_ids"))
    except CharacterVariantError as exc:
        text = str(exc)
        if VARIANT_ID_NOT_IN_CAST in text:
            blockers.append(VARIANT_ID_NOT_IN_CAST)
        else:
            blockers.append("character_variant_invalid")
        return blockers
    if start_frame_is_variant_still(scene):
        blockers.append(VARIANT_STILL_AS_START)
    return blockers


def world_lock_wardrobe_keys(world_lock: Any) -> list[str]:
    if not isinstance(world_lock, dict):
        return []
    return sorted(key for key in world_lock if str(key).strip().lower() in BANNED_WORLD_LOCK_KEYS)


def resolve_from_character_cards(
    cards: dict[str, Any] | None,
    *,
    character_id: str,
    phase: str | None = None,
    costume: str | None = None,
) -> dict[str, Any]:
    """Bind a cut to a CHARACTER_CARDS row. Does not ingest stills as H3 frames."""
    rows = (cards or {}).get("characters") if isinstance(cards, dict) else None
    if not isinstance(rows, list):
        raise CharacterVariantError("character cards have no characters[]")
    want_id = str(character_id).strip()
    want_phase = str(phase or "").strip()
    want_costume = str(costume or "").strip()
    hits: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        om_id = str(row.get("om_id") or row.get("id") or "").strip()
        if om_id != want_id:
            continue
        if want_phase and str(row.get("phase") or "").strip() != want_phase:
            continue
        row_costume = str(row.get("variant") or row.get("costume") or "").strip()
        if want_costume and row_costume != want_costume:
            continue
        hits.append(row)
    if not hits:
        raise CharacterVariantError(
            f"no character card for {want_id!r} phase={want_phase!r} costume={want_costume!r}"
        )
    row = hits[0]
    return normalize_character_variant(
        {
            "character_id": want_id,
            "phase": row.get("phase"),
            "costume": row.get("variant") or row.get("costume"),
            "must_show": row.get("must_show"),
            "still_refs": list(row.get("generated") or []),
        },
        [want_id],
    )
