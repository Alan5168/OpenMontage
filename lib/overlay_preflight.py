"""L0 overlay compiler. Runs before the full mp4. Does not call a model.

Glyph clip, single-character CJK widows, and safe-area overflow must fail here
so visual_review / Pi / Alan never see them.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from typing import Any

from schemas.artifacts import validate_artifact

CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uff00-\uffef]")
MAX_REPAIRS = 2
DEFAULT_CANVAS = (1080, 1920)
# GM_DESIGN 2026-08-09: top 10% / bottom 20% / side 5%
SAFE_FRAC = (0.05, 0.10, 0.95, 0.80)

PRESETS: dict[str, dict[str, Any]] = {
    "hero_title": {"font_size": 72, "max_width_frac": 0.85, "max_lines": 3, "line_height": 1.2},
    "section_title": {"font_size": 28, "max_width_frac": 0.80, "max_lines": 2, "line_height": 1.2},
    "text_card": {"font_size": 64, "max_width_frac": 0.80, "max_lines": 4, "line_height": 1.3},
    "stat_reveal": {"font_size": 96, "max_width_frac": 0.80, "max_lines": 2, "line_height": 1.1},
    "caption": {"font_size": 42, "max_width_frac": 0.80, "max_lines": 2, "line_height": 1.3},
}


class OverlayPreflightError(ValueError):
    """L0 overlay layout unresolved after automatic repair."""


def is_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def _cjk_len(text: str) -> int:
    return sum(1 for ch in text if CJK_RE.match(ch))


def char_width(ch: str, font_size: float) -> float:
    if ch in "\n\r":
        return 0.0
    if CJK_RE.match(ch) or unicodedata.east_asian_width(ch) in {"W", "F"}:
        return font_size
    if ch == " ":
        return font_size * 0.30
    return font_size * 0.55


def measure_line(text: str, font_size: float) -> float:
    return sum(char_width(ch, font_size) for ch in text)


def wrap_text(text: str, max_width: float, font_size: float) -> list[str]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    if "\n" in text:
        lines: list[str] = []
        for part in text.split("\n"):
            lines.extend(wrap_text(part, max_width, font_size) or [""])
        return lines
    lines = []
    current = ""
    for ch in text:
        trial = current + ch
        if current and measure_line(trial, font_size) > max_width:
            lines.append(current)
            current = ch.lstrip() if ch == " " else ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [text]


def balance_orphan(lines: list[str]) -> list[str]:
    """Steal characters so the last line is not a single CJK glyph."""
    if len(lines) < 2:
        return lines
    last = lines[-1].strip()
    if _cjk_len(last) != 1 or len(last) > 2:
        return lines
    prev = lines[-2]
    if _cjk_len(prev) < 4:
        return lines
    move = 2 if _cjk_len(prev) >= 6 else 1
    chars = list(prev)
    take = "".join(chars[-move:])
    lines[-2] = "".join(chars[:-move])
    lines[-1] = take + last
    return [line for line in lines if line != ""]


def _preset(kind: str) -> dict[str, Any]:
    return dict(PRESETS.get(kind, PRESETS["hero_title"]))


def _safe_box(canvas: tuple[int, int]) -> tuple[float, float, float, float]:
    width, height = canvas
    left, top, right, bottom = SAFE_FRAC
    return left * width, top * height, right * width, bottom * height


def check_layout(
    lines: list[str],
    *,
    font_size: float,
    max_width: float,
    max_lines: int,
    line_height: float,
    canvas: tuple[int, int],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not lines:
        issues.append({"code": "empty_text", "detail": "overlay text is empty"})
        return issues
    for line in lines:
        width = measure_line(line, font_size)
        if width > max_width + 0.5:
            issues.append({
                "code": "glyph_clip",
                "detail": f"line {line!r} width {width:.0f}px exceeds box {max_width:.0f}px",
            })
    if len(lines) >= 2 and _cjk_len(lines[-1].strip()) == 1:
        issues.append({
            "code": "orphan_line",
            "detail": f"last line is a single CJK glyph: {lines[-1]!r}",
        })
    if len(lines) > max_lines:
        issues.append({
            "code": "max_lines",
            "detail": f"{len(lines)} lines > max {max_lines}",
        })
    block_height = len(lines) * font_size * line_height
    _left, top, _right, bottom = _safe_box(canvas)
    if block_height > (bottom - top):
        issues.append({
            "code": "safe_area",
            "detail": f"block height {block_height:.0f}px exceeds safe area",
        })
    return issues


def repair_layout(
    text: str,
    kind: str,
    canvas: tuple[int, int] = DEFAULT_CANVAS,
) -> dict[str, Any]:
    preset = _preset(kind)
    font_size = float(preset["font_size"])
    max_width = canvas[0] * float(preset["max_width_frac"])
    repairs: list[str] = []
    lines = wrap_text(text, max_width, font_size)
    lines = balance_orphan(lines)
    issues = check_layout(
        lines,
        font_size=font_size,
        max_width=max_width,
        max_lines=int(preset["max_lines"]),
        line_height=float(preset["line_height"]),
        canvas=canvas,
    )
    attempt = 0
    while issues and attempt < MAX_REPAIRS:
        attempt += 1
        if any(item["code"] == "orphan_line" for item in issues):
            lines = balance_orphan(lines)
            repairs.append(f"balance_orphan@{attempt}")
        if any(item["code"] in {"glyph_clip", "max_lines", "safe_area"} for item in issues):
            font_size = round(font_size * 0.9, 1)
            max_width = canvas[0] * float(preset["max_width_frac"])
            lines = balance_orphan(wrap_text(text, max_width, font_size))
            repairs.append(f"shrink_font:{font_size}@{attempt}")
        issues = check_layout(
            lines,
            font_size=font_size,
            max_width=max_width,
            max_lines=int(preset["max_lines"]),
            line_height=float(preset["line_height"]),
            canvas=canvas,
        )
    return {
        "text": "\n".join(lines),
        "lines": lines,
        "font_size": font_size,
        "issues": issues,
        "repairs": repairs,
        "ok": not issues,
    }


def _kind_from_type(raw: str | None) -> str:
    value = (raw or "hero_title").lower()
    if value in PRESETS:
        return value
    if "caption" in value or "subtitle" in value:
        return "caption"
    if "section" in value:
        return "section_title"
    if "stat" in value:
        return "stat_reveal"
    if "card" in value or "text" in value:
        return "text_card"
    return "hero_title"


def collect_jobs(edit_decisions: dict[str, Any], scene_plan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    overlay_types = {"hero_title", "section_title", "text_card", "stat_reveal", "caption"}
    _ = scene_plan

    def _add(job_id: str, kind: str, text: str, pointer: tuple | None) -> None:
        if not str(text).strip():
            return
        jobs.append({"id": job_id, "kind": kind, "text": str(text), "pointer": pointer})

    for index, overlay in enumerate(edit_decisions.get("overlays") or []):
        field = "text" if overlay.get("text") else "title"
        _add(
            f"overlay[{index}]",
            _kind_from_type(overlay.get("type")),
            overlay.get(field) or "",
            ("overlays", index, field) if overlay.get(field) else None,
        )
    for index, cut in enumerate(edit_decisions.get("cuts") or []):
        cut_type = cut.get("type")
        if cut_type and cut_type not in overlay_types:
            continue
        field = "text" if cut.get("text") else "title"
        _add(
            f"cuts[{index}]",
            _kind_from_type(cut_type),
            cut.get(field) or "",
            ("cuts", index, field) if cut.get(field) else None,
        )
    for index, overlay in enumerate((edit_decisions.get("metadata") or {}).get("text_overlays") or []):
        _add(
            f"metadata.text_overlays[{index}]",
            _kind_from_type(overlay.get("type")),
            overlay.get("text") or "",
            ("metadata", "text_overlays", index, "text"),
        )
    return jobs


def _set_pointer(root: dict[str, Any], pointer: tuple | None, value: str) -> None:
    if not pointer:
        return
    cursor: Any = root
    for key in pointer[:-1]:
        cursor = cursor[key]
    cursor[pointer[-1]] = value


def run_overlay_preflight(
    edit_decisions: dict[str, Any],
    scene_plan: dict[str, Any] | None = None,
    *,
    canvas: tuple[int, int] = DEFAULT_CANVAS,
) -> dict[str, Any]:
    patched = copy.deepcopy(edit_decisions)
    jobs = collect_jobs(patched, scene_plan)
    results = []
    blocking = []
    for job in jobs:
        layout = repair_layout(job["text"], job["kind"], canvas=canvas)
        item = {
            "id": job["id"],
            "kind": job["kind"],
            "source_text": job["text"],
            "text": layout["text"],
            "lines": layout["lines"],
            "font_size": layout["font_size"],
            "repairs": layout["repairs"],
            "issues": layout["issues"],
            "ok": layout["ok"],
        }
        results.append(item)
        if layout["ok"]:
            _set_pointer(patched, job["pointer"], layout["text"])
            parent = patched
            for key in (job["pointer"] or [])[:-1]:
                parent = parent[key]
            if isinstance(parent, dict):
                parent["text"] = layout["text"]
                parent["font_size"] = layout["font_size"]
                parent["fontSize"] = layout["font_size"]
        else:
            blocking.append(item)
    report = {
        "version": "overlay-preflight/v0.1",
        "ok": not blocking,
        "canvas": {"width": canvas[0], "height": canvas[1]},
        "jobs": results,
        "unresolved": [
            {"id": item["id"], "issues": item["issues"]}
            for item in blocking
        ],
        "patched_edit_decisions": patched,
    }
    public = {key: value for key, value in report.items() if key != "patched_edit_decisions"}
    validate_artifact("overlay_preflight", public)
    report["artifact"] = public
    return report


def format_block_error(report: dict[str, Any]) -> str:
    lines = ["Overlay L0 preflight failed — full render blocked."]
    for item in report.get("unresolved") or []:
        details = "; ".join(
            f"{issue.get('code')}: {issue.get('detail')}"
            for issue in item.get("issues") or []
        )
        lines.append(f"  • {item['id']}: {details}")
    lines.append("Do not call Qwen. Fix wrap/font in overlay_preflight (max 2 automatic repairs).")
    return "\n".join(lines)


def dump_artifact(report: dict[str, Any]) -> dict[str, Any]:
    return report.get("artifact") or {
        key: value for key, value in report.items()
        if key not in {"patched_edit_decisions", "artifact"}
    }


def write_report(path: Any, report: dict[str, Any]) -> None:
    from pathlib import Path

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(dump_artifact(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
