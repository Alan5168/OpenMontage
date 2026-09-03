"""Live H3 equipment — compile against what is on disk, not the wish.

Ref2VA **weights are public** (Hugging Face FL2VA/ + Ref2VA/, official Comfy
R2V). This file only answers whether a 16GB-fit runtime is **promoted** on
this PC. Weights on disk + a spike graph ≠ production. FenomAI's NVFP4 DiT
is ~12GB; the author does not guarantee a 16GB card.

FL2VA production keep-set is separate from Ref2VA. Official ComfyUI R2V
uses a different diffusion unet (`MiniMaxH3ReferenceToVideo`). Whether
Comfy unloads/offloads/caches those unets is runtime VRAM management,
not an architecture contract.

H3-Context-IR is a different, still-hosted component. Do not conflate it
with Ref2VA weights.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

REF2VA_UNET_NAMES = (
    "minimax_h3_ref2va_pruned_nvfp4.safetensors",
    "MiniMax_H3_REF2VA_pruned_nvfp4.safetensors",
    "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
)
R2VA_RUNTIME_UNAVAILABLE = (
    "COMPILE FAIL: R2VA_RUNTIME_UNAVAILABLE. "
    "Ref2VA weights are public; this PC has not promoted a 16GB-fit Ref2VA runtime. "
    "INTERACTION preferred_renderer=h3_ref2va capability_available=false. "
    "Need unet + MiniMaxH3ReferenceToVideo spike graph + promote_to_production receipt. "
    "Do not dispatch. Do not fall back to FL2VA and pretend it is Ref2VA."
)

_SANDBOX_PROMOTE = Path(
    r"C:\ContentStudio\jobs\h3-capability-sandbox-v1\working\ref2va_spike\PROMOTE.json"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ref2va_workflow_path() -> Path:
    return _repo_root() / "tools" / "_comfyui" / "workflows" / "minimax-h3-r2v.json"


def turbo_workflow_path() -> Path:
    return _repo_root() / "tools" / "_comfyui" / "workflows" / "minimax-h3-i2v-turbo.json"


PDD_FL2VA_ACC_NAME = "MiniMax-H3-FL2VA-Acc-8Step.safetensors"
PDD_REF2VA_ACC_NAME = "MiniMax-H3-Ref2VA-Acc-8Step.safetensors"
COMFY_PIN_MIN = (0, 33, 0)
COMFY_PIN_MAX_EXCLUSIVE = (0, 34, 0)
COMFY_PIN_PREFERRED = "v0.33.4"


def pdd_workflow_path() -> Path:
    return _repo_root() / "tools" / "_comfyui" / "workflows" / "minimax-h3-i2v-pdd.json"


def pdd_lora_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.environ.get("H3_PDD_MODELS_DIR")
    if override:
        roots.append(Path(override))
    roots.append(Path(r"C:\ContentStudio\runtime\ComfyUI\models\pdd_acc"))
    roots.append(Path(r"C:\models\h3-nvfp4\pdd_acc"))
    return roots


def pdd_fl2va_acc_path() -> Path | None:
    for root in pdd_lora_roots():
        candidate = root / PDD_FL2VA_ACC_NAME
        if candidate.is_file():
            return candidate
    return None


def parse_comfy_version(text: str | None) -> tuple[int, int, int] | None:
    if not text:
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def comfy_pdd_pin_ok(version: tuple[int, int, int] | None) -> tuple[bool, str]:
    """PDD Acc needs carried-audio (#15243). H3 masking is broken in 0.34+ (#15978)."""
    if version is None:
        return False, "comfyui_version missing from /system_stats"
    pretty = f"{version[0]}.{version[1]}.{version[2]}"
    if version < COMFY_PIN_MIN:
        return False, (
            f"PDD Acc needs ComfyUI {COMFY_PIN_PREFERRED} or newer "
            f"(carried-audio #15243). Current {pretty}. Do not jump to 0.34+."
        )
    if version >= COMFY_PIN_MAX_EXCLUSIVE:
        return False, (
            f"ComfyUI {pretty} is 0.34+ — H3 latent masking regression #15978. "
            f"Pin {COMFY_PIN_PREFERRED}."
        )
    return True, f"ComfyUI {pretty} is inside the PDD pin window ({COMFY_PIN_PREFERRED})"


def ref2va_promote_path() -> Path:
    override = os.environ.get("H3_REF2VA_PROMOTE_PATH")
    if override:
        return Path(override)
    return _SANDBOX_PROMOTE


def ref2va_model_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.environ.get("H3_MODELS_DIR") or os.environ.get("H3_REF2VA_MODELS_DIR")
    if override:
        roots.append(Path(override))
    roots.append(Path(r"C:\models\h3-nvfp4"))
    return roots


def ref2va_unet_path() -> Path | None:
    for root in ref2va_model_roots():
        for name in REF2VA_UNET_NAMES:
            for candidate in (root / "diffusion_models" / name, root / name):
                if candidate.is_file():
                    return candidate
    return None


def ref2va_promoted_to_production() -> bool:
    path = ref2va_promote_path()
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("promote_to_production") is True


def ref2va_runtime_available() -> bool:
    """True only after an explicit promote receipt. Spike graphs do not count."""
    return (
        ref2va_unet_path() is not None
        and ref2va_workflow_path().is_file()
        and ref2va_promoted_to_production()
    )
