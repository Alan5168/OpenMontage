"""Narrow freeze-frame invariant for fiction_anime_episode compose.

Pure static hold output must not exceed the profile's freeze_frame_max_seconds.
Does not require blink, H3, or a new producibility platform.
"""

from __future__ import annotations

from typing import Any

from lib.scenario_catalog import load_profile

FICTION_ANIME_EPISODE = "fiction_anime_episode"
STATIC_ANIMATIONS = frozenset({"", "static", "none", "hold"})
DEFAULT_EXPLAINER_PAD_SECONDS = 1.0


def profile_id_of(inputs: dict[str, Any]) -> str | None:
    raw_profile = inputs.get("profile")
    if isinstance(raw_profile, str) and raw_profile.strip():
        return raw_profile.strip()
    if isinstance(raw_profile, dict):
        ident = raw_profile.get("id")
        if ident:
            return str(ident)
    plan = inputs.get("scene_plan")
    if isinstance(plan, dict):
        meta = plan.get("metadata") if isinstance(plan.get("metadata"), dict) else {}
        ident = meta.get("profile")
        if ident:
            return str(ident)
    return None


def freeze_frame_max_seconds(profile_id: str, profile: dict[str, Any] | None = None) -> float | None:
    if profile_id != FICTION_ANIME_EPISODE:
        return None
    blob = profile if isinstance(profile, dict) else None
    if blob is None or "quality_thresholds" not in blob:
        blob, _ = load_profile(profile_id)
    thresholds = blob.get("quality_thresholds") if isinstance(blob.get("quality_thresholds"), dict) else {}
    raw = thresholds.get("freeze_frame_max_seconds")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def is_pure_static_hold(cut: dict[str, Any]) -> bool:
    animation = str(cut.get("animation") or "").strip().lower()
    transform = cut.get("transform") if isinstance(cut.get("transform"), dict) else {}
    if not animation:
        animation = str(transform.get("animation") or "").strip().lower()
    motion = str(cut.get("motion_route") or "").strip().lower()
    if animation in STATIC_ANIMATIONS and motion in {"", "hold"}:
        return True
    if animation in STATIC_ANIMATIONS:
        return True
    return False


def cut_hold_seconds(cut: dict[str, Any]) -> float:
    try:
        start = float(cut.get("in_seconds", cut.get("start_seconds", 0)) or 0)
        end = float(cut.get("out_seconds", cut.get("end_seconds", start)) or start)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, end - start)


def explainer_pad_seconds(props: dict[str, Any], *, composition_id: str | None = None) -> float:
    if composition_id and composition_id != "Explainer":
        return 0.0
    raw = props.get("padEndSeconds")
    if raw is None:
        return DEFAULT_EXPLAINER_PAD_SECONDS
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return DEFAULT_EXPLAINER_PAD_SECONDS


def planned_static_output_seconds(cut: dict[str, Any], *, pad_seconds: float) -> float:
    return cut_hold_seconds(cut) + pad_seconds


def apply_static_hold_pad(props: dict[str, Any], profile_id: str | None) -> dict[str, Any]:
    """Explainer must not add a 1s fade pad onto a fiction_anime_episode static hold."""
    if profile_id != FICTION_ANIME_EPISODE:
        return props
    cuts = props.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        return props
    static_cuts = [row for row in cuts if isinstance(row, dict) and is_pure_static_hold(row)]
    if len(static_cuts) != len(cuts):
        return props
    props["padEndSeconds"] = 0
    return props


def freeze_hold_error(
    inputs: dict[str, Any],
    *,
    composition_id: str | None = None,
    props: dict[str, Any] | None = None,
) -> str | None:
    ident = profile_id_of(inputs)
    if ident != FICTION_ANIME_EPISODE:
        return None
    raw_profile = inputs.get("profile") if isinstance(inputs.get("profile"), dict) else None
    limit = freeze_frame_max_seconds(ident, raw_profile)
    if limit is None:
        return None
    payload = props if isinstance(props, dict) else {}
    cuts = payload.get("cuts")
    if not isinstance(cuts, list):
        decisions = inputs.get("edit_decisions")
        cuts = decisions.get("cuts") if isinstance(decisions, dict) else None
    if not isinstance(cuts, list):
        plan = inputs.get("scene_plan")
        scenes = plan.get("scenes") if isinstance(plan, dict) else None
        cuts = []
        for scene in scenes or []:
            if not isinstance(scene, dict):
                continue
            cuts.append(
                {
                    "in_seconds": scene.get("start_seconds"),
                    "out_seconds": scene.get("end_seconds"),
                    "animation": "static" if str(scene.get("motion_route") or "").upper() == "HOLD" else scene.get("animation"),
                    "motion_route": scene.get("motion_route"),
                }
            )
    pad = explainer_pad_seconds(payload if payload else (inputs.get("edit_decisions") or {}), composition_id=composition_id)
    for cut in cuts:
        if not isinstance(cut, dict) or not is_pure_static_hold(cut):
            continue
        output = planned_static_output_seconds(cut, pad_seconds=pad)
        if output > limit + 1e-6:
            return (
                "fiction_anime_episode static hold "
                f"{output:.2f}s exceeds freeze_frame_max_seconds={limit:g} "
                "(pure static hold only; pan/overlay/blink are out of scope)"
            )
    return None
