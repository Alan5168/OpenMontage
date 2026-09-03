"""Isolated H3 Turbo A/B, Ref2VA VRAM spike, Coverage previs, and PDD Acc A/B.

Does not call dispatch_cut, produce_keyframe, or compose_scene.
Does not patch the ship graph (minimax-h3-i2v.json stays 20-step, no LoRA, no PDD).
Does not set promote_to_production. Coverage views are not COMP_* / SHOT_KEYFRAME.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from lib.h3_context_ir import compile_h3_ir
from lib.h3_coverage_previs import (
    COVERAGE_HEIGHT,
    COVERAGE_LENGTH,
    COVERAGE_STEPS,
    COVERAGE_WIDTH,
    DEFAULT_COVERAGE_TARGET,
    ETHANFEL_VIEW_FRAMES,
    build_coverage_prompt,
    copy_scene_plate,
    extract_coverage_views,
    stitch_contact_sheet,
)
from lib.h3_runtime import (
    PDD_FL2VA_ACC_NAME,
    comfy_pdd_pin_ok,
    parse_comfy_version,
    pdd_fl2va_acc_path,
    pdd_workflow_path,
    ref2va_promote_path,
    ref2va_unet_path,
    ref2va_workflow_path,
    turbo_workflow_path,
)
from lib.h3_turbo_quality import (
    COMPARE_FRAMES,
    QUALITY_SPEC,
    copy_mcu_still,
    extract_compare_frames,
    stitch_compare_grid,
    stitch_quality_sheet,
)
from tools._comfyui.client import ComfyUIClient, ComfyUIError

JOB_DIR = Path(
    os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs")
) / "h3-capability-sandbox-v1"
SEED = 20260830
SHIP_WIDTH = 1344
SHIP_HEIGHT = 768
SPIKE_WIDTH = 864
SPIKE_HEIGHT = 480
TURBO_LENGTH = 124
SPIKE_LENGTH = 22
OUTPUT_NODE = "16"

_MICRO_SPEC = {
    "mode": "i2va",
    "style": "limited TV anime",
    "overview": "A still figure in a dim room. Only a shallow breath. Hands stay in frame.",
    "identity": {"name": "sandbox figure", "must": ["same face", "no costume change"]},
    "duration_seconds": 5,
    "width": SHIP_WIDTH,
    "height": SHIP_HEIGHT,
    "camera": "locked-off static",
    "shots": [
        {
            "t0": 0,
            "t1": 5,
            "framing": "medium close-up",
            "action": "Chest rises once. Fingers tighten. No walk. No smile. No camera move.",
            "camera": "locked-off static",
        }
    ],
    "audio": ["quiet room tone", "one restrained breath"],
    "avoid": ["smile", "push-in", "walk cycle", "new face"],
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_start_frame(dest: Path) -> Path:
    if dest.is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x2a2430:size={SHIP_WIDTH}x{SHIP_HEIGHT}:d=1",
                "-frames:v",
                "1",
                str(dest),
            ],
            check=True,
            capture_output=True,
        )
        return dest
    raise FileNotFoundError(f"Need {dest} or ffmpeg on PATH to make a sandbox start frame")


def vram_snapshot(client: ComfyUIClient) -> dict[str, Any]:
    try:
        resp = requests.get(f"{client.server_url}/system_stats", timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    devices = data.get("devices") or []
    rows = []
    for dev in devices:
        rows.append(
            {
                "name": dev.get("name"),
                "vram_total_mb": round((dev.get("vram_total") or 0) / (1024 * 1024), 1),
                "vram_free_mb": round((dev.get("vram_free") or 0) / (1024 * 1024), 1),
                "vram_used_mb": round(
                    ((dev.get("vram_total") or 0) - (dev.get("vram_free") or 0))
                    / (1024 * 1024),
                    1,
                ),
            }
        )
    return {"ok": True, "devices": rows}


def free_comfy_vram(client: ComfyUIClient) -> None:
    try:
        requests.post(
            f"{client.server_url}/free",
            json={"unload_models": True, "free_memory": True},
            timeout=30,
        )
    except Exception:
        pass
    time.sleep(2)


def nvidia_smi() -> dict[str, Any] | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    proc = subprocess.run(
        [
            exe,
            "--query-gpu=memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    used, total, util = [part.strip() for part in proc.stdout.strip().split(",")]
    return {
        "memory_used_mb": float(used),
        "memory_total_mb": float(total),
        "utilization": float(util),
    }


def _run_workflow(
    client: ComfyUIClient,
    workflow: dict[str, Any],
    dest: Path,
    *,
    timeout: int,
) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    before = {"comfy": vram_snapshot(client), "nvidia_smi": nvidia_smi()}
    t0 = time.perf_counter()
    peak_used = (before.get("nvidia_smi") or {}).get("memory_used_mb")
    try:
        paths = client.generate(workflow, OUTPUT_NODE, dest, timeout=timeout, interval=2)
        error = None
    except Exception as exc:
        paths = []
        error = str(exc)
    wall = round(time.perf_counter() - t0, 3)
    after = {"comfy": vram_snapshot(client), "nvidia_smi": nvidia_smi()}
    used = (after.get("nvidia_smi") or {}).get("memory_used_mb")
    if isinstance(used, (int, float)) and isinstance(peak_used, (int, float)):
        peak_used = max(peak_used, used)
    return {
        "ok": error is None and bool(paths),
        "error": error,
        "wall_s": wall,
        "timing": client.last_timing,
        "artifacts": [str(p) for p in paths],
        "vram_before": before,
        "vram_after": after,
        "nvidia_smi_peak_used_mb": peak_used,
    }


def run_turbo_ab(*, length: int = TURBO_LENGTH) -> dict[str, Any]:
    client = ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(client.unavailable_reason())
    frame = ensure_start_frame(JOB_DIR / "working" / "start_frame.png")
    staged = client.upload_image(frame, "h3_sandbox_start.png")
    prompt = compile_h3_ir(_MICRO_SPEC)["prompt"]
    out_dir = JOB_DIR / "working" / "turbo_ab"
    arms = [
        ("stock_20", turbo_workflow_path().with_name("minimax-h3-i2v.json"), 20, False),
        ("turbo_6", turbo_workflow_path(), 6, True),
        ("turbo_8", turbo_workflow_path(), 8, True),
    ]
    results: list[dict[str, Any]] = []
    for name, path, steps, _turbo in arms:
        workflow = ComfyUIClient.load_workflow(path)
        patches = {
            "3": {"device": "cpu"},
            "6": {"image": staged},
            "7": {
                "prompt": prompt,
                "width": SHIP_WIDTH,
                "height": SHIP_HEIGHT,
                "length": length,
            },
            "8": {"noise_seed": SEED},
            "10": {"steps": steps},
            "16": {"filename_prefix": f"sandbox_{name}"},
        }
        workflow = ComfyUIClient.patch_workflow(workflow, patches)
        dest = out_dir / f"{name}_len{length}.mp4"
        row = _run_workflow(client, workflow, dest, timeout=3600)
        row["arm"] = name
        row["steps"] = steps
        row["length"] = length
        row["seed"] = SEED
        results.append(row)
        if not row["ok"]:
            break
    receipt = {
        "schema_version": "h3-turbo-ab/v1",
        "job_id": "h3-capability-sandbox-v1",
        "ship_graph_unchanged": True,
        "turbo_in_ship_graph": False,
        "dispatch_cut": False,
        "seed": SEED,
        "length": length,
        "canvas": f"{SHIP_WIDTH}x{SHIP_HEIGHT}",
        "note": "Throughput/smoke. Sandbox still is not a SHOT_KEYFRAME. Not a quality verdict.",
        "started": _utc(),
        "arms": results,
    }
    _write_json(out_dir / "RECEIPT.json", receipt)
    return receipt


def run_ref2va_spike() -> dict[str, Any]:
    client = ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(client.unavailable_reason())
    free_comfy_vram(client)
    unet = ref2va_unet_path()
    graph = ref2va_workflow_path()
    frame = ensure_start_frame(JOB_DIR / "working" / "start_frame.png")
    staged = client.upload_image(frame, "h3_sandbox_start.png")
    prompt = (
        "For the target video, at 0.00 seconds into the target video, "
        "<Picture 1> (from [Shot 1]) is fully referenced.\n\n"
        "integrated_multimodal_description: [Shot 1] Limited TV anime. The figure in "
        "<Picture 1> holds still. One shallow breath. No walk. No smile.\n\n"
        "overall_soundscape: Quiet room tone.\n\n"
        "non_diegetic_music: N/A"
    )
    workflow = ComfyUIClient.load_workflow(graph)
    workflow = ComfyUIClient.patch_workflow(
        workflow,
        {
            "3": {"device": "cpu"},
            "6": {"image": staged},
            "7": {"prompt": prompt, "width": SPIKE_WIDTH, "height": SPIKE_HEIGHT, "length": SPIKE_LENGTH},
            "8": {"noise_seed": SEED},
            "16": {"filename_prefix": "sandbox_ref2va_spike"},
        },
    )
    dest = JOB_DIR / "working" / "ref2va_spike" / "spike.mp4"
    row = _run_workflow(client, workflow, dest, timeout=2400)
    smi = row.get("nvidia_smi_peak_used_mb")
    err = (row.get("error") or "").lower()
    oom = (not row["ok"]) and (
        "out of memory" in err or ("cuda" in err and "memory" in err)
    )
    fits = bool(row["ok"]) and isinstance(smi, (int, float)) and smi < 15360
    coverage_ok = bool(
        row["ok"] and not oom and isinstance(smi, (int, float)) and smi < 12000
    )
    receipt = {
        "schema_version": "h3-ref2va-16gb-spike/v1",
        "job_id": "h3-capability-sandbox-v1",
        "unet": str(unet) if unet else None,
        "workflow": str(graph),
        "canvas": f"{SPIKE_WIDTH}x{SPIKE_HEIGHT}",
        "length": SPIKE_LENGTH,
        "steps": 4,
        "ok": row["ok"],
        "oom": oom,
        "fits_16gb_hypothesis": fits,
        "promote_to_production": False,
        "coverage_allowed": coverage_ok,
        "note": (
            "Measurement only. promote_to_production stays false. "
            "Coverage previs may be queued later if ok and not OOM. "
            "Generated spike is not SHOT_KEYFRAME."
        ),
        "started": _utc(),
        "run": row,
    }
    spike_dir = JOB_DIR / "working" / "ref2va_spike"
    _write_json(spike_dir / "RECEIPT.json", receipt)
    promote = {
        "promote_to_production": False,
        "reason": "16GB spike is measurement-only until Alan promotes",
        "receipt": str(spike_dir / "RECEIPT.json"),
    }
    _write_json(ref2va_promote_path(), promote)
    return receipt


def run_coverage_previs() -> dict[str, Any]:
    """864×480 / 124-frame Ref2VA previs. Not COMP_*. Not SHOT_KEYFRAME. Not promote."""
    client = ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(client.unavailable_reason())
    free_comfy_vram(client)
    out_dir = JOB_DIR / "working" / "coverage_previs"
    plate = copy_scene_plate(out_dir / "scene_reference.jpg")
    staged = client.upload_image(Path(plate["dest"]), "h3_coverage_scene.jpg")
    prompt = build_coverage_prompt()
    graph = ref2va_workflow_path()
    workflow = ComfyUIClient.load_workflow(graph)
    workflow = ComfyUIClient.patch_workflow(
        workflow,
        {
            "3": {"device": "cpu"},
            "6": {"image": staged},
            "7": {
                "prompt": prompt,
                "width": COVERAGE_WIDTH,
                "height": COVERAGE_HEIGHT,
                "length": COVERAGE_LENGTH,
                "ref_image_size": "match",
            },
            "8": {"noise_seed": SEED},
            "10": {"steps": COVERAGE_STEPS},
            "16": {"filename_prefix": "sandbox_coverage_previs"},
        },
    )
    dest = out_dir / "coverage_124.mp4"
    started = _utc()
    row = _run_workflow(client, workflow, dest, timeout=3600)
    err = (row.get("error") or "").lower()
    oom = (not row["ok"]) and (
        "out of memory" in err or ("cuda" in err and "memory" in err)
    )
    views: list[str] = []
    sheet: str | None = None
    extract_error: str | None = None
    if row["ok"] and dest.is_file():
        try:
            view_paths = extract_coverage_views(dest, out_dir / "views")
            views = [str(p) for p in view_paths]
            sheet = str(stitch_contact_sheet(view_paths, out_dir / "contact_sheet.png"))
        except Exception as exc:
            extract_error = str(exc)
    receipt = {
        "schema_version": "h3-coverage-previs/v1",
        "job_id": "h3-capability-sandbox-v1",
        "workflow": str(graph),
        "official_ui_graph_not_queued": True,
        "canvas": f"{COVERAGE_WIDTH}x{COVERAGE_HEIGHT}",
        "length": COVERAGE_LENGTH,
        "steps": COVERAGE_STEPS,
        "seed": SEED,
        "coverage_target": DEFAULT_COVERAGE_TARGET,
        "ethanfel_view_frames": list(ETHANFEL_VIEW_FRAMES),
        "scene_plate": plate,
        "ok": row["ok"],
        "oom": oom,
        "promote_to_production": False,
        "dispatch_cut": False,
        "not_shot_keyframe": True,
        "not_comp_star": True,
        "anchor_bindings_status": "unbound",
        "note": (
            "Previs only. Human may pick COMP_* later from the contact sheet. "
            "Do not auto-bind. Do not treat views as SHOT_KEYFRAME. "
            "Official HF graph (1344×768 / 25-step / subgraph) was not queued."
        ),
        "started": started,
        "run": row,
        "views": views,
        "contact_sheet": sheet,
        "extract_error": extract_error,
    }
    _write_json(out_dir / "RECEIPT.json", receipt)
    return receipt


def run_turbo_quality(*, length: int = TURBO_LENGTH) -> dict[str, Any]:
    """Stock 20 vs Turbo 6/8 on a directed MCU copy. Ship graph unchanged."""
    client = ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(client.unavailable_reason())
    out_dir = JOB_DIR / "working" / "turbo_quality"
    plate = copy_mcu_still(out_dir / "picture1_a2_mcu.png")
    staged = client.upload_image(Path(plate["dest"]), "h3_turbo_quality_a2.png")
    prompt = compile_h3_ir(QUALITY_SPEC)["prompt"]
    arms = [
        ("stock_20", turbo_workflow_path().with_name("minimax-h3-i2v.json"), 20),
        ("turbo_6", turbo_workflow_path(), 6),
        ("turbo_8", turbo_workflow_path(), 8),
    ]
    results: list[dict[str, Any]] = []
    started = _utc()
    for name, path, steps in arms:
        free_comfy_vram(client)
        workflow = ComfyUIClient.load_workflow(path)
        workflow = ComfyUIClient.patch_workflow(
            workflow,
            {
                "3": {"device": "cpu"},
                "6": {"image": staged},
                "7": {
                    "prompt": prompt,
                    "width": SHIP_WIDTH,
                    "height": SHIP_HEIGHT,
                    "length": length,
                },
                "8": {"noise_seed": SEED},
                "10": {"steps": steps},
                "16": {"filename_prefix": f"sandbox_tq_{name}"},
            },
        )
        dest = out_dir / f"{name}_len{length}.mp4"
        row = _run_workflow(client, workflow, dest, timeout=3600)
        row["arm"] = name
        row["steps"] = steps
        row["length"] = length
        row["seed"] = SEED
        results.append(row)
        if not row["ok"]:
            break
    cells: list[str] = []
    sheet: str | None = None
    extract_error: str | None = None
    if all(bool(arm.get("ok")) for arm in results) and len(results) == 3:
        try:
            frame_paths: list[Path] = []
            for arm in results:
                video = Path(arm["artifacts"][0])
                frame_paths.extend(
                    extract_compare_frames(video, out_dir / "frames", str(arm["arm"]))
                )
            # extract order is arm-major (stock f0,f60,f120, turbo6 ..., turbo8 ...)
            # sheet wants time-major rows: f0 across arms, then f60, then f120
            by_arm = {
                arm["arm"]: frame_paths[i * len(COMPARE_FRAMES) : (i + 1) * len(COMPARE_FRAMES)]
                for i, arm in enumerate(results)
            }
            ordered: list[Path] = []
            for fi in range(len(COMPARE_FRAMES)):
                for arm in results:
                    ordered.append(by_arm[arm["arm"]][fi])
            sheet = str(stitch_quality_sheet(ordered, out_dir / "compare_3x3.png"))
            cells = [str(p) for p in ordered]
        except Exception as exc:
            extract_error = str(exc)
    receipt = {
        "schema_version": "h3-turbo-quality/v1",
        "job_id": "h3-capability-sandbox-v1",
        "ship_graph_unchanged": True,
        "turbo_in_ship_graph": False,
        "dispatch_cut": False,
        "legal_9x16_shot_keyframe": False,
        "legal_9x16_reason": (
            "vid-yt-chef-s1-v1 has briefs only. Identity 9x16 plates are "
            "IDENTITY_REFERENCE. Frozen S2/S1 stills not used."
        ),
        "picture1": plate,
        "canvas": f"{SHIP_WIDTH}x{SHIP_HEIGHT}",
        "length": length,
        "seed": SEED,
        "compare_frames": list(COMPARE_FRAMES),
        "note": (
            "Quality look on a directed 16:9 MCU copy at ship canvas. "
            "Not a 9:16 SHOT_KEYFRAME. Not a ship-graph promote."
        ),
        "started": started,
        "arms": results,
        "compare_cells": cells,
        "contact_sheet": sheet,
        "extract_error": extract_error,
    }
    _write_json(out_dir / "RECEIPT.json", receipt)
    return receipt


def comfy_version_from_stats(client: ComfyUIClient) -> tuple[str | None, tuple[int, int, int] | None]:
    try:
        resp = requests.get(f"{client.server_url}/system_stats", timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None, None
    raw = None
    system = data.get("system") if isinstance(data, dict) else None
    if isinstance(system, dict):
        raw = system.get("comfyui_version") or system.get("comfyui")
    parsed = parse_comfy_version(str(raw) if raw is not None else None)
    return (str(raw) if raw is not None else None), parsed


def pdd_node_loaded(client: ComfyUIClient) -> bool:
    try:
        resp = requests.get(
            f"{client.server_url}/object_info/MiniMaxH3PDDAccApply", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return False
    return "MiniMaxH3PDDAccApply" in data


def run_pdd_ab(*, length: int = TURBO_LENGTH) -> dict[str, Any]:
    """Stock 20 vs PDD Acc 8 on the same MCU copy. Isolated. No ship-graph promote."""
    client = ComfyUIClient()
    if not client.is_available():
        raise ComfyUIError(client.unavailable_reason())
    raw_version, parsed_version = comfy_version_from_stats(client)
    pin_ok, pin_note = comfy_pdd_pin_ok(parsed_version)
    out_dir = JOB_DIR / "working" / "pdd_001"
    plate = copy_mcu_still(out_dir / "picture1_a2_mcu.png")
    lora = pdd_fl2va_acc_path()
    blockers: list[str] = []
    if not pin_ok:
        blockers.append(pin_note)
    if not pdd_node_loaded(client):
        blockers.append(
            "MiniMaxH3PDDAccApply missing — restart Studio Comfy after cloning "
            "custom_nodes/ComfyUI-MiniMax-H3-PDD-Acc"
        )
    if lora is None:
        blockers.append(f"{PDD_FL2VA_ACC_NAME} missing under models/pdd_acc")
    if blockers:
        receipt = {
            "schema_version": "h3-pdd-ab/v1",
            "job_id": "h3-capability-sandbox-v1",
            "fixture": "PDD-001",
            "ok": False,
            "promote_to_production": False,
            "pdd_in_ship_graph": False,
            "turbo_in_ship_graph": False,
            "dispatch_cut": False,
            "legal_9x16_shot_keyframe": False,
            "comfyui_version": raw_version,
            "blockers": blockers,
            "picture1": plate,
            "pdd_file": str(lora) if lora else None,
        }
        _write_json(out_dir / "RECEIPT.json", receipt)
        return receipt
    staged = client.upload_image(Path(plate["dest"]), "h3_pdd_quality_a2.png")
    prompt = compile_h3_ir(QUALITY_SPEC)["prompt"]
    ship_path = turbo_workflow_path().with_name("minimax-h3-i2v.json")
    results: list[dict[str, Any]] = []
    started = _utc()
    arms = [
        ("stock_20", ship_path, {"10": {"steps": 20}}, 20),
        ("pdd_8", pdd_workflow_path(), {}, 8),
    ]
    for name, path, extra, steps in arms:
        free_comfy_vram(client)
        workflow = ComfyUIClient.load_workflow(path)
        patches: dict[str, Any] = {
            "3": {"device": "cpu"},
            "6": {"image": staged},
            "7": {
                "prompt": prompt,
                "width": SHIP_WIDTH,
                "height": SHIP_HEIGHT,
                "length": length,
            },
            "8": {"noise_seed": SEED},
            "16": {"filename_prefix": f"sandbox_pdd_{name}"},
        }
        patches.update(extra)
        workflow = ComfyUIClient.patch_workflow(workflow, patches)
        dest = out_dir / f"{name}_len{length}.mp4"
        row = _run_workflow(client, workflow, dest, timeout=3600)
        row["arm"] = name
        row["steps"] = steps
        row["length"] = length
        row["seed"] = SEED
        results.append(row)
        if not row["ok"]:
            break
    cells: list[str] = []
    sheet: str | None = None
    extract_error: str | None = None
    if all(bool(arm.get("ok")) for arm in results) and len(results) == 2:
        try:
            frame_paths: list[Path] = []
            for arm in results:
                video = Path(arm["artifacts"][0])
                frame_paths.extend(
                    extract_compare_frames(video, out_dir / "frames", str(arm["arm"]))
                )
            by_arm = {
                arm["arm"]: frame_paths[i * len(COMPARE_FRAMES) : (i + 1) * len(COMPARE_FRAMES)]
                for i, arm in enumerate(results)
            }
            ordered: list[Path] = []
            for fi in range(len(COMPARE_FRAMES)):
                for arm in results:
                    ordered.append(by_arm[arm["arm"]][fi])
            sheet = str(stitch_compare_grid(ordered, out_dir / "compare_2x3.png", n_cols=2))
            cells = [str(p) for p in ordered]
        except Exception as exc:
            extract_error = str(exc)
    receipt = {
        "schema_version": "h3-pdd-ab/v1",
        "job_id": "h3-capability-sandbox-v1",
        "fixture": "PDD-001",
        "ship_graph_unchanged": True,
        "pdd_in_ship_graph": False,
        "turbo_in_ship_graph": False,
        "promote_to_production": False,
        "dispatch_cut": False,
        "legal_9x16_shot_keyframe": False,
        "legal_9x16_reason": (
            "No legal 9:16 SHOT_KEYFRAME on disk. Same directed 16:9 MCU copy "
            "as turbo_quality (A2_mcu.png). Frozen S2/S1 unused."
        ),
        "picture1": plate,
        "canvas": f"{SHIP_WIDTH}x{SHIP_HEIGHT}",
        "length": length,
        "seed": SEED,
        "compare_frames": list(COMPARE_FRAMES),
        "comfyui_version": raw_version,
        "comfy_pin": pin_note,
        "pdd_file": str(lora),
        "pdd_recipe": {
            "sampler": "euler",
            "nfe": 8,
            "cfg": 1.0,
            "sigma_shift": [12.0, 3.0],
            "no_turbo": True,
            "no_easycache": True,
            "no_spectrum": True,
            "not_pdd_4": True,
        },
        "note": (
            "Isolated quality/speed/VRAM A/B. Success records a candidate only. "
            "Do not patch minimax-h3-i2v.json. Do not stack Turbo."
        ),
        "started": started,
        "arms": results,
        "compare_cells": cells,
        "contact_sheet": sheet,
        "extract_error": extract_error,
    }
    receipt["ok"] = all(bool(arm.get("ok")) for arm in results) and len(results) == 2
    _write_json(out_dir / "RECEIPT.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["turbo-ab", "ref2va-spike", "coverage-previs", "turbo-quality", "pdd-ab"],
    )
    parser.add_argument("--length", type=int, default=TURBO_LENGTH)
    args = parser.parse_args(argv)
    if args.command == "turbo-ab":
        payload = run_turbo_ab(length=args.length)
        ok = all(bool(arm.get("ok")) for arm in payload.get("arms") or [])
    elif args.command == "ref2va-spike":
        payload = run_ref2va_spike()
        ok = bool(payload.get("ok"))
    elif args.command == "coverage-previs":
        payload = run_coverage_previs()
        ok = bool(payload.get("ok"))
    elif args.command == "pdd-ab":
        payload = run_pdd_ab(length=args.length)
        ok = bool(payload.get("ok")) and not payload.get("blockers")
    else:
        payload = run_turbo_quality(length=args.length)
        ok = all(bool(arm.get("ok")) for arm in payload.get("arms") or [])
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
