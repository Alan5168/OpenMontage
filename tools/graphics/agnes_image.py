"""Agnes Image 2.1 provider for generation, editing, and composition."""

from __future__ import annotations

import base64
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


class AgnesImage(BaseTool):
    name = "agnes_image"
    version = "0.2.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "agnes"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:AGNES_API_KEY"]
    install_instructions = "Set AGNES_API_KEY in the local environment."
    agent_skills = ["flux-best-practices"]
    capabilities = ["text_to_image", "image_to_image", "multi_image_composition"]
    supports = {
        "text_to_image": True,
        "image_to_image": True,
        "multi_image_composition": True,
        "reference_image": True,
        "text_in_image": True,
        "offline": False,
    }
    best_for = [
        "zero-current-price concept art and scene-plan keyframes",
        "high-information-density illustrations and complex compositions",
        "image edits that should preserve the original layout",
    ]
    not_good_for = ["offline generation", "deterministic pixel-identical reruns"]
    fallback_tools = ["doubao_seedream", "image_gen", "local_diffusion"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "generation_mode": {
                "type": "string",
                "enum": ["generate", "edit"],
                "default": "generate",
            },
            "resolution": {
                "type": "string",
                "enum": ["1K", "2K", "3K", "4K"],
                "default": "1K",
            },
            "size": {"type": "string"},
            "aspect_ratio": {
                "type": "string",
                "enum": ["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"],
                "default": "1:1",
            },
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "image_url": {"type": "string"},
            "image_urls": {"type": "array", "items": {"type": "string"}},
            "image_path": {"type": "string"},
            "image_paths": {"type": "array", "items": {"type": "string"}},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=2,
        backoff_seconds=3.0,
        retryable_errors=["timeout", "rate_limit", "network"],
    )
    idempotency_key_fields = ["prompt", "generation_mode", "resolution", "aspect_ratio"]
    side_effects = ["writes an image file", "calls the Agnes image generation API"]
    user_visible_verification = ["Inspect the generated image at the asset checkpoint"]
    quality_score = 0.74
    latency_p50_seconds = 10.0

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._has_key() else ToolStatus.UNAVAILABLE

    @staticmethod
    def _has_key() -> bool:
        import os

        return bool(os.environ.get("AGNES_API_KEY", "").strip())

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._has_key():
            return ToolResult(success=False, error=self.install_instructions)

        started = time.time()
        output_path = Path(inputs.get("output_path", "agnes_image.png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image_inputs = self._image_inputs(inputs)
            if inputs.get("generation_mode") == "edit" and not image_inputs:
                return ToolResult(success=False, error="Agnes image edit requires at least one input image")

            size = self._size(inputs)
            payload: dict[str, Any] = {
                "model": "agnes-image-2.1-flash",
                "prompt": inputs["prompt"],
                "size": size,
                "extra_body": {"response_format": "url"},
            }
            ratio = inputs.get("aspect_ratio")
            if ratio and "x" not in size.lower():
                payload["ratio"] = ratio
            if image_inputs:
                payload["extra_body"]["image"] = image_inputs

            response = agnes_api.request_json(
                "POST", "/v1/images/generations", payload, timeout=180
            )
            item = self._first_output(response)
            source_url = item.get("url")
            if source_url:
                agnes_api.download(str(source_url), output_path, timeout=180)
            elif item.get("b64_json"):
                output_path.write_bytes(base64.b64decode(item["b64_json"]))
            else:
                return ToolResult(success=False, error="Agnes returned no image URL or Base64 output")
        except Exception as exc:
            return ToolResult(success=False, error=f"Agnes image generation failed: {exc}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "agnes-image-2.1-flash",
                "operation": "image_to_image" if image_inputs else "text_to_image",
                "reference_count": len(image_inputs),
                "size_requested": size,
                "aspect_ratio_requested": inputs.get("aspect_ratio", "1:1"),
                "output": str(output_path),
                "source_url": source_url,
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - started, 2),
            model="agnes-image-2.1-flash",
        )

    @staticmethod
    def _size(inputs: dict[str, Any]) -> str:
        if inputs.get("size"):
            return str(inputs["size"])
        if inputs.get("width") and inputs.get("height"):
            return f"{int(inputs['width'])}x{int(inputs['height'])}"
        return str(inputs.get("resolution", "1K"))

    @staticmethod
    def _first_output(response: dict[str, Any]) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise RuntimeError("Agnes returned an invalid image response")
        return data[0]

    @staticmethod
    def _image_inputs(inputs: dict[str, Any]) -> list[str]:
        values: list[str] = []
        for value in inputs.get("image_urls") or []:
            values.append(str(value))
        if inputs.get("image_url"):
            values.append(str(inputs["image_url"]))
        for value in inputs.get("image_paths") or []:
            values.append(agnes_api.file_to_data_uri(str(value)))
        if inputs.get("image_path"):
            values.append(agnes_api.file_to_data_uri(str(inputs["image_path"])))
        return values
