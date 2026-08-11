"""Windows-local Mandarin ASR via the official FunASR SenseVoiceSmall runtime."""

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
    ResumeSupport,
    RetryPolicy,
    ToolResult,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class SenseVoiceTranscriber(BaseTool):
    name = "sensevoice_transcriber"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "funasr_sensevoice"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["python:funasr", "python:torch"]
    install_instructions = (
        "Install an isolated FunASR runtime with compatible PyTorch, then install "
        "funasr==1.4.1. Official SenseVoiceSmall weights follow the FunASR Model "
        "Open Source License Agreement v1.1 and require attribution."
    )
    fallback = "transcriber"
    fallback_tools = ["transcriber"]
    agent_skills = ["speech-to-text"]
    capabilities = ["transcribe", "character_timestamps", "word_timestamps", "language_detection"]
    best_for = [
        "Windows-local Mandarin and Cantonese transcription",
        "fast CTC timing for approved-script alignment",
        "offline human-voice timing without cloud credentials",
    ]
    not_good_for = [
        "unreviewed product-name transcription",
        "speaker diarization",
        "blind fp16 mode on FunASR 1.4.1 SenseVoice+VAD",
    ]
    input_schema = {
        "type": "object",
        "required": ["input_path"],
        "properties": {
            "input_path": {"type": "string"},
            "output_dir": {"type": "string"},
            "model": {"type": "string", "default": "iic/SenseVoiceSmall"},
            "vad_model": {"type": "string", "default": "fsmn-vad"},
            "language": {"type": "string", "default": "zh"},
            "device": {"type": "string", "default": "auto"},
            "fp16": {
                "type": "boolean",
                "default": False,
                "description": "Disabled by default; FunASR 1.4.1 SenseVoice+VAD has a Float/Half input mismatch.",
            },
            "model_cache": {"type": "string"},
            "max_segment_seconds": {"type": "number", "default": 6.0, "minimum": 1.0},
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "segments": {"type": "array"},
            "word_timestamps": {"type": "array"},
            "language": {"type": "string"},
            "duration_seconds": {"type": "number"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=2, ram_mb=4096, vram_mb=2048, disk_mb=1800)
    retry_policy = RetryPolicy(max_retries=0)
    resume_support = ResumeSupport.FROM_START
    idempotency_key_fields = ["input_path", "model", "language", "device"]
    side_effects = ["downloads official model weights on first run", "writes transcript JSON to output_dir"]
    user_visible_verification = [
        "Compare product names and numbers against the approved script",
        "Verify CTC timestamps are monotonic and cover the spoken lines",
    ]

    def get_status(self) -> ToolStatus:
        try:
            import funasr  # noqa: F401
            import torch  # noqa: F401
            return ToolStatus.AVAILABLE
        except ImportError:
            return ToolStatus.UNAVAILABLE

    @staticmethod
    def _duration(path: Path, fallback: float) -> float:
        try:
            import soundfile as sf
            info = sf.info(str(path))
            return round(float(info.duration), 3)
        except Exception:
            return round(fallback, 3)

    @staticmethod
    def _group_segments(words: list[dict], max_seconds: float) -> list[dict]:
        groups: list[list[dict]] = []
        current: list[dict] = []
        punctuation = set("。！？!?；;")
        for word in words:
            current.append(word)
            elapsed = current[-1]["end"] - current[0]["start"]
            if str(word["word"]) in punctuation or elapsed >= max_seconds:
                groups.append(current)
                current = []
        if current:
            groups.append(current)
        return [
            {
                "id": index,
                "start": round(group[0]["start"], 3),
                "end": round(group[-1]["end"], 3),
                "text": "".join(str(item["word"]) for item in group).strip(),
                "words": group,
            }
            for index, group in enumerate(groups)
            if group
        ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        source = Path(inputs["input_path"])
        if not source.is_file():
            return ToolResult(success=False, error=f"Input file not found: {source}")
        if inputs.get("fp16"):
            return ToolResult(
                success=False,
                error=(
                    "fp16 is intentionally blocked for FunASR 1.4.1 SenseVoice+VAD: "
                    "the official path can produce a Float/Half dtype mismatch. Use fp32."
                ),
            )

        model_cache = inputs.get("model_cache")
        if model_cache:
            os.environ["MODELSCOPE_CACHE"] = str(Path(model_cache).resolve())
        try:
            import torch
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except ImportError:
            return ToolResult(success=False, error=self.install_instructions)

        device = inputs.get("device", "auto")
        if device == "auto":
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model_name = inputs.get("model", "iic/SenseVoiceSmall")
        vad_name = inputs.get("vad_model", "fsmn-vad")
        started = time.time()
        try:
            model = AutoModel(
                model=model_name,
                vad_model=vad_name,
                vad_kwargs={"max_single_segment_time": 30000},
                device=device,
                hub="ms",
                fp16=False,
                disable_update=True,
            )
            raw = model.generate(
                input=str(source),
                cache={},
                language=inputs.get("language", "zh"),
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
                output_timestamp=True,
                sentence_timestamp=True,
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"SenseVoice transcription failed: {type(exc).__name__}: {exc}")
        if not raw:
            return ToolResult(success=False, error="SenseVoice returned no result")
        item = raw[0]
        tokens = item.get("words") or []
        timestamps = item.get("timestamp") or []
        if len(tokens) != len(timestamps):
            return ToolResult(success=False, error="SenseVoice words/timestamp length mismatch")

        word_timestamps = [
            {
                "word": str(token),
                "start": round(float(pair[0]) / 1000.0, 3),
                "end": round(float(pair[1]) / 1000.0, 3),
                "probability": None,
            }
            for token, pair in zip(tokens, timestamps)
        ]
        last_end = word_timestamps[-1]["end"] if word_timestamps else 0.0
        data = {
            "segments": self._group_segments(
                word_timestamps, float(inputs.get("max_segment_seconds", 6.0))
            ),
            "word_timestamps": word_timestamps,
            "language": inputs.get("language", "zh"),
            "duration_seconds": self._duration(source, last_end),
            "text": rich_transcription_postprocess(item.get("text", "")),
            "model": model_name,
            "device": device,
            "precision": "fp32",
            "engine": "FunASR SenseVoiceSmall CTC",
            "license_policy": "FunASR Model Open Source License Agreement v1.1; attribution required",
        }
        output_dir = Path(inputs.get("output_dir", source.parent))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{source.stem}_sensevoice_transcript.json"
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ToolResult(
            success=True,
            data=data,
            artifacts=[str(output_path)],
            duration_seconds=round(time.time() - started, 3),
            model=model_name,
        )
