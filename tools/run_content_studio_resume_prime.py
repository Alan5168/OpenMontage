#!/usr/bin/env python3
"""Canonical body of content_studio_resume_prime (Pi extension entry)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage"))
ROOT = Path(os.environ.get("OM_PRIME_ADAPTER_ROOT", r"C:\ContentStudio"))
GATEWAY = REPO / "tools" / "content_studio_gateway.py"
CLI = Path(
    os.environ.get(
        "PRIME_AGENT_CLI_JS",
        str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "prime-agent" / "dist" / "bundle" / "cli.js"),
    )
)
DEFAULT_KERNEL = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_KERNEL_PYTHON",
        r"C:\ContentStudio\runtime\Prime-kernel-venv\Scripts\python.exe",
    )
)
PY = Path(
    os.environ.get(
        "CONTENT_STUDIO_PYTHON",
        r"C:\ContentStudio\runtime\OpenMontage-test-venv\Scripts\python.exe",
    )
)


def gateway(command: str, project_id: str | None, extra: list[str] | None = None) -> dict:
    args = [str(PY), "-X", "utf8", str(GATEWAY)]
    if project_id:
        args.extend(["--project-id", project_id])
    args.append(command)
    if extra:
        args.extend(extra)
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    text = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    payload = None
    # Gateway prints one JSON object; tolerate trailing noise by scanning lines.
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if payload is None:
        start = text.rfind("{")
        if start < 0:
            raise RuntimeError(proc.stderr or text or "gateway returned no JSON")
        payload = json.loads(text[start:])
    if proc.returncode != 0 or payload.get("status") == "ERROR":
        raise RuntimeError(payload.get("error") or proc.stderr or "gateway failed")
    return payload


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def verify_evidence(session_file: Path, nonce: str, job_id: str, start_line: int) -> dict:
    import sys

    sys.path.insert(0, str(REPO))
    from tools.prime_resume_evidence import verify_resume_events

    return verify_resume_events(
        session_file,
        nonce=nonce,
        expected_job_id=job_id,
        start_line=start_line,
    )


def gateway_direct(command: str, project_id: str | None, **kwargs):
    import sys

    sys.path.insert(0, str(REPO))
    from tools import content_studio_gateway as gw

    projects_dir = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", str(ROOT / "jobs")))
    if command == "prepare-resume":
        return gw.prepare_prime_resume(projects_dir, project_id)
    if command == "record-resume":
        return gw.record_prime_resume(
            projects_dir,
            project_id,
            kwargs["request_id"],
            kwargs["prime_response"],
            kwargs["evidence_json"],
        )
    raise RuntimeError(f"unsupported gateway command: {command}")


def run_resume(project_id: str | None) -> dict:
    request = gateway_direct("prepare-resume", project_id)
    session_file = Path(str(request["session_file"]))
    session_dir = str(request["session_dir"])
    agent_dir = str(request.get("agent_dir") or "")
    skill_path = str(request.get("skill_path") or (REPO / "integrations" / "prime-om-adapter"))
    kernel = str(request.get("kernel_python") or DEFAULT_KERNEL)
    if not str(session_file).lower().endswith(".jsonl"):
        raise RuntimeError("prepare-resume did not return a full .jsonl session_file")

    nonce = f"resume-nonce-{uuid.uuid4().hex[:16]}"
    start_line = count_lines(session_file)
    job_id = os.environ.get("CONTENT_STUDIO_EVIDENCE_JOB_ID") or str(request["project_id"])
    adapter_src = REPO / "integrations" / "prime-om-adapter" / "src"
    py_code = "\n".join(
        [
            "import json, os, sys",
            "os.environ['OM_PRIME_ADAPTER_ROOT']=r'C:\\\\ContentStudio'",
            f"sys.path.insert(0, r'{adapter_src}')",
            f"sys.path.insert(0, r'{REPO}')",
            "from om_prime_adapter import build_context_variables, reload_context",
            f"ledger=build_context_variables({job_id!r})",
            "reloaded=reload_context(ledger)",
            (
                "print(json.dumps({"
                f"'nonce': {nonce!r}, "
                "'job_id': ledger.get('job_id'), "
                "'variable_names': sorted(ledger.get('variables', {})), "
                "'reload_context': True, "
                "'om_job_ref': (ledger.get('variables') or {}).get('om_job_ref')"
                "}, ensure_ascii=False))"
            ),
        ]
    )
    prompt = (
        "You are resuming a project-bound Content Studio Prime session.\n"
        "Call the ipython tool exactly once with this code, then stop:\n"
        + py_code
        + "\nDo not start assets, H3, or rendering.\n"
    )
    args = [
        "node",
        str(CLI),
        "-p",
        "--provider",
        "bailian",
        "--model",
        "qwen3.8-max",
        "--thinking",
        "low",
        "--cwd",
        str(REPO),
        "--skill",
        skill_path,
        "--no-extensions",
        "--no-prompt-templates",
        "--no-context-files",
        "--session-dir",
        session_dir,
        "--resume",
        str(session_file),
        "--",
        prompt,
    ]
    joined = " ".join(args)
    if " --no-session " in f" {joined} " or " --no-tools " in f" {joined} ":
        raise RuntimeError("forbidden fake-resume flags present")

    env = os.environ.copy()
    env["OM_PRIME_ADAPTER_ROOT"] = str(ROOT)
    env["OPENMONTAGE_PROJECTS_DIR"] = os.environ.get("OPENMONTAGE_PROJECTS_DIR", str(ROOT / "jobs"))
    env["PRIME_AGENT_KERNEL_PYTHON"] = kernel
    if agent_dir:
        env["PRIME_AGENT_CODING_AGENT_DIR"] = agent_dir

    started = time.time()
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=240,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Prime persistent resume failed: {proc.stderr or proc.stdout}")

    evidence = verify_evidence(session_file, nonce, job_id, start_line)
    if evidence.get("status") != "PASS":
        raise RuntimeError(f"Mechanical resume evidence failed: {evidence.get('reason')}")

    ack = {
        "status": "PRIME_OM_RESUME_ACCEPTED",
        "project_id": request["project_id"],
        "checkpoint_sha256": request["checkpoint_sha256"],
        "next_stage": request["next_stage"],
        "session_file": request["session_file"],
        "resumed": True,
        "fake_json_echo": False,
        "evidence_line_range_1based": evidence.get("evidence_line_range_1based"),
        "nonce": nonce,
    }
    receipt = gateway_direct(
        "record-resume",
        project_id,
        request_id=str(request["request_id"]),
        prime_response=json.dumps(ack, ensure_ascii=False),
        evidence_json=json.dumps(evidence, ensure_ascii=False),
    )
    return {
        "status": "PASS",
        "request": request,
        "evidence": evidence,
        "receipt": receipt,
        "nonce": nonce,
        "kernel_python": kernel,
        "argv_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        "forbidden_flags_absent": True,
        "extension_entry": "integrations/pi/content-studio.ts -> tools/run_content_studio_resume_prime.py",
        "elapsed_seconds": round(time.time() - started, 3),
        "prime_returncode": proc.returncode,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id")
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        result = run_resume(args.project_id)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except Exception as exc:  # noqa: BLE001 - surface to Pi
        payload = {"status": "FAIL", "error": str(exc)}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
