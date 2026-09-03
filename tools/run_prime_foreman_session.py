#!/usr/bin/env python3
"""Start a NEW Prime Agent session as production foreman.

Does not resume the identity-plate session.
Does not generate media.
Does not list cuts. Prime must open_job and read OM story_refs.

This launcher is harness. The model inside Prime Agent is the caller of
open_job / submit_scene_proposal. Cursor must not write the scene proposal.
Reasoning failover stays inside one Prime RPC process.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage"))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lib.dispatch_cut import proven_status  # noqa: E402
from tools.prime_rpc_control_plane import (  # noqa: E402
    print_control_plane_summary,
    reasoning_chain_from_env,
    run_foreman_rpc,
    timeout_ms_from_env,
)

JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
ADAPTER = REPO / "integrations" / "prime-om-adapter"
ADAPTER_SRC = ADAPTER / "src"
KERNEL = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_KERNEL_PYTHON",
        r"C:\ContentStudio\runtime\Prime-kernel-venv\Scripts\python.exe",
    )
)
PRIME_CLI = Path(
    os.environ.get(
        "PRIME_AGENT_CLI_JS",
        str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "prime-agent" / "dist" / "bundle" / "cli.js"),
    )
)
PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_NEXT_SCENE_PROMPT.md"
CONTINUE_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_CONTINUE_SCENE_PROMPT.md"
DISPATCH_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_DISPATCH_B2_PROMPT.md"
PREREQ_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_RESOLVE_PREREQUISITE.md"
KEYFRAME_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_PRODUCE_B1.md"
SHOWPIECE_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_SHOWPIECE_PROOF.md"
FOREMAN_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_HEAD_TURN_PROOF.md"
LIGHTS_OUT_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_LIGHTS_OUT_SCENE_PROOF.md"
REVISE_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_SCENE_REVISE_PROOF.md"
NEXT_STEP_PROMPT = REPO / "integrations" / "prime-om-adapter" / "FOREMAN_COCKPIT_NEXT_STEP.md"
DEFAULT_AGENT_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".prime" / "agent"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_env(project_id: str) -> dict[str, str]:
    env = os.environ.copy()
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    env["NO_PROXY"] = "127.0.0.1,localhost,::1"
    env["no_proxy"] = "127.0.0.1,localhost,::1"
    env["OM_PRIME_ADAPTER_ROOT"] = r"C:\ContentStudio"
    env["OPENMONTAGE_PROJECTS_DIR"] = str(JOBS_DIR)
    env["PRIME_AGENT_KERNEL_PYTHON"] = str(KERNEL)
    env["PRIME_AGENT_CODING_AGENT_DIR"] = str(DEFAULT_AGENT_DIR)
    pythonpath = [str(ADAPTER_SRC), str(REPO)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return env


def load_prompt(project_id: str, prompt_path: Path) -> str:
    if prompt_path.is_file():
        return prompt_path.read_text(encoding="utf-8").replace("{{PROJECT_ID}}", project_id)
    return (
        f"Call om_prime_adapter.open_job({project_id!r}). Follow next_step. "
        "Do not polish Scene A. Do not generate. Do not ask Cursor to write cuts."
    )


def build_rpc_command(
    project_id: str,
    *,
    resume: Path | None,
    chain: tuple[str, ...],
) -> list[str]:
    session_dir = JOBS_DIR / project_id / "working" / "prime_rlm" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    provider, model_id = chain[0].split("/", 1)
    args = [
        "node",
        str(PRIME_CLI),
        "--mode",
        "rpc",
        "--thinking",
        "low",
        "--cwd",
        str(REPO),
        "--skill",
        str(ADAPTER),
        "--no-extensions",
        "--session-dir",
        str(session_dir),
        "--models",
        ",".join(chain),
        "--provider",
        provider,
        "--model",
        model_id,
    ]
    if resume is not None:
        args.extend(["--resume", str(resume)])
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Prime Agent foreman session (new, not resume)")
    parser.add_argument("--project-id", default="vid3-blacklisted-chef-90s-v1")
    parser.add_argument("--print", dest="print_mode", action="store_true", help="one-shot then exit")
    parser.add_argument("--resume", action="store_true", help="resume SESSION_POINTER instead of a new session")
    parser.add_argument("--continue-scene", action="store_true", help="use CONTINUE_SCENE foreman prompt")
    parser.add_argument("--dispatch-b2", action="store_true", help="use B2 dispatch_cut foreman prompt")
    parser.add_argument("--resolve-prerequisite", action="store_true", help="resolve B2 blocker via Lucien identity → B1 keyframe")
    parser.add_argument("--produce-b1", action="store_true", help="produce B1 NONE keyframe after Lucien identity lock")
    parser.add_argument("--foreman-proof", action="store_true", help="PRIME_FOREMAN_PROOF on vid-foreman-head-turn-v1 (not the paused showpiece S2)")
    parser.add_argument("--lights-out", action="store_true", help="LIGHTS_OUT_SCENE_PROOF on vid-lights-out-scene-v1")
    parser.add_argument("--scene-revise", action="store_true", help="SCENE_REVISE_PROPAGATION_PROOF on vid-scene-revise-v1")
    parser.add_argument("--next-step", dest="next_step", action="store_true", help="generic cockpit prompt: open_job and follow next_step")
    args = parser.parse_args()
    if not PRIME_CLI.is_file():
        print(json.dumps({"ok": False, "error": f"Prime CLI missing: {PRIME_CLI}"}), file=sys.stderr)
        return 2
    pointer_path = JOBS_DIR / args.project_id / "working" / "prime_rlm" / "SESSION_POINTER.json"
    resume = None
    if args.resume:
        if not pointer_path.is_file():
            print(json.dumps({"ok": False, "error": "SESSION_POINTER.json missing"}), file=sys.stderr)
            return 2
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        resume = Path(str(pointer.get("session_file") or ""))
        if not resume.is_file():
            print(json.dumps({"ok": False, "error": f"session_file missing: {resume}"}), file=sys.stderr)
            return 2
    if args.scene_revise:
        if args.project_id == "vid3-blacklisted-chef-90s-v1":
            args.project_id = "vid-scene-revise-v1"
        prompt_path = REVISE_PROMPT
    elif args.lights_out:
        if args.project_id == "vid3-blacklisted-chef-90s-v1":
            args.project_id = "vid-lights-out-scene-v1"
        prompt_path = LIGHTS_OUT_PROMPT
    elif args.foreman_proof:
        if args.project_id == "vid3-blacklisted-chef-90s-v1":
            args.project_id = "vid-foreman-head-turn-v1"
        prompt_path = FOREMAN_PROMPT if args.project_id == "vid-foreman-head-turn-v1" else SHOWPIECE_PROMPT
    elif args.produce_b1:
        prompt_path = KEYFRAME_PROMPT
    elif args.resolve_prerequisite:
        prompt_path = PREREQ_PROMPT
    elif args.dispatch_b2:
        prompt_path = DISPATCH_PROMPT
    elif args.continue_scene:
        prompt_path = CONTINUE_PROMPT
    elif args.next_step:
        prompt_path = NEXT_STEP_PROMPT
    else:
        prompt_path = PROMPT
    env = build_env(args.project_id)
    env["PYTHONUNBUFFERED"] = "1"
    chain = reasoning_chain_from_env(env)
    cmd = build_rpc_command(args.project_id, resume=resume, chain=chain)
    joined = " ".join(cmd)
    if "--no-session" in joined or "--no-tools" in joined:
        print(json.dumps({"ok": False, "error": "forbidden flags"}), file=sys.stderr)
        return 2
    prompt = load_prompt(args.project_id, prompt_path)
    timeout_ms = timeout_ms_from_env(env)
    turn_timeout_s = float(env.get("PRIME_TURN_TIMEOUT_S") or (7200 if (args.dispatch_b2 or args.foreman_proof or args.lights_out or args.scene_revise) else 1800))
    job_dir = JOBS_DIR / args.project_id
    print("=" * 64, flush=True)
    print("  Prime Agent TUI — foreman session", flush=True)
    print(f"  proven_status: {proven_status(job_dir)}", flush=True)
    print("  foreman_proven: false", flush=True)
    print("  control_plane: rpc failover (one process, IPython stays)", flush=True)
    print("=" * 64, flush=True)
    print(f"  project_id : {args.project_id}", flush=True)
    print(f"  resume     : {resume or '(new)'}", flush=True)
    print(f"  prompt     : {prompt_path.name}", flush=True)
    print(f"  chain      : {', '.join(chain)}", flush=True)
    print(f"  first_token_timeout_ms : {timeout_ms}", flush=True)
    print(f"  turn_timeout_s : {turn_timeout_s}", flush=True)
    print(f"  started_at : {_utc_now()}", flush=True)
    print("=" * 64, flush=True)
    result = run_foreman_rpc(
        cmd,
        prompt,
        env=env,
        chain=chain,
        first_token_timeout_ms=timeout_ms,
        command_timeout_s=120.0,
        turn_timeout_s=turn_timeout_s,
        log=lambda line: print(line, flush=True),
    )
    print_control_plane_summary(result, sys.stdout)
    if not args.print_mode:
        return 0 if result.ok else 1
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
