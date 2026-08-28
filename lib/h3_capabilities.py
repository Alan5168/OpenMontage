"""Fail-closed H3 capability selection for the Windows Content Studio.

This module compiles an already-approved motion route into deterministic
``video_selector`` inputs. It does not render, approve a cut, or infer rights.
Candidate capabilities must be requested explicitly and remain on the isolated
ComfyUI endpoint until their evidence gate is promoted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    _REPO_ROOT / "tools" / "_comfyui" / "workflows" / "h3" / "capabilities.json"
)
OWNED_REFERENCE_RIGHTS = frozenset({"owned", "licensed", "generated_owned"})


class H3CapabilityError(ValueError):
    """The requested capability is unknown or violates a hard gate."""


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise H3CapabilityError("unsupported H3 capability manifest")
    if not isinstance(payload.get("capabilities"), dict):
        raise H3CapabilityError("H3 capability manifest has no capabilities")
    return payload


def compile_dispatch(
    route_receipt: dict[str, Any],
    *,
    capability_id: str | None = None,
    reference_provenance: dict[str, Any] | None = None,
    adapter_gate_pass: bool = False,
    final_asset: bool = False,
    runtime_root: str | Path | None = None,
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    """Compile one legal I2V_HARD route to deterministic selector inputs."""
    if route_receipt.get("dispatch_class") != "I2V_HARD" or not route_receipt.get(
        "h3_allowed"
    ):
        raise H3CapabilityError("H3 dispatch requires an approved I2V_HARD route")

    manifest = load_manifest(manifest_path)
    selected = capability_id or manifest["default_capability_id"]
    try:
        capability = manifest["capabilities"][selected]
    except KeyError as exc:
        raise H3CapabilityError(f"unknown H3 capability: {selected}") from exc

    if capability.get("explicit_only") and capability_id is None:
        raise H3CapabilityError(f"candidate capability requires explicit selection: {selected}")
    if capability.get("requires_adapter_gate") and not adapter_gate_pass:
        raise H3CapabilityError(f"adapter gate has not passed for {selected}")
    if capability.get("previs_only") and final_asset:
        raise H3CapabilityError(f"previs capability cannot create final assets: {selected}")

    provenance = reference_provenance or {}
    rights = str(provenance.get("rights") or "").strip().lower()
    if capability.get("requires_reference_rights") and rights not in OWNED_REFERENCE_RIGHTS:
        raise H3CapabilityError(
            f"reference rights must be owned or licensed for {selected}; got {rights or 'missing'}"
        )

    workflow = capability.get("workflow")
    output_node = capability.get("output_node")
    if not workflow or not output_node:
        raise H3CapabilityError(f"capability has no pinned runnable workflow: {selected}")
    if not capability.get("api_runnable"):
        raise H3CapabilityError(
            f"capability workflow is not an API-format OM dispatch asset: {selected}"
        )

    workflow_path = _resolve_workflow_path(workflow, runtime_root=runtime_root)
    return {
        "preferred_provider": "comfyui",
        "operation": capability["operation"],
        "workflow_path": str(workflow_path.resolve()),
        "output_node": str(output_node),
        "workflow_name": selected,
        "workflow_model": selected,
        "workflow_model_stack": capability.get("model_stack", []),
        "workflow_capability_id": selected,
        "comfyui_server_url": manifest["endpoint"],
        "previs_only": bool(capability.get("previs_only")),
        "cut_id": route_receipt.get("cut_id"),
    }


def capability_health(
    capability_id: str,
    *,
    model_root: str | Path,
    runtime_root: str | Path | None = None,
    verify_hashes: bool = False,
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    """Check the pinned files for one H3 profile without starting ComfyUI."""
    manifest = load_manifest(manifest_path)
    try:
        capability = manifest["capabilities"][capability_id]
    except KeyError as exc:
        raise H3CapabilityError(f"unknown H3 capability: {capability_id}") from exc

    root = Path(model_root)
    missing: list[str] = []
    invalid: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    for item in capability.get("model_stack", []):
        target = root / item["file"]
        if not target.is_file():
            missing.append(str(target))
            continue
        size = target.stat().st_size
        row = {"path": str(target), "bytes": size}
        if size != int(item["bytes"]):
            row["expected_bytes"] = int(item["bytes"])
            invalid.append(row)
            continue
        if verify_hashes:
            digest = _sha256(target)
            row["sha256"] = digest
            if digest != item.get("sha256"):
                row["expected_sha256"] = item.get("sha256")
                invalid.append(row)
                continue
        checked.append(row)

    workflow = capability.get("workflow")
    workflow_path: Path | None = None
    if workflow:
        workflow_path = _resolve_workflow_path(workflow, runtime_root=runtime_root)
        if not workflow_path.is_file():
            missing.append(str(workflow_path))
        elif capability.get("workflow_sha256"):
            digest = _sha256(workflow_path)
            if digest != capability["workflow_sha256"]:
                invalid.append(
                    {
                        "path": str(workflow_path),
                        "sha256": digest,
                        "expected_sha256": capability["workflow_sha256"],
                    }
                )

    ready = not missing and not invalid and bool(workflow_path or not workflow)
    return {
        "capability_id": capability_id,
        "status": capability["status"],
        "ready": ready,
        "endpoint": manifest["endpoint"],
        "missing": missing,
        "invalid": invalid,
        "checked": checked,
        "previs_only": bool(capability.get("previs_only")),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_workflow_path(
    workflow: str, *, runtime_root: str | Path | None
) -> Path:
    relative = Path(workflow)
    if relative.parts and relative.parts[0] == "runtime" and runtime_root is not None:
        return Path(runtime_root).joinpath(*relative.parts[1:])
    return _REPO_ROOT / relative
