"""Contract tests for the Xiaomi MiMo-V2.5 TTS provider."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from tools.audio.mimo_tts import MiMoTTS
from tools.audio.tts_selector import TTSSelector
from tools.base_tool import ToolStatus
from tools.tool_registry import ToolRegistry


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_status_requires_mimo_key_not_litellm_key(monkeypatch):
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_TTS_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_MASTER_KEY", "wrong-provider")
    assert MiMoTTS().get_status() == ToolStatus.UNAVAILABLE


def test_selector_declares_mimo_as_default():
    preferred = TTSSelector.input_schema["properties"]["preferred_provider"]
    assert preferred["default"] == "mimo"


def test_audio_registry_discovers_mimo(monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "test-only")
    registry = ToolRegistry()
    names = registry.discover("tools.audio")
    assert "mimo_tts" in names
    assert registry.get("mimo_tts").get_status() == ToolStatus.AVAILABLE


def test_default_route_does_not_silently_fall_back_to_minimax(monkeypatch):
    selector = TTSSelector()
    mimo = MiMoTTS()
    minimax = MiMoTTS()
    minimax.name = "minimax_tts"
    minimax.provider = "minimax"
    monkeypatch.setattr(mimo, "get_status", lambda: ToolStatus.UNAVAILABLE)
    monkeypatch.setattr(minimax, "get_status", lambda: ToolStatus.AVAILABLE)
    context = selector._prepare_task_context({"text": "测试"})

    selected, _ = selector._select_best_tool({}, [mimo, minimax], context)
    assert selected is None

    selected, _ = selector._select_best_tool(
        {"preferred_provider": "minimax"}, [mimo, minimax], context
    )
    assert selected is minimax


def test_official_chat_completions_contract(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("MIMO_API_KEY", "test-only")
    monkeypatch.delenv("MIMO_TTS_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_TTS_API_BASE", raising=False)
    monkeypatch.delenv("MIMO_TTS_MODEL", raising=False)
    captured = {}
    wav_bytes = b"RIFF-test-wave"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse(
            {"choices": [{"message": {"audio": {"data": base64.b64encode(wav_bytes).decode()}}}]}
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    output = tmp_path / "sample.wav"
    result = MiMoTTS().execute(
        {
            "text": "这是一段测试旁白。",
            "voice_id": "茉莉",
            "speed": 1.2,
            "output_path": str(output),
        }
    )

    assert result.success is True
    assert output.read_bytes() == wav_bytes
    assert captured["url"] == "https://api.xiaomimimo.com/v1/chat/completions"
    assert captured["body"]["model"] == "mimo-v2.5-tts"
    assert captured["body"]["messages"][1] == {
        "role": "assistant",
        "content": "这是一段测试旁白。",
    }
    assert captured["body"]["audio"] == {"format": "wav", "voice": "茉莉"}
    assert result.data["provider_word_timestamps"] is False
    assert result.data["timing_source_required"] == "post_tts_asr"


def test_rejects_non_wav_without_network(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("MIMO_API_KEY", "test-only")
    result = MiMoTTS().execute(
        {"text": "测试", "format": "mp3", "output_path": str(tmp_path / "bad.mp3")}
    )
    assert result.success is False
    assert "WAV" in result.error
