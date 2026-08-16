from __future__ import annotations

import base64

from tools.base_tool import ToolStatus
from tools.graphics.agnes_image import AgnesImage
from tools.video.agnes_video import AgnesVideo
from tools.analysis.agnes_vision import AgnesVision


def test_agnes_tools_require_environment_key(monkeypatch) -> None:
    monkeypatch.delenv("AGNES_API_KEY", raising=False)
    assert AgnesImage().get_status() == ToolStatus.UNAVAILABLE
    assert AgnesVideo().get_status() == ToolStatus.UNAVAILABLE
    assert AgnesVision().get_status() == ToolStatus.UNAVAILABLE

    monkeypatch.setenv("AGNES_API_KEY", "test-only")
    assert AgnesImage().get_status() == ToolStatus.AVAILABLE
    assert AgnesVideo().get_status() == ToolStatus.AVAILABLE
    assert AgnesVision().get_status() == ToolStatus.AVAILABLE


def test_image_uses_current_model_and_edit_shape(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-only")
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    captured = {}

    def fake_request(method, path, body, *, timeout):
        captured.update(method=method, path=path, body=body, timeout=timeout)
        return {"data": [{"b64_json": base64.b64encode(b"image").decode("ascii")}]}

    monkeypatch.setattr("tools.agnes_api.request_json", fake_request)
    output = tmp_path / "out.png"
    result = AgnesImage().execute(
        {
            "prompt": "preserve layout, convert to ink anime",
            "generation_mode": "edit",
            "resolution": "2K",
            "aspect_ratio": "9:16",
            "image_path": str(source),
            "output_path": str(output),
        }
    )

    assert result.success is True
    assert output.read_bytes() == b"image"
    assert captured["path"] == "/v1/images/generations"
    assert captured["body"]["model"] == "agnes-image-2.1-flash"
    assert captured["body"]["size"] == "2K"
    assert captured["body"]["ratio"] == "9:16"
    assert captured["body"]["extra_body"]["image"][0].startswith("data:image/png;base64,")


def test_video_uses_videos_endpoint_and_metadata_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-only")
    calls = []

    def fake_request(method, path, body=None, *, timeout):
        calls.append((method, path, body))
        if method == "POST":
            assert body["model"] == "agnes-video-v2.0"
            assert body["num_frames"] == 121
            return {"task_id": "task-1", "video_id": "video-1"}
        return {
            "status": "completed",
            "seconds": "5.0",
            "size": "720x1280",
            "metadata": {"url": "https://example.invalid/result.mp4"},
        }

    def fake_download(url, output_path, *, timeout):
        assert url.endswith("result.mp4")
        output_path.write_bytes(b"video")

    monkeypatch.setattr("tools.agnes_api.request_json", fake_request)
    monkeypatch.setattr("tools.agnes_api.download", fake_download)
    output = tmp_path / "clip.mp4"
    result = AgnesVideo().execute(
        {
            "prompt": "subtle breathing, stable face",
            "operation": "image_to_video",
            "image_url": "https://example.invalid/keyframe.png",
            "aspect_ratio": "9:16",
            "duration": 5,
            "poll_interval_seconds": 0,
            "output_path": str(output),
        }
    )

    assert result.success is True
    assert output.read_bytes() == b"video"
    assert calls[0][1] == "/v1/videos"
    assert calls[0][2]["image"].endswith("keyframe.png")
    assert calls[1][1] == "/agnesapi?video_id=video-1"
    assert result.data["actual_size"] == "720x1280"


def test_video_keyframes_use_extra_body(monkeypatch) -> None:
    tool = AgnesVideo()
    payload, frames, fps = tool._payload(
        {
            "prompt": "smooth transition",
            "operation": "reference_to_video",
            "reference_image_urls": ["https://a/1.png", "https://a/2.png"],
            "num_frames": 81,
            "frame_rate": 24,
        }
    )
    assert frames == 81
    assert fps == 24
    assert payload["extra_body"] == {
        "image": ["https://a/1.png", "https://a/2.png"],
        "mode": "keyframes",
    }


def test_vision_uses_25_flash_and_writes_text(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-only")
    source = tmp_path / "frame.jpg"
    source.write_bytes(b"jpeg")
    captured = {}

    def fake_request(method, path, body, *, timeout):
        captured.update(path=path, body=body)
        return {"choices": [{"message": {"content": "OCR result"}}]}

    monkeypatch.setattr("tools.agnes_api.request_json", fake_request)
    output = tmp_path / "ocr.txt"
    result = AgnesVision().execute(
        {"operation": "ocr", "image_path": str(source), "output_path": str(output)}
    )

    assert result.success is True
    assert output.read_text(encoding="utf-8") == "OCR result"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["body"]["model"] == "agnes-2.5-flash"
    content = captured["body"]["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_registry_discovers_all_agnes_tools(monkeypatch) -> None:
    import tools.analysis.agnes_vision as vision_module
    import tools.graphics.agnes_image as image_module
    import tools.video.agnes_video as video_module
    from tools.tool_registry import ToolRegistry

    monkeypatch.setenv("AGNES_API_KEY", "test-only")
    registry = ToolRegistry()
    registry.register_module(image_module)
    registry.register_module(video_module)
    registry.register_module(vision_module)
    assert {"agnes_image", "agnes_video", "agnes_vision"}.issubset(registry.list_all())
