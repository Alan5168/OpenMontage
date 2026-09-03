"""Agnes 2.5 Flash image understanding and OCR provider."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools import agnes_api
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


_DEFAULT_PROMPTS = {
    "ocr": "Extract all visible text exactly. Preserve reading order, line breaks, numbers, and punctuation. Do not add commentary.",
    "describe": "Describe this image precisely, including composition, subjects, actions, camera, lighting, style, and visible text.",
    "extract": "Extract the requested information from this image. Return only the requested structured content.",
}


class AgnesVision(BaseTool):
    name = "agnes_vision"
    version = "0.1.0"
    tier = ToolTier.ANALYZE
    capability = "analysis"
    provider = "agnes"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = ["env:AGNES_API_KEY"]
    install_instructions = "Set AGNES_API_KEY in the local environment."
    agent_skills = ["video-understand"]
    capabilities = ["image_understanding", "ocr", "structured_visual_extraction"]
    supports = {
        "image_understanding": True,
        "ocr": True,
        "local_image_data_uri": True,
        "video_understanding": False,
        "offline": False,
    }
    best_for = [
        "OCR and screenshot interpretation when the Prime text model has no vision",
        "scene-plan keyframe description and visual evidence extraction",
        "structured checks over a single image",
    ]
    not_good_for = ["offline/private-only images that must not leave the machine", "video understanding"]
    fallback_tools = ["video_understand", "visual_qa"]

    input_schema = {
        "type": "object",
        "required": ["operation"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["ocr", "describe", "extract"],
            },
            "image_url": {"type": "string"},
            "image_path": {"type": "string"},
            "prompt": {"type": "string"},
            "max_tokens": {"type": "integer", "default": 4096},
            "output_path": {"type": "string"},
        },
        "oneOf": [{"required": ["image_url"]}, {"required": ["image_path"]}],
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=16, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=2.0,
        retryable_errors=["timeout", "rate_limit", "network"],
    )
    idempotency_key_fields = ["operation", "image_url", "image_path", "prompt"]
    side_effects = ["optionally writes a text artifact", "sends the image to Agnes AI"]
    user_visible_verification = ["Compare OCR or description against the source image"]
    latency_p50_seconds = 10.0

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._has_key() else ToolStatus.UNAVAILABLE

    @staticmethod
    def _has_key() -> bool:
        import os

        return bool(os.environ.get("AGNES_API_KEY", "").strip())

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._has_key():
            return ToolResult(success=False, error=self.install_instructions)

        started = time.time()
        operation = str(inputs["operation"])
        prompt = str(inputs.get("prompt") or _DEFAULT_PROMPTS[operation])
        try:
            image_ref = self._image_ref(inputs)
            response = agnes_api.request_json(
                "POST",
                "/v1/chat/completions",
                {
                    "model": "agnes-2.5-flash",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_ref}},
                            ],
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": int(inputs.get("max_tokens", 4096)),
                },
                timeout=120,
            )
            text = self._message_text(response)
            artifacts: list[str] = []
            if inputs.get("output_path"):
                output_path = Path(str(inputs["output_path"]))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(text, encoding="utf-8")
                artifacts.append(str(output_path))
        except Exception as exc:
            return ToolResult(success=False, error=f"Agnes vision request failed: {exc}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "agnes-2.5-flash",
                "operation": operation,
                "text": text,
                "output": artifacts[0] if artifacts else None,
            },
            artifacts=artifacts,
            cost_usd=0.0,
            duration_seconds=round(time.time() - started, 2),
            model="agnes-2.5-flash",
        )

    @staticmethod
    def _image_ref(inputs: dict[str, Any]) -> str:
        if inputs.get("image_url"):
            return str(inputs["image_url"])
        if inputs.get("image_path"):
            return agnes_api.file_to_data_uri(str(inputs["image_path"]))
        raise ValueError("Agnes vision requires image_url or image_path")

    @staticmethod
    def _message_text(response: dict[str, Any]) -> str:
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Agnes returned an invalid vision response") from exc
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Agnes returned an empty vision response")
        return text.strip()
