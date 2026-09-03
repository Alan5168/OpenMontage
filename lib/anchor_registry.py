"""Resolve scene_plan anchor ids to on-disk plates + sha256.

Text ids are not visual anchors. A bound plate is. Missing files stay
``unresolved`` — that is a compile fact, not a fake hash.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

STUDIO_ROOT = Path(__file__).resolve().parents[3]
VID3 = STUDIO_ROOT / "jobs" / "vid3-blacklisted-chef-90s-v1"
ASPECT_NOTE = "16:9 Scene A corpus; 9:16 rewrite required before this job locks layout."

# Relative to VID3. Bind identity/layout plates that already exist.
_PLATES: dict[str, tuple[str, str]] = {
    "CHAR_AVERY_V1": ("character", "bible/avery/master_sheet.png"),
    "CHAR_LUCIEN_V1": ("character", "bible/lucien/master_sheet.png"),
    "SCENE_BACK_KITCHEN_V2": ("scene", "bible/avery/approved/backkitchen_wide.jpg"),
    "PROP_LUNCHBOX_V1": ("prop", "assets/stills/scene_a/A6_lunchbox.png"),
    "COMP_AVERY_COOLER_MCU": ("composition", "assets/stills/scene_a/A2_mcu.png"),
    "COMP_HUD_BLACK": ("composition", "assets/stills/scene_a/A1a_hud.png"),
    "COMP_KITCHEN_EST_AVERY_SMALL": ("composition", "assets/stills/scene_a/A4_wide.png"),
    "COMP_LUNCHBOX_INSERT": ("composition", "assets/stills/scene_a/A6_lunchbox.png"),
    "COMP_LUNCHBOX_ON_TILE": ("composition", "assets/stills/scene_a/A6_lunchbox.png"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind_anchor(anchor_id: str) -> dict[str, Any]:
    spec = _PLATES.get(anchor_id)
    if spec is None:
        kind = "style" if anchor_id.startswith("STYLE") else (
            "sound" if anchor_id.startswith("SOUND") else "unspecified"
        )
        return {
            "id": anchor_id,
            "kind": kind,
            "status": "unresolved",
            "path": None,
            "sha256": None,
            "aspect_note": None,
        }
    kind, rel = spec
    path = VID3 / rel
    if not path.is_file():
        return {
            "id": anchor_id,
            "kind": kind,
            "status": "unresolved",
            "path": str(path).replace("\\", "/"),
            "sha256": None,
            "aspect_note": ASPECT_NOTE,
        }
    return {
        "id": anchor_id,
        "kind": kind,
        "status": "bound",
        "path": str(path).replace("\\", "/"),
        "sha256": _sha256(path),
        "aspect_note": ASPECT_NOTE,
    }


def bind_anchors(anchor_ids: list[str]) -> list[dict[str, Any]]:
    return [bind_anchor(aid) for aid in anchor_ids]


def layout_plate(bindings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer a bound composition plate, then the first bound character, then scene."""
    for kind in ("composition", "character", "scene", "prop"):
        for row in bindings:
            if row.get("status") == "bound" and row.get("kind") == kind and row.get("path"):
                return row
    return None
