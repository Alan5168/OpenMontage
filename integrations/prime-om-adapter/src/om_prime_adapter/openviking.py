"""Read-only OpenViking access for Prime sessions launched by OpenMontage."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener


def _endpoint() -> str:
    return os.environ.get("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933").rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-OpenViking-Account": os.environ.get("OPENVIKING_ACCOUNT", "content-studio"),
        "X-OpenViking-User": os.environ.get("OPENVIKING_USER", "alan"),
        "X-OpenViking-Actor-Peer": os.environ.get("OPENVIKING_AGENT", "prime-agent"),
    }


def _request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{_endpoint()}{path}",
        data=data,
        headers=_headers(),
        method="POST" if data is not None else "GET",
    )
    # OpenViking is loopback-only. Never send its traffic through the user's
    # system proxy, especially when that proxy uses a SOCKS scheme.
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def openviking_health() -> dict[str, Any]:
    """Return the health of the shared local OpenViking service."""
    return _request("/health")


def search_openviking(
    query: str,
    target_uri: str = "viking://resources/content-studio/",
    limit: int = 8,
) -> dict[str, Any]:
    """Semantic-search shared context without mutating OM or OpenViking."""
    return _request(
        "/api/v1/search/find",
        {
            "query": query,
            "target_uri": target_uri,
            "limit": max(1, min(int(limit), 20)),
            "include_provenance": True,
        },
    )


def read_openviking(uri: str) -> dict[str, Any]:
    """Read a concrete viking:// URI returned by semantic search."""
    return _request(f"/api/v1/content/read?uri={quote(uri, safe='')}")
