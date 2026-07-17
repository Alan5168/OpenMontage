"""MiniMax Speech text-to-speech provider tool (Token Plan / t2a_v2).

Primary path for OpenMontage narration under an active MiniMax Token Plan.
Uses the domestic API host by default (api.minimaxi.com).

Configuration (prefer ~/.codex/skills.env, then OpenMontage .env):
  MINIMAX_API_KEY     — Token Plan subscription key (sk-cp-...)
  MINIMAX_API_HOST    — default https://api.minimaxi.com
  MINIMAX_TTS_MODEL   — default speech-2.8-hd
  MINIMAX_TTS_VOICE   — default AlanBilibiliNarrator02 (channel clone; override if needed)

API: POST {host}/v1/t2a_v2  (sync, up to ~10k chars)
CLI equivalent: mmx speech synthesize --text "..." --out out.mp3
Docs: https://platform.minimaxi.com/docs/api-reference/speech-t2a-http
"""

from __future__ import annotations

import json
import os
import time
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


class MiniMaxTTS(BaseTool):
    name = "minimax_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "minimax"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set MINIMAX_API_KEY (Token Plan subscription key) in ~/.codex/skills.env "
        "or OpenMontage .env.\n"
        "Optional: MINIMAX_API_HOST, MINIMAX_TTS_MODEL, MINIMAX_TTS_VOICE.\n"
        "CLI smoke: mmx speech synthesize --text '你好' --out /tmp/mmx.mp3\n"
        "API: POST https://api.minimaxi.com/v1/t2a_v2"
    )
    fallback = "doubao_tts"
    fallback_tools = ["doubao_tts", "google_tts", "piper_tts"]
    agent_skills = ["minimax-tts", "text-to-speech", "chinese-tts"]

    capabilities = [
        "text_to_speech",
        "voice_selection",
        "multilingual",
        "emotion_control",
    ]
    supports = {
        "voice_cloning": True,  # via separate voice-clone API + voice_id
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "timestamps": True,  # subtitle_enable on API
    }
    best_for = [
        "Alan channel Bilibili long-form narration (AlanBilibiliNarrator02)",
        "Chinese explainer / short-form on MiniMax Token Plan",
        "high-quality Mandarin TTS without ElevenLabs spend",
    ]
    not_good_for = [
        "fully offline production",
        "when MiniMax Token Plan quota is exhausted",
    ]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string", "description": "Text to convert to speech (max ~10k chars sync)"},
            "voice_id": {
                "type": "string",
                "description": (
                    "MiniMax system or cloned voice_id. "
                    "Defaults to MINIMAX_TTS_VOICE / AlanBilibiliNarrator02 (channel primary)."
                ),
            },
            "model": {
                "type": "string",
                "default": "speech-2.8-hd",
                "description": "speech-2.8-hd | speech-2.6-hd | speech-02-hd | speech-02-turbo, etc.",
            },
            "format": {
                "type": "string",
                "default": "mp3",
                "enum": ["mp3", "pcm", "flac", "wav"],
            },
            "sample_rate": {
                "type": "integer",
                "default": 32000,
                "enum": [8000, 16000, 22050, 24000, 32000, 44100],
            },
            "bitrate": {
                "type": "integer",
                "default": 128000,
            },
            "speed": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
                "description": "Speech speed multiplier.",
            },
            "vol": {
                "type": "number",
                "default": 1.0,
                "description": "Volume multiplier.",
            },
            "pitch": {
                "type": "integer",
                "default": 0,
                "description": "Pitch adjustment.",
            },
            "emotion": {
                "type": "string",
                "description": "Optional emotion tag (e.g. happy, sad) when supported by voice/model.",
            },
            "language_boost": {
                "type": "string",
                "description": "Optional language boost code (e.g. Chinese, English).",
            },
            "subtitle_enable": {
                "type": "boolean",
                "default": False,
                "description": "Request subtitle timing data when available.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=20, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=2.0,
        retryable_errors=["timeout", "rate_limit", "502", "503", "429"],
    )
    idempotency_key_fields = ["text", "voice_id", "model", "speed", "format"]
    side_effects = ["writes audio file to output_path", "calls MiniMax t2a_v2 API"]
    user_visible_verification = ["Listen to generated audio for naturalness and pacing"]
    quality_score = 0.90
    latency_p50_seconds = 4.0

    DEFAULT_HOST = "https://api.minimaxi.com"
    DEFAULT_MODEL = "speech-2.8-hd"
    # Channel default: Alan MiniMax clone for Bilibili long-form (2026-07-15).
    # Override via MINIMAX_TTS_VOICE or per-call voice_id.
    DEFAULT_VOICE = "AlanBilibiliNarrator02"

    def _api_key(self) -> str | None:
        return (
            os.environ.get("MINIMAX_API_KEY")
            or os.environ.get("MINIMAX_GROUP_API_KEY")
            or os.environ.get("MINIMAX_TTS_API_KEY")
        )

    def _host(self) -> str:
        return (
            os.environ.get("MINIMAX_API_HOST")
            or os.environ.get("MINIMAX_BASE_URL")
            or self.DEFAULT_HOST
        ).rstrip("/")

    def get_status(self) -> ToolStatus:
        if self._api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # Token Plan billed against subscription quota, not USD per call.
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._api_key():
            return ToolResult(success=False, error="No MiniMax API key. " + self.install_instructions)

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"MiniMax TTS failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        import urllib.error
        import urllib.request

        text = inputs["text"]
        model = inputs.get("model") or os.environ.get("MINIMAX_TTS_MODEL") or self.DEFAULT_MODEL
        voice_id = (
            inputs.get("voice_id")
            or os.environ.get("MINIMAX_TTS_VOICE")
            or self.DEFAULT_VOICE
        )
        fmt = inputs.get("format", "mp3")
        sample_rate = int(inputs.get("sample_rate", 32000))
        bitrate = int(inputs.get("bitrate", 128000))
        speed = float(inputs.get("speed", 1.0))
        vol = float(inputs.get("vol", 1.0))
        pitch = int(inputs.get("pitch", 0))
        output_path = Path(inputs.get("output_path", f"minimax_tts.{fmt}"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_setting: dict[str, Any] = {
            "voice_id": voice_id,
            "speed": speed,
            "vol": vol,
            "pitch": pitch,
        }
        if inputs.get("emotion"):
            voice_setting["emotion"] = inputs["emotion"]

        body: dict[str, Any] = {
            "model": model,
            "text": text,
            "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": sample_rate,
                "bitrate": bitrate,
                "format": fmt,
                "channel": 1,
            },
            "subtitle_enable": bool(inputs.get("subtitle_enable", False)),
        }
        if inputs.get("language_boost"):
            body["language_boost"] = inputs["language_boost"]

        url = f"{self._host()}/v1/t2a_v2"
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"HTTP {e.code}: {err_body}") from e

        base = payload.get("base_resp") or {}
        if base.get("status_code", 0) not in (0, None):
            raise RuntimeError(
                f"MiniMax base_resp {base.get('status_code')}: {base.get('status_msg')}"
            )

        data = payload.get("data") or {}
        audio_hex = data.get("audio")
        if not audio_hex:
            raise RuntimeError(f"No audio in response: keys={list(payload.keys())}")

        audio_bytes = bytes.fromhex(audio_hex)
        output_path.write_bytes(audio_bytes)

        extra = payload.get("extra_info") or {}
        audio_length_ms = extra.get("audio_length")
        duration_s = (audio_length_ms / 1000.0) if isinstance(audio_length_ms, (int, float)) else None

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": model,
                "voice_id": voice_id,
                "format": fmt,
                "speed": speed,
                "text_length": len(text),
                "audio_duration_seconds": round(duration_s, 2) if duration_s is not None else None,
                "audio_size_bytes": len(audio_bytes),
                "usage_characters": extra.get("usage_characters"),
                "trace_id": payload.get("trace_id"),
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            model=model,
        )
