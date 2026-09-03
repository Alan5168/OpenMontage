"""Experimental H3/Seedance *provider dialect* for typed reference stills.

RWTS-001 H4. NOT a production policy. NOT a ShotContract schema.
NOT “every CHARACTER_IDENTITY must emit this inherit / do_not_inherit list.”

Use only when a caller sets ``experimental_reference_binding``.
CHARACTER_IDENTITY defaults are a *candidate* grounded in one RunningHub
9-ref teacher. They are not promoted.

Do **not** treat SCENE / PROP / COMPOSITION tables as learned policy.
Those tuples are UNVERIFIED_DEFAULTS and must not drive production compiles.

Picture 1 (SHOT_KEYFRAME / DIRECTED_MCU_COPY) stays composition.
Identity stills never become <Picture 1>.
"""

from __future__ import annotations

from typing import Any

EXPERIMENTAL_DIALECT = True
PRODUCTION_POLICY = False

CHARACTER_IDENTITY = "CHARACTER_IDENTITY"
SCENE_REFERENCE = "SCENE_REFERENCE"
PROP_REFERENCE = "PROP_REFERENCE"
COMPOSITION_REFERENCE = "COMPOSITION_REFERENCE"
SHOT_KEYFRAME = "SHOT_KEYFRAME"

# Candidate only. One 9-ref teacher. Not a global identity rule.
CHARACTER_INHERIT = ("face", "hair", "costume", "proportions")
CHARACTER_DO_NOT_INHERIT = (
    "sheet background",
    "duplicate bodies",
    "panel divisions",
    "pose",
    "model-sheet layout",
    "studio lighting",
)

# Do not promote. Do not attach in packers. Second teacher / held-out first.
UNVERIFIED_DEFAULTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    SCENE_REFERENCE: (
        ("space", "set dressing", "lighting direction"),
        ("extra characters", "duplicate architecture", "caption text"),
    ),
    PROP_REFERENCE: (
        ("object shape", "material", "scale relative to the owner"),
        ("product-shot backdrop", "duplicate props", "catalog typography"),
    ),
    COMPOSITION_REFERENCE: (
        ("framing", "eyeline", "blocking"),
        ("identity swap", "wardrobe from a different owner"),
    ),
}

_ROLE_FROM_PACK = {
    "IDENTITY_REFERENCE": CHARACTER_IDENTITY,
    "SCENE_REFERENCE": SCENE_REFERENCE,
    "PROP_REFERENCE": PROP_REFERENCE,
    "COMPOSITION_REFERENCE": COMPOSITION_REFERENCE,
    "SHOT_KEYFRAME": SHOT_KEYFRAME,
}


def defaults_for_role(semantic_role: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Candidate lists. SCENE/PROP are unverified and must not be treated as policy."""
    role = str(semantic_role or "").strip()
    if role in {CHARACTER_IDENTITY, "IDENTITY_REFERENCE"}:
        return CHARACTER_INHERIT, CHARACTER_DO_NOT_INHERIT
    if role in UNVERIFIED_DEFAULTS:
        return UNVERIFIED_DEFAULTS[role]
    return (), ()


def binding(
    *,
    owner: str,
    semantic_role: str = CHARACTER_IDENTITY,
    slot: str | None = None,
    source_asset: str | None = None,
    inherit: tuple[str, ...] | list[str] | None = None,
    do_not_inherit: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    role = str(semantic_role or CHARACTER_IDENTITY).strip() or CHARACTER_IDENTITY
    default_in, default_out = defaults_for_role(role)
    row: dict[str, Any] = {
        "experimental": True,
        "slot": slot or "REF_1",
        "semantic_role": role,
        "owner": str(owner or "").strip(),
        "inherit": list(inherit if inherit is not None else default_in),
        "do_not_inherit": list(
            do_not_inherit if do_not_inherit is not None else default_out
        ),
    }
    if source_asset:
        row["source_asset"] = str(source_asset).replace("\\", "/")
    return row


def bindings_from_owner(
    *,
    owner: str,
    still_refs: list[str] | None,
    semantic_role: str = CHARACTER_IDENTITY,
) -> list[dict[str, Any]]:
    name = str(owner or "").strip()
    refs = [str(item).replace("\\", "/").strip() for item in (still_refs or []) if str(item).strip()]
    if not name or not refs:
        return []
    out: list[dict[str, Any]] = []
    for index, path in enumerate(refs, start=1):
        out.append(
            binding(
                owner=name,
                semantic_role=semantic_role,
                slot=f"REF_{index}",
                source_asset=path,
            )
        )
    return out


def annotate_packed_role(
    row: dict[str, Any],
    *,
    owner: str | None = None,
    experimental: bool = False,
) -> dict[str, Any]:
    """Opt-in only. CHARACTER_IDENTITY candidate lists. Never SCENE/PROP policy."""
    packed = dict(row)
    if not experimental:
        return packed
    pack_role = str(packed.get("role") or "").strip()
    semantic = _ROLE_FROM_PACK.get(pack_role, pack_role)
    if semantic != CHARACTER_IDENTITY:
        return packed
    inherit, banned = defaults_for_role(CHARACTER_IDENTITY)
    packed["experimental"] = True
    packed["semantic_role"] = CHARACTER_IDENTITY
    packed["inherit"] = list(inherit)
    packed["do_not_inherit"] = list(banned)
    if owner:
        packed["owner"] = str(owner).strip()
    return packed


def compile_bindings_stanza(bindings: Any) -> str:
    """Experimental dialect text. Does not name a still as Picture 1."""
    rows = [item for item in (bindings or []) if isinstance(item, dict) and item.get("owner")]
    if not rows:
        return ""
    bits: list[str] = ["[experimental_reference_binding]"]
    for row in rows:
        role = str(row.get("semantic_role") or CHARACTER_IDENTITY)
        owner = str(row.get("owner") or "").strip()
        slot = str(row.get("slot") or "REF")
        inherit = ", ".join(str(x) for x in (row.get("inherit") or []) if str(x).strip())
        banned = ", ".join(str(x) for x in (row.get("do_not_inherit") or []) if str(x).strip())
        bits.append(
            f"{slot} is {role} owned by {owner} only. "
            f"One body. Inherit {inherit}. "
            f"Do not inherit {banned}."
        )
    bits.append(
        "Each reference identity permanently belongs to one body only. "
        "Multi-view sheets must never become additional people."
    )
    return " ".join(bits)
