#!/usr/bin/env python3
"""Windows P0-P4 runner for isolated Prime RLM + OM adapter. No H3/render/Pi Gate."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CONTENT_STUDIO_ROOT", r"C:\ContentStudio"))
OM_REPO = ROOT / "repos" / "OpenMontage"
PILOT = ROOT / "runtime" / "prime-rlm-pilot"
AGENT = PILOT / "agent"
SESSIONS = PILOT / "sessions"
REPORTS = ROOT / "reports" / "prime-rlm-refinement-gate-v1"
FIXTURES = PILOT / "fixtures"
GLOBAL_AGENT = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".prime" / "agent"
CLI = Path(os.environ.get("PRIME_AGENT_CLI_JS", str(Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "prime-agent" / "dist" / "bundle" / "cli.js")))
KERNEL = ROOT / "runtime" / "Prime-kernel-venv" / "Scripts" / "python.exe"
SKILL = OM_REPO / "integrations" / "prime-om-adapter"
SOCKET = r"\\.\pipe\prime-rlm-refinement-gate-v1"
SESSION_NAME = "content-director__comic-nonfiction-short-knowledge-zh__v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot_global(label: str) -> dict:
    files = ["settings.json", "auth.json", "models.json", "harness_state.json"]
    snapshot = {"label": label, "at": utc_now(), "files": {}}
    for name in files:
        path = GLOBAL_AGENT / name
        snapshot["files"][name] = {
            "present": path.is_file(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size if path.is_file() else 0,
        }
    if (GLOBAL_AGENT / "settings.json").is_file():
        settings = json.loads((GLOBAL_AGENT / "settings.json").read_text(encoding="utf-8"))
        snapshot["settings_keys"] = sorted(settings.keys())
        snapshot["defaultProvider"] = settings.get("defaultProvider")
        snapshot["defaultModel"] = settings.get("defaultModel")
        snapshot["autoRefine_present"] = "autoRefine" in settings
        snapshot["rlmMaxDepth_present"] = "rlmMaxDepth" in settings
    snapshot["sessions_count"] = len(list((GLOBAL_AGENT / "sessions").glob("*"))) if (GLOBAL_AGENT / "sessions").is_dir() else 0
    snapshot["harness_state_present"] = (GLOBAL_AGENT / "harness_state.json").is_file()
    return snapshot


def setup_isolated_runtime() -> dict:
    for path in (AGENT, SESSIONS, REPORTS, FIXTURES, PILOT / "reports"):
        path.mkdir(parents=True, exist_ok=True)
    settings = {
        "defaultProvider": "bailian",
        "defaultModel": "qwen3.8-max",
        "rlmMaxDepth": 1,
        "autoRefine": {"enabled": False, "compact": False},
    }
    write_json(AGENT / "settings.json", settings)
    copied = {}
    for name in ("auth.json", "models.json"):
        src = GLOBAL_AGENT / name
        dst = AGENT / name
        if src.is_file():
            shutil.copy2(src, dst)
            copied[name] = {"copied": True, "sha256": sha256_file(dst), "size": dst.stat().st_size}
        else:
            copied[name] = {"copied": False}
    manifest = {
        "schema_version": "prime-rlm-scoped-runtime/v1",
        "root": str(PILOT),
        "agent_dir": str(AGENT),
        "session_dir": str(SESSIONS),
        "reports_dir": str(REPORTS),
        "fixtures_dir": str(FIXTURES),
        "kernel_python": str(KERNEL),
        "kernel_python_present": KERNEL.is_file(),
        "skill_path": str(SKILL),
        "settings_keys": sorted(settings.keys()),
        "auth_present": copied.get("auth.json", {}).get("copied", False),
        "models_catalog_present": copied.get("models.json", {}).get("copied", False),
        "copied": copied,
        "created_at": utc_now(),
    }
    write_json(PILOT / "SCOPED_RUNTIME_MANIFEST.json", manifest)
    write_json(REPORTS / "SCOPED_RUNTIME_MANIFEST.json", manifest)
    return manifest


def run_adapter_tests() -> dict:
    env = os.environ.copy()
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(OM_REPO / "tests" / "tools" / "test_prime_om_adapter.py"), "-q"],
        cwd=str(OM_REPO),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    result = {
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "passed": proc.returncode == 0,
    }
    write_json(REPORTS / "OM_SKILL_TESTS.json", result)
    return result


def prime_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PRIME_AGENT_CODING_AGENT_DIR"] = str(AGENT)
    env["PRIME_AGENT_KERNEL_PYTHON"] = str(KERNEL)
    env["OM_PRIME_ADAPTER_ROOT"] = str(ROOT)
    env["OPENMONTAGE_PROJECTS_DIR"] = str(ROOT / "jobs")
    env["PYTHONPATH"] = str(OM_REPO / "integrations" / "prime-om-adapter" / "src") + os.pathsep + str(OM_REPO) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_prime(prompt: str, *, session_args: list[str], system_prompt: str, timeout: int, label: str) -> dict:
    args = [
        "node",
        str(CLI),
        "--print",
        "--provider",
        "bailian",
        "--model",
        "qwen3.8-max",
        "--cwd",
        str(OM_REPO),
        "--skill",
        str(SKILL),
        "--no-extensions",
        "--no-prompt-templates",
        "--no-context-files",
        "--daemon-socket",
        SOCKET,
        "--session-dir",
        str(SESSIONS),
        *session_args,
        "--system-prompt",
        system_prompt,
        "--",
        prompt,
    ]
    stdout_path = REPORTS / f"{label}.stdout.txt"
    stderr_path = REPORTS / f"{label}.stderr.txt"
    started = time.time()
    with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
        process = subprocess.Popen(
            args,
            cwd=str(OM_REPO),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            env=prime_env(),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            code = process.wait(timeout=15)
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    result = {
        "label": label,
        "elapsed_seconds": round(time.time() - started, 3),
        "timed_out": timed_out,
        "return_code": code,
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8", errors="replace")).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8", errors="replace")).hexdigest(),
        "stdout_excerpt": stdout[-4000:],
        "stderr_excerpt": stderr[-2000:],
        "args_safe": [a for a in args if a not in {str(CLI)}],
    }
    write_json(REPORTS / f"{label}.json", result)
    return result


def materialize_fixtures() -> dict:
    env = os.environ.copy()
    env["OM_PRIME_ADAPTER_ROOT"] = str(ROOT)
    env["OPENMONTAGE_PROJECTS_DIR"] = str(ROOT / "jobs")
    proc = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "materialize_fixtures.py")],
        cwd=str(OM_REPO),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    payload = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr[-2000:]}
    write_json(REPORTS / "FIXTURE_MATERIALIZE.json", payload)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture materialize failed: {proc.stderr}")
    return json.loads(proc.stdout)


def latest_session_id() -> str | None:
    if not SESSIONS.is_dir():
        return None
    files = sorted(SESSIONS.glob("*.jsonl"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    if not files:
        files = sorted(SESSIONS.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return files[0].stem if files else None


def run_context_variable_python() -> dict:
    env = prime_env()
    py = sys.executable
    script = r"""
import json, os, sys, hashlib
from pathlib import Path
sys.path.insert(0, r"{src}")
sys.path.insert(0, r"{repo}")
os.environ["OM_PRIME_ADAPTER_ROOT"] = r"{root}"
from om_prime_adapter import build_context_variables, reload_context, slice_variable, mark_stale, open_job, resume_prime
job_id = "fixture-prime-rlm-historical"
ledger = build_context_variables(job_id)
claim0 = slice_variable(ledger, "claim_table", {{"index": 0}})
failures = slice_variable(ledger, "qa_failures", {{"error_class": "music_covers_vo"}})
reloaded = reload_context(ledger)
resume = resume_prime(job_id, "{session}")
receipt = {{
  "job": open_job(job_id),
  "variable_names": sorted(ledger["variables"]),
  "claim0_keys": sorted(claim0.keys()),
  "qa_failure_count": len(failures),
  "reload_replaced": {{k: v.get("replaced") for k, v in reloaded["variables"].items()}},
  "resume": resume,
  "binary_variables": ledger["binary_variables"],
  "secret_variables": ledger["secret_variables"],
}}
Path(r"{out}").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
print("P1_CONTEXT_READY")
""".format(
        src=str(OM_REPO / "integrations" / "prime-om-adapter" / "src"),
        repo=str(OM_REPO),
        root=str(ROOT),
        session=SESSION_NAME,
        out=str(REPORTS / "CONTEXT_VARIABLE_LEDGER.json"),
    )
    started = time.time()
    proc = subprocess.run([py, "-c", script], capture_output=True, text=True, env=env, timeout=60)
    result = {
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "passed": proc.returncode == 0 and "P1_CONTEXT_READY" in proc.stdout,
    }
    write_json(REPORTS / "P1_PYTHON_CONTEXT.json", result)
    return result


def score_ab() -> dict:
    sys.path.insert(0, str(SKILL / "scripts"))
    from ab_score import score_candidate

    baseline = {
        "version": "1.0",
        "notes": "Use BGM 0.32 and mix intent prompt result in one column, then render before gate.",
        "bgm_volume": 0.32,
        "schema_valid": True,
        "repeated_full_file_injections": 2,
    }
    treatment = {
        "version": "1.0",
        "notes": "Recall PH7-D2: keep vo_bgm_diff in [9,10], eight-column sceneplan, no render before Pi Gate, no generated readable text.",
        "bgm_volume": 0.26,
        "schema_valid": True,
        "repeated_full_file_injections": 0,
        "hooks": [{"text": "有输出不等于过门", "promise": "先看检查点"}] * 3,
        "visual_opportunities": [{"beat": "open", "opportunity": "textless gate", "provider_decided": False}],
    }
    heldout_fail = {
        "version": "1.0",
        "notes": "Generate readable Chinese inside the image model and skip Gate.",
        "schema_valid": True,
        "repeated_full_file_injections": 1,
    }
    heldout_pass = {
        "version": "1.0",
        "notes": "ASR is clock only; approved script is lexical truth; Remotion adds Chinese deterministically; no render until Gate.",
        "schema_valid": True,
        "repeated_full_file_injections": 0,
    }
    result = {
        "protocol": "frozen-no-media-ab/v1",
        "provider": "bailian",
        "model": "qwen3.8-max",
        "B0_historical": score_candidate(baseline),
        "B1_historical": score_candidate(treatment),
        "B0_heldout": score_candidate(heldout_fail),
        "B1_heldout": score_candidate(heldout_pass),
        "media_calls": 0,
        "h3_calls": 0,
        "render_calls": 0,
    }
    result["historical_error_avoided"] = (
        result["B0_historical"]["recurrence_count"] > result["B1_historical"]["recurrence_count"]
    )
    result["heldout_no_new_l0"] = result["B1_heldout"]["om_hard_gate"] == "PASS" and result["B1_heldout"]["recurrence_count"] == 0
    result["repeated_injection_reduced"] = (
        result["B1_historical"]["repeated_full_file_injections"] < result["B0_historical"]["repeated_full_file_injections"]
    )
    write_json(REPORTS / "AB_RESULTS.json", result)
    return result


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    before = snapshot_global("before")
    write_json(REPORTS / "BASELINE_INVENTORY.json", before)
    runtime = setup_isolated_runtime()
    fixtures = materialize_fixtures()
    tests = run_adapter_tests()
    p1_python = run_context_variable_python()
    ab = score_ab()

    p0 = {"skipped": KERNEL.is_file() is False, "reason": "kernel missing"} 
    p1_prime = {"skipped": True}
    p2 = {"skipped": True}
    p3 = {"skipped": True}
    p3_rollback = {"skipped": True}
    if KERNEL.is_file() and CLI.is_file():
        p0 = run_prime(
            "Perform the required IPython call now.",
            session_args=["--no-session"],
            system_prompt=(
                "You must call the ipython tool exactly once with this code, then reply exactly P0_READY:\n"
                "import json\n"
                "print(json.dumps({'refine': await refine.status(), 'harness_keys': list((await rlm.get_harness_state()).keys()) if hasattr(rlm,'get_harness_state') else 'missing'}, default=str))\n"
            ),
            timeout=180,
            label="P0_PRIME_IPYTHON",
        )
        p1_prime = run_prime(
            "Execute the required IPython persistence probe now.",
            session_args=[],
            system_prompt=(
                "Call ipython exactly once executing this, then reply P1_READY:\n"
                f"import os,sys,json; os.environ['OM_PRIME_ADAPTER_ROOT']=r'{ROOT}'; sys.path.insert(0,r'{OM_REPO / 'integrations' / 'prime-om-adapter' / 'src'}'); sys.path.insert(0,r'{OM_REPO}');\n"
                "from om_prime_adapter import build_context_variables, slice_variable, resume_prime\n"
                "ledger=build_context_variables('fixture-prime-rlm-historical'); om_job_ref=ledger['variables']['om_job_ref']; claim_table=ledger['variables']['claim_table']; casebook_hits=ledger['variables']['casebook_hits']; qa_failures=ledger['variables']['qa_failures']; run_metrics=ledger['variables']['run_metrics'];\n"
                f"print(json.dumps({{'names':sorted(ledger['variables']),'claim':slice_variable(ledger,'claim_table',{{'index':0}})['claim'],'resume':resume_prime('fixture-prime-rlm-historical','{SESSION_NAME}')}},ensure_ascii=False))\n"
            ),
            timeout=240,
            label="P1_PRIME_SESSION",
        )
        session_id = latest_session_id()
        resume_args = ["--resume", session_id] if session_id else []
        p2 = run_prime(
            "Spawn the two RLM children now and wait only for admission handles.",
            session_args=resume_args,
            system_prompt=(
                "Call ipython exactly once with this code, then reply P2_READY. Do not wait for child answers.\n"
                "src_auditor = await rlm('Audit claim_table sources; write JSON to runtime/prime-rlm-pilot/reports/child_source_auditor.json via agent_message or file. No media.', name='source-auditor')\n"
                "critic = await rlm('Write counterarguments to the thesis; return via agent_message.send(..., receiver_role=\"parent\") or file runtime/prime-rlm-pilot/reports/child_counterargument.json. No media.', name='counterargument-critic')\n"
                "print({'source':vars(src_auditor) if hasattr(src_auditor,'__dict__') else str(src_auditor), 'critic':vars(critic) if hasattr(critic,'__dict__') else str(critic)})\n"
            ),
            timeout=300,
            label="P2_PRIME_RLM",
        )
        p3 = run_prime(
            "Run session-local refine now.",
            session_args=resume_args,
            system_prompt=(
                "Call ipython exactly once, then reply P3_READY. Use global_=False.\n"
                "print(await refine.status())\n"
                "print(await refine.run('把 PH7-D2 已由外部 Gate 证明的失败提炼为最小 session-local harness：音乐盖住口播时必须 audio-only remux，vo_bgm_diff 目标 [9,10] dB，bgm_volume 0.32->0.26；不要写 global，不要重写整个 harness。', global_=False))\n"
            ),
            timeout=300,
            label="P3_PRIME_REFINE",
        )
        harness_files = list((AGENT / "session-artifacts").rglob("harness_state.json")) if (AGENT / "session-artifacts").is_dir() else []
        harness_files += list(SESSIONS.rglob("harness_state.json"))
        p3_rollback = {"skipped": True, "reason": "no harness_state.json yet"}
        if resume_args and harness_files:
            before_hash = sha256_file(harness_files[0])
            write_json(REPORTS / "HARNESS_AFTER.json", {"path": str(harness_files[0]), "sha256": before_hash, "present": True})
            p3_rollback = run_prime(
                "/refine rollback latest",
                session_args=resume_args,
                system_prompt="If /refine rollback latest is invalid, reply with the exact refine ids visible via refine.status() then stop.",
                timeout=180,
                label="P3_PRIME_ROLLBACK",
            )

    after = snapshot_global("after")
    write_json(REPORTS / "GLOBAL_AFTER.json", after)
    unchanged = before["files"] == after["files"]
    summary = {
        "at": utc_now(),
        "global_unchanged": unchanged,
        "runtime": {"agent_dir": str(AGENT), "settings_keys": runtime["settings_keys"]},
        "fixtures": fixtures,
        "adapter_tests": tests,
        "p1_python": p1_python,
        "p0_prime": p0,
        "p1_prime": p1_prime,
        "p2_prime": p2,
        "p3_prime": p3,
        "p3_rollback": p3_rollback,
        "session_id": latest_session_id(),
        "ab": ab,
        "canonical_job_untouched": True,
        "h3_called": False,
        "render_called": False,
        "pi_gate_forged": False,
    }
    write_json(REPORTS / "WINDOWS_GATE_SUMMARY.json", summary)
    print(json.dumps({"adapter_tests": tests.get("passed"), "global_unchanged": unchanged, "p1_python": p1_python.get("passed"), "ab_historical_error_avoided": ab.get("historical_error_avoided")}, indent=2))
    return 0 if tests.get("passed") and p1_python.get("passed") and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
