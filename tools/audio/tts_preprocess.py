"""Preprocess schema-valid script text for TTS engines.

OpenMontage ``tts_selector`` historically passed ``script.sections[].text``
straight to providers. Number expansion, markdown residue, abbreviation
expansion, and locale punctuation were left to agents or external side cars.

This tool is the missing hop:

    script JSON  ->  tts_preprocess  ->  engine-ready strings / files

It is intentionally deterministic and dependency-free so unit tests do not
need network, voices, or API keys.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)

# ---------------------------------------------------------------------------
# Number / abbreviation helpers
# ---------------------------------------------------------------------------

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = [
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
]
_ZH_DIGITS = "零一二三四五六七八九"


def _en_under_1000(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        ten, one = divmod(n, 10)
        return _TENS[ten] if one == 0 else f"{_TENS[ten]}-{_ONES[one]}"
    hun, rest = divmod(n, 100)
    if rest == 0:
        return f"{_ONES[hun]} hundred"
    return f"{_ONES[hun]} hundred {_en_under_1000(rest)}"


def number_to_english(n: int) -> str:
    if n < 0:
        return f"minus {number_to_english(-n)}"
    if n < 1000:
        return _en_under_1000(n)
    if n < 1_000_000:
        thou, rest = divmod(n, 1000)
        head = _en_under_1000(thou) + " thousand"
        return head if rest == 0 else f"{head} {number_to_english(rest)}"
    if n < 1_000_000_000:
        mil, rest = divmod(n, 1_000_000)
        head = number_to_english(mil) + " million"
        return head if rest == 0 else f"{head} {number_to_english(rest)}"
    bil, rest = divmod(n, 1_000_000_000)
    head = number_to_english(bil) + " billion"
    return head if rest == 0 else f"{head} {number_to_english(rest)}"


def number_to_chinese(n: int) -> str:
    """Simple integer reader for narration (not full financial form)."""
    if n < 0:
        return "负" + number_to_chinese(-n)
    if n < 10:
        return _ZH_DIGITS[n]
    if n < 20:
        return "十" if n == 10 else "十" + _ZH_DIGITS[n % 10]
    if n < 100:
        ten, one = divmod(n, 10)
        return _ZH_DIGITS[ten] + "十" + (_ZH_DIGITS[one] if one else "")
    if n < 1000:
        hun, rest = divmod(n, 100)
        head = _ZH_DIGITS[hun] + "百"
        if rest == 0:
            return head
        if rest < 10:
            return head + "零" + _ZH_DIGITS[rest]
        return head + number_to_chinese(rest)
    if n < 10000:
        thou, rest = divmod(n, 1000)
        head = _ZH_DIGITS[thou] + "千"
        if rest == 0:
            return head
        if rest < 100:
            return head + "零" + number_to_chinese(rest)
        return head + number_to_chinese(rest)
    if n < 100_000_000:
        wan, rest = divmod(n, 10000)
        head = number_to_chinese(wan) + "万"
        if rest == 0:
            return head
        if rest < 1000:
            return head + "零" + number_to_chinese(rest)
        return head + number_to_chinese(rest)
    yi, rest = divmod(n, 100_000_000)
    head = number_to_chinese(yi) + "亿"
    if rest == 0:
        return head
    if rest < 10_000_000:
        return head + "零" + number_to_chinese(rest)
    return head + number_to_chinese(rest)


_EN_ABBREV = {
    r"\bU\.S\.": "United States",
    r"\bU\.K\.": "United Kingdom",
    r"\bEIC\b": "East India Company",
    r"\bMP\b": "Member of Parliament",
    r"\bHMS\b": "H M S",
    r"\bvs\.\b": "versus",
    r"\bVS\b": "versus",
    r"\betc\.\b": "et cetera",
}

_MD_RESIDUE = re.compile(r"[#*_>`]+")
_PAUSE_TAG = re.compile(r"\[(?:pause|停顿|slow|formal|放慢|保留力度|weighted)[^\]]*\]", re.I)


def strip_markdown_residue(text: str) -> str:
    text = text.replace("**", "").replace("__", "").replace("``", "")
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = _MD_RESIDUE.sub("", text)
    return text


def expand_abbreviations_en(text: str) -> str:
    for pat, rep in _EN_ABBREV.items():
        text = re.sub(pat, rep, text)
    return text


def expand_numbers_en(text: str) -> str:
    # currency $26 million / $1M
    def money(m: re.Match) -> str:
        num = m.group(1).replace(",", "")
        unit = (m.group(2) or "").lower()
        try:
            if "." in num:
                whole, frac = num.split(".", 1)
                spoken = number_to_english(int(whole)) + " point " + " ".join(
                    _ONES[int(d)] for d in frac if d.isdigit()
                )
            else:
                spoken = number_to_english(int(num))
        except ValueError:
            return m.group(0)
        if unit.startswith("m"):
            spoken += " million"
        elif unit.startswith("b"):
            spoken += " billion"
        elif unit.startswith("k"):
            spoken += " thousand"
        return spoken + " dollars"

    text = re.sub(
        r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([MmBbKk])?(?:illion)?",
        money,
        text,
    )

    # percentages 7.5% / 3.6%
    def pct(m: re.Match) -> str:
        num = m.group(1).replace(",", "")
        try:
            if "." in num:
                whole, frac = num.split(".", 1)
                spoken = number_to_english(int(whole)) + " point " + " ".join(
                    _ONES[int(d)] for d in frac if d.isdigit()
                )
            else:
                spoken = number_to_english(int(num))
        except ValueError:
            return m.group(0)
        return spoken + " percent"

    text = re.sub(r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\s*%", pct, text)

    # plain integers with optional commas (avoid years? expand years too for TTS clarity)
    def plain_int(m: re.Match) -> str:
        raw = m.group(0).replace(",", "")
        try:
            return number_to_english(int(raw))
        except ValueError:
            return m.group(0)

    text = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", plain_int, text)
    text = re.sub(r"\b\d+\b", plain_int, text)
    return text


def expand_numbers_zh(text: str) -> str:
    def pct(m: re.Match) -> str:
        num = m.group(1)
        try:
            if "." in num:
                whole, frac = num.split(".", 1)
                spoken = number_to_chinese(int(whole)) + "点" + "".join(
                    _ZH_DIGITS[int(d)] for d in frac if d.isdigit()
                )
            else:
                spoken = number_to_chinese(int(num))
        except ValueError:
            return m.group(0)
        return spoken + "个百分点"

    text = re.sub(r"([0-9]+(?:\.[0-9]+)?)\s*%", pct, text)
    text = re.sub(r"([0-9]+(?:\.[0-9]+)?)\s*％", pct, text)

    def money_usd(m: re.Match) -> str:
        num = m.group(1).replace(",", "")
        try:
            n = int(float(num)) if "." in num else int(num)
            return number_to_chinese(n) + "美元"
        except ValueError:
            return m.group(0)

    text = re.sub(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)", money_usd, text)

    def plain(m: re.Match) -> str:
        raw = m.group(0).replace(",", "")
        try:
            if "." in raw:
                whole, frac = raw.split(".", 1)
                return number_to_chinese(int(whole)) + "点" + "".join(
                    _ZH_DIGITS[int(d)] for d in frac if d.isdigit()
                )
            return number_to_chinese(int(raw))
        except ValueError:
            return m.group(0)

    text = re.sub(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", plain, text)
    text = re.sub(r"\d+(?:\.\d+)?", plain, text)
    return text


def locale_punct_zh(text: str) -> str:
    # em dash / long dash often poorly spoken — soften to comma
    text = text.replace("——", "，").replace("—", "，").replace("--", "，")
    return text


def directions_to_pause_tag(directions: str | None, locale: str) -> str | None:
    if not directions:
        return None
    d = directions.lower()
    seconds = None
    m = re.search(r"pause[_\s-]*after[_\s-]*seconds[\"'=\s:]*([0-9.]+)", d)
    if m:
        seconds = m.group(1)
    m2 = re.search(r"([0-9.]+)\s*s(ec|econds)?", d)
    if seconds is None and m2:
        seconds = m2.group(1)
    if seconds is None and ("pause" in d or "停顿" in directions):
        seconds = "1"
    if seconds is None:
        return None
    if locale.startswith("zh"):
        return f"[停顿 {seconds}秒]"
    return f"[pause {seconds}s]"


def preprocess_text(
    text: str,
    *,
    locale: str = "en",
    expand_numbers: bool = True,
    expand_abbreviations: bool = True,
    strip_markdown: bool = True,
    locale_rules: bool = True,
    strip_existing_pause_tags: bool = False,
) -> str:
    out = text or ""
    if strip_existing_pause_tags:
        out = _PAUSE_TAG.sub("", out)
    if strip_markdown:
        out = strip_markdown_residue(out)
    if expand_abbreviations and locale.startswith("en"):
        out = expand_abbreviations_en(out)
    if expand_numbers:
        out = expand_numbers_zh(out) if locale.startswith("zh") else expand_numbers_en(out)
    if locale_rules and locale.startswith("zh"):
        out = locale_punct_zh(out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def preprocess_script_artifact(
    script: dict[str, Any],
    *,
    locale: str = "en",
    expand_numbers: bool = True,
    expand_abbreviations: bool = True,
    strip_markdown: bool = True,
    locale_rules: bool = True,
    include_pause_tags: bool = True,
) -> dict[str, Any]:
    """Return a parallel structure with engine-ready section texts."""
    sections_out: list[dict[str, Any]] = []
    for sec in script.get("sections") or []:
        raw = sec.get("text") or ""
        cleaned = preprocess_text(
            raw,
            locale=locale,
            expand_numbers=expand_numbers,
            expand_abbreviations=expand_abbreviations,
            strip_markdown=strip_markdown,
            locale_rules=locale_rules,
        )
        pause = None
        if include_pause_tags:
            pause = directions_to_pause_tag(sec.get("speaker_directions"), locale)
        engine_text = cleaned if not pause else f"{cleaned}\n\n{pause}"
        sections_out.append(
            {
                "id": sec.get("id"),
                "label": sec.get("label"),
                "text": engine_text,
                "source_text": raw,
                "start_seconds": sec.get("start_seconds"),
                "end_seconds": sec.get("end_seconds"),
                "pronunciation_guides": sec.get("pronunciation_guides") or [],
            }
        )
    merged_parts = []
    for s in sections_out:
        label = s.get("label") or s.get("id") or "section"
        header = f"SECTION: {label}" if locale.startswith("en") else f"段落: {label}"
        merged_parts.append(f"{header}\n\n{s['text']}")
    return {
        "version": "1.0",
        "locale": locale,
        "title": script.get("title"),
        "total_duration_seconds": script.get("total_duration_seconds"),
        "sections": sections_out,
        "merged_text": "\n\n".join(merged_parts).strip() + "\n",
    }


class TTSPreprocess(BaseTool):
    name = "tts_preprocess"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts_preprocess"
    provider = "openmontage"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies: list[str] = []
    install_instructions = "Bundled with OpenMontage; no external deps."
    agent_skills = ["text-to-speech"]

    capabilities = [
        "number_expansion",
        "abbreviation_expansion",
        "markdown_strip",
        "locale_punctuation",
        "script_to_tts_text",
    ]
    supports = {
        "offline": True,
        "multilingual": True,
        "deterministic": True,
    }
    best_for = [
        "script JSON → engine-ready narration before tts_selector",
        "dual-language longform explainers (en/zh)",
        "reproducible TTS side cars without ad-hoc agent transforms",
    ]
    not_good_for = [
        "prosody cloning",
        "emotion transfer",
    ]

    input_schema = {
        "type": "object",
        "properties": {
            "script": {
                "type": "object",
                "description": "Schema-valid OpenMontage script artifact",
            },
            "script_path": {
                "type": "string",
                "description": "Path to script JSON (alternative to inline script)",
            },
            "text": {
                "type": "string",
                "description": "Raw text mode (when not processing a full script)",
            },
            "locale": {
                "type": "string",
                "default": "en",
                "description": "en | zh (and variants like zh-CN)",
            },
            "expand_numbers": {"type": "boolean", "default": True},
            "expand_abbreviations": {"type": "boolean", "default": True},
            "strip_markdown": {"type": "boolean", "default": True},
            "locale_rules": {"type": "boolean", "default": True},
            "include_pause_tags": {"type": "boolean", "default": True},
            "output_path": {
                "type": "string",
                "description": "Optional path for merged TTS-ready .txt",
            },
            "output_json_path": {
                "type": "string",
                "description": "Optional path for structured preprocess result JSON",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=5, network_required=False
    )
    side_effects = ["may write output_path / output_json_path"]
    user_visible_verification = [
        "Spot-check expanded numbers and proper nouns before sending to TTS",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        locale = (inputs.get("locale") or "en").lower()
        expand_numbers = inputs.get("expand_numbers", True)
        expand_abbreviations = inputs.get("expand_abbreviations", True)
        strip_markdown = inputs.get("strip_markdown", True)
        locale_rules = inputs.get("locale_rules", True)
        include_pause_tags = inputs.get("include_pause_tags", True)

        script = inputs.get("script")
        script_path = inputs.get("script_path")
        if script is None and script_path:
            script = json.loads(Path(script_path).read_text(encoding="utf-8"))

        artifacts: list[str] = []
        try:
            if script is not None:
                result = preprocess_script_artifact(
                    script,
                    locale=locale,
                    expand_numbers=expand_numbers,
                    expand_abbreviations=expand_abbreviations,
                    strip_markdown=strip_markdown,
                    locale_rules=locale_rules,
                    include_pause_tags=include_pause_tags,
                )
                merged = result["merged_text"]
            else:
                text = inputs.get("text")
                if not text:
                    return ToolResult(
                        success=False,
                        error="Provide script, script_path, or text",
                    )
                cleaned = preprocess_text(
                    text,
                    locale=locale,
                    expand_numbers=expand_numbers,
                    expand_abbreviations=expand_abbreviations,
                    strip_markdown=strip_markdown,
                    locale_rules=locale_rules,
                )
                result = {
                    "version": "1.0",
                    "locale": locale,
                    "sections": [{"id": "text", "text": cleaned}],
                    "merged_text": cleaned + "\n",
                }
                merged = result["merged_text"]

            out_path = inputs.get("output_path")
            if out_path:
                p = Path(out_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(merged, encoding="utf-8")
                artifacts.append(str(p))

            json_path = inputs.get("output_json_path")
            if json_path:
                jp = Path(json_path)
                jp.parent.mkdir(parents=True, exist_ok=True)
                jp.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                artifacts.append(str(jp))

            return ToolResult(
                success=True,
                data={
                    "locale": locale,
                    "section_count": len(result.get("sections") or []),
                    "merged_text": merged,
                    "sections": result.get("sections"),
                    "char_count": len(merged),
                },
                artifacts=artifacts,
                cost_usd=0.0,
            )
        except Exception as exc:  # noqa: BLE001 — surface as tool error
            return ToolResult(success=False, error=f"{type(exc).__name__}: {exc}")
