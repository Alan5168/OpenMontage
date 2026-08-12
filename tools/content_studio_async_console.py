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
) -> dict[str, Any]:
    """提交连续性重新生成任务。

    5秒内返回 ACCEPTED，后台启动 worker。
    状态流: QUEUED -> RUNNING -> AWAITING_REVIEW | FAILED
    """
    job_id = f"continuity-regen-{uuid.uuid4().hex[:12]}"
    status_path = _job_status_path(project_id, job_id)

    # 初始状态: QUEUED
    initial_status = {
        "schema_version": "content-studio-async-console/v1",
        "job_id": job_id,
        "project_id": project_id,
        "action": "continuity_regen",
        "status": STATUS_QUEUED,
        "status_path": str(status_path),
        "created_at": _utc_now(),
        "delay_seconds": delay_seconds,
        "provider": "fake",
    }
    _write_job_status(project_id, job_id, initial_status)

    # 立即转为 RUNNING
    initial_status["status"] = STATUS_RUNNING
    initial_status["started_at"] = _utc_now()
    _write_job_status(project_id, job_id, initial_status)

    # 后台启动 worker（独立进程，确保进程退出后 worker 仍可运行）
    _spawn_worker_process(project_id, job_id, delay_seconds)

    return {
        "status": "ACCEPTED",
        "job_id": job_id,
        "project_id": project_id,
        "action": "continuity_regen",
        "status_path": str(status_path),
        "production_started": False,
    }


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
def _create_placeholder_jpeg(path: Path) -> None:
    """创建 contact_sheet.jpg 占位文件（最小 JPEG: SOI + EOI）。"""
    # FF D8 = SOI (Start Of Image), FF D9 = EOI (End Of Image)
    path.write_bytes(b"\xff\xd8\xff\xd9")


def _build_visual_qa_schema(project_id: str) -> dict[str, Any]:
    """构建 VISUAL_QA.schema.json 内容。"""
    return {
        "schema_version": "visual-qa/v1",
        "project_id": project_id,
        "created_at": _utc_now(),
        "checks": [
            {
                "id": "continuity",
                "label": "视觉连续性",
                "status": "pending",
                "required": True,
            },
            {
                "id": "composition",
                "label": "构图一致性",
                "status": "pending",
                "required": True,
            },
            {
                "id": "color_grading",
                "label": "调色一致性",
                "status": "pending",
                "required": True,
            },
            {
                "id": "character_consistency",
                "label": "角色一致性",
                "status": "pending",
                "required": False,
            },
        ],
        "overall_status": "pending",
    }


def cmd_build_review_packet(project_id: str) -> dict[str, Any]:
    """构建 review_packet/ 目录。

    包含: contact_sheet.jpg 占位 + manifest.json + images/ + VISUAL_QA.schema.json
    """
    project_dir = _job_dir(project_id)
    packet_dir = project_dir / "working" / "review_packet"
    images_dir = packet_dir / "images"

    # 创建目录结构
    packet_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # contact_sheet.jpg 占位文件
    contact_sheet = packet_dir / "contact_sheet.jpg"
    _create_placeholder_jpeg(contact_sheet)

    # VISUAL_QA.schema.json
    qa_schema = _build_visual_qa_schema(project_id)
    qa_path = packet_dir / "VISUAL_QA.schema.json"
    _atomic_write_json(qa_path, qa_schema)

    # images/.gitkeep 占位
    (images_dir / ".gitkeep").write_text("", encoding="utf-8")

    # manifest.json
    manifest = {
        "schema_version": "content-studio-review-packet/v1",
        "project_id": project_id,
        "created_at": _utc_now(),
        "contact_sheet": {
            "path": "contact_sheet.jpg",
            "sha256": _sha256_file(contact_sheet),
            "type": "placeholder",
        },
        "images_dir": "images/",
        "visual_qa_schema": "VISUAL_QA.schema.json",
        "visual_qa_sha256": _sha256_file(qa_path),
        "items": [],
    }
    manifest_path = packet_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)

    return {
        "status": "BUILT",
        "project_id": project_id,
        "packet_dir": str(packet_dir),
        "files": {
            "contact_sheet": str(contact_sheet),
            "manifest": str(manifest_path),
            "visual_qa_schema": str(qa_path),
            "images_dir": str(images_dir),
        },
        "manifest_sha256": _sha256_file(manifest_path),
    }


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
        help="worker 延迟完成秒数（默认 30）",
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

    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "submit-continuity-regen":
            payload = cmd_submit_continuity_regen(args.project_id, args.delay_seconds)
        elif args.command == "job-status":
            payload = cmd_job_status(args.project_id, args.job_id)
        elif args.command == "build-review-packet":
            payload = cmd_build_review_packet(args.project_id)
        elif args.command == "open-prime":
            payload = cmd_open_prime(args.project_id)
        elif args.command == "_worker":
            # 隐藏子命令：运行 delayed worker，不输出 JSON
            _delayed_worker(args.project_id, args.job_id, args.delay_seconds)
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
