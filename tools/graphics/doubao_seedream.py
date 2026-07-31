"""Doubao Seedream text-to-image via Volcano Ark Token Plan.

Primary image generation path for OpenMontage under active Volcano Ark
Token Plan (方舟套餐). Uses the cn-beijing regional Token Plan endpoint
which is distinct from the standard ARK v3 endpoint.

Configuration (prefer ~/.codex/skills.env, then OpenMontage .env):
  ARK_API_KEY              — Token Plan subscription key (ark-...)
  ARK_API_BASE             — default https://ark.cn-beijing.volces.com/api/plan/v3
  DOUBAO_SEEDREAM_MODEL    — default doubao-seedream-5.0-lite

Endpoint:
  POST {base}/images/generations
  Body: {"model": "doubao-seedream-5.0-lite",
         "prompt": "...",
         "size": "1024x1024" | "864x1152" | "1152x864" | ...,
         "response_format": "url" | "b64_json",
         "seed": <int optional>,
         "watermark": false}

Auth: Bearer ${ARK_API_KEY}
Docs: https://console.volcengine.com/ark/region:cn-beijing/docs/82379/2375486?lang=zh

Fallback chain (declared in image_selector): volcengine -> agnes -> flux -> google_imagen -> recraft -> stock
"""

from __future__ import annotations

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
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "volcengine"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies = []  # ARK_API_KEY checked dynamically
    fallback = "agnes_image"
    fallback_tools = [
        "agnes_image",
        "comfyui_image",
        "flux_image",
        "google_imagen",
        "recraft_image",
    ]
    agent_skills = ["text-to-image", "volcengine-ark", "doubao-seedream"]

    capabilities = [
        "generate_image",
        "text_to_image",
    ]
    supports = {
        "image_edit": True,  # Doubao Seedream supports image-to-image with image field
        "offline": False,
        "native_audio": False,
        "seed": True,
        "size_presets": True,
        "watermark_control": True,
    }
    best_for = [
        "Alan CN-channel hero art on Volcano Ark Token Plan (5.0-lite cheap)",
        "character plate / storyboard frames for Ep1-style productions",
        "first/last frames that hand off to React/Remotion for middle motion",
    ]
    not_good_for = [
        "very high resolution (>2K) — Seedream 5.0-lite caps at 1536x1536",
        "production environments with strict no-watermark compliance (set watermark=true to opt out)",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the desired image. Chinese-friendly.",
            },
            "negative_prompt": {
                "type": "string",
                "description": "What to avoid. Passed only if the API supports it for the chosen model.",
            },
            "size": {
                "type": "string",
                "default": "1024x1024",
                "description": (
                    "Image size preset. Doubao Seedream-5.0-lite supports "
                    "1024x1024, 864x1152, 1152x864, 1280x720, 720x1280, 1536x1024, 1024x1536, etc."
                ),
            },
            "width": {
                "type": "integer",
                "description": "Optional explicit width. Overrides size if both provided.",
            },
            "height": {
                "type": "integer",
                "description": "Optional explicit height. Overrides size if both provided.",
            },
            "seed": {
                "type": "integer",
                "description": "Random seed for reproducibility.",
            },
            "watermark": {
                "type": "boolean",
                "default": False,
                "description": "Whether to embed AI-generated content watermark.",
            },
            "response_format": {
                "type": "string",
                "enum": ["url", "b64_json"],
                "default": "url",
                "description": "url returns CDN links (default); b64_json returns inline base64 (no CDN hop).",
            },
            "image": {
                "type": "string",
                "description": (
                    "Optional source image URL or path for image-to-image / edit mode. "
                    "When provided, the call switches to edit mode (image_url)."
                ),
            },
            "n": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 4,
                "description": "Number of images to generate (1-4 supported by Token Plan).",
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
    idempotency_key_fields = ["prompt", "size", "seed", "image"]
    side_effects = ["writes image file to output_path", "calls Volcano Ark images/generations"]
    user_visible_verification = [
        "Open the generated image and confirm content matches prompt + size preset.",
    ]
    quality_score = 0.90
    latency_p50_seconds = 8.0

    DEFAULT_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
    DEFAULT_MODEL = "doubao-seedream-5.0-lite"

    def _api_key(self) -> str | None:
        return (
            os.environ.get("ARK_API_KEY")
            or os.environ.get("DOUBAO_ARK_API_KEY")
            or os.environ.get("VOLCENGINE_ARK_API_KEY")
        )

    def _base(self) -> str:
        return (os.environ.get("ARK_API_BASE") or self.DEFAULT_BASE).rstrip("/")

    def _model(self) -> str:
        return os.environ.get("DOUBAO_SEEDREAM_MODEL") or self.DEFAULT_MODEL

    def get_status(self) -> ToolStatus:
        if self._api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # Token Plan: billed against subscription quota, not per-call USD.
        return 0.0

    install_instructions = (
        "Set ARK_API_KEY (Volcano Ark Token Plan key, format ark-...) in "
        "~/.codex/skills.env or OpenMontage .env.\n"
        "Optional: ARK_API_BASE (default https://ark.cn-beijing.volces.com/api/plan/v3), "
        "DOUBAO_SEEDREAM_MODEL (default doubao-seedream-5.0-lite).\n"
        "API: POST {base}/images/generations with model + prompt + size.\n"
        "Docs: https://console.volcengine.com/ark/region:cn-beijing/docs/82379/2375486?lang=zh"
    )

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._api_key():
            return ToolResult(success=False, error="No ARK_API_KEY. " + self.install_instructions)

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Doubao Seedream generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        prompt = inputs["prompt"]
        size = inputs.get("size") or "1024x1024"
        if inputs.get("width") and inputs.get("height"):
            size = f"{int(inputs['width'])}x{int(inputs['height'])}"

        body: dict[str, Any] = {
            "model": self._model(),
            "prompt": prompt,
            "size": size,
            "response_format": inputs.get("response_format", "url"),
            "watermark": bool(inputs.get("watermark", False)),
        }
        if inputs.get("seed") is not None:
            body["seed"] = int(inputs["seed"])
        if inputs.get("n") and inputs["n"] > 1:
            body["n"] = int(inputs["n"])
        # image-to-image / edit mode
        if inputs.get("image"):
            body["image"] = inputs["image"]
        # negative_prompt is supported on some Seedream variants; pass-through if provided
        if inputs.get("negative_prompt"):
            body["negative_prompt"] = inputs["negative_prompt"]

        url = f"{self._base()}/images/generations"
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

        # Token Plan responses: {"data": [{"url": "..."} | {"b64_json": "..."}], "usage": {...}, ...}
        data = payload.get("data") or []
        if not data:
            raise RuntimeError(f"No image data in response: keys={list(payload.keys())}")

        artifacts: list[str] = []
        urls: list[str] = []
        for idx, item in enumerate(data):
            if inputs.get("output_path"):
                # If single output requested, use it; else derive
                if len(data) == 1:
                    out = Path(inputs["output_path"])
                else:
                    p = Path(inputs["output_path"])
                    out = p.with_name(f"{p.stem}_{idx}{p.suffix or '.png'}")
            else:
                out = Path(f"doubao_seedream_{idx}.png")

            if "b64_json" in item:
                import base64
                out.write_bytes(base64.b64decode(item["b64_json"]))
            elif "url" in item:
                url_str = item["url"]
                urls.append(url_str)
                with urllib.request.urlopen(url_str, timeout=120) as resp:
                    out.write_bytes(resp.read())
            else:
                raise RuntimeError(f"Unknown response item keys: {list(item.keys())}")

            out.parent.mkdir(parents=True, exist_ok=True)
            artifacts.append(str(out))

        usage = payload.get("usage") or {}
        return ToolResult(
            success=True,
            data={
                "provider": "volcengine",
                "model": self._model(),
                "prompt": prompt,
                "size": size,
                "seed": inputs.get("seed"),
                "watermark": body["watermark"],
                "response_format": body["response_format"],
                "image_urls": urls,
                "n_generated": len(data),
                "usage": usage,
                "output_paths": artifacts,
                "edit_mode": bool(inputs.get("image")),
            },
            artifacts=artifacts,
            model=self._model(),
        )