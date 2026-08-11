"""Doubao Seedream image generation through the Volcano Ark AgentPlan API."""

from __future__ import annotations

import base64
import hashlib
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


class DoubaoSeedream(BaseTool):
    name = "doubao_seedream"
    version = "0.2.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "volcengine"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies: list[str] = []
    install_instructions = (
        "Set ARK_AGENTPLAN_API_KEY in the host-local secret store. "
        "Optional non-secret overrides: ARK_AGENTPLAN_BASE and DOUBAO_SEEDREAM_MODEL."
    )
    agent_skills: list[str] = []
    capabilities = ["generate_image", "text_to_image", "sceneplan_layout_reference"]
    supports = {
        "negative_prompt": True,
        "seed": True,
        "custom_size": True,
        "multiple_outputs": True,
        "watermark_control": True,
        "chinese_prompt": True,
    }
    best_for = [
        "Chinese textless layout and keyframe references",
        "seeded scene-plan composition references",
        "Volcano Ark AgentPlan quota-backed image generation",
    ]
    not_good_for = ["offline generation", "final readable text layers"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "size": {"type": "string", "default": "2048x2048"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "seed": {"type": "integer"},
            "watermark": {"type": "boolean", "default": False},
            "response_format": {"type": "string", "enum": ["url", "b64_json"], "default": "url"},
            "n": {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=128, disk_mb=20, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, backoff_seconds=2.0, retryable_errors=["timeout", "429", "502", "503"])
    idempotency_key_fields = ["prompt", "size", "seed"]
    side_effects = ["writes image file to output_path", "calls Volcano Ark images/generations"]
    user_visible_verification = ["Inspect composition, viewpoint, action, and textlessness"]
    quality_score = 0.90
    latency_p50_seconds = 8.0

    DEFAULT_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
    DEFAULT_MODEL = "doubao-seedream-5.0-lite"

    def _api_key(self) -> str | None:
        return os.environ.get("ARK_AGENTPLAN_API_KEY")

    def _base(self) -> str:
        return (os.environ.get("ARK_AGENTPLAN_BASE") or self.DEFAULT_BASE).rstrip("/")

    def _model(self) -> str:
        return os.environ.get("DOUBAO_SEEDREAM_MODEL") or self.DEFAULT_MODEL

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._api_key() else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    @staticmethod
    def _output_paths(output_path: str | None, count: int) -> list[Path]:
        path = Path(output_path or "doubao_seedream.png")
        path = path if path.suffix else path.with_suffix(".png")
        if count == 1:
            return [path]
        return [path.with_name(f"{path.stem}_{index + 1}{path.suffix}") for index in range(count)]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._api_key()
        if not api_key:
            return ToolResult(success=False, error="ARK_AGENTPLAN_API_KEY not set. " + self.install_instructions)

        size = inputs.get("size") or "2048x2048"
        if inputs.get("width") and inputs.get("height"):
            size = f"{int(inputs['width'])}x{int(inputs['height'])}"
        body: dict[str, Any] = {
            "model": self._model(),
            "prompt": inputs["prompt"],
            "size": size,
            "response_format": inputs.get("response_format", "url"),
            "watermark": bool(inputs.get("watermark", False)),
            "n": int(inputs.get("n", 1)),
        }
        if inputs.get("negative_prompt"):
            body["negative_prompt"] = inputs["negative_prompt"]
        if inputs.get("seed") is not None:
            body["seed"] = int(inputs["seed"])

        request = urllib.request.Request(
            f"{self._base()}/images/generations",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            items = payload.get("data") or []
            if not items:
                raise RuntimeError(f"No image data in response; keys={sorted(payload)}")
            paths = self._output_paths(inputs.get("output_path"), len(items))
            artifacts: list[str] = []
            hashes: list[str] = []
            urls: list[str] = []
            for item, path in zip(items, paths):
                path.parent.mkdir(parents=True, exist_ok=True)
                if item.get("b64_json"):
                    content = base64.b64decode(item["b64_json"])
                elif item.get("url"):
                    urls.append(item["url"])
                    with urllib.request.urlopen(item["url"], timeout=120) as image_response:
                        content = image_response.read()
                else:
                    raise RuntimeError(f"Unsupported response item keys: {sorted(item)}")
                path.write_bytes(content)
                artifacts.append(str(path))
                hashes.append(hashlib.sha256(content).hexdigest())
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return ToolResult(success=False, error=f"Doubao Seedream HTTP {exc.code}: {body_text[:500]}")
        except Exception as exc:
            return ToolResult(success=False, error=f"Doubao Seedream generation failed: {exc}")

        request_id = payload.get("request_id") or payload.get("id") or "provider-not-returned"
        usage = payload.get("usage") or {}
        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": self._model(),
                "prompt": inputs["prompt"],
                "negative_prompt": inputs.get("negative_prompt"),
                "seed": inputs.get("seed"),
                "size": size,
                "request_id": request_id,
                "cost_or_plan_usage": usage or "agentplan-quota",
                "output_hashes": hashes,
                "license_policy": "volcano-ark-service-terms-review-required",
                "image_urls": urls,
                "output_paths": artifacts,
            },
            artifacts=artifacts,
            cost_usd=0.0,
            duration_seconds=round(time.time() - started, 2),
            seed=inputs.get("seed"),
            model=self._model(),
        )
