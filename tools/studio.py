#!/usr/bin/env python3
"""Thin Content Studio launcher. Reads OM next_step. Does not produce.

Humans see: studio status | continue | run
OM protocol labels stay inside this file. Prime remains the foreman.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(r"C:\ContentStudio")
CONTINUE = "CONTINUE_SCENE"
STOP = "STOP"
REVISE = "REVISE"
REVIEW = {
    "a": "A",
    "b": "B",
    "neither": "NEITHER",
    "keep": "KEEP_WATCHING",
    "ship": "SHIP",
    "no": "DO_NOT_SHIP",
    "revise": "REVISE",
}
CONTINUE_LABELS = {CONTINUE, STOP, REVISE}
SCENE_REVIEW_LABELS = {"KEEP_WATCHING", "SHIP", "DO_NOT_SHIP", "REVISE"}
AB_LABELS = {"A", "B", "NEITHER"}


def _config_path() -> Path:
    override = os.environ.get("CONTENT_STUDIO_CONFIG")
    if override:
        return Path(override)
    here = Path.cwd()
    for candidate in (here, *here.parents):
        path = candidate / "studio.json"
        if path.is_file():
            return path
    return DEFAULT_ROOT / "studio.json"


def load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        raise SystemExit(f"studio.json missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["_path"] = str(path)
    return data


def apply_env(cfg: dict[str, Any]) -> dict[str, str]:
    root = Path(cfg["studio_root"])
    repo = Path(cfg["om_repo"])
    jobs = Path(cfg["jobs_dir"])
    adapter = repo / "integrations" / "prime-om-adapter" / "src"
    env = os.environ
    env["CONTENT_STUDIO_OM_REPO"] = str(repo)
    env["OPENMONTAGE_PROJECTS_DIR"] = str(jobs)
    env["OM_PRIME_ADAPTER_ROOT"] = str(root)
    pythonpath = [str(adapter), str(repo)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    for path in (str(adapter), str(repo)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return env


def _save_current_job(cfg: dict[str, Any], job_id: str) -> None:
    path = Path(cfg["_path"])
    blob = json.loads(path.read_text(encoding="utf-8-sig"))
    blob["current_job"] = job_id
    path.write_text(json.dumps(blob, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cfg["current_job"] = job_id


def _job_id(cfg: dict[str, Any], explicit: str | None) -> str:
    job = (explicit or cfg.get("current_job") or "").strip()
    if not job:
        raise SystemExit("No current job. studio use <job-id>")
    return job


def _open(job_id: str) -> dict[str, Any]:
    from om_prime_adapter import open_job

    return open_job(job_id)


def _step(job: dict[str, Any]) -> dict[str, Any]:
    return (job.get("next_step") or (job.get("production_world") or {}).get("next_step") or {})


def _healthy(cfg: dict[str, Any], job_id: str) -> dict[str, str]:
    repo = Path(cfg["om_repo"])
    jobs = Path(cfg["jobs_dir"]) / job_id
    ov = Path(cfg["studio_root"]) / "runtime"
    return {
        "OM": "healthy" if (repo / "lib").is_dir() else "missing",
        "job": "ready" if (jobs / "project.json").is_file() else "missing",
        "runtime": "present" if ov.is_dir() else "missing",
    }


def prime_running(job_id: str) -> bool:
    """True only if a python/node process is the foreman session.

    The PowerShell probe command line itself contains the script name and
    job id; ignoring non-python/node processes avoids a false positive.
    """
    token = "".join(ch for ch in job_id if ch.isalnum() or ch in "-_")
    if not token:
        return False
    ps = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match 'python|node' -and $_.CommandLine -and "
        "($_.CommandLine -like '*run_prime_foreman_session.py*') -and "
        f"($_.CommandLine -like '*{token}*') "
        "} | Select-Object -First 1 -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool((result.stdout or "").strip())


def _gate_kind(step: dict[str, Any]) -> str:
    blob = " ".join(
        [
            str(step.get("summary") or ""),
            str(step.get("action") or ""),
            json.dumps(step.get("review_queue") or {}, ensure_ascii=False),
        ]
    ).upper()
    if "KEEP_WATCHING" in blob or "REVIEW QUEUE" in blob or "COMPOSED SCENE" in blob:
        return "scene_review"
    if "A/B" in blob or "NEITHER" in blob:
        return "ab"
    return "continue"


def _print_gate(cfg: dict[str, Any], job_id: str, step: dict[str, Any]) -> None:
    kind = _gate_kind(step)
    print(step.get("summary") or "Human decision required.")
    print(f"scene: {step.get('scene_id')}")
    queue = step.get("review_queue") if isinstance(step.get("review_queue"), dict) else {}
    composed = queue.get("composed_path")
    if composed:
        print(f"watch: {Path(cfg['studio_root']) / composed}")
    else:
        fallback = Path(cfg["jobs_dir"]) / job_id / "working" / "prime_rlm" / "composed" / "scene_v2.mp4"
        if not fallback.is_file():
            fallback = Path(cfg["jobs_dir"]) / job_id / "working" / "prime_rlm" / "composed" / "scene_lights_out.mp4"
        if fallback.is_file():
            print(f"watch: {fallback}")
    print()
    print("Not an interactive prompt. Type a full studio command:")
    if kind == "scene_review":
        print("  .\\studio review keep")
        print("  .\\studio review ship")
        print("  .\\studio review no")
        print("  .\\studio review revise")
        print("Do not type C. Continue was the earlier gate.")
        print("Do not stamp a quality proven_status from this review.")
    elif kind == "ab":
        print("  .\\studio review a")
        print("  .\\studio review b")
        print("  .\\studio review neither")
    else:
        print("  .\\studio continue")
        print("  .\\studio revise")
        print("  .\\studio stop")


def cmd_status(cfg: dict[str, Any], job_id: str) -> int:
    job = _open(job_id)
    world = job.get("production_world") or {}
    step = _step(job)
    action = str(step.get("action") or "")
    health = _healthy(cfg, job_id)
    running = prime_running(job_id)
    print("Windows Content Studio")
    print()
    print(f"Current job:\n{job_id}")
    print()
    print("State:")
    print((world.get("job_skeleton") or {}).get("status") or job.get("status") or "unknown")
    print()
    print("Prime:")
    print("running" if running else "idle")
    print()
    print("OM:")
    print(health["OM"])
    print()
    print("Next:")
    if action == "wait_human_preference":
        _print_gate(cfg, job_id, step)
    elif running:
        shot = step.get("shot_id")
        extra = f" {shot}" if shot else ""
        print(f"Prime is producing{extra} ({action or 'in session'}). No human action required.")
    else:
        print(step.get("summary") or action or "No next_step.")
    return 0


def _labels_for(kind: str) -> list[str]:
    if kind == "scene_review":
        return sorted(SCENE_REVIEW_LABELS)
    if kind == "ab":
        return sorted(AB_LABELS)
    return sorted(CONTINUE_LABELS)


def _watch_paths(cfg: dict[str, Any], job_id: str, step: dict[str, Any]) -> dict[str, Any]:
    queue = step.get("review_queue") if isinstance(step.get("review_queue"), dict) else {}
    watch = None
    composed = queue.get("composed_path")
    if composed:
        candidate = Path(cfg["studio_root"]) / composed
        watch = str(candidate) if candidate.is_file() else str(composed)
    if not watch:
        composed_dir = Path(cfg["jobs_dir"]) / job_id / "working" / "prime_rlm" / "composed"
        if composed_dir.is_dir():
            mp4s = sorted(composed_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mp4s:
                watch = str(mp4s[0])
    latest_take = None
    rollouts = Path(cfg["jobs_dir"]) / job_id / "working" / "prime_rlm" / "rollouts"
    if rollouts.is_dir():
        takes = sorted(rollouts.glob("*/*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if takes:
            latest_take = str(takes[0])
    return {"watch": watch, "latest_take": latest_take}


def cmd_state(cfg: dict[str, Any], job_id: str) -> int:
    """Machine-readable snapshot for the Pi cockpit. Read-only."""
    try:
        job = _open(job_id)
    except Exception as err:  # adapter refusals must not crash the cockpit
        print(json.dumps(
            {"job": job_id, "error": str(err), "prime_running": prime_running(job_id), "health": _healthy(cfg, job_id)},
            ensure_ascii=False,
        ))
        return 0
    world = job.get("production_world") or {}
    step = _step(job)
    skeleton = world.get("job_skeleton") or {}
    if not skeleton:
        try:
            skeleton = json.loads((Path(cfg["jobs_dir"]) / job_id / "JOB_SKELETON.json").read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            skeleton = {}
    action = str(step.get("action") or "")
    gate_open = action == "wait_human_preference"
    kind = _gate_kind(step) if gate_open else None
    payload = {
        "job": job_id,
        "status": skeleton.get("status") or job.get("status") or "unknown",
        "frozen": bool(skeleton.get("frozen")),
        "prime_running": prime_running(job_id),
        "action": action or None,
        "summary": step.get("summary"),
        "scene_id": step.get("scene_id"),
        "shot_id": step.get("shot_id"),
        "gate_open": gate_open,
        "gate_kind": kind,
        "labels": _labels_for(kind) if gate_open else [],
        "health": _healthy(cfg, job_id),
    }
    payload.update(_watch_paths(cfg, job_id, step))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def cmd_jobs(cfg: dict[str, Any]) -> int:
    """Machine-readable job list for the Pi cockpit. Read-only."""
    jobs_dir = Path(cfg["jobs_dir"])
    out = []
    for child in sorted(jobs_dir.iterdir()):
        if not child.is_dir():
            continue
        skeleton: dict[str, Any] = {}
        try:
            skeleton = json.loads((child / "JOB_SKELETON.json").read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            skeleton = {}
        out.append({
            "job": child.name,
            "status": skeleton.get("status") or "unknown",
            "frozen": bool(skeleton.get("frozen")),
            "fixture": bool(skeleton.get("fixture")) or child.name.startswith("fixture-"),
            "current": child.name == (cfg.get("current_job") or ""),
        })
    print(json.dumps(out, ensure_ascii=False))
    return 0


def _gate_target(step: dict[str, Any]) -> str:
    target = str(step.get("scene_id") or step.get("target") or "").strip()
    if not target:
        raise SystemExit("OM next_step has no human target. Not guessing.")
    return target


def cmd_prefer(cfg: dict[str, Any], job_id: str, label: str) -> int:
    job = _open(job_id)
    step = _step(job)
    if str(step.get("action") or "") != "wait_human_preference":
        raise SystemExit(
            f"No human gate. OM next_step is {step.get('action')!r}. Launcher will not invent a preference."
        )
    kind = _gate_kind(step)
    allowed = SCENE_REVIEW_LABELS if kind == "scene_review" else AB_LABELS if kind == "ab" else CONTINUE_LABELS
    if label not in allowed:
        raise SystemExit(
            f"This gate is {kind}. {label} is not valid here. Run .\\studio status and use the printed command."
        )
    from om_prime_adapter import record_human_preference

    target = _gate_target(step)
    payload = record_human_preference(job_id, label, caller="human", target=target)
    print(json.dumps({"ok": True, "label": payload.get("label"), "target": payload.get("target")}, ensure_ascii=False))
    return 0


def _run_argv(cfg: dict[str, Any], job_id: str, flags: list[str]) -> list[str]:
    py = Path(cfg.get("kernel_python") or sys.executable)
    if not py.is_file():
        py = Path(sys.executable)
    script = Path(cfg["om_repo"]) / "tools" / "run_prime_foreman_session.py"
    argv = [str(py), str(script), "--project-id", job_id]
    skeleton = {}
    try:
        skeleton = json.loads((Path(cfg["jobs_dir"]) / job_id / "JOB_SKELETON.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        skeleton = {}
    status = str(skeleton.get("status") or "")
    if "--scene-revise" in flags or status == "SCENE_REVISE_PROPAGATION_PROOF":
        argv.append("--scene-revise")
    elif "--lights-out" in flags or status == "LIGHTS_OUT_SCENE_PROOF":
        argv.append("--lights-out")
    elif "--foreman-proof" in flags or status == "PRIME_FOREMAN_PROOF":
        argv.append("--foreman-proof")
    else:
        # Non-proof jobs get the generic follow-next_step foreman prompt.
        argv.append("--next-step")
    return argv


def cmd_run(cfg: dict[str, Any], job_id: str, flags: list[str], *, ask: bool) -> int:
    if prime_running(job_id):
        raise SystemExit(f"Prime already running on {job_id}. Not starting a second session.")
    job = _open(job_id)
    step = _step(job)
    if str(step.get("action") or "") == "wait_human_preference":
        if _gate_kind(step) != "continue":
            raise SystemExit("Human review is open. Do not launch Prime. Run .\\studio status.")
        if not ask or not sys.stdin.isatty():
            raise SystemExit("Human gate is open. studio continue | revise | stop, then studio run.")
        print(step.get("summary") or "Human decision required.")
        print("[C] Continue  [R] Revise  [S] Stop")
        choice = input("> ").strip().lower()
        label = {"c": CONTINUE, "r": REVISE, "s": STOP}.get(choice)
        if not label:
            raise SystemExit("Cancelled.")
        cmd_prefer(cfg, job_id, label)
        if label != CONTINUE:
            return 0
    argv = _run_argv(cfg, job_id, flags)
    print("Launching Prime (foreman). Launcher does not dispatch.")
    return subprocess.call(argv, env=os.environ.copy())


def cmd_tui(cfg: dict[str, Any], job_id: str) -> int:
    py = Path(cfg.get("kernel_python") or sys.executable)
    if not py.is_file():
        py = Path(sys.executable)
    script = Path(cfg["om_repo"]) / "tools" / "run_prime_production_tui.py"
    return subprocess.call([str(py), str(script), "--project-id", job_id], env=os.environ.copy())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio", description="Windows Content Studio launcher")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("rest", nargs="*")
    args = parser.parse_args(argv)
    cfg = load_config()
    apply_env(cfg)
    cmd = args.command
    rest = list(args.rest)
    if cmd == "use":
        if not rest:
            raise SystemExit("studio use <job-id>")
        _save_current_job(cfg, rest[0])
        print(rest[0])
        return 0
    if cmd == "jobs":
        return cmd_jobs(cfg)
    job_id = _job_id(cfg, rest[0] if cmd == "run" and rest and not rest[0].startswith("-") else None)
    if cmd in {"status", "studio"}:
        return cmd_status(cfg, job_id)
    if cmd == "state":
        return cmd_state(cfg, job_id)
    if cmd == "continue":
        return cmd_prefer(cfg, job_id, CONTINUE)
    if cmd == "revise":
        return cmd_prefer(cfg, job_id, REVISE)
    if cmd == "stop":
        return cmd_prefer(cfg, job_id, STOP)
    if cmd == "review":
        token = (rest[0] if rest else "").lower()
        if token not in REVIEW:
            raise SystemExit("studio review keep|ship|no|revise  or  a|b|neither")
        return cmd_prefer(cfg, job_id, REVIEW[token])
    if cmd == "run":
        flags = [item for item in rest if item.startswith("-")]
        if rest and not rest[0].startswith("-"):
            job_id = rest[0]
            _save_current_job(cfg, job_id)
        return cmd_run(cfg, job_id, flags, ask=True)
    if cmd == "tui":
        return cmd_tui(cfg, job_id)
    if cmd in {"prime-preflight", "preflight"}:
        from prime_foreman_preflight import cmd_preflight

        return cmd_preflight(cfg)
    raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
