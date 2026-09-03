from lib.runninghub_adapter import (
    RunningHubError,
    compile_runninghub,
    quote_runninghub,
    submit_task,
)
from lib.shot_render_package import (
    LIBTV_LAB_ONLY,
    XIAOYUNQUE_TEACHER_ONLY,
    ShotPackageError,
    compile_provider,
    frame_ref,
    pack_shot,
)


def _pkg(tmp_path, *, kind="DIRECTED_MCU_COPY"):
    still = tmp_path / "a2.png"
    still.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 32)
    return pack_shot(
        project_id="h3-capability-sandbox-v1",
        scene_id="sandbox_a2",
        shot_id="sandbox_a2_mcu",
        shot_intent="MCU hold.",
        duration_s=5,
        aspect_ratio="16:9",
        motion_obligation="PERFORMANCE",
        first_frame=frame_ref(kind=kind, path=still),
        render_policy={
            "stage": "DRAFT",
            "preferred_target": "local_h3",
            "fallback_targets": ["runninghub"],
            "profile": "rh_h3_fl2va_final_v1",
        },
        acceptance={"motion": "hold"},
    )


def test_identity_still_cannot_be_first_frame(tmp_path):
    try:
        _pkg(tmp_path, kind="IDENTITY_REFERENCE")
        raise AssertionError("should refuse identity as first_frame")
    except ShotPackageError as exc:
        assert "IDENTITY_REFERENCE" in str(exc)


def test_shot_keyframe_without_pixels_refused():
    try:
        pack_shot(
            project_id="p",
            scene_id="s",
            shot_id="x",
            shot_intent="wide",
            duration_s=5,
            aspect_ratio="9:16",
            motion_obligation="PERFORMANCE",
            first_frame={"kind": "SHOT_KEYFRAME", "asset_ref": None, "sha256": None},
            render_policy={"stage": "DRAFT", "preferred_target": "runninghub"},
            acceptance={"motion": "walk"},
        )
        raise AssertionError("empty SHOT_KEYFRAME should fail")
    except ShotPackageError as exc:
        assert "no pixels" in str(exc)


def test_xiaoyunque_and_libtv_compilers_refuse_api(tmp_path):
    package = _pkg(tmp_path)
    try:
        compile_provider(package, "xiaoyunque")
        raise AssertionError("xiaoyunque must stay teacher")
    except ShotPackageError as exc:
        assert "TEACHER" in str(exc)
        assert XIAOYUNQUE_TEACHER_ONLY[:20] in str(exc)
    try:
        compile_provider(package, "libtv")
        raise AssertionError("libtv must stay lab")
    except ShotPackageError as exc:
        assert LIBTV_LAB_ONLY[:12] in str(exc)


def test_runninghub_quote_requires_confirm_and_does_not_execute(tmp_path):
    package = _pkg(tmp_path)
    quote = quote_runninghub(package)
    assert quote["quoted"] is True
    assert quote["execute"] is False
    assert quote["requires_confirm"] is True
    assert quote["coins_unknown"] is True
    compiled = compile_runninghub(package)
    assert compiled["submit"] is False
    assert compiled["provider"] == "runninghub"


def test_submit_without_confirm_is_refused():
    try:
        submit_task(workflow_id="1", node_info_list=[], confirm=False, key="x")
        raise AssertionError("unconfirmed submit")
    except RunningHubError as exc:
        assert "requires_confirm" in str(exc)


def test_confirmed_submit_posts_create(monkeypatch):
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 0, "msg": "success", "data": {"taskId": "99", "taskStatus": "QUEUED"}}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr("lib.runninghub_adapter.requests.post", fake_post)
    out = submit_task(
        workflow_id="1904136902449209346",
        node_info_list=[{"nodeId": "6", "fieldName": "text", "fieldValue": "hold"}],
        confirm=True,
        key="test-key",
    )
    assert "task/openapi/create" in captured["url"]
    assert captured["json"]["workflowId"] == "1904136902449209346"
    assert out["data"]["taskId"] == "99"
