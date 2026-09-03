"""Xiaomi MiMo-V2.5 text-to-speech provider.

Official API contract:
  POST https://api.xiaomimimo.com/v1/chat/completions
  model=mimo-v2.5-tts
  user message=performance direction; assistant message=text to synthesize
  audio.data=base64-encoded audio

Configuration:
  MIMO_API_KEY       — canonical Xiaomi MiMo platform key
  MIMO_TTS_API_KEY   — backwards-compatible alias
  MIMO_TTS_API_BASE  — default https://api.xiaomimimo.com/v1
  MIMO_TTS_MODEL     — default mimo-v2.5-tts
  MIMO_TTS_VOICE     — default mimo_default
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class MiMoTTS(BaseTool):
    name = "mimo_tts"
    version = "0.2.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "mimo"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set MIMO_API_KEY in the machine-local secret store. "
        "Optional: MIMO_TTS_API_BASE, MIMO_TTS_MODEL, MIMO_TTS_VOICE."
    )
    fallback = "doubao_tts"
    fallback_tools = ["doubao_tts", "piper_tts"]
    agent_skills = ["text-to-speech"]

    capabilities = ["text_to_speech", "multilingual", "style_direction"]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "style_direction": True,
        "provider_word_timestamps": False,
    }
    best_for = [
        "Chinese narration under an active MiMo Token Plan",
        "instruction-controlled delivery and emotion",
        "built-in Mandarin voices",
    ]
    not_good_for = [
        "offline production",
        "provider-native word timestamps",
        "persistent cloned voice IDs",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string", "description": "Text to synthesize"},
            "voice_id": {
                "type": "string",
                "description": (
                    "MiMo built-in voice ID. Chinese choices include 冰糖, 茉莉, 苏打, 白桦; "
                    "defaults to MIMO_TTS_VOICE / mimo_default."
                ),
            },
            "model": {"type": "string"},
            "model_id": {"type": "string"},
            "format": {"type": "string", "default": "wav", "enum": ["wav"]},
            "output_format": {"type": "string"},
            "speed": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
                "description": "Converted into a natural-language performance instruction.",
            },
            "style_instruction": {
                "type": "string",
                "description": "Natural-language performance direction for the user message.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=10, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=2.0,
        retryable_errors=["timeout", "rate_limit", "502", "503"],
    )
    idempotency_key_fields = ["text", "voice_id", "model", "speed", "style_instruction"]
    side_effects = ["writes audio file to output_path", "calls Xiaomi MiMo API"]
    user_visible_verification = [
        "Listen for pronunciation, pacing, and artifacts",
        "Run post-TTS ASR alignment because MiMo does not return word timestamps",
    ]
    quality_score = 0.85
    latency_p50_seconds = 5.0

    DEFAULT_BASE = "https://api.xiaomimimo.com/v1"
    DEFAULT_MODEL = "mimo-v2.5-tts"
    DEFAULT_VOICE = "mimo_default"

    def _api_key(self) -> str:
        api_key = os.environ.get("MIMO_API_KEY") or os.environ.get("MIMO_TTS_API_KEY")
        if not api_key:
            raise RuntimeError("MIMO_API_KEY is not configured")
        return api_key

    def _api_base(self) -> str:
        return os.environ.get("MIMO_TTS_API_BASE", self.DEFAULT_BASE).rstrip("/")

    def _model(self, inputs: dict[str, Any]) -> str:
        return (
            inputs.get("model")
            or inputs.get("model_id")
            or os.environ.get("MIMO_TTS_MODEL")
            or self.DEFAULT_MODEL
        )

    def _voice(self, inputs: dict[str, Any]) -> str:
        return inputs.get("voice_id") or os.environ.get("MIMO_TTS_VOICE") or self.DEFAULT_VOICE

    def get_status(self) -> ToolStatus:
        return (
            ToolStatus.AVAILABLE
            if os.environ.get("MIMO_API_KEY") or os.environ.get("MIMO_TTS_API_KEY")
            else ToolStatus.UNAVAILABLE
        )

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    @staticmethod
    def _style_instruction(inputs: dict[str, Any]) -> str:
        explicit = str(inputs.get("style_instruction") or "").strip()
        if explicit:
            return explicit
        speed = float(inputs.get("speed", 1.0))
        if speed >= 1.15:
            pace = "语速稍快，但吐字清晰，不吞数字和英文缩写。"
        elif speed <= 0.9:
            pace = "语速稍慢，停顿自然，重点词清晰。"
        else:
            pace = "语速自然，停顿克制，吐字清晰。"
        return f"专业、可信的中文解说口吻。{pace}"

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="MiMo TTS unavailable. " + self.install_instructions)
        start = time.time()
        try:
            return self._generate(inputs, start)
        except Exception as exc:
            return ToolResult(success=False, error=f"MiMo TTS failed: {exc}")

    def _generate(self, inputs: dict[str, Any], start: float) -> ToolResult:
        text = str(inputs["text"]).strip()
        if not text:
            raise ValueError("text must not be empty")

        requested_format = str(inputs.get("format") or inputs.get("output_format") or "wav").lower()
        if requested_format not in {"wav", "wav_24000"}:
            raise ValueError("MiMo non-streaming TTS currently supports WAV output in OpenMontage")
        fmt = "wav"
        model = self._model(inputs)
        voice = self._voice(inputs)
        output_path = Path(inputs.get("output_path") or "mimo_tts.wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        body = {
            "model": model,
            "messages": [
                {"role": "user", "content": self._style_instruction(inputs)},
                {"role": "assistant", "content": text},
            ],
            "audio": {"format": fmt, "voice": voice},
        }
        api_key = self._api_key()
        request = urllib.request.Request(
            f"{self._api_base()}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "api-key": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"API error {exc.code}: {detail}") from exc

        try:
            encoded_audio = payload["choices"][0]["message"]["audio"]["data"]
            audio_data = base64.b64decode(encoded_audio, validate=True)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("response did not contain valid choices[0].message.audio.data") from exc
        if not audio_data:
            raise RuntimeError("response contained empty audio data")

        output_path.write_bytes(audio_data)
        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": model,
                "voice": voice,
                "format": fmt,
                "text_length": len(text),
                "output": str(output_path),
                "audio_size_bytes": len(audio_data),
                "provider_word_timestamps": False,
                "timing_source_required": "post_tts_asr",
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
