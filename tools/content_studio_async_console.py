#!/usr/bin/env python3
"""OM 异步 Director Console - 异步任务提交与状态查询。

扩展 OM Gateway（不修改原文件），支持:
- submit-continuity-regen: 5秒内返回 ACCEPTED，后台启动 worker
- job-status: 查询任务状态 QUEUED -> RUNNING -> AWAITING_REVIEW | FAILED
- build-review-packet: 构建 review_packet/ 目录
- open-prime: 调用 Direct Prime Console
所有命令使用 argparse CLI，JSON 输出。fixture 使用 fake provider / delayed worker。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage"))
JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
PRIME_CHAT_SCRIPT = REPO / "tools" / "run_content_studio_prime_chat.py"
DEFAULT_KERNEL = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_KERNEL_PYTHON",
        r"C:\ContentStudio\runtime\Prime-kernel-venv\Scripts\python.exe",
    )
)

# 任务状态枚举
STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"
STATUS_AWAITING_REVIEW = "AWAITING_REVIEW"
STATUS_FAILED = "FAILED"

# worker 最大重试次数（失败三次停止并报告 root cause）
MAX_WORKER_RETRIES = 3


class ConsoleError(RuntimeError):
    """异步控制台错误。"""


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    """UTC 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    """安全读取 JSON 文件。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConsoleError(f"无法读取 JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConsoleError(f"JSON 不是对象: {path}")
    return data


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """原子写入 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _job_dir(project_id: str) -> Path:
    """获取项目目录。"""
    return JOBS_DIR / project_id


def _jobs_state_dir(project_id: str) -> Path:
    """获取项目异步任务状态目录。"""
    return _job_dir(project_id) / "working" / "async_console" / "jobs"


def _job_status_path(project_id: str, job_id: str) -> Path:
    """获取任务状态文件路径。"""
    return _jobs_state_dir(project_id) / f"{job_id}.json"


def _write_job_status(project_id: str, job_id: str, status: dict[str, Any]) -> None:
    """写入任务状态。"""
    _atomic_write_json(_job_status_path(project_id, job_id), status)


def _read_job_status(project_id: str, job_id: str) -> dict[str, Any] | None:
    """读取任务状态。"""
    path = _job_status_path(project_id, job_id)
    if not path.is_file():
        return None
    return _read_json(path)


# ---------------------------------------------------------------------------
# 异步 worker（fake provider，延迟完成）
# ---------------------------------------------------------------------------
def _delayed_worker(
    project_id: str,
    job_id: str,
    delay_seconds: float,
) -> None:
    """模拟异步 worker：延迟后将状态改为 AWAITING_REVIEW。

    使用 fake provider，不调用真实 API。
    失败三次停止并报告 root cause。
    """
    last_error = ""
    for attempt in range(1, MAX_WORKER_RETRIES + 1):
        try:
            time.sleep(delay_seconds)
            status = _read_job_status(project_id, job_id)
            if not status:
                raise ConsoleError(f"任务状态文件丢失: {job_id}")
            if status.get("status") != STATUS_RUNNING:
                # 已被其他流程处理，不再修改
                return
            status["status"] = STATUS_AWAITING_REVIEW
            status["completed_at"] = _utc_now()
            status["worker_trace"] = "fake_provider_delayed_complete"
            status["worker_attempts"] = attempt
            _write_job_status(project_id, job_id, status)
            return
        except Exception as exc:
            last_error = str(exc)
            # 重试前等待一小段时间
            if attempt < MAX_WORKER_RETRIES:
                time.sleep(1.0)
                continue

    # 失败三次，标记为 FAILED 并记录 root cause
    status = _read_job_status(project_id, job_id) or {}
    status["status"] = STATUS_FAILED
    status["error"] = f"worker 重试 {MAX_WORKER_RETRIES} 次后失败: {last_error}"
    status["failed_at"] = _utc_now()
    status["worker_attempts"] = MAX_WORKER_RETRIES
    _write_job_status(project_id, job_id, status)


# ---------------------------------------------------------------------------
# worker 进程启动
# ---------------------------------------------------------------------------
def _spawn_worker_process(
    project_id: str,
    job_id: str,
    delay_seconds: float,
) -> None:
    """在独立进程中启动 worker，确保主进程退出后 worker 仍可运行。"""
    args = [
        sys.executable,
        "-X", "utf8",
        __file__,
        "--project-id", project_id,
        "_worker",
        "--job-id", job_id,
        "--delay-seconds", str(delay_seconds),
    ]
    # Windows 下使用 DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP
    creationflags = 0
    if sys.platform == "win32":
        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        args,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# 命令: submit-continuity-regen
# ---------------------------------------------------------------------------
def cmd_submit_continuity_regen(
    project_id: str,
    delay_seconds: float = 30.0,
    fixture: bool = False,
) -> dict[str, Any]:
    """提交连续性重新生成任务。

    fixture=True 才允许 delayed fake worker（T2 异步 ACK）。
    生产路径必须走真实 continuity worker。
    """
    job_id = f"continuity-regen-{uuid.uuid4().hex[:12]}"
    status_path = _job_status_path(project_id, job_id)

    initial_status = {
        "schema_version": "content-studio-async-console/v1",
        "job_id": job_id,
        "project_id": project_id,
        "action": "continuity_regen",
        "status": STATUS_QUEUED,
        "status_path": str(status_path),
        "created_at": _utc_now(),
        "delay_seconds": delay_seconds,
        "provider": "fixture_fake" if fixture else "sceneplan_continuity",
        "fixture": fixture,
    }
    _write_job_status(project_id, job_id, initial_status)

    initial_status["status"] = STATUS_RUNNING
    initial_status["started_at"] = _utc_now()
    _write_job_status(project_id, job_id, initial_status)

    if fixture:
        _spawn_worker_process(project_id, job_id, delay_seconds)
        production_started = False
    else:
        _spawn_real_continuity_worker(project_id, job_id)
        production_started = True

    return {
        "status": "ACCEPTED",
        "job_id": job_id,
        "project_id": project_id,
        "action": "continuity_regen",
        "status_path": str(status_path),
        "production_started": production_started,
        "fixture": fixture,
    }


def _spawn_real_continuity_worker(project_id: str, job_id: str) -> None:
    args = [
        sys.executable,
        "-X", "utf8",
        __file__,
        "--project-id", project_id,
        "_real_worker",
        "--job-id", job_id,
    ]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = 0x00000008 | 0x00000200
    subprocess.Popen(
        args,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _real_continuity_worker(project_id: str, job_id: str) -> None:
    """Production worker: evaluate existing VCP; do not invent images."""
    last_error = ""
    for attempt in range(1, MAX_WORKER_RETRIES + 1):
        try:
            from tools.sceneplan_continuity import evaluate_visual_continuity

            project_dir = _job_dir(project_id)
            artifact = project_dir / "artifacts" / "scene_plan.json"
            if not artifact.is_file():
                raise ConsoleError(f"scene_plan 不存在: {artifact}")
            scene_plan = _read_json(artifact)
            evaluation = evaluate_visual_continuity(scene_plan)
            status = _read_job_status(project_id, job_id) or {}
            status["status"] = STATUS_AWAITING_REVIEW
            status["completed_at"] = _utc_now()
            status["worker_trace"] = "sceneplan_continuity_evaluate"
            status["worker_attempts"] = attempt
            status["evaluation"] = evaluation
            status["production_started"] = True
            _write_job_status(project_id, job_id, status)
            return
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_WORKER_RETRIES:
                time.sleep(1.0)
                continue
    status = _read_job_status(project_id, job_id) or {}
    status["status"] = STATUS_FAILED
    status["error"] = f"real worker 重试 {MAX_WORKER_RETRIES} 次后失败: {last_error}"
    status["failed_at"] = _utc_now()
    _write_job_status(project_id, job_id, status)


# ---------------------------------------------------------------------------
# 命令: job-status
# ---------------------------------------------------------------------------
def cmd_job_status(project_id: str, job_id: str) -> dict[str, Any]:
    """查询任务状态。"""
    status = _read_job_status(project_id, job_id)
    if not status:
        return {
            "status": "NOT_FOUND",
            "job_id": job_id,
            "project_id": project_id,
            "error": f"任务不存在: {job_id}",
        }
    return {
        "status": status.get("status", "UNKNOWN"),
        "job_id": job_id,
        "project_id": project_id,
        "action": status.get("action"),
        "created_at": status.get("created_at"),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "failed_at": status.get("failed_at"),
        "error": status.get("error"),
        "worker_trace": status.get("worker_trace"),
        "worker_attempts": status.get("worker_attempts"),
    }


# ---------------------------------------------------------------------------
# 命令: build-review-packet
# ---------------------------------------------------------------------------
def cmd_build_review_packet(project_id: str) -> dict[str, Any]:
    """委托 review_packet_builder；禁止 0/4-byte placeholder。"""
    from tools.review_packet_builder import build_review_packet

    receipt = build_review_packet(project_id)
    contact = Path(receipt["files"]["contact_sheet"])
    if not contact.is_file() or contact.stat().st_size < 1024:
        raise ConsoleError(f"contact sheet 过小或缺失，拒绝 placeholder: {contact}")
    return receipt


# ---------------------------------------------------------------------------
# 命令: open-prime
# ---------------------------------------------------------------------------
def cmd_open_prime(project_id: str) -> dict[str, Any]:
    """调用 Direct Prime Console (run_content_studio_prime_chat.py)。

    在新控制台窗口中启动 Prime Chat 交互式会话。
    """
    if not PRIME_CHAT_SCRIPT.is_file():
        raise ConsoleError(f"Prime Chat 脚本不存在: {PRIME_CHAT_SCRIPT}")

    args = [
        str(DEFAULT_KERNEL),
        "-X", "utf8",
        str(PRIME_CHAT_SCRIPT),
        "--project-id", project_id,
    ]

    # 在新控制台窗口中启动（Windows）
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    try:
        proc = subprocess.Popen(args, creationflags=creationflags)
        return {
            "status": "LAUNCHED",
            "project_id": project_id,
            "pid": proc.pid,
            "script": str(PRIME_CHAT_SCRIPT),
        }
    except FileNotFoundError as exc:
        raise ConsoleError(f"无法启动 Prime Chat: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OM 异步 Director Console - 异步任务提交与状态查询"
    )
    parser.add_argument("--project-id", required=True, help="OM project ID")
    sub = parser.add_subparsers(dest="command", required=True)

    # submit-continuity-regen
    regen_parser = sub.add_parser("submit-continuity-regen")
    regen_parser.add_argument(
        "--delay-seconds", type=float, default=30.0,
        help="fixture worker 延迟完成秒数（默认 30）",
    )
    regen_parser.add_argument(
        "--fixture",
        action="store_true",
        help="仅 T2 异步 ACK 使用 fake delayed worker",
    )

    # job-status
    status_parser = sub.add_parser("job-status")
    status_parser.add_argument("--job-id", required=True, help="任务 ID")

    # build-review-packet
    sub.add_parser("build-review-packet")

    # open-prime
    sub.add_parser("open-prime")

    # _worker（隐藏子命令，由 _spawn_worker_process 调用）
    worker_parser = sub.add_parser("_worker")
    worker_parser.add_argument("--job-id", required=True)
    worker_parser.add_argument("--delay-seconds", type=float, default=30.0)
    real_worker = sub.add_parser("_real_worker")
    real_worker.add_argument("--job-id", required=True)

    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "submit-continuity-regen":
            payload = cmd_submit_continuity_regen(
                args.project_id, args.delay_seconds, fixture=args.fixture
            )
        elif args.command == "job-status":
            payload = cmd_job_status(args.project_id, args.job_id)
        elif args.command == "build-review-packet":
            payload = cmd_build_review_packet(args.project_id)
        elif args.command == "open-prime":
            payload = cmd_open_prime(args.project_id)
        elif args.command == "_worker":
            _delayed_worker(args.project_id, args.job_id, args.delay_seconds)
            return 0
        elif args.command == "_real_worker":
            _real_continuity_worker(args.project_id, args.job_id)
            return 0
        else:
            payload = {"status": "ERROR", "error": f"未知命令: {args.command}"}
    except ConsoleError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
