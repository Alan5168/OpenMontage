#!/usr/bin/env python3
"""Windows Prime Production TUI — open_job → compile_cut.

This is the production entry. Cursor is not the foreman.
Prime reads OM canonical truth and writes execution proposals only.
Does not generate media, does not APPROVE, does not polish A4.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage"))
ADAPTER_SRC = REPO / "integrations" / "prime-om-adapter" / "src"
for path in (str(ADAPTER_SRC), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

from om_prime_adapter import (  # noqa: E402
    AdapterError,
    compile_cut,
    open_job,
    propose_identity_candidates,
    record_human_preference,
    submit_prerequisite_plan,
)


def _print(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _summarize_open(job: dict[str, Any]) -> dict[str, Any]:
    world = job.get("production_world") or {}
    return {
        "job_id": job.get("job_id"),
        "canonical_owner": job.get("canonical_owner"),
        "checkpoint_stage": job.get("stage"),
        "checkpoint_status": job.get("status"),
        "next_step": job.get("next_step") or world.get("next_step"),
        "scene_state": (world.get("scene_state") or {}).get("status"),
        "human_lock": world.get("human_lock"),
        "identity": world.get("identity"),
        "shot_ids": [row.get("id") for row in (world.get("shot_contracts") or [])],
        "checkpoint_vs_artifacts": world.get("checkpoint_vs_artifacts"),
        "openviking": {
            "available": (world.get("openviking") or {}).get("available"),
            "pointer_count": len((world.get("openviking") or {}).get("pointers") or []),
            "invented": (world.get("openviking") or {}).get("invented"),
        },
        "story_ref_count": len(world.get("story_refs") or []),
        "proven_status": world.get("proven_status"),
        "foreman_proven": world.get("foreman_proven"),
        "observation_count": len(world.get("observations") or []),
        "rollout_count": len(world.get("rollouts") or []),
        "generate": job.get("generate"),
    }


def cmd_open_job(job_id: str) -> dict[str, Any]:
    job = open_job(job_id)
    return _summarize_open(job)


def cmd_compile_cut(job_id: str, shot_id: str, *, write: bool) -> dict[str, Any]:
    return compile_cut(job_id, shot_id, caller="prime", write=write)


def _jobs_dir() -> Path:
    return Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))


def identity_board(job_id: str) -> dict[str, Any]:
    job = open_job(job_id)
    world = job.get("production_world") or {}
    lucien = ((world.get("character_identities") or {}).get("lucien_mercer") or {})
    pack = world.get("identity_candidates") or {}
    rows = []
    for row in pack.get("candidates") or []:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("path") or "")
        abs_path = _jobs_dir() / job_id / rel.replace("/", os.sep)
        rows.append(
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "path": rel,
                "exists": abs_path.is_file(),
                "abs_path": str(abs_path),
            }
        )
    folder = _jobs_dir() / job_id / "bible" / "lucien" / "candidates"
    return {
        "next_step": job.get("next_step") or world.get("next_step"),
        "lucien_locked": bool(lucien.get("locked")),
        "lucien_path": lucien.get("path"),
        "candidates": rows,
        "folder": str(folder),
        "folder_exists": folder.is_dir(),
        "look_first": "Look at A.png and B.png before typing prefer A identity.",
    }


def resolve_prefer_args(parts: list[str]) -> tuple[str, str | None]:
    if len(parts) < 2:
        raise AdapterError("usage: prefer A identity | prefer CONTINUE_SCENE")
    label = parts[1]
    token = label.strip().upper()
    target = None
    if len(parts) >= 3:
        raw = parts[2].strip()
        if raw.lower() in {"identity", "lucien", "identity:lucien_mercer"}:
            target = "identity:lucien_mercer"
        else:
            target = raw
    elif token in {"A", "B", "NEITHER"}:
        raise AdapterError(
            "A/B/NEITHER is Lucien identity, not Scene B. Type: prefer A identity"
        )
    return label, target


def _print_identity_board(board: dict[str, Any]) -> None:
    nxt = board.get("next_step") or {}
    print(f"  next     : {nxt.get('action')}")
    print(f"  summary  : {nxt.get('summary')}")
    print(f"  Lucien   : {'LOCKED' if board.get('lucien_locked') else 'unlocked'}")
    rows = board.get("candidates") or []
    if not rows:
        print("  plates   : none yet — there is no image link to open")
        print(f"  will be  : {board.get('folder')}\\A.png")
        print(f"             {board.get('folder')}\\B.png")
        print("  type     : propose_identity    (generates the two plates)")
        return
    for row in rows:
        mark = "on disk" if row.get("exists") else "MISSING"
        print(f"  plate {row.get('id')}: {row.get('status')} ({mark})")
        print(f"           {row.get('abs_path')}")


def repl(job_id: str, *, write: bool) -> int:
    print("=" * 64)
    print("  Windows Prime Production TUI")
    print("  Type short commands. You do not need the long --command line.")
    print("=" * 64)
    print(f"  job_id : {job_id}")
    print("  next | identity | propose_identity | prefer A identity | prefer B identity")
    print("  prefer NEITHER identity | prefer CONTINUE_SCENE | quit")
    print("=" * 64)
    board = identity_board(job_id)
    _print_identity_board(board)
    print("=" * 64)
    current = None
    while True:
        try:
            raw = input("prime> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        parts = raw.split()
        command = parts[0].lower()
        try:
            if command in {"quit", "exit"}:
                return 0
            if command in {"help", "?"}:
                print("next | identity | propose_identity | prefer A identity | quit")
            elif command == "open_job":
                current = cmd_open_job(job_id)
                _print(current)
            elif command == "next":
                current = current or cmd_open_job(job_id)
                _print(current.get("next_step") or {})
            elif command == "identity":
                board = identity_board(job_id)
                _print_identity_board(board)
                folder = Path(str(board.get("folder") or ""))
                if folder.is_dir() and hasattr(os, "startfile"):
                    os.startfile(folder)  # type: ignore[attr-defined]
                    print("  opened candidate folder in Explorer")
                elif not board.get("candidates"):
                    print("  no plates yet. Type: propose_identity")
            elif command == "propose_identity":
                print("  generating Lucien identity plates A/B via ComfyUI. Wait.")
                submit_prerequisite_plan(job_id, caller="prime")
                payload = propose_identity_candidates(job_id, caller="prime")
                _print(payload)
                board = identity_board(job_id)
                _print_identity_board(board)
                folder = Path(str(board.get("folder") or ""))
                if folder.is_dir() and hasattr(os, "startfile"):
                    os.startfile(folder)  # type: ignore[attr-defined]
                    print("  opened candidate folder in Explorer")
            elif command == "prefer":
                label, target = resolve_prefer_args(parts)
                _print(record_human_preference(job_id, label, caller="human", target=target))
            elif command == "compile_cut":
                if len(parts) < 2:
                    print("usage: compile_cut <shot_id>", file=sys.stderr)
                    continue
                payload = cmd_compile_cut(job_id, parts[1], write=write)
                _print(payload)
            else:
                print(f"unknown command: {command}", file=sys.stderr)
        except AdapterError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows Prime Production TUI")
    parser.add_argument("--project-id", required=True)
    parser.add_argument(
        "--command",
        choices=["open_job", "compile_cut", "prefer", "propose_identity", "repl"],
        default="repl",
    )
    parser.add_argument("--shot-id")
    parser.add_argument("--label", help="HumanPreference label for prefer")
    parser.add_argument("--target", help="HumanPreference target (scene_b or identity:lucien_mercer)")
    parser.add_argument("--no-write", action="store_true", help="compile without writing the proposal")
    parser.add_argument("--full", action="store_true", help="print full open_job payload")
    args = parser.parse_args()
    os.environ.setdefault("OM_PRIME_ADAPTER_ROOT", r"C:\ContentStudio")
    try:
        if args.command == "open_job":
            job = open_job(args.project_id)
            _print(job if args.full else _summarize_open(job))
            return 0
        if args.command == "compile_cut":
            if not args.shot_id:
                print("--shot-id is required for compile_cut", file=sys.stderr)
                return 2
            _print(cmd_compile_cut(args.project_id, args.shot_id, write=not args.no_write))
            return 0
        if args.command == "propose_identity":
            print("generating Lucien identity plates A/B via ComfyUI...", flush=True)
            submit_prerequisite_plan(args.project_id, caller="prime")
            payload = propose_identity_candidates(args.project_id, caller="prime")
            _print(payload)
            board = identity_board(args.project_id)
            _print_identity_board(board)
            return 0 if any(row.get("exists") for row in (board.get("candidates") or [])) else 2
        if args.command == "prefer":
            if not args.label:
                print("--label is required for prefer", file=sys.stderr)
                return 2
            _print(
                record_human_preference(
                    args.project_id, args.label, caller="human", target=args.target
                )
            )
            return 0
        return repl(args.project_id, write=not args.no_write)
    except AdapterError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
