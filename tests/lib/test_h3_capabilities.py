from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.h3_capabilities import H3CapabilityError, capability_health, compile_dispatch


ROUTE = {"cut_id": "c007", "dispatch_class": "I2V_HARD", "h3_allowed": True}


def test_default_compiles_to_comfyui_baseline():
    result = compile_dispatch(ROUTE, reference_provenance={"rights": "owned"})
    assert result["preferred_provider"] == "comfyui"
    assert result["workflow_capability_id"] == "h3.fl2va.base_nvfp4"
    assert result["comfyui_server_url"].endswith(":8190")


def test_non_hard_route_is_rejected():
    with pytest.raises(H3CapabilityError, match="I2V_HARD"):
        compile_dispatch(
            {"cut_id": "c1", "dispatch_class": "LIMITED", "h3_allowed": False},
            reference_provenance={"rights": "owned"},
        )


def test_reference_only_goodcase_is_rejected():
    with pytest.raises(H3CapabilityError, match="owned or licensed"):
        compile_dispatch(
            ROUTE,
            reference_provenance={"rights": "reference_only_not_for_render"},
        )


def test_ref2va_requires_adapter_gate_and_pinned_workflow():
    with pytest.raises(H3CapabilityError, match="adapter gate"):
        compile_dispatch(
            ROUTE,
            capability_id="h3.ref2va.nvfp4",
            reference_provenance={"rights": "owned"},
        )
    with pytest.raises(H3CapabilityError, match="pinned runnable workflow"):
        compile_dispatch(
            ROUTE,
            capability_id="h3.ref2va.nvfp4",
            reference_provenance={"rights": "owned"},
            adapter_gate_pass=True,
        )


def test_multishot_cannot_be_final_asset():
    with pytest.raises(H3CapabilityError, match="cannot create final assets"):
        compile_dispatch(
            ROUTE,
            capability_id="h3.ref2va.multishot_previs",
            reference_provenance={"rights": "licensed"},
            adapter_gate_pass=True,
            final_asset=True,
        )


def test_multishot_ui_workflow_cannot_be_dispatched_by_om():
    with pytest.raises(H3CapabilityError, match="not an API-format"):
        compile_dispatch(
            ROUTE,
            capability_id="h3.ref2va.multishot_previs",
            reference_provenance={"rights": "licensed"},
            adapter_gate_pass=True,
            final_asset=False,
        )


def test_health_is_profile_specific(tmp_path: Path):
    manifest = {
        "schema_version": "1.0",
        "default_capability_id": "test",
        "endpoint": "http://127.0.0.1:8190",
        "capabilities": {
            "test": {
                "status": "candidate",
                "previs_only": False,
                "model_stack": [
                    {"file": "diffusion_models/test.bin", "bytes": 4, "sha256": None}
                ],
                "workflow": None,
            }
        },
    }
    manifest_path = tmp_path / "capabilities.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = capability_health("test", model_root=tmp_path, manifest_path=manifest_path)
    assert result["ready"] is False
    target = tmp_path / "diffusion_models" / "test.bin"
    target.parent.mkdir()
    target.write_bytes(b"1234")
    result = capability_health("test", model_root=tmp_path, manifest_path=manifest_path)
    assert result["ready"] is True
