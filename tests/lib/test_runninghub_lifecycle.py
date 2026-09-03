"""RH-001 lifecycle is quote-legal and submit-gated. No live HTTP."""

from pathlib import Path

from lib.runninghub_adapter import (
    AUTH_PROFILE,
    RunningHubError,
    build_node_info_list,
    external_handle,
    file_name_from_upload,
    lifecycle_blockers,
    load_profile,
    run_lifecycle,
    select_output_url,
    submit_task,
)
from lib.shot_render_package import frame_ref, pack_shot, sha256_file


def _pkg(tmp_path: Path) -> dict:
    still = tmp_path / "a2.png"
    still.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 32)
    return pack_shot(
        project_id="rh-001-provider-lifecycle-v1",
        scene_id="sandbox_a2",
        shot_id="sandbox_a2_mcu",
        shot_intent="MCU hold.",
        duration_s=5,
        aspect_ratio="16:9",
        motion_obligation="PERFORMANCE",
        first_frame=frame_ref(kind="DIRECTED_MCU_COPY", path=still),
        render_policy={
            "stage": "DRAFT",
            "preferred_target": "runninghub",
            "profile": "rh_h3_fl2va_final_v1",
        },
        acceptance={"motion": "hold"},
        provider_prompt={"neutral_prompt": "Kitchen MCU. One breath. No smile."},
    )


def test_empty_profile_blocks_submit_and_quotes(tmp_path, monkeypatch):
    monkeypatch.delenv("RUNNINGHUB_API_KEY", raising=False)
    monkeypatch.delenv("RUNNINGHUB_WORKFLOW_ID", raising=False)
    package = _pkg(tmp_path)
    blockers = lifecycle_blockers()
    assert "workflow_id_missing" in blockers
    assert "first_frame_nodeId_missing" in blockers
    assert "workflow_api_json_sha256_missing" in blockers
    assert "RUNNINGHUB_API_KEY_missing" in blockers
    dest = tmp_path / "rh001"
    out = run_lifecycle(package, dest_dir=dest, confirm=False, submit=False)
    assert out["submit"] is False
    assert out["receipt"]["status"] == "QUOTED_AWAITING_SUBMIT"
    assert out["receipt"]["auth_profile"] == "runninghub_default"
    assert "api_key" not in out["receipt"]
    try:
        run_lifecycle(package, dest_dir=dest, confirm=True, submit=True)
        raise AssertionError("submit must refuse empty profile")
    except RunningHubError as exc:
        assert "blocked" in str(exc)


def test_external_handle_is_not_an_om_registry():
    row = external_handle(
        external_asset_id="api/abc.png",
        source_sha256="deadbeef",
        kind="first_frame",
    )
    assert row["provider"] == "runninghub"
    assert row["external_asset_id"] == "api/abc.png"
    assert row["source_sha256"] == "deadbeef"
    assert "registry" not in row


def test_upload_payload_file_name_and_node_info():
    name = file_name_from_upload(
        {"code": 0, "data": {"fileName": "api/abc.png", "fileType": "image"}}
    )
    assert name == "api/abc.png"
    package = {
        "provider_prompt": {"neutral_prompt": "hold"},
        "creative": {"duration_s": 5},
        "render_policy": {"profile": "rh_h3_fl2va_final_v1"},
    }
    profile = {
        "workflow_id": "1",
        "bindings": {
            "prompt": {"node_id": "6", "field": "text"},
            "first_frame": {"node_id": "14", "field": "image"},
        },
    }
    rows = build_node_info_list(
        package, profile=profile, first_frame_file_name=name
    )
    assert {"nodeId": "6", "fieldName": "text", "fieldValue": "hold"} in rows
    assert {"nodeId": "14", "fieldName": "image", "fieldValue": "api/abc.png"} in rows


def test_mocked_lifecycle_writes_hashed_output_and_handle(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNNINGHUB_API_KEY", "test-key")
    monkeypatch.setenv("RUNNINGHUB_WORKFLOW_ID", "1904136902449209346")
    package = _pkg(tmp_path)
    dest = tmp_path / "rh001"
    api_json = tmp_path / "API_WORKFLOW.json"
    api_json.write_text('{"export": "api", "nodes": {"6": {}, "14": {}}}\n', encoding="utf-8")
    digest = sha256_file(api_json)
    profile = {
        "workflow_id": "1904136902449209346",
        "workflow_api_json": str(api_json),
        "workflow_api_json_sha256": digest,
        "bindings": {
            "prompt": {"node_id": "6", "field": "text"},
            "first_frame": {"node_id": "14", "field": "image"},
        },
    }

    def fake_load(profile_id="rh_h3_fl2va_final_v1"):
        return profile

    monkeypatch.setattr("lib.runninghub_adapter.load_profile", fake_load)
    monkeypatch.setattr("lib.runninghub_adapter.api_key", lambda: "test-key")

    def fake_upload(path):
        assert Path(path).is_file()
        return {"code": 0, "data": {"fileName": "api/uploaded.png"}}

    def fake_create(*, workflow_id, node_info_list, confirm):
        assert confirm is True
        assert workflow_id == "1904136902449209346"
        assert any(row["fieldValue"] == "api/uploaded.png" for row in node_info_list)
        return {"code": 0, "data": {"taskId": "77"}}

    def fake_poll(*, task_id):
        assert task_id == "77"
        return {
            "code": 0,
            "data": [{"fileUrl": "https://example.invalid/out.mp4", "fileType": "mp4"}],
        }

    def fake_download(url, dest_path):
        Path(dest_path).write_bytes(b"fake-mp4")
        return Path(dest_path)

    out = run_lifecycle(
        package,
        dest_dir=dest,
        confirm=True,
        submit=True,
        upload=fake_upload,
        create=fake_create,
        poll=fake_poll,
        download=fake_download,
    )
    receipt = out["receipt"]
    blob = str(receipt)
    assert "test-key" not in blob
    assert "api_key" not in receipt
    assert receipt["auth_profile"] == AUTH_PROFILE
    assert receipt["workflow_id"] == "1904136902449209346"
    assert receipt["inputs"]["workflow_json_hash"] == digest
    assert out["submit"] is True
    assert receipt["status"] == "OUTPUT_RECEIVED"
    assert receipt["om_pass"] is False
    assert receipt["usage"]["rh_coins"] is None
    assert receipt["usage"]["wallet_usd"] is None
    assert isinstance(receipt["usage"]["wall_time_s"], float)
    assert receipt["output"]["duration_s"] is None
    handle = receipt["inputs"]["provider_handles"][0]
    assert handle["external_asset_id"] == "api/uploaded.png"
    assert handle["source_sha256"] == package["frames"]["first_frame"]["sha256"]
    assert (dest / "output.mp4").read_bytes() == b"fake-mp4"
    assert receipt["output"]["sha256"]


def test_workflow_hash_mismatch_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNNINGHUB_API_KEY", "test-key")
    api_json = tmp_path / "API_WORKFLOW.json"
    api_json.write_text('{"nodes": {}}\n', encoding="utf-8")
    profile = {
        "workflow_id": "1",
        "workflow_api_json": str(api_json),
        "workflow_api_json_sha256": "0" * 64,
        "bindings": {
            "first_frame": {"node_id": "14", "field": "image"},
            "prompt": {"node_id": "6", "field": "text"},
        },
    }
    monkeypatch.setattr("lib.runninghub_adapter.api_key", lambda: "test-key")
    monkeypatch.setattr("lib.runninghub_adapter.load_profile", lambda profile_id="x": profile)
    blockers = lifecycle_blockers(profile)
    assert "workflow_api_json_hash_mismatch" in blockers
    try:
        run_lifecycle(
            _pkg(tmp_path),
            dest_dir=tmp_path / "rh001",
            confirm=True,
            submit=True,
        )
        raise AssertionError("mismatch must fail closed")
    except RunningHubError as exc:
        assert "blocked" in str(exc)


def test_load_profile_rejects_yaml_secret(tmp_path, monkeypatch):
    (tmp_path / "rh_h3_fl2va_final_v1.yaml").write_text(
        "provider: runninghub\napi_key: rh_should_not_live_here\nworkflow_id: ''\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("lib.runninghub_adapter.PROFILE_DIR", tmp_path)
    try:
        load_profile()
        raise AssertionError("yaml key must be refused")
    except RunningHubError as exc:
        assert "YAML" in str(exc)


def test_select_output_prefers_mp4():
    url = select_output_url(
        {
            "code": 0,
            "data": [
                {"fileUrl": "https://x/a.png", "fileType": "image"},
                {"fileUrl": "https://x/out.mp4", "fileType": "mp4"},
            ],
        }
    )
    assert url.endswith("out.mp4")


def test_submit_without_confirm_still_refused():
    try:
        submit_task(workflow_id="1", node_info_list=[], confirm=False, key="x")
        raise AssertionError("unconfirmed submit")
    except RunningHubError as exc:
        assert "requires_confirm" in str(exc)
