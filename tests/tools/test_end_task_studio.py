from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".agents" / "skills" / "end-task-studio" / "scripts" / "end_task.py"
SPEC = importlib.util.spec_from_file_location("end_task_studio", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_upsert(hot: Path, job_id: str, *, focus: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "upsert",
        "--hot-file",
        str(hot),
        "--no-sync",
        "--task",
        f"Task {job_id}",
        "--job-id",
        job_id,
        "--summary",
        f"summary {job_id}",
        "--next-action",
        f"next {job_id}",
        "--saved-by",
        "pytest",
    ]
    if focus:
        command.append("--set-focus")
    return subprocess.run(command, text=True, capture_output=True, check=False)


def test_legacy_singleton_is_migrated_without_loss(tmp_path: Path) -> None:
    hot = tmp_path / "current_task_context.json"
    hot.write_text(
        json.dumps(
            {
                "timestamp": "2026-09-01T11:43:17+08:00",
                "task": "Comfy memory governance",
                "job_id": "sys-comfy",
                "summary": "legacy summary",
                "pending_gate": "RESTART",
                "next_action": "restart Windows",
                "saved_by": "codex",
            }
        ),
        encoding="utf-8",
    )
    result = run_upsert(hot, "h3-sandbox", focus=True)
    assert result.returncode == 0, result.stderr + result.stdout
    document = json.loads(hot.read_text(encoding="utf-8"))
    assert document["schema_version"] == 2
    assert set(document["active_handoffs"]) == {"sys-comfy", "h3-sandbox"}
    assert document["active_handoffs"]["sys-comfy"]["pending_gate"] == "RESTART"
    assert document["focus_job_id"] == "h3-sandbox"


def test_concurrent_writers_do_not_lose_jobs(tmp_path: Path) -> None:
    hot = tmp_path / "current_task_context.json"
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "upsert",
                "--hot-file",
                str(hot),
                "--no-sync",
                "--task",
                f"Task {index}",
                "--job-id",
                f"job-{index}",
                "--summary",
                "concurrency probe",
                "--next-action",
                "continue",
                "--saved-by",
                "pytest",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(8)
    ]
    results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
    assert all(returncode == 0 for _stdout, _stderr, returncode in results), results
    document = json.loads(hot.read_text(encoding="utf-8"))
    assert set(document["active_handoffs"]) == {f"job-{index}" for index in range(8)}
    assert document["revision"] == 8


def test_atomic_replace_failure_preserves_original(tmp_path: Path) -> None:
    hot = tmp_path / "current_task_context.json"
    original = b'{"safe": true}\n'
    hot.write_bytes(original)
    with mock.patch.object(MODULE.os, "replace", side_effect=OSError("injected")):
        try:
            MODULE._atomic_write_json(hot, {"safe": False})
        except OSError:
            pass
        else:
            raise AssertionError("expected injected replace failure")
    assert hot.read_bytes() == original
    assert not list(tmp_path.glob(".current_task_context.json.*.tmp"))


def test_close_is_bounded_and_retargets_focus(tmp_path: Path) -> None:
    hot = tmp_path / "current_task_context.json"
    assert run_upsert(hot, "job-a", focus=True).returncode == 0
    assert run_upsert(hot, "job-b").returncode == 0
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "close",
            "--hot-file",
            str(hot),
            "--no-sync",
            "--job-id",
            "job-a",
            "--reason",
            "complete",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    document = json.loads(hot.read_text(encoding="utf-8"))
    assert "job-a" not in document["active_handoffs"]
    assert document["focus_job_id"] == "job-b"
    assert document["recent_closed"][0]["job_id"] == "job-a"

