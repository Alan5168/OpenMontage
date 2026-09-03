"""ComfyUI nodes for the shared local OpenViking context service."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener


ENDPOINT = os.environ.get("OPENVIKING_ENDPOINT", "http://127.0.0.1:1933").rstrip("/")
ACCOUNT = os.environ.get("OPENVIKING_ACCOUNT", "content-studio")
USER = os.environ.get("OPENVIKING_USER", "alan")
PEER = os.environ.get("OPENVIKING_AGENT", "comfyui")
_OPENER = build_opener(ProxyHandler({}))


def _request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "X-OpenViking-Account": ACCOUNT,
        "X-OpenViking-User": USER,
        "X-OpenViking-Actor-Peer": PEER,
    }
    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = Request(f"{ENDPOINT}{path}", data=data, headers=headers, method=method)
    with _OPENER.open(req, timeout=90) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected OpenViking response: {type(parsed).__name__}")
    return parsed


def _context_text(payload: dict[str, Any]) -> str:
    result = payload.get("result", payload)
    if not isinstance(result, dict):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines: list[str] = []
    for bucket in ("memories", "resources", "skills", "results", "items", "hits"):
        items = result.get(bucket)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            uri = str(item.get("uri", ""))
            score = item.get("score")
            summary = item.get("abstract") or item.get("overview") or item.get("content") or item.get("text") or ""
            prefix = f"[{bucket[:-1] if bucket.endswith('s') else bucket}] {uri}".strip()
            if score is not None:
                prefix += f" (score={score})"
            lines.append(f"{prefix}\n{summary}".strip())
    return "\n\n".join(lines)


class OpenVikingHealth:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status_json",)
    FUNCTION = "check"
    CATEGORY = "OpenViking"

    def check(self):
        return (json.dumps(_request("/health"), ensure_ascii=False, indent=2),)


class OpenVikingFind:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "query": ("STRING", {"multiline": True}),
                "target_uri": ("STRING", {"default": "viking://resources/content-studio/"}),
                "limit": ("INT", {"default": 5, "min": 1, "max": 20}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("context", "result_json")
    FUNCTION = "find"
    CATEGORY = "OpenViking"

    def find(self, query: str, target_uri: str, limit: int):
        payload = _request(
            "/api/v1/search/find",
            {
                "query": query,
                "target_uri": target_uri,
                "limit": limit,
                "include_provenance": True,
            },
        )
        return (
            _context_text(payload),
            json.dumps(payload, ensure_ascii=False, indent=2),
        )


class OpenVikingRead:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"uri": ("STRING", {"default": "viking://resources/"})}}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("content", "result_json")
    FUNCTION = "read"
    CATEGORY = "OpenViking"

    def read(self, uri: str):
        payload = _request(f"/api/v1/content/read?uri={quote(uri, safe='')}")
        result = payload.get("result", payload)
        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = result
        return (
            str(content),
            json.dumps(payload, ensure_ascii=False, indent=2),
        )


class OpenVikingRemember:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "content": ("STRING", {"multiline": True}),
                "category": (
                    ["preferences", "entities", "events", "cases", "patterns"],
                    {"default": "patterns"},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("uri", "result_json")
    FUNCTION = "remember"
    CATEGORY = "OpenViking"
    OUTPUT_NODE = True

    def remember(self, content: str, category: str):
        uri = (
            f"viking://user/{USER}/peers/{PEER}/memories/{category}/"
            f"mem_{uuid.uuid4().hex}.md"
        )
        payload = _request(
            "/api/v1/content/write",
            {
                "uri": uri,
                "content": content,
                "mode": "create",
                "wait": True,
                "timeout": 60,
                "processing_mode": "vectors_only",
            },
        )
        return (uri, json.dumps(payload, ensure_ascii=False, indent=2))


NODE_CLASS_MAPPINGS = {
    "OpenVikingHealth": OpenVikingHealth,
    "OpenVikingFind": OpenVikingFind,
    "OpenVikingRead": OpenVikingRead,
    "OpenVikingRemember": OpenVikingRemember,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenVikingHealth": "OpenViking Health",
    "OpenVikingFind": "OpenViking Find Context",
    "OpenVikingRead": "OpenViking Read URI",
    "OpenVikingRemember": "OpenViking Remember",
}
