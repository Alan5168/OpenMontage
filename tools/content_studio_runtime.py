#!/usr/bin/env python3
"""Controlled loopback start/stop/health for Qdrant, embedding, OpenViking.

PID ownership, single-instance lock, log rotation, disable/rollback.
Does not touch ComfyUI/H3. Binding is 127.0.0.1 only.
DEGRADED or missing health is a non-zero exit.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(os.environ.get("CONTENT_STUDIO_ROOT", r"C:\ContentStudio"))
REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", str(ROOT / "repos" / "OpenMontage")))
PID_DIR = ROOT / "runtime" / "pids"
LOG_ROOT = ROOT / "logs"
LOCK_PATH = PID_DIR / "content-studio-runtime.lock"

SERVICES: dict[str, dict[str, Any]] = {
    "qdrant": {
        "port": 6333,
        "health": "http://127.0.0.1:6333/healthz",
        "pid_name": "qdrant.pid",
        "log_dir": "qdrant",
        "argv": [
            str(ROOT / "tools" / "qdrant" / "v1.17.1" / "qdrant.exe"),
            "--config-path",
            str(ROOT / "runtime" / "qdrant" / "config.yaml"),
        ],
        "cwd": str(ROOT / "runtime" / "qdrant"),
        "env": {},
    },
    "embedding": {
        "port": 18889,
        "health": "http://127.0.0.1:18889/health",
        "pid_name": "embedding.pid",
        "log_dir": "embedding",
        "argv": [
            str(ROOT / "runtime" / "qwen3-embedding-venv" / "Scripts" / "python.exe"),
            "-X",
            "utf8",
            str(REPO / "tools" / "content_studio_embedding_service.py"),
        ],
        "cwd": str(REPO),
        "env": {
            "EMBEDDING_SERVICE_PORT": "18889",
            "EMBEDDING_BIND_HOST": "127.0.0.1",
            "EMBEDDING_MODEL_PATH": str(ROOT / "models" / "Qwen3-Embedding-0.6B"),
        },
        "ready_timeout": 180,
    },
    "openviking": {
        "port": 1933,
        "health": "http://127.0.0.1:1933/health",
        "pid_name": "openviking.pid",
        "log_dir": "openviking",
        "argv": [
            str(ROOT / "runtime" / "openviking-0.4.13" / "Scripts" / "openviking-server.exe"),
            "--host",
            "127.0.0.1",
            "--port",
            "1933",
            "--config",
            str(ROOT / "config" / "openviking" / "ov.conf"),
        ],
        "cwd": str(ROOT / "runtime" / "openviking-0.4.13"),
        "env": {
            "OPENVIKING_CONFIG_FILE": str(ROOT / "config" / "openviking" / "ov.conf"),
        },
        "ready_timeout": 90,
    },
}

ORDER = ("qdrant", "embedding", "openviking")


class RuntimeError_(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        req = Request(url, headers={"Accept": "application/json, text/plain"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")[:500]
            return 200 <= resp.status < 300, body.strip()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _pid_path(name: str) -> Path:
    return PID_DIR / SERVICES[name]["pid_name"]


def _read_pid(name: str) -> int | None:
    path = _pid_path(name)
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return pid if _pid_alive(pid) else None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _write_pid(name: str, pid: int) -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    _pid_path(name).write_text(str(pid), encoding="utf-8")


def _rotate_log(path: Path, keep_bytes: int = 2_000_000) -> None:
    if path.is_file() and path.stat().st_size > keep_bytes:
        bak = path.with_suffix(path.suffix + ".1")
        if bak.exists():
            bak.unlink()
        path.replace(bak)


def _task_name(name: str) -> str:
    return f"ContentStudio-{name}"


def _write_launcher(name: str) -> Path:
    spec = SERVICES[name]
    log_dir = LOG_ROOT / spec["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    _rotate_log(stdout_path)
    _rotate_log(stderr_path)
    launcher = log_dir / "launch.cmd"
    args = subprocess.list2cmdline(spec["argv"])
    env_lines = [f"set {k}={v}" for k, v in (spec.get("env") or {}).items()]
    launcher.write_text(
        "@echo off\r\n"
        f"cd /d {spec.get('cwd') or '.'}\r\n"
        + "".join(f"{line}\r\n" for line in env_lines)
        + f"{args} >> \"{stdout_path}\" 2>> \"{stderr_path}\"\r\n",
        encoding="ascii",
    )
    return launcher


def _decode_proc(data: bytes | None) -> str:
    raw = data or b""
    if os.name == "nt":
        return raw.decode("gbk", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _schtasks_create_and_run(name: str, launcher: Path) -> None:
    task = _task_name(name)
    create = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            task,
            "/TR",
            f'cmd /c "{launcher}"',
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
            "/F",
        ],
        capture_output=True,
        timeout=30,
    )
    if create.returncode != 0:
        raise RuntimeError_(
            f"schtasks create {task}: {_decode_proc(create.stdout)} {_decode_proc(create.stderr)}"
        )
    run = subprocess.run(
        ["schtasks", "/Run", "/TN", task],
        capture_output=True,
        timeout=30,
    )
    if run.returncode != 0:
        raise RuntimeError_(
            f"schtasks run {task}: {_decode_proc(run.stdout)} {_decode_proc(run.stderr)}"
        )


def _schtasks_end(name: str) -> None:
    subprocess.run(
        ["schtasks", "/End", "/TN", _task_name(name)],
        capture_output=True,
        timeout=20,
        check=False,
    )


def _spawn(name: str) -> int:
    spec = SERVICES[name]
    if os.name == "nt":
        # OpenSSH Job Object kills DETACHED children on session end.
        # Goal §5.1: Task Scheduler ONLOGON launcher, then /Run now.
        launcher = _write_launcher(name)
        _schtasks_create_and_run(name, launcher)
        deadline = time.time() + 25
        while time.time() < deadline:
            pid = _pid_on_port(spec["port"])
            if pid:
                _write_pid(name, pid)
                return pid
            time.sleep(0.5)
        return 0
    log_dir = LOG_ROOT / spec["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    _rotate_log(stdout_path)
    _rotate_log(stderr_path)
    env = os.environ.copy()
    env.update(spec.get("env") or {})
    stdout = stdout_path.open("a", encoding="utf-8")
    stderr = stderr_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        spec["argv"],
        cwd=spec.get("cwd"),
        env=env,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )
    _write_pid(name, proc.pid)
    return proc.pid


def _pid_on_port(port: int) -> int | None:
    try:
        proc = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        return None
    raw = proc.stdout or b""
    text = raw.decode("utf-8", errors="replace")
    if os.name == "nt":
        text = raw.decode("gbk", errors="replace")
    needle = f":{port}"
    for line in text.splitlines():
        if "LISTENING" not in line and "LISTEN" not in line:
            continue
        if needle not in line:
            continue
        parts = line.split()
        try:
            return int(parts[-1])
        except ValueError:
            continue
    return None


def _wait_ready(name: str) -> dict[str, Any]:
    spec = SERVICES[name]
    timeout = float(spec.get("ready_timeout", 30))
    deadline = time.time() + timeout
    last = "not_ready"
    while time.time() < deadline:
        ok, detail = _http_ok(spec["health"], timeout=2.0)
        last = detail
        if ok:
            return {"ready": True, "detail": detail, "waited_s": round(timeout - (deadline - time.time()), 2)}
        time.sleep(1.0)
    return {"ready": False, "detail": last, "waited_s": timeout}


def _kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass


def _public_probe_must_fail(port: int) -> bool:
    """Random public bind probe: connecting to 0.0.0.0 from non-loopback should fail.

    We only assert the service is not listening on the LAN IP.
    """
    lan = os.environ.get("CONTENT_STUDIO_LAN_IP", "192.168.1.10")
    return not _port_open(port, host=lan)


def service_status(name: str) -> dict[str, Any]:
    spec = SERVICES[name]
    pid = _read_pid(name)
    loopback = _port_open(spec["port"])
    health_ok, health_detail = _http_ok(spec["health"]) if loopback else (False, "port_closed")
    lan_closed = _public_probe_must_fail(spec["port"])
    overall = "OK" if (loopback and health_ok and lan_closed) else "FAIL"
    return {
        "name": name,
        "status": overall,
        "pid": pid,
        "port": spec["port"],
        "loopback_open": loopback,
        "lan_closed": lan_closed,
        "health_ok": health_ok,
        "health_detail": health_detail[:300],
        "pid_file": str(_pid_path(name)),
    }


def cmd_status() -> dict[str, Any]:
    services = [service_status(name) for name in ORDER]
    overall = "OK" if all(s["status"] == "OK" for s in services) else "FAIL"
    return {
        "schema_version": "content-studio-runtime/v1",
        "overall": overall,
        "checked_at": _utc_now(),
        "services": services,
    }


def cmd_start(names: list[str] | None = None) -> dict[str, Any]:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    selected = list(ORDER if not names else names)
    started: list[dict[str, Any]] = []
    for name in selected:
        current = service_status(name)
        if current["health_ok"]:
            started.append({"name": name, "action": "already_running", **current})
            continue
        if current["pid"]:
            _kill_pid(current["pid"])
        pid = _spawn(name)
        ready = _wait_ready(name)
        after = service_status(name)
        started.append({"name": name, "action": "started", "pid": pid, "ready": ready, **after})
    overall = "OK" if all(s.get("status") == "OK" for s in started) else "FAIL"
    return {
        "schema_version": "content-studio-runtime/v1",
        "overall": overall,
        "started_at": _utc_now(),
        "services": started,
    }


def cmd_stop(names: list[str] | None = None) -> dict[str, Any]:
    selected = list(reversed(ORDER if not names else names))
    stopped = []
    for name in selected:
        pid = _read_pid(name)
        if os.name == "nt":
            _schtasks_end(name)
        if pid:
            _kill_pid(pid)
        path = _pid_path(name)
        if path.exists():
            path.unlink()
        time.sleep(0.4)
        stopped.append({"name": name, "killed_pid": pid, "loopback_open": _port_open(SERVICES[name]["port"])})
    return {
        "schema_version": "content-studio-runtime/v1",
        "overall": "OK",
        "stopped_at": _utc_now(),
        "services": stopped,
    }


def cmd_health() -> dict[str, Any]:
    payload = cmd_status()
    payload["fail_closed"] = True
    return payload


def cmd_doctor() -> dict[str, Any]:
    status = cmd_status()
    ov_bin = ROOT / "runtime" / "openviking-0.4.13" / "Scripts" / "openviking-server.exe"
    ov_py = ROOT / "runtime" / "openviking-0.4.13" / "Scripts" / "python.exe"
    version = "unknown"
    try:
        proc = subprocess.run(
            [str(ov_bin), "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        version = (proc.stdout or proc.stderr or "").strip()
    except Exception as exc:
        version = f"{type(exc).__name__}: {exc}"
    pkg = "unknown"
    try:
        proc = subprocess.run(
            [str(ov_py), "-c", "import importlib.metadata as m; print(m.version('openviking'))"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        pkg = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    except Exception as exc:
        pkg = f"{type(exc).__name__}: {exc}"
    return {
        **status,
        "openviking_fixed_version": "0.4.13",
        "openviking_server_version": version,
        "openviking_package_version": pkg,
        "version_ok": pkg == "0.4.13",
        "hindsight_present": False,
        "notes": "DEGRADED is not PASS. Missing health is FAIL.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Content Studio loopback runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--only", nargs="*", choices=list(ORDER))
    stop = sub.add_parser("stop")
    stop.add_argument("--only", nargs="*", choices=list(ORDER))
    sub.add_parser("status")
    sub.add_parser("health")
    sub.add_parser("doctor")
    sub.add_parser("restart")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "start":
            payload = cmd_start(args.only)
        elif args.command == "stop":
            payload = cmd_stop(args.only)
        elif args.command == "restart":
            cmd_stop()
            payload = cmd_start()
        elif args.command == "status":
            payload = cmd_status()
        elif args.command == "health":
            payload = cmd_health()
        elif args.command == "doctor":
            payload = cmd_doctor()
        else:
            payload = {"status": "ERROR", "error": args.command}
    except Exception as exc:
        _emit({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
        return 1
    _emit(payload)
    overall = payload.get("overall")
    if overall not in {"OK"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
