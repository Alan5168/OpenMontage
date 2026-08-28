#!/usr/bin/env python3
"""Promote pinned Ref2VA assets into the isolated Windows H3 runtime.

The large model is downloaded separately with ``hf download``. This installer
verifies it before an atomic move, downloads the exact upstream multishot UI
workflow, preserves the raw file, and creates an NVFP4-adapted copy. It never
starts ComfyUI or changes the production 8188 runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen


REF2VA_BYTES = 12_528_636_800
REF2VA_SHA256 = "8eea02f43902e69904990c4405968d01a13c6656aa392d37ab80331e79b5df2f"
REF2VA_NAME = "minimax_h3_ref2va_pruned_nvfp4.safetensors"
WORKFLOW_REVISION = "7d4866c1dd99be30ced39855be3c06e4da0524e2"
WORKFLOW_NAME = "H3_Cinematic_Multishot_Coverage.json"
WORKFLOW_SHA256 = "9fe92e6f6fb6ab5abc217660ffee52335b40ab015a186ad24d55949d8dedd1fb"
WORKFLOW_URL = (
    "https://huggingface.co/ethanfel/H3_Cinematic_Multishot_Coverage/resolve/"
    f"{WORKFLOW_REVISION}/{WORKFLOW_NAME}"
)
UPSTREAM_MODEL = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_model_name(value: object) -> tuple[object, int]:
    if isinstance(value, str):
        count = value.count(UPSTREAM_MODEL)
        return value.replace(UPSTREAM_MODEL, REF2VA_NAME), count
    if isinstance(value, list):
        output: list[object] = []
        count = 0
        for item in value:
            replaced, seen = replace_model_name(item)
            output.append(replaced)
            count += seen
        return output, count
    if isinstance(value, dict):
        output_dict: dict[str, object] = {}
        count = 0
        for key, item in value.items():
            replaced, seen = replace_model_name(item)
            output_dict[key] = replaced
            count += seen
        return output_dict, count
    return value, 0


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-file", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()

    if not args.staging_file.is_file():
        raise SystemExit(f"missing staged Ref2VA model: {args.staging_file}")
    if args.staging_file.stat().st_size != REF2VA_BYTES:
        raise SystemExit("Ref2VA byte-size mismatch; staged file left untouched")
    digest = sha256(args.staging_file)
    if digest != REF2VA_SHA256:
        raise SystemExit("Ref2VA SHA-256 mismatch; staged file left untouched")

    target = args.model_root / "diffusion_models" / REF2VA_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.stat().st_size != REF2VA_BYTES or sha256(target) != REF2VA_SHA256:
            raise SystemExit(f"conflicting Ref2VA target exists: {target}")
    else:
        os.replace(args.staging_file, target)

    with urlopen(WORKFLOW_URL, timeout=60) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != WORKFLOW_SHA256:
        raise SystemExit("multishot workflow hash mismatch")

    raw_path = args.runtime_root / "h3" / "raw" / WORKFLOW_NAME
    atomic_bytes(raw_path, raw)
    payload = json.loads(raw.decode("utf-8"))
    adapted, replacements = replace_model_name(payload)
    if replacements < 1:
        raise SystemExit("upstream workflow did not contain the expected INT8 model name")
    adapted_path = args.runtime_root / "h3" / WORKFLOW_NAME
    adapted_bytes = json.dumps(adapted, ensure_ascii=False, indent=2).encode("utf-8")
    atomic_bytes(adapted_path, adapted_bytes)

    report = {
        "status": "ASSETS_INSTALLED_NOT_RUNTIME_PROVEN",
        "ref2va": {"path": str(target), "bytes": REF2VA_BYTES, "sha256": digest},
        "multishot_raw": {
            "path": str(raw_path),
            "revision": WORKFLOW_REVISION,
            "sha256": WORKFLOW_SHA256,
        },
        "multishot_nvfp4": {
            "path": str(adapted_path),
            "sha256": hashlib.sha256(adapted_bytes).hexdigest(),
            "model_name_replacements": replacements,
        },
        "runtime_proven": False,
        "production_promoted": False,
    }
    atomic_bytes(
        args.runtime_root / "h3" / "ASSET_INSTALL_RECEIPT.json",
        json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
