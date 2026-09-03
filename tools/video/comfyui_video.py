"""ComfyUI video generation via a local or remote ComfyUI server.

Supports local ComfyUI video. Bundled stacks:

- MiniMax H3 I2V (Studio keep-set, ``workflow_model=minimax-h3``)
- WAN 2.2 14B FP8 + LightX2V 4-step (legacy bundled default)

Custom workflows are accepted via ``workflow_json`` / ``workflow_path``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

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
from lib.h3_context_ir import compile_h3_ir
from tools._comfyui.client import ComfyUIClient, ComfyUIError
from tools._comfyui.metadata import (
    BUNDLED_MODEL_STACKS,
    COMFYUI_SETUP_OFFER,
    missing_models_payload,
    model_stack,
    workflow_hash,
)

_WORKFLOWS = Path(__file__).resolve().parent.parent / "_comfyui" / "workflows"

# Output node IDs in the bundled workflows
_T2V_OUTPUT_NODE = "16"
_I2V_OUTPUT_NODE = "108"
_H3_I2V_OUTPUT_NODE = "16"
_H3_WORKFLOW_KEYS = frozenset({"minimax-h3", "minimax-h3-i2v", "h3", "h3-comfyui"})
_H3_POLL_INTERVAL_S = 2
_H3_CLIP_DEVICE = "cpu"

# Models required by the bundled WAN 2.2 workflows
_REQUIRED_MODELS_COMMON = [
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
]
_REQUIRED_MODELS_I2V = [
    *_REQUIRED_MODELS_COMMON,
    "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
    "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
    "wan_2.1_vae.safetensors",
    "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
    "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors",
]
_REQUIRED_MODELS_T2V = [
    *_REQUIRED_MODELS_COMMON,
    "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
    "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
    "wan_2.1_vae.safetensors",
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors",
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors",
]
_REQUIRED_MODELS_H3_I2V = [
    "MiniMax_H3_FL2VA_pruned_nvfp4.safetensors",
    "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "minimax_h3_video_vae_fp16.safetensors",
    "minimax_h3_audio_vae_fp32.safetensors",
]


def _wants_h3(inputs: dict[str, Any]) -> bool:
    if inputs.get("h3_ir"):
        return True
    key = str(inputs.get("workflow_model") or inputs.get("model") or "").strip().lower()
    return key in _H3_WORKFLOW_KEYS


_RESOURCE_PROFILES = {
    "provider_floor": {
        "vram_mb": 8000,
        "ram_mb": 16000,
        "applies_to": (
            "ComfyUI provider availability and low-VRAM custom workflows. "
            "Actual requirements depend on workflow_json/workflow_path."
        ),
    },
    "bundled_wan22_14b_fp8": {
        "vram_mb": 16000,
        "ram_mb": 32000,
        "applies_to": (
            "Bundled WAN 2.2 14B FP8 T2V/I2V workflows. This is not a "
            "ComfyUI provider-wide requirement."
        ),
    },
    "bundled_minimax_h3_nvfp4": {
        "vram_mb": 16000,
        "ram_mb": 32000,
        "applies_to": (
            "Bundled MiniMax H3 I2V keep-set (NVFP4). Studio ComfyUI 0.31+ "
            "with extra_model_paths to C:\\models\\h3-nvfp4."
        ),
    },
    "low_vram_custom_workflows": {
        "vram_mb": "8000-12000",
        "ram_mb": "16000-32000",
        "examples": [
            "Wan 2.1 1.3B",
            "LTX-Video / LTXV FP8 or quantized workflows",
            "Wan 2.2 GGUF / quantized community workflows",
        ],
    },
}


class ComfyUIVideo(BaseTool):
    name = "comfyui_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "comfyui"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    dependencies = []
    setup_offer = COMFYUI_SETUP_OFFER
    install_instructions = (
        "Start a ComfyUI server and set COMFYUI_SERVER_URL "
        "(default http://localhost:8188).\n"
        "Studio I2V_HARD uses MiniMax H3 keep-set "
        "(workflow_model=minimax-h3). WAN 2.2 remains the bundled default "
        "for callers that do not request H3."
    )
    agent_skills = ["comfyui", "ai-video-gen", "ltx2"]

    capabilities = ["text_to_video", "image_to_video"]
    supports = {
        "seed": True,
        "reference_image": True,
        "custom_workflow": True,
        "custom_output_node": True,
        "offline": True,
    }
    best_for = [
        "local GPU video generation without API costs",
        "Blackwell / DGX Spark hardware where diffusers is unsupported",
        "image-to-video with MiniMax H3 keep-set (workflow_model=minimax-h3)",
        "image-to-video with WAN 2.2 14B (4-step accelerated, legacy default)",
        "text-to-video with WAN 2.2 14B (4-step accelerated)",
        "custom low-VRAM ComfyUI workflows on 8GB-12GB GPUs",
    ]
    not_good_for = [
        "setups without a running ComfyUI server",
        "CPU-only machines",
        "running the bundled WAN 2.2 14B FP8 workflows on GPUs below 16GB VRAM",
    ]
    fallback = "wan_video"
    fallback_tools = ["wan_video", "hunyuan_video", "ltx_video_local", "kling_video"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Text prompt for video generation. Optional when h3_ir is "
                    "supplied; the OM Context-IR compiler fills it."
                ),
            },
            "h3_ir": {
                "type": "object",
                "description": (
                    "Structured H3 cut spec. Compiled locally by lib.h3_context_ir "
                    "(not MiniMax hosted Context-IR)."
                ),
            },
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video"],
                "default": "text_to_video",
            },
            "reference_image_path": {
                "type": "string",
                "description": "Local path to reference image (for image_to_video)",
            },
            "reference_image_url": {
                "type": "string",
                "description": "URL of reference image (for image_to_video, downloaded first)",
            },
            "last_frame_path": {
                "type": "string",
                "description": "Optional last-frame path for MiniMax H3 FL2VA.",
            },
            "width": {"type": "integer", "default": 832, "description": "T2V default 832, I2V default 640"},
            "height": {"type": "integer", "default": 480, "description": "T2V default 480, I2V default 640"},
            "num_frames": {"type": "integer", "default": 81, "description": "81 frames = 5s at 16fps"},
            "seed": {"type": "integer", "description": "Random if omitted"},
            "output_path": {"type": "string", "description": "Where to save the video"},
            "workflow_json": {
                "type": "string",
                "description": "Optional full ComfyUI workflow JSON. Requires output_node.",
            },
            "workflow_path": {
                "type": "string",
                "description": "Optional path to a ComfyUI workflow JSON file. Requires output_node.",
            },
            "output_node": {
                "type": "string",
                "description": "ComfyUI output node ID for custom workflow_json/workflow_path.",
            },
            "workflow_name": {
                "type": "string",
                "description": "Optional human-readable provenance label for a custom workflow.",
            },
            "workflow_model": {
                "type": "string",
                "description": "Optional model/provenance label for a custom workflow.",
            },
            "workflow_model_stack": {
                "type": "array",
                "description": (
                    "Optional provenance metadata for custom workflow dependencies. "
                    "Items should include name, role, quantization, scheduler, "
                    "and LoRA strengths when known."
                ),
                "items": {"type": "object"},
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=16000, vram_mb=8000, disk_mb=2000, network_required=False,
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["timeout"])
    idempotency_key_fields = ["prompt", "operation", "width", "height", "num_frames", "seed"]
    side_effects = ["writes video file to output_path"]
    user_visible_verification = ["Watch generated clip for motion coherence and artifacts"]

    def __init__(self) -> None:
        self._client = ComfyUIClient()

    def get_status(self) -> ToolStatus:
        if not self._client.is_available():
            return ToolStatus.UNAVAILABLE
        statuses = self.operation_statuses()
        if any(status == "available" for status in statuses.values()):
            return ToolStatus.AVAILABLE
        if statuses:
            return ToolStatus.DEGRADED
        return ToolStatus.UNAVAILABLE

    def operation_statuses(self) -> dict[str, str]:
        """Return per-operation readiness for selector routing and preflight."""
        if not self._client.is_available():
            return {
                "text_to_video": "unavailable",
                "image_to_video": "unavailable",
            }

        _, missing_t2v = self._client.check_models(_REQUIRED_MODELS_T2V)
        _, missing_i2v = self._client.check_models(_REQUIRED_MODELS_I2V)
        _, missing_h3 = self._client.check_models(_REQUIRED_MODELS_H3_I2V)
        i2v_ready = (not missing_i2v) or (not missing_h3)
        return {
            "text_to_video": "available" if not missing_t2v else "degraded",
            "image_to_video": "available" if i2v_ready else "degraded",
        }

    def is_operation_available(self, operation: str) -> bool:
        if operation not in {"text_to_video", "image_to_video"}:
            return False
        return self.operation_statuses().get(operation) == "available"

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["operation_statuses"] = self.operation_statuses()
        info["resource_profiles"] = _RESOURCE_PROFILES
        info["setup_offer"] = self.setup_offer
        info["bundled_model_stacks"] = {
            "text_to_video": BUNDLED_MODEL_STACKS["wan22-t2v-4step"],
            "image_to_video": BUNDLED_MODEL_STACKS["wan22-i2v-4step"],
            "minimax-h3-i2v": BUNDLED_MODEL_STACKS["minimax-h3-i2v"],
        }
        info["resource_profile_note"] = (
            "The top-level resource_profile is a ComfyUI provider floor, not a "
            "promise that every workflow fits 8GB VRAM. Bundled WAN 2.2 14B FP8 "
            "workflows recommend 16GB VRAM; custom low-VRAM workflows can target "
            "8GB-12GB depending on model, quantization, resolution, and frame count."
        )
        return info

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        if _wants_h3(inputs):
            # Budget, not a measurement. 124-frame ship grid + CPU CLIP.
            return 300.0
        operation = inputs.get("operation", "text_to_video")
        if operation == "image_to_video":
            return 210.0  # ~3.5 min
        return 240.0  # ~4 min

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        from lib.shot_production_gate import motion_dispatch_error

        blocked = motion_dispatch_error(inputs)
        if blocked:
            return ToolResult(success=False, error=blocked)

        inputs = dict(inputs)
        compiled = None
        if inputs.get("h3_ir"):
            compiled = compile_h3_ir(inputs["h3_ir"])
            inputs["prompt"] = compiled["prompt"]
            inputs.setdefault("width", compiled["width"])
            inputs.setdefault("height", compiled["height"])
            inputs.setdefault("num_frames", compiled["length"])
            inputs.setdefault("operation", "image_to_video")
            if compiled.get("first_frame") and not inputs.get("reference_image_path"):
                inputs["reference_image_path"] = compiled["first_frame"]
            if compiled.get("last_frame") and not inputs.get("last_frame_path"):
                inputs["last_frame_path"] = compiled["last_frame"]

        if not inputs.get("prompt") and not (
            inputs.get("workflow_json") or inputs.get("workflow_path")
        ):
            return ToolResult(
                success=False,
                error="comfyui_video requires prompt or h3_ir",
            )

        custom_workflow = bool(inputs.get("workflow_json") or inputs.get("workflow_path"))
        if custom_workflow and not inputs.get("output_node"):
            return ToolResult(
                success=False,
                error=(
                    "Custom ComfyUI workflows require output_node so OpenMontage "
                    "knows which ComfyUI node to download artifacts from."
                ),
            )

        if not self._client.is_available():
            return ToolResult(
                success=False,
                error=self._client.unavailable_reason(),
            )

        operation = inputs.get("operation", "text_to_video")
        wants_h3 = (not custom_workflow) and _wants_h3(inputs)

        if not custom_workflow:
            if wants_h3:
                required = _REQUIRED_MODELS_H3_I2V
                workflow_key = "minimax-h3-i2v"
            elif operation == "image_to_video":
                required = _REQUIRED_MODELS_I2V
                workflow_key = "wan22-i2v-4step"
            else:
                required = _REQUIRED_MODELS_T2V
                workflow_key = "wan22-t2v-4step"
            _, missing = self._client.check_models(required)
            if missing:
                return ToolResult(
                    success=False,
                    data=missing_models_payload(
                        missing,
                        workflow_key=workflow_key,
                        workflow_name=f"{workflow_key}.json",
                        operation=operation,
                    ),
                    error=(
                        f"ComfyUI server is running but missing models for {operation}: "
                        f"{', '.join(missing)}.\n"
                        f"See data.missing_models for destination hints and download URLs."
                    ),
                )
        start = time.perf_counter()
        seed = inputs.get("seed") or ComfyUIClient.random_seed()
        output_path = Path(
            inputs.get("output_path", f"comfyui_video_{operation}_{seed}.mp4")
        )
        stage_s = 0.0

        try:
            if custom_workflow:
                workflow = self._load_custom_workflow(inputs)
                output_node = str(inputs["output_node"])
            elif wants_h3:
                staged = time.perf_counter()
                workflow, output_node = self._build_h3_i2v(inputs, seed, output_path)
                stage_s = round(time.perf_counter() - staged, 3)
            elif operation == "image_to_video":
                workflow, output_node = self._build_i2v(inputs, seed, output_path)
            else:
                workflow, output_node = self._build_t2v(inputs, seed, output_path)

            provenance = self._workflow_provenance(
                inputs, custom_workflow, output_node, operation, workflow, wants_h3=wants_h3
            )
            poll_interval = _H3_POLL_INTERVAL_S if wants_h3 else 10
            paths = self._client.generate(
                workflow,
                output_node=output_node,
                dest=output_path,
                timeout=900,
                interval=poll_interval,
            )

        except ComfyUIError as exc:
            return ToolResult(success=False, error=str(exc))
        except Exception as exc:
            return ToolResult(success=False, error=f"ComfyUI video generation failed: {exc}")

        fps = 24 if wants_h3 else 16
        if wants_h3:
            width = inputs.get("width", 1344)
            height = inputs.get("height", 768)
            num_frames = inputs.get("num_frames", 124)
        else:
            width = inputs.get("width", 832 if operation == "text_to_video" else 640)
            height = inputs.get("height", 480 if operation == "text_to_video" else 640)
            num_frames = inputs.get("num_frames", 81)

        model_name = self._model_name(inputs, custom_workflow, wants_h3=wants_h3)
        data = {
            "provider": "comfyui",
            "model": model_name,
            "prompt": inputs["prompt"],
            "operation": operation,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "fps": fps,
            "duration_seconds": round(num_frames / fps, 2),
            "output": str(paths[0]),
            "format": "mp4",
            "workflow_provenance": provenance,
            "hosted_minimax_ir": False,
        }
        if compiled is not None:
            data["h3_ir"] = {
                "schema_version": compiled["schema_version"],
                "avoid": compiled["avoid"],
                "length": compiled["length"],
                "camera_lock": compiled["camera_lock"],
                "requested_duration_seconds": compiled.get("requested_duration_seconds"),
                "duration_capped_to_ship_grid": compiled.get("duration_capped_to_ship_grid"),
            }
        wall = round(time.perf_counter() - start, 3)
        comfy_timing = dict(getattr(self._client, "last_timing", None) or {})
        exec_s = comfy_timing.get("comfy_prompt_exec_s")
        overhead = wall
        if isinstance(exec_s, (int, float)):
            overhead = round(max(0.0, wall - float(exec_s)), 3)
        data["timing"] = {
            **comfy_timing,
            "harness_stage_s": stage_s,
            "harness_overhead_s": overhead,
            "wall_s": wall,
        }
        return ToolResult(
            success=True,
            data=data,
            artifacts=[str(p) for p in paths],
            cost_usd=0.0,
            duration_seconds=wall,
            seed=seed,
            model=model_name,
        )

    # ------------------------------------------------------------------
    # Workflow builders
    # ------------------------------------------------------------------

    def _build_t2v(
        self, inputs: dict[str, Any], seed: int, output_path: Path
    ) -> tuple[dict, str]:
        width = inputs.get("width", 832)
        height = inputs.get("height", 480)
        num_frames = inputs.get("num_frames", 81)

        workflow = ComfyUIClient.load_workflow(_WORKFLOWS / "wan22-t2v-4step.json")
        workflow = ComfyUIClient.patch_workflow(workflow, {
            "2": {"text": inputs["prompt"]},
            "11": {"width": width, "height": height, "batch_size": num_frames},
            "12": {"noise_seed": seed},
            "16": {"filename_prefix": output_path.stem},
        })
        return workflow, _T2V_OUTPUT_NODE

    def _stage_reference(self, inputs: dict[str, Any], output_path: Path) -> str:
        ref_path = inputs.get("reference_image_path")
        ref_url = inputs.get("reference_image_url")

        if ref_url and not ref_path:
            resp = requests.get(ref_url, timeout=60)
            resp.raise_for_status()
            ref_path = str(output_path.with_suffix(".ref.png"))
            Path(ref_path).parent.mkdir(parents=True, exist_ok=True)
            Path(ref_path).write_bytes(resp.content)

        if not ref_path:
            raise ComfyUIError(
                "image_to_video requires reference_image_path or reference_image_url"
            )

        upload_name = f"om_{output_path.stem}.png"
        return self._client.upload_image(Path(ref_path), upload_name)

    def _build_i2v(
        self, inputs: dict[str, Any], seed: int, output_path: Path
    ) -> tuple[dict, str]:
        width = inputs.get("width", 640)
        height = inputs.get("height", 640)
        num_frames = inputs.get("num_frames", 81)
        server_name = self._stage_reference(inputs, output_path)

        workflow = ComfyUIClient.load_workflow(_WORKFLOWS / "wan22-i2v-4step.json")
        workflow = ComfyUIClient.patch_workflow(workflow, {
            "93": {"text": inputs["prompt"]},
            "97": {"image": server_name},
            "98": {"width": width, "height": height, "length": num_frames},
            "86": {"noise_seed": seed},
            "108": {"filename_prefix": output_path.stem},
        })
        return workflow, _I2V_OUTPUT_NODE

    def _build_h3_i2v(
        self, inputs: dict[str, Any], seed: int, output_path: Path
    ) -> tuple[dict, str]:
        width = inputs.get("width", 1344)
        height = inputs.get("height", 768)
        num_frames = inputs.get("num_frames", 124)
        server_name = self._stage_reference(inputs, output_path)

        workflow = ComfyUIClient.load_workflow(_WORKFLOWS / "minimax-h3-i2v.json")
        patches = {
            "3": {"device": _H3_CLIP_DEVICE},
            "6": {"image": server_name},
            "7": {
                "prompt": inputs["prompt"],
                "width": width,
                "height": height,
                "length": num_frames,
            },
            "8": {"noise_seed": seed},
            "16": {"filename_prefix": output_path.stem},
        }
        last_path = inputs.get("last_frame_path")
        if last_path:
            last_name = self._client.upload_image(
                Path(last_path), f"om_{output_path.stem}_last.png"
            )
            workflow["17"] = {
                "class_type": "LoadImage",
                "inputs": {"image": last_name},
            }
            patches["7"]["last_frame"] = ["17", 0]
        workflow = ComfyUIClient.patch_workflow(workflow, patches)
        return workflow, _H3_I2V_OUTPUT_NODE

    @staticmethod
    def _load_custom_workflow(inputs: dict[str, Any]) -> dict:
        if inputs.get("workflow_json"):
            return json.loads(inputs["workflow_json"])
        return ComfyUIClient.load_workflow(Path(inputs["workflow_path"]))

    @staticmethod
    def _model_name(
        inputs: dict[str, Any], custom_workflow: bool, *, wants_h3: bool = False
    ) -> str:
        if wants_h3:
            return inputs.get("workflow_model") or "minimax-h3-i2v"
        if not custom_workflow:
            return "wan2.2-14b-fp8-4step"
        return (
            inputs.get("workflow_model")
            or inputs.get("model")
            or inputs.get("workflow_name")
            or "custom-comfyui-workflow"
        )

    @staticmethod
    def _workflow_provenance(
        inputs: dict[str, Any],
        custom_workflow: bool,
        output_node: str,
        operation: str,
        workflow: dict[str, Any],
        *,
        wants_h3: bool = False,
    ) -> dict[str, Any]:
        if not custom_workflow:
            if wants_h3:
                workflow_key = "minimax-h3-i2v"
                workflow_name = "minimax-h3-i2v.json"
            elif operation == "image_to_video":
                workflow_key = "wan22-i2v-4step"
                workflow_name = "wan22-i2v-4step.json"
            else:
                workflow_key = "wan22-t2v-4step"
                workflow_name = "wan22-t2v-4step.json"
            return {
                "source": "bundled",
                "workflow": workflow_name,
                "workflow_hash_sha256": workflow_hash(workflow),
                "model_stack": model_stack(workflow_key, inputs),
                "output_node": output_node,
            }
        return {
            "source": "user_supplied",
            "workflow_name": inputs.get("workflow_name"),
            "workflow_path": inputs.get("workflow_path"),
            "model": inputs.get("workflow_model") or inputs.get("model"),
            "workflow_hash_sha256": workflow_hash(workflow),
            "model_stack": model_stack(None, inputs),
            "model_stack_source": (
                "caller_supplied"
                if inputs.get("workflow_model_stack")
                else "unknown_custom_workflow"
            ),
            "output_node": output_node,
        }
