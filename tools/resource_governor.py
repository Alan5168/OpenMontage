#!/usr/bin/env python3
"""资源治理模块 - Resource Governor。

负责磁盘/GC/GPU 的状态检查和资源回收。

命令:
  disk-status       检查磁盘使用率，对比 BASELINE
  gc --dry-run      扫描可回收空间（dry-run）
  gc --execute      执行垃圾回收（只回收 dry-run 发现的且超过 7 天的）
  gpu-status        检查 GPU 显存占用
  threshold-check   检查是否超过 warn(80%)/block(90%) 阈值
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
CONTENT_STUDIO_ROOT = Path(r"C:\ContentStudio")
WARN_THRESHOLD = 80  # 磁盘使用率告警阈值
BLOCK_THRESHOLD = 90  # 磁盘使用率阻塞阈值
GC_AGE_THRESHOLD_DAYS = 7  # GC 只回收超过此天数的文件
QUARANTINE_ROOT = Path(
    os.environ.get(
        "CONTENT_STUDIO_QUARANTINE",
        r"C:\ContentStudio\quarantine\gc",
    )
)
PRESERVE_NAMES = {
    "project.json",
    "job_manifest.json",
    "decision_log.json",
    "LICENSE",
    "license.json",
}
# GC 扫描的目标模式
GC_SCAN_PATTERNS = [
    "working/review_packet",  # 过期的 review packet
    "working/async_console",  # 旧 job cache
    "working/tmp",  # 临时文件
    "renders",  # 旧渲染产物（超过阈值时）
]
GC_MAX_RENDER_AGE_DAYS = 30  # renders 目录最大保留天数
SCHEMA_VERSION = "content-studio-resource-governor/v1"


class GovernorError(RuntimeError):
    """资源治理错误。"""


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    """安全读取 JSON 文件。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernorError(f"无法读取 JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GovernorError(f"JSON 不是对象: {path}")
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


def _disk_usage_pct(path: Path) -> float:
    """获取磁盘使用率百分比。"""
    usage = shutil.disk_usage(str(path))
    return round(usage.used / usage.total * 100, 1)


def _disk_usage_detail(path: Path) -> dict[str, Any]:
    """获取磁盘使用详情。"""
    usage = shutil.disk_usage(str(path))
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_pct": round(usage.used / usage.total * 100, 1),
    }


def _dir_size(path: Path) -> int:
    """递归计算目录大小。"""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _file_age_days(path: Path) -> float:
    """获取文件/目录的修改时间距今天数。"""
    try:
        mtime = path.stat().st_mtime
        age_seconds = time.time() - mtime
        return round(age_seconds / 86400, 1)
    except OSError:
        return 0.0


# ---------------------------------------------------------------------------
# 命令: disk-status
# ---------------------------------------------------------------------------
def cmd_disk_status() -> dict[str, Any]:
    """检查磁盘使用率。"""
    detail = _disk_usage_detail(CONTENT_STUDIO_ROOT)
    used_pct = detail["used_pct"]
    if used_pct >= BLOCK_THRESHOLD:
        status = "BLOCK"
    elif used_pct >= WARN_THRESHOLD:
        status = "WARN"
    else:
        status = "OK"
    return {
        "schema_version": SCHEMA_VERSION,
        "disk": {
            "used_pct": used_pct,
            "total_bytes": detail["total_bytes"],
            "used_bytes": detail["used_bytes"],
            "free_bytes": detail["free_bytes"],
            "warn_threshold": WARN_THRESHOLD,
            "block_threshold": BLOCK_THRESHOLD,
            "status": status,
        },
        "checked_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# 命令: gc (dry-run / execute)
# ---------------------------------------------------------------------------
def _scan_gc_candidates() -> list[dict[str, Any]]:
    """扫描可回收空间，返回候选列表。"""
    candidates: list[dict[str, Any]] = []
    if not JOBS_DIR.is_dir():
        return candidates
    for project_dir in JOBS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        for pattern in GC_SCAN_PATTERNS:
            target = project_dir / pattern
            if not target.exists():
                continue
            size = _dir_size(target) if target.is_dir() else target.stat().st_size
            age = _file_age_days(target)
            # renders 目录有更长的保留期
            min_age = GC_MAX_RENDER_AGE_DAYS if pattern == "renders" else GC_AGE_THRESHOLD_DAYS
            safe = age > min_age
            candidates.append({
                "path": str(target),
                "size_bytes": size,
                "age_days": age,
                "pattern": pattern,
                "safe_to_delete": safe,
                "min_age_threshold": min_age,
            })
    return candidates


def _quarantine_move(src: Path, reason: str) -> dict[str, Any]:
    """Move to quarantine/trash with manifest; never unlink/rmtree production files."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_root = QUARANTINE_ROOT / stamp
    dest = dest_root / src.name
    dest_root.mkdir(parents=True, exist_ok=True)
    sha = ""
    size = 0
    if src.is_file():
        size = src.stat().st_size
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        shutil.move(str(src), str(dest))
    else:
        size = _dir_size(src)
        shutil.move(str(src), str(dest))
    receipt = {
        "source": str(src),
        "quarantine_path": str(dest),
        "reason": reason,
        "sha256": sha,
        "size_bytes": size,
        "moved_at": _utc_now(),
        "restore": {
            "command": "resource_governor.py gc-restore --manifest <this>",
            "destination": str(src),
        },
    }
    (dest_root / "MANIFEST.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


def cmd_gc(execute: bool = False) -> dict[str, Any]:
    """Quarantine GC. execute=False is dry-run. Never direct-delete."""
    candidates = _scan_gc_candidates()
    quarantined: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if execute:
        for cand in candidates:
            if not cand["safe_to_delete"]:
                skipped.append(cand)
                continue
            path = Path(cand["path"])
            try:
                receipt = _quarantine_move(path, f"gc:{cand['pattern']}")
                cand["quarantined"] = True
                cand["receipt"] = receipt
                quarantined.append(cand)
            except OSError as exc:
                cand["quarantined"] = False
                cand["error"] = str(exc)
                skipped.append(cand)
    total_size = sum(c["size_bytes"] for c in candidates)
    moved_size = sum(c["size_bytes"] for c in quarantined)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "EXECUTE_QUARANTINE" if execute else "DRY_RUN",
        "direct_delete": False,
        "gc_candidates": candidates,
        "quarantined": quarantined if execute else [],
        "deleted": [],
        "skipped": skipped if execute else [],
        "summary": {
            "candidate_count": len(candidates),
            "safe_to_delete_count": sum(1 for c in candidates if c["safe_to_delete"]),
            "quarantined_count": len(quarantined),
            "skipped_count": len(skipped),
            "total_candidate_size_bytes": total_size,
            "reclaimed_bytes": moved_size,
            "bytes_generated": None,
            "bytes_retained": None,
        },
        "gc_age_threshold_days": GC_AGE_THRESHOLD_DAYS,
        "quarantine_root": str(QUARANTINE_ROOT),
        "scanned_at": _utc_now(),
    }


def cmd_gc_restore(manifest_path: str) -> dict[str, Any]:
    path = Path(manifest_path)
    receipt = _read_json(path)
    src = Path(receipt["quarantine_path"])
    dest = Path(receipt["restore"]["destination"])
    if not src.exists():
        raise GovernorError(f"quarantine 源不存在: {src}")
    if dest.exists():
        raise GovernorError(f"恢复目标已存在，拒绝覆盖: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return {
        "status": "RESTORED",
        "from": str(src),
        "to": str(dest),
        "restored_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# 命令: gpu-status
# ---------------------------------------------------------------------------
def _query_nvidia_smi() -> dict[str, Any] | None:
    """通过 nvidia-smi 查询 GPU 显存占用。

    返回 {"vram_used_mib": int, "vram_free_mib": int, "vram_total_mib": int} 或 None。
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.free,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip().split("\n")[0].strip()
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            return None
        return {
            "vram_used_mib": int(parts[0]),
            "vram_free_mib": int(parts[1]),
            "vram_total_mib": int(parts[2]),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None


def cmd_gpu_status() -> dict[str, Any]:
    """检查 GPU 显存占用。"""
    gpu_info = _query_nvidia_smi()
    if gpu_info is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "gpu": {
                "vram_used_mib": 0,
                "vram_free_mib": 0,
                "vram_total_mib": 0,
                "status": "UNAVAILABLE",
                "message": "nvidia-smi 不可用或无 NVIDIA GPU",
            },
            "checked_at": _utc_now(),
        }
    used_pct = round(
        gpu_info["vram_used_mib"] / gpu_info["vram_total_mib"] * 100, 1
    ) if gpu_info["vram_total_mib"] > 0 else 0.0
    if used_pct >= BLOCK_THRESHOLD:
        status = "BLOCK"
    elif used_pct >= WARN_THRESHOLD:
        status = "WARN"
    else:
        status = "OK"
    return {
        "schema_version": SCHEMA_VERSION,
        "gpu": {
            "vram_used_mib": gpu_info["vram_used_mib"],
            "vram_free_mib": gpu_info["vram_free_mib"],
            "vram_total_mib": gpu_info["vram_total_mib"],
            "vram_used_pct": used_pct,
            "status": status,
        },
        "checked_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# 命令: threshold-check
# ---------------------------------------------------------------------------
def cmd_threshold_check() -> dict[str, Any]:
    """检查磁盘和 GPU 是否超过 warn/block 阈值。"""
    disk = cmd_disk_status()
    gpu = cmd_gpu_status()
    disk_status = disk["disk"]["status"]
    gpu_status = gpu["gpu"]["status"]
    # 综合状态：任一 BLOCK 则 BLOCK，任一 WARN 则 WARN
    if "BLOCK" in (disk_status, gpu_status):
        overall = "BLOCK"
    elif "WARN" in (disk_status, gpu_status):
        overall = "WARN"
    else:
        overall = "OK"
    return {
        "schema_version": SCHEMA_VERSION,
        "overall_status": overall,
        "disk": disk["disk"],
        "gpu": gpu["gpu"],
        "thresholds": {
            "warn": WARN_THRESHOLD,
            "block": BLOCK_THRESHOLD,
        },
        "checked_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="资源治理模块 - Resource Governor"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # disk-status
    sub.add_parser("disk-status")

    # gc
    gc_parser = sub.add_parser("gc")
    gc_mode = gc_parser.add_mutually_exclusive_group(required=True)
    gc_mode.add_argument("--dry-run", action="store_true", help="只扫描不删除")
    gc_mode.add_argument("--execute", action="store_true", help="移入 quarantine（可恢复）")

    restore = sub.add_parser("gc-restore")
    restore.add_argument("--manifest", required=True, help="quarantine MANIFEST.json")

    # gpu-status
    sub.add_parser("gpu-status")

    # threshold-check
    sub.add_parser("threshold-check")

    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "disk-status":
            result = cmd_disk_status()
        elif args.command == "gc":
            result = cmd_gc(execute=args.execute)
        elif args.command == "gc-restore":
            result = cmd_gc_restore(args.manifest)
        elif args.command == "gpu-status":
            result = cmd_gpu_status()
        elif args.command == "threshold-check":
            result = cmd_threshold_check()
        else:
            result = {"status": "ERROR", "error": f"未知命令: {args.command}"}
    except (GovernorError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
