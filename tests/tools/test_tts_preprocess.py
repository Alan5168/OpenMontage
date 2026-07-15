"""Unit tests for tools/audio/tts_preprocess.py — offline, no API keys."""

from __future__ import annotations

import json
from pathlib import Path

from tools.audio.tts_preprocess import (
    TTSPreprocess,
    expand_abbreviations_en,
    number_to_chinese,
    number_to_english,
    preprocess_script_artifact,
    preprocess_text,
)


def test_number_to_english_basics():
    assert number_to_english(0) == "zero"
    assert number_to_english(26) == "twenty-six"
    assert "thousand" in number_to_english(280000)
    assert "million" in number_to_english(3_500_000)


def test_number_to_chinese_basics():
    assert number_to_chinese(0) == "零"
    assert number_to_chinese(10) == "十"
    assert number_to_chinese(26) == "二十六"
    assert number_to_chinese(100) == "一百"
    assert "万" in number_to_chinese(10_000)
    assert number_to_chinese(20) == "二十"


def test_expand_abbreviations_en():
    text = expand_abbreviations_en("The EIC met U.S. traders.")
    assert "East India Company" in text
    assert "United States" in text
    assert "EIC" not in text


def test_preprocess_text_en_numbers_and_markdown():
    raw = "Opium was about **7.5%** of revenue; the *Royal Saxon* carried $26 million."
    out = preprocess_text(raw, locale="en")
    assert "*" not in out
    assert "%" not in out
    assert "$" not in out
    assert "percent" in out
    assert "dollars" in out
    assert "Royal Saxon" in out


def test_preprocess_text_zh_dash_and_numbers():
    raw = "鸦片约占**7.5%**——白银流向反转。"
    out = preprocess_text(raw, locale="zh")
    assert "*" not in out
    assert "——" not in out
    assert "，" in out
    assert "个百分点" in out


def test_preprocess_script_artifact_sections(tmp_path: Path):
    script = {
        "version": "1.0",
        "title": "Test",
        "total_duration_seconds": 12,
        "sections": [
            {
                "id": "s1",
                "label": "COLD OPEN",
                "text": "In 1839 the EIC spent $1 million.",
                "start_seconds": 0,
                "end_seconds": 12,
                "speaker_directions": "pause after 1.5s",
            }
        ],
    }
    result = preprocess_script_artifact(script, locale="en")
    assert result["sections"][0]["text"]
    assert "East India Company" in result["sections"][0]["text"]
    assert "million" in result["sections"][0]["text"]
    assert "SECTION: COLD OPEN" in result["merged_text"]
    assert "[pause" in result["sections"][0]["text"].lower() or "[pause" in result["merged_text"].lower()


def test_tool_execute_text_mode(tmp_path: Path):
    tool = TTSPreprocess()
    out_txt = tmp_path / "out.txt"
    out_json = tmp_path / "out.json"
    result = tool.execute(
        {
            "text": "HMS *Volage* fired in 1839.",
            "locale": "en",
            "output_path": str(out_txt),
            "output_json_path": str(out_json),
        }
    )
    assert result.success, result.error
    assert out_txt.exists()
    body = out_txt.read_text(encoding="utf-8")
    assert "Volage" in body
    assert "eighteen thirty-nine" in body or "one thousand eight hundred" in body
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["locale"] == "en"


def test_tool_execute_script_path(tmp_path: Path):
    script = {
        "version": "1.0",
        "title": "Path Test",
        "total_duration_seconds": 5,
        "sections": [
            {
                "id": "a",
                "label": "A",
                "text": "About 40,000 chests by 1839.",
                "start_seconds": 0,
                "end_seconds": 5,
            }
        ],
    }
    sp = tmp_path / "script.json"
    sp.write_text(json.dumps(script), encoding="utf-8")
    tool = TTSPreprocess()
    result = tool.execute({"script_path": str(sp), "locale": "en"})
    assert result.success, result.error
    merged = result.data["merged_text"]
    assert "forty thousand" in merged or "thousand" in merged
