from __future__ import annotations

import json

from lib.h3_runtime import (
    PDD_FL2VA_ACC_NAME,
    PDD_REF2VA_ACC_NAME,
    comfy_pdd_pin_ok,
    parse_comfy_version,
    pdd_workflow_path,
    ref2va_promote_path,
    ref2va_runtime_available,
    ref2va_unet_path,
    ref2va_workflow_path,
    turbo_workflow_path,
)


def test_turbo_shadow_graph_exists_and_is_not_the_ship_graph():
    turbo = json.loads(turbo_workflow_path().read_text(encoding="utf-8"))
    ship = json.loads(
        turbo_workflow_path().with_name("minimax-h3-i2v.json").read_text(encoding="utf-8")
    )
    assert turbo["18"]["class_type"] == "LoraLoaderModelOnly"
    assert "18" not in ship
    assert ship["10"]["inputs"]["steps"] == 20
    assert turbo["10"]["inputs"]["steps"] == 6
    r2v = json.loads(ref2va_workflow_path().read_text(encoding="utf-8"))
    assert r2v["1"]["inputs"]["unet_name"] == "minimax_h3_ref2va_pruned_nvfp4.safetensors"
    assert "ref_images.ref_image_0" in r2v["7"]["inputs"]


def test_ref2va_spike_graph_exists_without_promoting_production():
    assert ref2va_workflow_path().is_file()
    assert ref2va_runtime_available() is False


def test_fenomai_nvfp4_name_is_recognized(tmp_path, monkeypatch):
    unet = tmp_path / "diffusion_models" / "minimax_h3_ref2va_pruned_nvfp4.safetensors"
    unet.parent.mkdir(parents=True)
    unet.write_bytes(b"fake")
    monkeypatch.setenv("H3_MODELS_DIR", str(tmp_path))
    assert ref2va_unet_path() == unet
    assert ref2va_runtime_available() is False


def test_ref2va_runtime_true_only_with_promote_receipt(tmp_path, monkeypatch):
    unet = tmp_path / "diffusion_models" / "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
    unet.parent.mkdir(parents=True)
    unet.write_bytes(b"fake")
    monkeypatch.setenv("H3_MODELS_DIR", str(tmp_path))
    promote = tmp_path / "PROMOTE.json"
    promote.write_text('{"promote_to_production": true}', encoding="utf-8")
    monkeypatch.setenv("H3_REF2VA_PROMOTE_PATH", str(promote))
    monkeypatch.setattr(
        "lib.h3_runtime.ref2va_workflow_path",
        lambda: tmp_path / "minimax-h3-r2v.json",
    )
    (tmp_path / "minimax-h3-r2v.json").write_text("{}", encoding="utf-8")
    assert ref2va_runtime_available() is True
    assert ref2va_unet_path() == unet
    assert ref2va_promote_path() == promote


def test_pdd_shadow_graph_is_isolated_and_not_the_ship_graph():
    pdd = json.loads(pdd_workflow_path().read_text(encoding="utf-8"))
    ship = json.loads(
        turbo_workflow_path().with_name("minimax-h3-i2v.json").read_text(encoding="utf-8")
    )
    assert pdd["20"]["class_type"] == "MiniMaxH3PDDAccApply"
    assert pdd["20"]["inputs"]["pdd_file"] == PDD_FL2VA_ACC_NAME
    assert PDD_REF2VA_ACC_NAME not in json.dumps(pdd)
    assert pdd["9"]["inputs"]["sampler_name"] == "euler"
    assert pdd["11"]["inputs"]["model"] == ["20", 0]
    assert pdd["12"]["inputs"]["sigmas"] == ["20", 1]
    assert "10" not in pdd
    assert "MiniMaxH3PDDAccApply" not in json.dumps(ship)
    assert ship["9"]["inputs"]["sampler_name"] == "res_multistep"
    assert ship["10"]["inputs"]["steps"] == 20
    assert ship["11"]["inputs"]["model"] == ["2", 0]


def test_comfy_pdd_pin_rejects_031_and_034():
    assert parse_comfy_version("0.33.4") == (0, 33, 4)
    ok, _ = comfy_pdd_pin_ok((0, 33, 4))
    assert ok is True
    ok, note = comfy_pdd_pin_ok((0, 31, 0))
    assert ok is False
    assert "0.33.4" in note
    ok, note = comfy_pdd_pin_ok((0, 34, 0))
    assert ok is False
    assert "15978" in note
