#!/usr/bin/env python3
"""受控自进化闭环 - Learning System。

实现 learning event 的记录、回归验证、提升和导出。

状态流:
  candidate -> [refine: held-out regression] -> [promote: OM receipt 验证] -> accepted

命令:
  record-event    --type <type> --description <desc> --evidence <path>
  list-events     [--status candidate|accepted|rejected]
  refine          --event-id <id>
  promote         --event-id <id> --promotion-receipt <path>
  casebook-export
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(
    os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage")
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
CASEBOOK_DIR = Path(
    os.environ.get(
        "CONTENT_STUDIO_CASEBOOK_DIR",
        r"C:\ContentStudio\context\openviking\content-studio\casebook",
    )
)
CANDIDATES_DIR = CASEBOOK_DIR / "candidates"
ACCEPTED_DIR = CASEBOOK_DIR / "accepted"
REPO_ROOT = Path(
    os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage")
)
EVENT_TYPES = {
    "continuity_fix",
    "style_adjustment",
    "prompt_improvement",
    "flow_optimization",
}
EVENT_STATUSES = {"candidate", "accepted", "rejected"}
SCHEMA_VERSION = "content-studio-learning-system/v1"


class LearningError(RuntimeError):
    """Learning system 错误。"""


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_compact() -> str:
    """紧凑时间戳，用于 event_id。"""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    """安全读取 JSON 文件。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearningError(f"无法读取 JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LearningError(f"JSON 不是对象: {path}")
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


def _generate_event_id() -> str:
    """生成 event_id: le-YYYYMMDD-HHMMSS-xxx。"""
    suffix = hashlib.sha256(_utc_now().encode()).hexdigest()[:6]
    return f"le-{_utc_compact()}-{suffix}"


def _event_path(event_id: str) -> Path:
    """根据 event_id 推断文件路径（在 candidates 或 accepted 中查找）。"""
    fname = f"{event_id}.json"
    candidate = CANDIDATES_DIR / fname
    accepted = ACCEPTED_DIR / fname
    if candidate.is_file():
        return candidate
    if accepted.is_file():
        return accepted
    # 默认返回 candidates 路径（用于新建）
    return candidate


def _find_event(event_id: str) -> tuple[Path, dict[str, Any]]:
    """查找 event，返回 (path, data)。"""
    path = _event_path(event_id)
    if not path.is_file():
        raise LearningError(f"learning event 不存在: {event_id}")
    return path, _read_json(path)


def _is_event_file(path: Path) -> bool:
    """判断是否为 event 文件（排除 _refine.json 等附属文件）。"""
    return path.is_file() and path.name.startswith("le-") and "_refine" not in path.stem


def _list_event_files(status: str | None = None) -> list[Path]:
    """列出所有 event 文件。"""
    files: list[Path] = []
    if status is None or status == "candidate":
        if CANDIDATES_DIR.is_dir():
            files.extend(f for f in CANDIDATES_DIR.glob("le-*.json") if _is_event_file(f))
    if status is None or status == "accepted":
        if ACCEPTED_DIR.is_dir():
            files.extend(f for f in ACCEPTED_DIR.glob("le-*.json") if _is_event_file(f))
    return sorted(files, key=lambda f: f.name)


# ---------------------------------------------------------------------------
# 命令: record-event
# ---------------------------------------------------------------------------
def cmd_record_event(
    event_type: str,
    description: str,
    evidence_path: str,
) -> dict[str, Any]:
    """记录 learning event 到 candidates/。"""
    if event_type not in EVENT_TYPES:
        raise LearningError(
            f"无效的 event type: {event_type}，允许: {', '.join(sorted(EVENT_TYPES))}"
        )
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    event_id = _generate_event_id()
    event = {
        "event_id": event_id,
        "type": event_type,
        "description": description,
        "evidence_path": evidence_path,
        "status": "candidate",
        "created_at": _utc_now(),
        "regression_result": None,
        "promotion_receipt": None,
    }
    path = CANDIDATES_DIR / f"{event_id}.json"
    _atomic_write_json(path, event)
    return {
        "status": "RECORDED",
        "event_id": event_id,
        "path": str(path),
        "event": event,
    }


# ---------------------------------------------------------------------------
# 命令: list-events
# ---------------------------------------------------------------------------
def cmd_list_events(status: str | None = None) -> dict[str, Any]:
    """列出 learning events。"""
    if status is not None and status not in EVENT_STATUSES:
        raise LearningError(
            f"无效的 status: {status}，允许: {', '.join(sorted(EVENT_STATUSES))}"
        )
    files = _list_event_files(status)
    events: list[dict[str, Any]] = []
    for f in files:
        try:
            data = _read_json(f)
            # 如果指定了 status 但文件实际状态不匹配，跳过
            if status is not None and data.get("status") != status:
                continue
            events.append({
                "event_id": data.get("event_id", f.stem),
                "type": data.get("type"),
                "status": data.get("status"),
                "description": data.get("description", ""),
                "created_at": data.get("created_at"),
                "path": str(f),
            })
        except LearningError:
            continue
    return {
        "status": "OK",
        "count": len(events),
        "filter_status": status,
        "events": events,
    }


# ---------------------------------------------------------------------------
# 命令: refine
# ---------------------------------------------------------------------------
def _simulate_held_out_regression(event: dict[str, Any]) -> dict[str, Any]:
    raise LearningError(
        "hash 模拟 held-out 已禁用。请调用 cmd_refine，它会跑 tests/fixtures/content_studio/learning/"
    )


HELD_OUT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "content_studio" / "learning" / "held_out_continuity.json"


def _run_held_out_regression(event: dict[str, Any]) -> dict[str, Any]:
    """Run the frozen continuity held-out fixture. No hash simulation."""
    if not HELD_OUT_FIXTURE.is_file():
        raise LearningError(f"held-out fixture 不存在: {HELD_OUT_FIXTURE}")
    fixture = _read_json(HELD_OUT_FIXTURE)
    cases = fixture.get("cases") or []
    if not cases:
        raise LearningError("held-out fixture 没有 cases")
    from tools.visual_qa import evaluate_continuity, _load_image

    results = []
    pass_count = 0
    for case in cases:
        left = Path(case["left"])
        right = Path(case["right"])
        if not left.is_absolute():
            left = HELD_OUT_FIXTURE.parent / left
            right = HELD_OUT_FIXTURE.parent / right
        expected = case["expected_continuity"]
        _, left_stat = _load_image(left)
        _, right_stat = _load_image(right)
        verdict, notes = evaluate_continuity(right_stat, left_stat, None)
        ok = verdict == expected
        if ok:
            pass_count += 1
        results.append({
            "id": case.get("id"),
            "expected": expected,
            "actual": verdict,
            "passed": ok,
            "notes": notes,
            "left": str(left),
            "right": str(right),
            "left_bytes": left.stat().st_size,
            "right_bytes": right.stat().st_size,
        })
    test_count = len(results)
    fail_count = test_count - pass_count
    passed = fail_count == 0
    return {
        "test_count": test_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_count / test_count, 4) if test_count else 0.0,
        "threshold": 1.0,
        "passed": passed,
        "method": "held_out_continuity_fixture",
        "fixture": str(HELD_OUT_FIXTURE),
        "event_type": event.get("type"),
        "cases": results,
        "simulation": False,
    }


def cmd_refine(event_id: str) -> dict[str, Any]:
    """对 candidate 经验执行 held-out regression，生成 /refine receipt。"""
    path, event = _find_event(event_id)
    if event.get("status") != "candidate":
        raise LearningError(
            f"只能对 candidate 状态的 event 执行 refine，当前状态: {event.get('status')}"
        )
    before_hash = _sha256_bytes(path.read_bytes())
    regression = _run_held_out_regression(event)
    refine_status = "PASS" if regression["passed"] else "FAIL"
    notes = (
        f"held-out 回归测试{'通过' if regression['passed'] else '失败'}: "
        f"{regression['pass_count']}/{regression['test_count']} 通过"
    )
    receipt = {
        "event_id": event_id,
        "refine_status": refine_status,
        "held_out_regression": regression,
        "before_sha256": before_hash,
        "after_sha256": _sha256_bytes(path.read_bytes()),
        "rollback": {
            "candidate_path": str(path),
            "restore_sha256": before_hash,
        },
        "notes": notes,
        "refined_at": _utc_now(),
        "simulation": False,
    }
    # 更新 event 的 regression_result
    event["regression_result"] = receipt
    _atomic_write_json(path, event)
    # 保存 refine receipt 到单独文件
    receipt_path = CANDIDATES_DIR / f"{event_id}_refine.json"
    _atomic_write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    return receipt


# ---------------------------------------------------------------------------
# 命令: promote
# ---------------------------------------------------------------------------
def cmd_promote(event_id: str, promotion_receipt_path: str) -> dict[str, Any]:
    """提升 candidate 到 accepted（需要 OM promotion receipt 验证）。"""
    path, event = _find_event(event_id)
    if event.get("status") != "candidate":
        raise LearningError(
            f"只能对 candidate 状态的 event 执行 promote，当前状态: {event.get('status')}"
        )
    # 验证 refine 是否已执行且通过
    regression_result = event.get("regression_result")
    if regression_result is None:
        raise LearningError(f"必须先执行 refine 才能 promote: {event_id}")
    if regression_result.get("refine_status") != "PASS":
        raise LearningError(
            f"refine 未通过，无法 promote: refine_status={regression_result.get('refine_status')}"
        )
    # 读取并验证 promotion receipt
    receipt_path = Path(promotion_receipt_path)
    if not receipt_path.is_file():
        raise LearningError(f"promotion receipt 文件不存在: {receipt_path}")
    promotion_receipt = _read_json(receipt_path)
    # 验证 receipt 内容
    if promotion_receipt.get("event_id") != event_id:
        raise LearningError(
            f"promotion receipt 的 event_id 不匹配: "
            f"{promotion_receipt.get('event_id')} != {event_id}"
        )
    if promotion_receipt.get("decision") != "PROMOTE":
        raise LearningError(
            f"promotion receipt 的 decision 不是 PROMOTE: {promotion_receipt.get('decision')}"
        )
    if not promotion_receipt.get("regression_passed"):
        raise LearningError("promotion receipt 的 regression_passed 不是 true")
    if promotion_receipt.get("promoted_by") != "OM-async-console":
        raise LearningError(
            f"promotion receipt 的 promoted_by 不是 OM-async-console: "
            f"{promotion_receipt.get('promoted_by')}"
        )
    # 执行提升：复制到 accepted/，保留 candidate 作为 rollback 源
    ACCEPTED_DIR.mkdir(parents=True, exist_ok=True)
    target_path = ACCEPTED_DIR / f"{event_id}.json"
    event["status"] = "accepted"
    event["promotion_receipt"] = promotion_receipt
    _atomic_write_json(target_path, event)
    rollback_copy = CANDIDATES_DIR / f"{event_id}.pre_promote.json"
    if path.is_file():
        rollback_copy.write_bytes(path.read_bytes())
        path.unlink()
    # 清理 refine receipt
    refine_path = CANDIDATES_DIR / f"{event_id}_refine.json"
    if refine_path.is_file():
        refine_path.unlink()
    return {
        "status": "PROMOTED",
        "event_id": event_id,
        "accepted_path": str(target_path),
        "promotion_receipt": promotion_receipt,
        "rollback_copy": str(rollback_copy),
        "promoted_at": _utc_now(),
    }


def cmd_rollback(event_id: str) -> dict[str, Any]:
    """Restore candidate from pre_promote copy; accepted file is quarantined not deleted."""
    accepted = ACCEPTED_DIR / f"{event_id}.json"
    rollback_copy = CANDIDATES_DIR / f"{event_id}.pre_promote.json"
    candidate = CANDIDATES_DIR / f"{event_id}.json"
    if not rollback_copy.is_file() and not candidate.is_file():
        raise LearningError(f"没有 rollback 源: {event_id}")
    source = rollback_copy if rollback_copy.is_file() else candidate
    before = _sha256_bytes(source.read_bytes())
    if accepted.is_file():
        tomb = ACCEPTED_DIR / f"{event_id}.rolled_back.json"
        tomb.write_bytes(accepted.read_bytes())
        accepted.unlink()
    data = _read_json(source)
    data["status"] = "candidate"
    _atomic_write_json(candidate, data)
    return {
        "status": "ROLLED_BACK",
        "event_id": event_id,
        "restored_path": str(candidate),
        "restore_sha256": before,
        "rolled_back_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# 命令: casebook-export
# ---------------------------------------------------------------------------
def cmd_casebook_export() -> dict[str, Any]:
    """导出 casebook 为 JSON。"""
    candidates: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    # 收集 candidates（排除 _refine.json 等附属文件）
    if CANDIDATES_DIR.is_dir():
        for f in sorted(CANDIDATES_DIR.glob("le-*.json")):
            if not _is_event_file(f):
                continue
            try:
                candidates.append(_read_json(f))
            except LearningError:
                continue
    # 收集 accepted
    if ACCEPTED_DIR.is_dir():
        for f in sorted(ACCEPTED_DIR.glob("le-*.json")):
            if not _is_event_file(f):
                continue
            try:
                accepted.append(_read_json(f))
            except LearningError:
                continue
    export = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": _utc_now(),
        "casebook_dir": str(CASEBOOK_DIR),
        "candidates": candidates,
        "accepted": accepted,
        "summary": {
            "candidate_count": len(candidates),
            "accepted_count": len(accepted),
            "total": len(candidates) + len(accepted),
        },
    }
    return export


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="受控自进化闭环 - Learning System"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # record-event
    rec = sub.add_parser("record-event")
    rec.add_argument("--type", required=True, help="event 类型")
    rec.add_argument("--description", required=True, help="中文描述")
    rec.add_argument("--evidence", required=True, help="evidence 路径（repo-relative）")

    # list-events
    lst = sub.add_parser("list-events")
    lst.add_argument(
        "--status",
        choices=sorted(EVENT_STATUSES),
        default=None,
        help="按状态过滤",
    )

    # refine
    ref = sub.add_parser("refine")
    ref.add_argument("--event-id", required=True, help="event ID")

    # promote
    prom = sub.add_parser("promote")
    prom.add_argument("--event-id", required=True, help="event ID")
    prom.add_argument("--promotion-receipt", required=True, help="OM promotion receipt 路径")

    rb = sub.add_parser("rollback")
    rb.add_argument("--event-id", required=True)

    # casebook-export
    sub.add_parser("casebook-export")

    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "record-event":
            result = cmd_record_event(args.type, args.description, args.evidence)
        elif args.command == "list-events":
            result = cmd_list_events(args.status)
        elif args.command == "refine":
            result = cmd_refine(args.event_id)
        elif args.command == "promote":
            result = cmd_promote(args.event_id, args.promotion_receipt)
        elif args.command == "rollback":
            result = cmd_rollback(args.event_id)
        elif args.command == "casebook-export":
            result = cmd_casebook_export()
        else:
            result = {"status": "ERROR", "error": f"未知命令: {args.command}"}
    except (LearningError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
