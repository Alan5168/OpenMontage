"""Agnes Video V2.0 provider using the current asynchronous API."""

from __future__ import annotations

import time
import urllib.parse
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


_DIMENSIONS = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
}


class AgnesVideo(BaseTool):
    name = "agnes_video"
    version = "0.2.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "agnes"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies = ["env:AGNES_API_KEY"]
    install_instructions = "Set AGNES_API_KEY in the local environment."
    agent_skills = ["ai-video-gen"]
    capabilities = ["text_to_video", "image_to_video", "reference_to_video", "keyframe_animation"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "reference_to_video": True,
        "keyframes": True,
        "camera_direction": True,
        "seed": True,
        "native_audio": False,
        "offline": False,
    }
    best_for = [
        "zero-current-price motion drafts and short social clips",
        "animating a public scene-plan keyframe",
        "smooth transitions between public keyframes",
    ]
    not_good_for = [
        "local-only reference images without an upload path",
        "native dialogue or synchronized audio",
    ]
    fallback_tools = ["comfyui_video", "seedance_video", "wan_video"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video", "reference_to_video"],
                "default": "text_to_video",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                "default": "16:9",
            },
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "duration": {"type": ["number", "string"], "default": 5},
            "frame_rate": {"type": "number", "minimum": 1, "maximum": 60, "default": 24},
            "num_frames": {"type": "integer", "minimum": 9, "maximum": 441},
            "seed": {"type": "integer"},
            "negative_prompt": {"type": "string"},
            "image_url": {"type": "string"},
            "reference_image_url": {"type": "string"},
            "reference_image_urls": {"type": "array", "items": {"type": "string"}},
            "output_path": {"type": "string"},
            "timeout_seconds": {"type": "integer", "default": 360},
            "poll_interval_seconds": {"type": "number", "default": 8},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=256, network_required=True
    )
    retry_policy = RetryPolicy(
        max_retries=1,
        backoff_seconds=8.0,
        retryable_errors=["timeout", "rate_limit", "network"],
    )
    idempotency_key_fields = ["prompt", "operation", "duration", "seed"]
    side_effects = ["writes a video file", "submits and polls an Agnes video task"]
    user_visible_verification = ["Watch the clip and verify motion and identity continuity"]
    quality_score = 0.70
    latency_p50_seconds = 120.0

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if self._has_key() else ToolStatus.UNAVAILABLE

    @staticmethod
    def _has_key() -> bool:
        import os

        return bool(os.environ.get("AGNES_API_KEY", "").strip())

    def is_operation_available(self, operation: str) -> bool:
        return operation in {"text_to_video", "image_to_video", "reference_to_video"}

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 120.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._has_key():
            return ToolResult(success=False, error=self.install_instructions)

        started = time.time()
        output_path = Path(inputs.get("output_path", "agnes_video.mp4"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            payload, frames, fps = self._payload(inputs)
            submitted = agnes_api.request_json("POST", "/v1/videos", payload, timeout=120)
            video_id = submitted.get("video_id")
            task_id = submitted.get("task_id") or submitted.get("id")
            if not video_id and not task_id:
                return ToolResult(success=False, error="Agnes returned no video_id or task_id")

            result = self._poll(
                video_id=str(video_id) if video_id else None,
                task_id=str(task_id) if task_id else None,
                timeout_seconds=int(inputs.get("timeout_seconds", 360)),
                interval=float(inputs.get("poll_interval_seconds", 8)),
            )
            url = self._result_url(result)
            if not url:
                return ToolResult(success=False, error="Agnes completed without a video URL")
            agnes_api.download(url, output_path, timeout=240)
        except Exception as exc:
            return ToolResult(success=False, error=f"Agnes video generation failed: {exc}")

        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "agnes-video-v2.0",
                "operation": inputs.get("operation", "text_to_video"),
                "video_id": video_id,
                "task_id": task_id,
                "output": str(output_path),
                "source_url": url,
                "requested_num_frames": frames,
                "requested_frame_rate": fps,
                "actual_seconds": result.get("seconds"),
                "actual_size": result.get("size"),
                "size_mapping": metadata.get("size_mapping"),
            },
            artifacts=[str(output_path)],
            cost_usd=0.0,
            duration_seconds=round(time.time() - started, 2),
            seed=inputs.get("seed"),
            model="agnes-video-v2.0",
        )

    def _payload(self, inputs: dict[str, Any]) -> tuple[dict[str, Any], int, float]:
        operation = str(inputs.get("operation", "text_to_video"))
        fps = float(inputs.get("frame_rate", 24))
        frames = self._num_frames(inputs, fps)
        ratio = str(inputs.get("aspect_ratio", "16:9"))
        default_width, default_height = _DIMENSIONS.get(ratio, _DIMENSIONS["16:9"])
        payload: dict[str, Any] = {
            "model": "agnes-video-v2.0",
            "prompt": inputs["prompt"],
            "width": int(inputs.get("width", default_width)),
            "height": int(inputs.get("height", default_height)),
            "num_frames": frames,
            "frame_rate": fps,
        }
        if inputs.get("seed") is not None:
            payload["seed"] = int(inputs["seed"])
        if inputs.get("negative_prompt"):
            payload["negative_prompt"] = str(inputs["negative_prompt"])

        if operation == "image_to_video":
            image_url = inputs.get("image_url") or inputs.get("reference_image_url")
            if not image_url:
                raise ValueError("Agnes image_to_video requires a public image URL")
            payload["image"] = str(image_url)
        elif operation == "reference_to_video":
            urls = [str(value) for value in inputs.get("reference_image_urls") or []]
            if len(urls) < 2:
                raise ValueError("Agnes keyframe animation requires at least two public image URLs")
            payload["extra_body"] = {"image": urls, "mode": "keyframes"}
        elif operation != "text_to_video":
            raise ValueError(f"Unsupported Agnes video operation: {operation}")
        return payload, frames, fps

    @staticmethod
    def _num_frames(inputs: dict[str, Any], fps: float) -> int:
        if fps < 1 or fps > 60:
            raise ValueError("frame_rate must be between 1 and 60")
        if inputs.get("num_frames") is not None:
            frames = int(inputs["num_frames"])
        else:
            duration = float(inputs.get("duration", 5))
            frames = round(((duration * fps) - 1) / 8) * 8 + 1
        if frames < 9 or frames > 441 or (frames - 1) % 8 != 0:
            raise ValueError("num_frames must be <= 441 and follow the 8n+1 rule")
        return frames

    @staticmethod
    def _result_url(result: dict[str, Any]) -> str | None:
        metadata = result.get("metadata")
        if isinstance(metadata, dict) and metadata.get("url"):
            return str(metadata["url"])
        for key in ("video_url", "url"):
            if result.get(key):
                return str(result[key])
        return None

    def _poll(
        self,
        *,
        video_id: str | None,
        task_id: str | None,
        timeout_seconds: int,
        interval: float,
    ) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if video_id:
                query = urllib.parse.urlencode({"video_id": video_id})
                response = agnes_api.request_json("GET", f"/agnesapi?{query}", timeout=60)
            else:
                response = agnes_api.request_json("GET", f"/v1/videos/{task_id}", timeout=60)
            result = response.get("data") if isinstance(response.get("data"), dict) else response
            status = str(result.get("status", "")).lower()
            if status in {"completed", "success"}:
                return result
            if status in {"failed", "error"}:
                raise RuntimeError(f"Agnes video task failed: {result.get('error') or result.get('fail_reason') or 'unknown'}")
            time.sleep(max(interval, 0))
        raise TimeoutError(f"Agnes video task did not finish within {timeout_seconds}s")
