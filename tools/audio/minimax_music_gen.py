"""MiniMax Music generation tool (Token Plan, music_generation API).

Primary path for OpenMontage background music under an active MiniMax Token Plan.
Uses the domestic API host by default (api.minimaxi.com) and the
`music-2.6-free` model (unlimited for Token Plan key holders, RPM=3 per mmx-cli skill).

Configuration (prefer ~/.codex/skills.env, then OpenMontage .env):
  MINIMAX_API_KEY     — Token Plan subscription key (sk-cp-...)
  MINIMAX_API_HOST    — default https://api.minimaxi.com
  Optional:
    DOUBAO_SEEDREAM_MODEL — only used by image tools, ignored here.

CLI equivalent (verified working 2026-07-19 per
knowledge/memory-md/nf_ep1_mmx_ident_round2_20260719.md):
  mmx music generate --prompt "..." [--instrumental] --out bgm.mp3 --quiet

API: POST {host}/v1/music_generation  (sync, returns hex-encoded audio)
Docs: https://platform.minimaxi.com/docs/api-reference/music-generation
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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


class MiniMaxMusicGen(BaseTool):
    name = "minimax_music_gen"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "music_generation"
    provider = "minimax"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []  # checked dynamically: API key OR mmx CLI
    fallback = "music_gen"  # falls back to ElevenLabs if MiniMax unavailable
    fallback_tools = ["music_gen", "suno_music", "google_music"]
    agent_skills = ["music", "minimax-tts"]

    capabilities = [
        "generate_background_music",
        "generate_instrumental",
    ]
    supports = {
        "instrumental": True,
        "lyrics": True,
        "lyrics_optimizer": True,
        "bpm_control": True,
        "vocal_style": True,
        "multilingual": True,
    }
    best_for = [
        "free/cheap background music on MiniMax Token Plan (music-2.6-free, RPM=3)",
        "instrumental BGM for explainer / cinematic / short-video work",
        "music with structured lyrics (verse/chorus/bridge tags)",
    ]
    not_good_for = [
        "production environments needing > 3 RPM (rate limit is hard)",
        "low-latency interactive audio",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Music style description. Supports detailed multi-aspect prompts: "
                    "genre, mood, instruments, BPM, key, structure, vocal style, "
                    "use case. Mirrors mmx-cli's rich prompt model."
                ),
            },
            "lyrics": {
                "type": "string",
                "description": "Song lyrics with structure tags. Required unless instrumental/lyrics_optimizer.",
            },
            "lyrics_optimizer": {
                "type": "boolean",
                "default": False,
                "description": "Auto-generate lyrics from prompt. Cannot combine with lyrics/instrumental.",
            },
            "instrumental": {
                "type": "boolean",
                "default": False,
                "description": "Generate instrumental-only music (no vocals).",
            },
            "vocals": {
                "type": "string",
                "description": "Vocal style, e.g. 'warm male baritone', 'bright female soprano'.",
            },
            "genre": {"type": "string"},
            "mood": {"type": "string"},
            "instruments": {"type": "string"},
            "tempo": {"type": "string", "description": "Tempo description (fast/slow/moderate)."},
            "bpm": {"type": "integer", "minimum": 30, "maximum": 240},
            "key": {"type": "string"},
            "avoid": {"type": "string", "description": "Elements to avoid in generated music."},
            "use_case": {
                "type": "string",
                "description": "Use case context, e.g. 'background music for video narration'.",
            },
            "structure": {
                "type": "string",
                "description": "Song structure, e.g. 'verse-chorus-verse-bridge-chorus'.",
            },
            "references": {"type": "string", "description": "Reference tracks or artists."},
            "format": {
                "type": "string",
                "default": "mp3",
                "enum": ["mp3", "wav", "pcm"],
            },
            "sample_rate": {"type": "integer", "default": 44100},
            "bitrate": {"type": "integer", "default": 256000},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=2.0,
        retryable_errors=["timeout", "rate_limit", "502", "503", "429"],
    )
    idempotency_key_fields = ["prompt", "lyrics", "instrumental", "bpm"]
    side_effects = ["writes audio file to output_path", "calls MiniMax music_generation API"]
    user_visible_verification = ["Listen to generated music for mood, BPM, and length match."]
    quality_score = 0.88
    latency_p50_seconds = 30.0  # music generation is slower than TTS

    DEFAULT_HOST = "https://api.minimaxi.com"
    DEFAULT_MODEL = "music-2.6-free"

    def _api_key(self) -> str | None:
        return (
            os.environ.get("MINIMAX_API_KEY")
            or os.environ.get("MINIMAX_GROUP_API_KEY")
        )

    def _host(self) -> str:
        return (
            os.environ.get("MINIMAX_API_HOST")
            or os.environ.get("MINIMAX_BASE_URL")
            or self.DEFAULT_HOST
        ).rstrip("/")

    def _has_mmx_cli(self) -> bool:
        return shutil.which("mmx") is not None

    def get_status(self) -> ToolStatus:
        # Available if either direct API key OR mmx CLI is present
        if self._api_key() or self._has_mmx_cli():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # Token Plan: music-2.6-free is unlimited for key holders (no per-call USD).
        return 0.0

    def install_instructions(self) -> str:
        return (
            "Set MINIMAX_API_KEY (Token Plan subscription key) in ~/.codex/skills.env "
            "or OpenMontage .env.\n"
            "Optional: MINIMAX_API_HOST (default https://api.minimaxi.com).\n"
            "Fallback: install mmx CLI via `npm install -g mmx-cli` and run "
            "`mmx auth login --api-key <key>`.\n"
            "CLI smoke: mmx music generate --prompt 'cinematic ambient, 90 BPM, hopeful strings' "
            "--instrumental --out /tmp/test.mp3 --quiet\n"
            f"Direct API: POST {self.DEFAULT_HOST}/v1/music_generation"
        )

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"MiniMax music generation failed: {exc}",
                install_instructions=self.install_instructions(),
            )

        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        prompt = inputs["prompt"]
        output_path = Path(inputs.get("output_path", "minimax_music.mp3"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prefer mmx CLI when available (verified working per 2026-07-19 memory)
        if self._has_mmx_cli():
            return self._generate_via_cli(inputs, prompt, output_path)

        # Fallback: direct API call
        if self._api_key():
            return self._generate_via_api(inputs, prompt, output_path)

        return ToolResult(
            success=False,
            error="No MiniMax credentials. Need either MINIMAX_API_KEY in env OR `mmx` CLI on PATH.",
            install_instructions=self.install_instructions(),
        )

    def _build_cli_command(self, inputs: dict[str, Any], output_path: Path) -> list[str]:
        cmd = [
            "mmx",
            "music",
            "generate",
            "--prompt",
            inputs["prompt"],
            "--out",
            str(output_path),
            "--quiet",
        ]
        if inputs.get("instrumental"):
            cmd.append("--instrumental")
        elif inputs.get("lyrics_optimizer"):
            cmd.append("--lyrics-optimizer")
        elif inputs.get("lyrics"):
            cmd.extend(["--lyrics", inputs["lyrics"]])
        if inputs.get("vocals"):
            cmd.extend(["--vocals", inputs["vocals"]])
        if inputs.get("genre"):
            cmd.extend(["--genre", inputs["genre"]])
        if inputs.get("mood"):
            cmd.extend(["--mood", inputs["mood"]])
        if inputs.get("instruments"):
            cmd.extend(["--instruments", inputs["instruments"]])
        if inputs.get("tempo"):
            cmd.extend(["--tempo", inputs["tempo"]])
        if inputs.get("bpm"):
            cmd.extend(["--bpm", str(inputs["bpm"])])
        if inputs.get("key"):
            cmd.extend(["--key", inputs["key"]])
        if inputs.get("avoid"):
            cmd.extend(["--avoid", inputs["avoid"]])
        if inputs.get("use_case"):
            cmd.extend(["--use-case", inputs["use_case"]])
        if inputs.get("structure"):
            cmd.extend(["--structure", inputs["structure"]])
        if inputs.get("references"):
            cmd.extend(["--references", inputs["references"]])
        if inputs.get("format"):
            cmd.extend(["--format", inputs["format"]])
        return cmd

    def _generate_via_cli(self, inputs: dict[str, Any], prompt: str, output_path: Path) -> ToolResult:
        cmd = self._build_cli_command(inputs, output_path)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="mmx music generate timed out after 300s")
        except FileNotFoundError:
            return ToolResult(success=False, error="mmx CLI not found on PATH despite which() check")

        if proc.returncode != 0:
            return ToolResult(
                success=False,
                error=f"mmx music generate failed (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
            )

        if not output_path.exists():
            return ToolResult(success=False, error=f"mmx CLI exited 0 but {output_path} not produced")

        return ToolResult(
            success=True,
            data={
                "provider": "minimax",
                "model": self.DEFAULT_MODEL,
                "transport": "mmx-cli",
                "prompt": prompt,
                "instrumental": inputs.get("instrumental", False),
                "bpm": inputs.get("bpm"),
                "output": str(output_path),
                "format": inputs.get("format", "mp3"),
                "size_bytes": output_path.stat().st_size,
            },
            artifacts=[str(output_path)],
            model=self.DEFAULT_MODEL,
        )

    def _generate_via_api(self, inputs: dict[str, Any], prompt: str, output_path: Path) -> ToolResult:
        import urllib.error
        import urllib.request

        body: dict[str, Any] = {
            "model": self.DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        if inputs.get("lyrics"):
            body["lyrics"] = inputs["lyrics"]
        if inputs.get("instrumental"):
            body["instrumental"] = True
        if inputs.get("lyrics_optimizer"):
            body["lyrics_optimizer"] = True
        for k in ("vocals", "genre", "mood", "instruments", "tempo", "key", "use_case", "structure", "references", "avoid"):
            if inputs.get(k):
                body[k] = inputs[k]
        if inputs.get("bpm"):
            body["bpm"] = int(inputs["bpm"])
        if inputs.get("format"):
            body["format"] = inputs["format"]
        if inputs.get("sample_rate"):
            body["sample_rate"] = int(inputs["sample_rate"])
        if inputs.get("bitrate"):
            body["bitrate"] = int(inputs["bitrate"])

        url = f"{self._host()}/v1/music_generation"
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
            with urllib.request.urlopen(req, timeout=300) as resp:
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
            # Some Token Plan responses return a download URL instead
            audio_url = data.get("audio_url") or data.get("url")
            if audio_url:
                with urllib.request.urlopen(audio_url, timeout=120) as resp:
                    output_path.write_bytes(resp.read())
            else:
                raise RuntimeError(f"No audio in response: keys={list(payload.keys())}")
        else:
            output_path.write_bytes(bytes.fromhex(audio_hex))

        return ToolResult(
            success=True,
            data={
                "provider": "minimax",
                "model": self.DEFAULT_MODEL,
                "transport": "direct-api",
                "prompt": prompt,
                "instrumental": inputs.get("instrumental", False),
                "bpm": inputs.get("bpm"),
                "output": str(output_path),
                "format": inputs.get("format", "mp3"),
                "size_bytes": output_path.stat().st_size,
                "trace_id": payload.get("trace_id"),
            },
            artifacts=[str(output_path)],
            model=self.DEFAULT_MODEL,
        )