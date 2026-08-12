"""Path allowlist, secret scan, and fail-closed helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

DEFAULT_WINDOWS_ROOT = Path(r"C:\ContentStudio")
SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|access[_-]?token|secret|password|passwd|authorization|cookie|credential|private[_-]?key)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|bearer\s+[A-Za-z0-9\-_.]+|eyJ[A-Za-z0-9_-]{20,})",
    re.I,
)
MEDIA_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".wav",
    ".mp3",
    ".aac",
    ".flac",
    ".safetensors",
    ".ckpt",
    ".pt",
    ".bin",
    ".onnx",
}


class AdapterError(RuntimeError):
    pass


def authorized_root() -> Path:
    override = os.environ.get("OM_PRIME_ADAPTER_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    if DEFAULT_WINDOWS_ROOT.exists():
        return DEFAULT_WINDOWS_ROOT.resolve()
    raise AdapterError(
        "Authorized Content Studio root is missing. Set OM_PRIME_ADAPTER_ROOT for tests."
    )


def resolve_authorized(path: str | Path, *, root: Path | None = None) -> Path:
    root = (root or authorized_root()).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AdapterError(f"Path escapes authorized root {root}: {path}") from exc
    return resolved


def jobs_dir(root: Path | None = None) -> Path:
    root = (root or authorized_root()).resolve()
    return root / "jobs"


def casebook_dir(root: Path | None = None) -> Path:
    root = (root or authorized_root()).resolve()
    return root / "runtime" / "prime-rlm-pilot" / "fixtures" / "casebook"


def scan_secrets(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_s = str(key)
            if SECRET_KEY_RE.search(key_s):
                raise AdapterError(f"Secret-like key refused at {path}.{key_s}")
            scan_secrets(item, path=f"{path}.{key_s}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            scan_secrets(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and SECRET_VALUE_RE.search(value):
        raise AdapterError(f"Secret-like value refused at {path}")


def reject_media_payload(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            reject_media_payload(item)
        return
    if isinstance(value, list):
        for item in value:
            reject_media_payload(item)
        return
    if isinstance(value, str):
        suffix = Path(value).suffix.lower()
        if suffix in MEDIA_SUFFIXES and ("base64" in value.lower() or len(value) > 4096):
            raise AdapterError("Binary or media payload refused; store path/hash only")


def display_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
