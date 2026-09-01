#!/usr/bin/env python3
"""Atomic multi-job hot handoff writer for Windows Content Studio."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator


DEFAULT_HOT_FILE = Path(
    r"C:\ContentStudio\context\openviking\user\alan\memories\hot\current_task_context.json"
)
HOT_URI = "viking://user/alan/memories/hot/current_task_context.json"
OV_BASE = "http://127.0.0.1:1933"
OV_HEADERS = {
    "X-OpenViking-Account": "content-studio",
    "X-OpenViking-User": "alan",
    "X-OpenViking-Actor-Peer": "end-task-studio-v2",
}
MAX_ACTIVE_HANDOFFS = 32
MAX_RECENT_CLOSED = 5
MAX_LIST_ITEMS = 24


class HotMemoryError(RuntimeError):
    """Fail-closed hot memory error."""


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _semantic_json_sha(text: str) -> str:
    """Hash JSON meaning; OpenViking strips the final newline on content/write."""

    value = json.loads(text)
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(canonical.encode("utf-8"))


def _unique_bounded(old: list[str], new: list[str]) -> list[str]:
    values: list[str] = []
    for item in [*old, *new]:
        value = str(item).strip()
        if value and value not in values:
            values.append(value)
    return values[-MAX_LIST_ITEMS:]


@contextlib.contextmanager
def _file_lock(lock_path: Path, timeout_seconds: float = 15.0) -> Iterator[None]:
    """Cross-platform one-byte advisory lock released automatically on process exit."""

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    try:
        while not acquired:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise HotMemoryError(f"timed out acquiring hot-memory lock: {lock_path}") from exc
                time.sleep(0.05)
        yield
    finally:
        if acquired:
            with contextlib.suppress(OSError):
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
    return content


def _legacy_entry(data: dict[str, Any]) -> dict[str, Any]:
    job_id = str(data.get("job_id") or "legacy-unscoped-task")
    timestamp = str(data.get("timestamp") or _now_iso())
    return {
        "job_id": job_id,
        "task": str(data.get("task") or job_id),
        "lane": str(data.get("lane") or "studio-infra"),
        "status": str(data.get("status") or "ACTIVE"),
        "summary": str(data.get("summary") or ""),
        "pending_gate": str(data.get("pending_gate") or "NONE"),
        "decisions_made": list(data.get("decisions_made") or []),
        "next_action": str(data.get("next_action") or ""),
        "pointers": list(data.get("pointers") or []),
        "source_writeback": str(data.get("source_writeback") or ""),
        "created_at": timestamp,
        "updated_at": timestamp,
        "saved_by": str(data.get("saved_by") or "legacy-writer"),
    }


def _load_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 2,
            "revision": 0,
            "updated_at": _now_iso(),
            "focus_job_id": None,
            "active_handoffs": {},
            "recent_closed": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HotMemoryError(f"invalid hot-memory JSON; refusing overwrite: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HotMemoryError("hot-memory root must be an object")
    if data.get("schema_version") != 2:
        entry = _legacy_entry(data)
        job_id = entry["job_id"]
        return {
            "schema_version": 2,
            "revision": 0,
            "updated_at": entry["updated_at"],
            "focus_job_id": job_id,
            "active_handoffs": {job_id: entry},
            "recent_closed": [],
        }
    if not isinstance(data.get("active_handoffs"), dict):
        raise HotMemoryError("active_handoffs must be an object")
    if not isinstance(data.get("recent_closed"), list):
        raise HotMemoryError("recent_closed must be an array")
    if not isinstance(data.get("revision"), int):
        raise HotMemoryError("revision must be an integer")
    return data


def _upsert_document(document: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    active = document["active_handoffs"]
    if args.job_id not in active and len(active) >= MAX_ACTIVE_HANDOFFS:
        raise HotMemoryError(
            f"active handoff limit {MAX_ACTIVE_HANDOFFS} reached; close stale tasks explicitly"
        )
    old = active.get(args.job_id, {})
    now = _now_iso()
    entry = {
        "job_id": args.job_id,
        "task": args.task,
        "lane": args.lane,
        "status": args.status,
        "summary": args.summary,
        "pending_gate": args.gate or "NONE",
        "decisions_made": _unique_bounded(old.get("decisions_made", []), args.decision or []),
        "next_action": args.next_action,
        "pointers": _unique_bounded(old.get("pointers", []), args.pointer or []),
        "source_writeback": args.source_writeback or old.get("source_writeback", ""),
        "created_at": old.get("created_at", now),
        "updated_at": now,
        "saved_by": args.saved_by,
    }
    active[args.job_id] = entry
    document["revision"] += 1
    document["updated_at"] = now
    if args.set_focus or document.get("focus_job_id") not in active:
        document["focus_job_id"] = args.job_id
    return document


def _close_document(document: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    active = document["active_handoffs"]
    if args.job_id not in active:
        raise HotMemoryError(f"cannot close unknown active job: {args.job_id}")
    now = _now_iso()
    closed = dict(active.pop(args.job_id))
    closed.update({"status": "CLOSED", "closed_at": now, "close_reason": args.reason})
    recent = [item for item in document["recent_closed"] if item.get("job_id") != args.job_id]
    document["recent_closed"] = ([closed] + recent)[:MAX_RECENT_CLOSED]
    if document.get("focus_job_id") == args.job_id:
        ordered = sorted(active.values(), key=lambda item: item.get("updated_at", ""), reverse=True)
        document["focus_job_id"] = ordered[0]["job_id"] if ordered else None
    document["revision"] += 1
    document["updated_at"] = now
    return document


def _request_json(url: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = dict(OV_HEADERS)
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=130) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise HotMemoryError(f"OpenViking HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise HotMemoryError(f"OpenViking request failed: {type(exc).__name__}: {exc}") from exc


def _sync_and_verify(content: bytes) -> dict[str, Any]:
    text = content.decode("utf-8")
    write_url = f"{OV_BASE}/api/v1/content/write"
    write_payload = {
        "uri": HOT_URI,
        "content": text,
        "mode": "replace",
        "wait": True,
        "timeout": 120,
        "processing_mode": "vectors_only",
    }
    try:
        write_result = _request_json(write_url, payload=write_payload)
    except HotMemoryError as exc:
        if "404" not in str(exc) and "NOT_FOUND" not in str(exc):
            raise
        write_payload["mode"] = "create"
        write_result = _request_json(write_url, payload=write_payload)

    read_url = f"{OV_BASE}/api/v1/content/read?uri={urllib.parse.quote(HOT_URI, safe='')}"
    read_result = _request_json(read_url)
    remote_content = read_result.get("result")
    if not isinstance(remote_content, str):
        raise HotMemoryError("OpenViking readback did not return string content")
    local_sha = _semantic_json_sha(text)
    remote_sha = _semantic_json_sha(remote_content)
    if local_sha != remote_sha:
        raise HotMemoryError(
            f"OpenViking semantic readback hash mismatch: local={local_sha} remote={remote_sha}"
        )
    return {"write_result": write_result.get("status"), "remote_semantic_sha256": remote_sha}


def _write_mutation(path: Path, mutate: Any) -> tuple[dict[str, Any], bytes]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    with _file_lock(lock_path):
        document = _load_document(path)
        updated = mutate(document)
        content = _atomic_write_json(path, updated)
    return updated, content


def _receipt(
    document: dict[str, Any], content: bytes, path: Path, ov_verified: bool, error: str | None = None
) -> dict[str, Any]:
    return {
        "status": "PASS_HOT_WRITE" if ov_verified else "PARTIAL_HOT_SYNC_FAILED",
        "hot_write": {
            "file": str(path),
            "uri": HOT_URI,
            "revision": document["revision"],
            "sha256": _sha256_bytes(content),
            "active_handoff_count": len(document["active_handoffs"]),
            "focus_job_id": document.get("focus_job_id"),
            "ov_verified": ov_verified,
            "error": error,
        },
    }


def _add_common_file_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--hot-file", type=Path, default=DEFAULT_HOT_FILE, help=argparse.SUPPRESS)
    parser.add_argument("--no-sync", action="store_true", help=argparse.SUPPRESS)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Content Studio end-task hot handoff")
    sub = parser.add_subparsers(dest="command", required=True)

    upsert = sub.add_parser("upsert", help="atomically upsert one active handoff")
    upsert.add_argument("--task", required=True)
    upsert.add_argument("--job-id", required=True)
    upsert.add_argument("--lane", default="content-production")
    upsert.add_argument("--status", default="ACTIVE")
    upsert.add_argument("--summary", required=True)
    upsert.add_argument("--gate", "--pending-gate", dest="gate", default="NONE")
    upsert.add_argument("--next-action", required=True)
    upsert.add_argument("--source-writeback", default="")
    upsert.add_argument("--decision", action="append")
    upsert.add_argument("--pointer", action="append")
    upsert.add_argument("--saved-by", default=os.environ.get("CONTENT_STUDIO_FRONTEND", "unknown-frontend"))
    upsert.add_argument("--set-focus", action="store_true")
    _add_common_file_flags(upsert)

    close = sub.add_parser("close", help="move one active handoff to bounded recent_closed")
    close.add_argument("--job-id", required=True)
    close.add_argument("--reason", required=True)
    _add_common_file_flags(close)

    show = sub.add_parser("show", help="show local hot index")
    show.add_argument("--hot-file", type=Path, default=DEFAULT_HOT_FILE, help=argparse.SUPPRESS)

    verify = sub.add_parser("verify", help="verify local content against OpenViking readback")
    verify.add_argument("--hot-file", type=Path, default=DEFAULT_HOT_FILE, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Backward compatibility with the legacy script's no-subcommand invocation.
    if argv and argv[0] not in {"upsert", "close", "show", "verify", "-h", "--help"}:
        argv.insert(0, "upsert")
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "show":
            print(json.dumps(_load_document(args.hot_file), ensure_ascii=False, indent=2))
            return 0
        if args.command == "verify":
            content = args.hot_file.read_bytes()
            document = _load_document(args.hot_file)
            _sync_and_verify(content)
            print(json.dumps(_receipt(document, content, args.hot_file, True), ensure_ascii=False, indent=2))
            return 0
        if args.command == "upsert":
            document, content = _write_mutation(args.hot_file, lambda doc: _upsert_document(doc, args))
        else:
            document, content = _write_mutation(args.hot_file, lambda doc: _close_document(doc, args))

        if args.no_sync:
            result = _receipt(document, content, args.hot_file, False, "sync explicitly disabled")
            result["status"] = "PASS_LOCAL_ONLY"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        try:
            _sync_and_verify(content)
        except HotMemoryError as exc:
            print(json.dumps(_receipt(document, content, args.hot_file, False, str(exc)), ensure_ascii=False, indent=2))
            return 3
        print(json.dumps(_receipt(document, content, args.hot_file, True), ensure_ascii=False, indent=2))
        return 0
    except (HotMemoryError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL_HOT_WRITE", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
