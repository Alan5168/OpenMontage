from __future__ import annotations

import sys
from pathlib import Path


ADAPTER_SRC = Path(__file__).resolve().parents[2] / "integrations" / "prime-om-adapter" / "src"
sys.path.insert(0, str(ADAPTER_SRC))

from om_prime_adapter import openviking as ov  # noqa: E402


def test_request_bypasses_proxy_and_sets_peer(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"status":"ok"}'

    class Opener:
        def open(self, request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

    def fake_build_opener(handler):
        captured["proxies"] = handler.proxies
        return Opener()

    monkeypatch.setattr(ov, "build_opener", fake_build_opener)
    monkeypatch.setenv("HTTP_PROXY", "socks5://127.0.0.1:9999")
    monkeypatch.setenv("OPENVIKING_AGENT", "prime-test")

    assert ov.openviking_health() == {"status": "ok"}
    assert captured["proxies"] == {}
    assert captured["request"].headers["X-openviking-account"] == "content-studio"
    assert captured["request"].headers["X-openviking-actor-peer"] == "prime-test"
    assert captured["timeout"] == 60


def test_search_is_read_only_and_clamps_limit(monkeypatch):
    calls = []

    def fake_request(path, payload=None):
        calls.append((path, payload))
        return {"result": []}

    monkeypatch.setattr(ov, "_request", fake_request)
    ov.search_openviking("identity lock", target_uri="viking://resources/content-studio/", limit=99)

    assert calls == [
        (
            "/api/v1/search/find",
            {
                "query": "identity lock",
                "target_uri": "viking://resources/content-studio/",
                "limit": 20,
                "include_provenance": True,
            },
        )
    ]
