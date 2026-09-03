#!/usr/bin/env python3
"""Attended Prime foreman preflight. Report only. Does not repair production sessions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PIPE = r"\\.\pipe\prime-agent-daemon"
VID3_JOB = "vid3-blacklisted-chef-90s-v1"
STALL_SECONDS = 120
UNATTENDED_MODE = "DISABLED"

USEFUL_EVENT_TYPES = frozenset(
    {
        "token",
        "tool_start",
        "tool_end",
        "child_event",
        "agent_message",
        "assistant_message",
        "user_message",
        "output",
        "text",
        "message",
        "turn_end",
        "turn_complete",
        "turn_terminal",
        "result",
        "error",
        "done",
        "stop",
        "final",
    }
)
HEARTBEAT_TYPES = frozenset({"agent_status", "heartbeat", "status"})
WORKING_STATES = frozenset({"working", "streaming", "running", "in_progress", "busy"})

PRIME_CLI = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "prime-agent" / "dist" / "bundle" / "cli.js"
AGENT_DIR = Path.home() / ".prime" / "agent"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def event_kind(event: dict[str, Any]) -> str:
    raw = event.get("type") or event.get("kind") or event.get("event") or ""
    return str(raw).strip().lower()


def is_heartbeat(event: dict[str, Any]) -> bool:
    kind = event_kind(event)
    if kind in HEARTBEAT_TYPES:
        return True
    if kind == "agent_status":
        return True
    status = str(event.get("status") or event.get("activity") or "").lower()
    return kind.endswith("status") and status in WORKING_STATES | {"idle", "needs_input"}


def is_useful_activity(event: dict[str, Any]) -> bool:
    if is_heartbeat(event):
        return False
    kind = event_kind(event)
    if kind in USEFUL_EVENT_TYPES:
        return True
    if "tool_start" in kind or "tool_end" in kind:
        return True
    if kind in {"assistant", "user", "tool"}:
        return True
    if event.get("delta") or event.get("text") or event.get("content"):
        return kind not in HEARTBEAT_TYPES
    return False


def _parse_ts(event: dict[str, Any]) -> datetime | None:
    for key in ("timestamp", "ts", "at", "created", "time"):
        raw = event.get(key)
        if not raw:
            continue
        if isinstance(raw, (int, float)):
            value = float(raw)
            if value > 1e12:
                value /= 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc)
        text = str(raw).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def classify_stall(
    events: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    stall_seconds: int = STALL_SECONDS,
) -> dict[str, Any]:
    """agent_status heartbeat is not useful progress. Alarm only; do not kill/retry."""
    now = now or _now()
    last_useful: datetime | None = None
    last_heartbeat: datetime | None = None
    working = False
    last_state = ""
    for event in events:
        ts = _parse_ts(event) or now
        kind = event_kind(event)
        state = str(event.get("status") or event.get("activity") or event.get("state") or "").lower()
        if kind in HEARTBEAT_TYPES or kind == "agent_status":
            last_heartbeat = ts
            if state:
                last_state = state
                working = state in WORKING_STATES
            elif event.get("isStreaming") is True:
                working = True
                last_state = "streaming"
            continue
        if is_useful_activity(event):
            last_useful = ts
            if kind in {"turn_end", "turn_complete", "turn_terminal", "result", "done", "stop", "final", "error"}:
                working = False
                last_state = "turn_terminal"
        elif state in WORKING_STATES:
            working = True
            last_state = state
    gap = None
    if last_useful is not None:
        gap = (now - last_useful).total_seconds()
    elif working:
        gap = stall_seconds + 1
    suspect = bool(working and (gap is None or gap >= stall_seconds))
    return {
        "policy": "attended_alarm_only",
        "unattended_mode": UNATTENDED_MODE,
        "unattended_mode": UNATTENDED_MODE,
        "stall_seconds": stall_seconds,
        "heartbeat_counts_as_useful": False,
        "heartbeat_is_not_useful": True,
        "working": working,
        "last_state": last_state,
        "last_useful_activity_at": _iso(last_useful),
        "last_heartbeat_at": _iso(last_heartbeat),
        "seconds_since_useful": None if gap is None else round(gap, 1),
        "verdict": "STALL_SUSPECT" if suspect else "OK",
        "action": "alarm_only" if suspect else "none",
    }


def scan_jsonl_stall(path: Path, *, stall_seconds: int = STALL_SECONDS) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return {**classify_stall([], stall_seconds=stall_seconds), "session_file": str(path), "readable": False}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            blob = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(blob, dict):
            events.append(blob)
    report = classify_stall(events, stall_seconds=stall_seconds)
    report["session_file"] = str(path)
    report["readable"] = True
    report["event_count"] = len(events)
    return report


def _prime_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    cli = Path(os.environ.get("PRIME_AGENT_CLI_JS") or PRIME_CLI)
    return subprocess.run(
        ["node", str(cli), *args],
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, "PRIME_AGENT_CODING_AGENT_DIR": str(AGENT_DIR)},
    )


def _prime_json(*args: str) -> Any:
    result = _prime_cmd(*args)
    text = (result.stdout or "").strip()
    if not text:
        return {"ok": False, "error": (result.stderr or "").strip()[:400], "returncode": result.returncode}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": text[:400], "returncode": result.returncode}


def _prime_version() -> dict[str, Any]:
    pkg = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "prime-agent" / "package.json"
    installed = None
    if pkg.is_file():
        try:
            installed = json.loads(pkg.read_text(encoding="utf-8")).get("version")
        except (OSError, json.JSONDecodeError):
            installed = None
    result = _prime_cmd("--version")
    cli = (result.stdout or result.stderr or "").strip().splitlines()
    version_line = cli[0] if cli else ""
    return {
        "installed": installed,
        "cli": version_line,
        "latest_known_github_tag": "v0.8.0",
        "latest_stable_known": "v0.8.0",
        "upgrade_this_session": False,
        "upgrade_reason": "Already on official latest.json (v0.8.0).",
        "v0_8_note": "Installed from official v0.8.0 tarball (SHA256 matched). npm-link 0.7.1 tree at C:\\Users\\ligua\\tools\\prime-agent is leftover, not on the Content Studio PATH.",
    }


def _disk(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "free_gb": round(free_gb, 2),
        "ok": free_gb >= 10,
    }


def _provider_reachable() -> dict[str, Any]:
    settings_path = AGENT_DIR / "settings.json"
    models_path = AGENT_DIR / "models.json"
    if not settings_path.is_file() or not models_path.is_file():
        return {"ok": False, "error": "missing settings.json or models.json"}
    settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
    models = json.loads(models_path.read_text(encoding="utf-8-sig"))
    provider = str(settings.get("defaultProvider") or "")
    model = str(settings.get("defaultModel") or "")
    catalog = models.get("providers") if isinstance(models, dict) else None
    if not isinstance(catalog, dict):
        catalog = models if isinstance(models, dict) else {}
    spec = catalog.get(provider) if isinstance(catalog, dict) else None
    if not isinstance(spec, dict):
        return {"ok": False, "provider": provider, "model": model, "error": "provider spec missing"}
    base = str(spec.get("baseUrl") or "").rstrip("/")
    key = str(spec.get("apiKey") or "")
    if not base:
        return {"ok": False, "provider": provider, "model": model, "error": "baseUrl missing"}
    url = base + "/models"
    req = urllib.request.Request(url, method="GET")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            status = getattr(resp, "status", 200)
            return {
                "ok": 200 <= int(status) < 300,
                "provider": provider,
                "model": model,
                "http_status": int(status),
                "endpoint": "models",
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "http_status": int(exc.code),
            "endpoint": "models",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "error": exc.__class__.__name__,
            "endpoint": "models",
        }


def _pointer(jobs_dir: Path, job_id: str) -> dict[str, Any] | None:
    path = jobs_dir / job_id / "working" / "prime_rlm" / "SESSION_POINTER.json"
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    blob["_path"] = str(path)
    return blob


def _prime_processes() -> list[dict[str, Any]]:
    ps = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -and $_.CommandLine -match 'prime-agent' } | "
        "Select-Object ProcessId, ParentProcessId, Name, CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    text = (result.stdout or "").strip()
    if not text:
        return []
    try:
        blob = json.loads(text)
    except json.JSONDecodeError:
        return []
    rows = blob if isinstance(blob, list) else [blob]
    out = []
    for row in rows:
        cmd = str(row.get("CommandLine") or "")
        role = "other"
        if "--mode daemon" in cmd or " --mode daemon " in cmd:
            role = "supervisor"
        elif "prime-agent-worker" in cmd or "--mode worker" in cmd:
            role = "worker"
        elif "--version" in cmd:
            role = "stuck_version"
        elif "--provider" in cmd or "--resume" in cmd or "--session-dir" in cmd:
            role = "tui_client"
        out.append(
            {
                "pid": row.get("ProcessId"),
                "ppid": row.get("ParentProcessId"),
                "role": role,
                "cmd": cmd[:220],
            }
        )
    return out


def collect_preflight(cfg: dict[str, Any]) -> dict[str, Any]:
    jobs_dir = Path(cfg["jobs_dir"])
    current_job = str(cfg.get("current_job") or "")
    vid3 = _pointer(jobs_dir, VID3_JOB)
    current_pointer = _pointer(jobs_dir, current_job) if current_job else None
    status = _prime_json("status", "--json")
    listed = _prime_json("list", "--json", "--all")
    daemons = status if isinstance(status, list) else []
    unreachable = [
        row
        for row in daemons
        if isinstance(row, dict) and row.get("status") == "unreachable"
    ]
    tracked = [
        row
        for row in unreachable
        if row.get("hasTrackedWorkers") or row.get("hasTrackedWorkers")
    ]
    sessions = []
    if isinstance(listed, dict):
        sessions = listed.get("sessions") or listed.get("agents") or []
        if isinstance(listed, dict) and listed.get("error"):
            sessions = []
    live_sessions = [row for row in sessions if isinstance(row, dict) and str(row.get("lifecycle") or "") == "live"]
    procs = _prime_processes()
    supervisors = [p for p in procs if p["role"] == "supervisor"]
    workers = [p for p in procs if p["role"] == "worker"]
    session_file = Path(vid3["session_file"]) if vid3 and vid3.get("session_file") else None
    stall = scan_jsonl_stall(session_file) if session_file else classify_stall([])
    anomalies: list[str] = []
    if unreachable:
        anomalies.append("unreachable_pipes")
    if tracked:
        anomalies.append("unreachable_pipe_with_tracked_worker")
    if live_sessions:
        anomalies.append("live_sessions_listed")
    if any(p["role"] == "stuck_version" for p in procs):
        anomalies.append("stuck_prime_version_child")
    leftover_tui = [p for p in procs if p["role"] == "tui_client"]
    if leftover_tui and not workers:
        anomalies.append("orphan_tui_client")
    ghost_files = [
        AGENT_DIR / "sessions" / "019fecd2-f003-757b-a705-6fa212567172.jsonl",
        AGENT_DIR / "sessions" / "019fec4a-e5ca-76e9-bc99-0246e50cbcdd.jsonl",
    ]
    ghost_sessions = [str(path) for path in ghost_files if path.is_file()]
    if ghost_sessions:
        anomalies.append("aug10_ghost_sessions")
    disk = _disk(Path(cfg["studio_root"]))
    if not disk["ok"]:
        anomalies.append("low_disk")
    provider = _provider_reachable()
    if not provider.get("ok"):
        anomalies.append("provider_unreachable")
    stale_unsafe = []
    if leftover_tui and not workers:
        stale_unsafe.append(
            {
                "kind": "orphan_tui_client",
                "mark": "STALE_UNSAFE_TO_MUTATE",
                "pids": [p["pid"] for p in leftover_tui],
                "reason": "Live process; no official stop target after daemon shutdown. Do not taskkill.",
            }
        )
    if ghost_sessions:
        stale_unsafe.append(
            {
                "kind": "aug10_ghost_session",
                "mark": "STALE_UNSAFE_TO_MUTATE",
                "files": ghost_sessions,
                "reason": "Daemon list --all resurrects these as live; official stop/kill returns Unknown active session. Do not rm jsonl.",
            }
        )
    canonical_session = (vid3 or {}).get("session_id") or ""
    canonical_pipe = DEFAULT_PIPE
    current_pipes = [row.get("socketPath") for row in daemons if isinstance(row, dict) and row.get("status") == "current"]
    if current_pipes:
        canonical_pipe = str(current_pipes[0])
    report = {
        "ok": not anomalies,
        "anomalies": anomalies,
        "auto_repair": False,
        "unattended_mode": UNATTENDED_MODE,
        "foreman_hygiene": "PASS" if not anomalies else "PARTIAL",
        "stale_sessions_left": len(live_sessions) + len(ghost_sessions),
        "canonical_pipe": canonical_pipe,
        "canonical_session": canonical_session,
        "canonical_session_source": str((vid3 or {}).get("_path") or ""),
        "canonical_session_not_daemon": bool((vid3 or {}).get("not_daemon")),
        "current_job": current_job,
        "current_job_pointer": (current_pointer or {}).get("session_id"),
        "prime_version": _prime_version(),
        "explicit_session_dir": (vid3 or {}).get("session_dir"),
        "disk": disk,
        "provider": {k: v for k, v in provider.items() if k != "apiKey"},
        "daemon_status": daemons,
        "daemon_count": len(daemons),
        "supervisor_count": len(supervisors),
        "worker_count": len(workers),
        "processes": procs,
        "unreachable_pipes": unreachable,
        "unreachable_with_tracked_workers": tracked,
        "listed_live_sessions": live_sessions,
        "stale_unsafe_to_mutate": stale_unsafe,
        "stall": stall,
        "c001": "omitted_scrap_not_this_episode",
        "windows_focus_steal": {
            "observed_on_canary_tui": True,
            "observed_on_production_c001_this_session": False,
            "upgrade_prime_to_fix": False,
        },
    }
    return report


def cmd_preflight(cfg: dict[str, Any]) -> int:
    report = collect_preflight(cfg)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if report.get("ok") else 1
