from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
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
        "unittest",
    ]
    if focus:
        command.append("--set-focus")
    return subprocess.run(command, text=True, capture_output=True, check=False)


class EndTaskStudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_legacy_singleton_is_migrated_without_loss(self) -> None:
        hot = self.root / "current_task_context.json"
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
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        document = json.loads(hot.read_text(encoding="utf-8"))
        self.assertEqual(document["schema_version"], 2)
        self.assertEqual(set(document["active_handoffs"]), {"sys-comfy", "h3-sandbox"})
        self.assertEqual(document["active_handoffs"]["sys-comfy"]["pending_gate"], "RESTART")
        self.assertEqual(document["focus_job_id"], "h3-sandbox")

    def test_concurrent_writers_do_not_lose_jobs(self) -> None:
        hot = self.root / "current_task_context.json"
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
                    "unittest",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(8)
        ]
        results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
        self.assertTrue(all(returncode == 0 for _stdout, _stderr, returncode in results), results)
        document = json.loads(hot.read_text(encoding="utf-8"))
        self.assertEqual(set(document["active_handoffs"]), {f"job-{index}" for index in range(8)})
        self.assertEqual(document["revision"], 8)

    def test_reupsert_one_job_preserves_the_other(self) -> None:
        hot = self.root / "current_task_context.json"
        self.assertEqual(run_upsert(hot, "job-a", focus=True).returncode, 0)
        self.assertEqual(run_upsert(hot, "job-b").returncode, 0)
        before = json.loads(hot.read_text(encoding="utf-8"))["active_handoffs"]["job-b"]
        self.assertEqual(run_upsert(hot, "job-a", focus=True).returncode, 0)
        document = json.loads(hot.read_text(encoding="utf-8"))
        self.assertEqual(document["active_handoffs"]["job-b"], before)
        self.assertEqual(document["focus_job_id"], "job-a")

    def test_atomic_replace_failure_preserves_original(self) -> None:
        hot = self.root / "current_task_context.json"
        original = b'{"safe": true}\n'
        hot.write_bytes(original)
        with mock.patch.object(MODULE.os, "replace", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                MODULE._atomic_write_json(hot, {"safe": False})
        self.assertEqual(hot.read_bytes(), original)
        self.assertFalse(list(self.root.glob(".current_task_context.json.*.tmp")))

    def test_semantic_hash_tolerates_openviking_trailing_newline_normalization(self) -> None:
        with_newline = '{"job_id":"a","summary":"中文"}\n'
        without_newline = '{"job_id":"a","summary":"中文"}'
        self.assertEqual(MODULE._semantic_json_sha(with_newline), MODULE._semantic_json_sha(without_newline))

    def test_close_is_bounded_and_retargets_focus(self) -> None:
        hot = self.root / "current_task_context.json"
        self.assertEqual(run_upsert(hot, "job-a", focus=True).returncode, 0)
        self.assertEqual(run_upsert(hot, "job-b").returncode, 0)
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
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        document = json.loads(hot.read_text(encoding="utf-8"))
        self.assertNotIn("job-a", document["active_handoffs"])
        self.assertEqual(document["focus_job_id"], "job-b")
        self.assertEqual(document["recent_closed"][0]["job_id"], "job-a")


if __name__ == "__main__":
    unittest.main()
