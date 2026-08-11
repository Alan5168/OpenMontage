from __future__ import annotations

import base64
import json

from tools.base_tool import ToolStatus
from tools.graphics.doubao_seedream import DoubaoSeedream


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_status_requires_only_agentplan_key(monkeypatch) -> None:
    monkeypatch.delenv("ARK_AGENTPLAN_API_KEY", raising=False)
    assert DoubaoSeedream().get_status() == ToolStatus.UNAVAILABLE
    monkeypatch.setenv("ARK_AGENTPLAN_API_KEY", "test-only")
    assert DoubaoSeedream().get_status() == ToolStatus.AVAILABLE


def test_generation_records_sceneplan_provenance(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ARK_AGENTPLAN_API_KEY", "test-only")
    image = b"fixture-png"

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/images/generations")
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["model"] == "doubao-seedream-5.0-lite"
        assert payload["seed"] == 42
        return FakeResponse({
            "request_id": "req-fixture",
            "usage": {"images": 1},
            "data": [{"b64_json": base64.b64encode(image).decode("ascii")}],
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    output = tmp_path / "nested" / "ref.png"
    result = DoubaoSeedream().execute({
        "prompt": "textless layout",
        "seed": 42,
        "size": "1080x1920",
        "response_format": "b64_json",
        "output_path": str(output),
    })
    assert result.success is True
    assert output.read_bytes() == image
    assert result.data["request_id"] == "req-fixture"
    assert len(result.data["output_hashes"][0]) == 64
    assert result.data["license_policy"]
