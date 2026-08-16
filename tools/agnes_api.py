"""Small dependency-free client helpers for the Agnes AI provider tools."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_ORIGIN = "https://apihub.agnes-ai.com"


def api_key() -> str:
    value = os.environ.get("AGNES_API_KEY", "").strip()
    if not value:
        raise RuntimeError("AGNES_API_KEY is not configured")
    return value


def request_json(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: int = 120,
) -> dict[str, Any]:
    url = f"{API_ORIGIN}{path}"
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            parsed = json.loads(payload)
            if not isinstance(parsed, dict):
                raise RuntimeError("Agnes API returned a non-object JSON response")
            return parsed
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"Agnes API HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Agnes API network error: {exc.reason}") from exc


def file_to_data_uri(path_value: str) -> str:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input image not found: {path}")
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def download(url: str, output_path: Path, *, timeout: int = 180) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "OpenMontage/Agnes"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
