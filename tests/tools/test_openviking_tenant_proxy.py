from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "integrations"
    / "openviking-tenant-proxy"
    / "openviking_tenant_proxy.py"
)
SPEC = importlib.util.spec_from_file_location("openviking_tenant_proxy", MODULE_PATH)
assert SPEC and SPEC.loader
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)


def test_upstream_headers_pin_content_studio_tenant(monkeypatch):
    monkeypatch.delenv("OPENVIKING_ACCOUNT", raising=False)
    monkeypatch.delenv("OPENVIKING_USER", raising=False)
    monkeypatch.delenv("OPENVIKING_AGENT", raising=False)
    headers = proxy.build_upstream_headers(
        {"Accept": "application/json", "Host": "127.0.0.1:1934", "Connection": "keep-alive"},
        17,
    )
    assert headers["X-OpenViking-Account"] == "content-studio"
    assert headers["X-OpenViking-User"] == "alan"
    assert headers["X-OpenViking-Actor-Peer"] == "prime-agent"
    assert headers["Content-Length"] == "17"
    assert headers["Host"] == "127.0.0.1:1933"
    assert "Connection" not in headers


def test_upstream_headers_honor_explicit_identity(monkeypatch):
    monkeypatch.setenv("OPENVIKING_ACCOUNT", "another-account")
    monkeypatch.setenv("OPENVIKING_USER", "another-user")
    monkeypatch.setenv("OPENVIKING_AGENT", "another-peer")
    headers = proxy.build_upstream_headers({}, 0)
    assert headers["X-OpenViking-Account"] == "another-account"
    assert headers["X-OpenViking-User"] == "another-user"
    assert headers["X-OpenViking-Actor-Peer"] == "another-peer"
    assert "Content-Length" not in headers
