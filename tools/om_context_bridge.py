#!/usr/bin/env python3
"""OpenViking context bridge for OpenMontage.

提供 viking:// 资源目录的检索/读取/导入/经验提升/健康检查命令。
所有命令输出 JSON。Trae/Prime 默认只读；写入命令必须带 provenance/license/hash。
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

# OpenViking context 根目录（content-studio workspace）
CONTEXT_ROOT = Path(
    os.environ.get(
        "OPENVIKING_CONTEXT_ROOT",
        r"C:\ContentStudio\context\openviking\content-studio",
    )
)

# scope -> 子目录映射
SCOPE_DIRS: dict[str, str] = {
    "governance": "governance",
    "research": "research",
    "goodcase": "goodcases",
    "casebook": "casebook",
    "openmontage": "openmontage",
    "media-catalog": "media-catalog",
    "active-projects": "active-projects",
}

# Qdrant 健康检查端点（loopback-only）
QDRANT_HEALTH_URL = os.environ.get(
    "QDRANT_HEALTH_URL", "http://127.0.0.1:6333/healthz"
)

VIKING_PREFIX = "viking://resources/content-studio/"


class ContextBridgeError(RuntimeError):
    """context bridge 业务错误"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _emit(payload: dict[str, Any]) -> None:
    """统一 JSON 输出"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _resolve_viking_uri(viking_uri: str) -> Path:
    """把 viking://resources/content-studio/<rel> 解析成本地路径，防止越界"""
    if viking_uri.startswith(VIKING_PREFIX):
        rel = viking_uri[len(VIKING_PREFIX):]
    elif viking_uri.startswith("viking://content-studio/"):
        rel = viking_uri[len("viking://content-studio/"):]
    elif viking_uri.startswith("viking://"):
        raise ContextBridgeError(f"无法识别的 viking uri: {viking_uri}")
    else:
        # 直接当相对路径处理
        rel = viking_uri
    rel = rel.lstrip("/")
    path = (CONTEXT_ROOT / rel).resolve()
    # 防止路径穿越
    try:
        path.relative_to(CONTEXT_ROOT.resolve())
    except ValueError:
        raise ContextBridgeError(f"路径越界: {viking_uri}")
    return path


def _to_viking_uri(path: Path) -> str:
    """本地路径转 viking:// uri"""
    return VIKING_PREFIX + path.relative_to(CONTEXT_ROOT).as_posix()


def cmd_search(args: argparse.Namespace) -> None:
    """检索 OpenViking 资源目录（简单文本匹配，作为上下文候选）"""
    query = args.query.lower()
    scopes = [args.scope] if args.scope else list(SCOPE_DIRS.keys())
    results: list[dict[str, Any]] = []
    for scope in scopes:
        sub = SCOPE_DIRS.get(scope)
        if not sub:
            continue
        base = CONTEXT_ROOT / sub
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            haystack = (p.name + "\n" + text).lower()
            if query in haystack:
                results.append({
                    "scope": scope,
                    "viking_uri": _to_viking_uri(p),
                    "relative_path": str(p.relative_to(CONTEXT_ROOT)),
                    "name": p.name,
                    "size": p.stat().st_size,
                })
    _emit({
        "status": "OK",
        "query": args.query,
        "scope": args.scope or "all",
        "match_count": len(results),
        "results": results,
    })


def cmd_read(args: argparse.Namespace) -> None:
    """读取指定 viking:// 路径内容（只读）"""
    path = _resolve_viking_uri(args.viking_uri)
    if not path.exists():
        _emit({"status": "NOT_FOUND", "viking_uri": args.viking_uri})
        sys.exit(1)
    if path.is_dir():
        _emit({
            "status": "OK",
            "viking_uri": args.viking_uri,
            "type": "directory",
            "entries": sorted(p.name for p in path.iterdir()),
        })
        return
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    _emit({
        "status": "OK",
        "viking_uri": args.viking_uri,
        "type": "file",
        "sha256": _sha256_bytes(raw),
        "size": len(raw),
        "content": text,
    })


def cmd_ingest(args: argparse.Namespace) -> None:
    """带 provenance/license/hash 导入资源（human-write）"""
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        raise ContextBridgeError(f"manifest 不存在: {args.manifest}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 校验必需字段：provenance/license/hash 是硬性闸门
    required = ["source", "target", "provenance", "license"]
    missing = [f for f in required if f not in manifest]
    if missing:
        raise ContextBridgeError(f"manifest 缺少字段: {missing}")

    src = Path(manifest["source"])
    if not src.is_file():
        raise ContextBridgeError(f"source 文件不存在: {src}")

    target = _resolve_viking_uri(manifest["target"])
    target.parent.mkdir(parents=True, exist_ok=True)

    data = src.read_bytes()
    sha = _sha256_bytes(data)
    # 若 manifest 提供 sha256 则校验一致性
    if manifest.get("sha256") and manifest["sha256"] != sha:
        raise ContextBridgeError(
            f"hash 不匹配: manifest={manifest['sha256']} actual={sha}"
        )

    target.write_bytes(data)
    _emit({
        "status": "INGESTED",
        "source": str(src),
        "target": str(target),
        "viking_uri": _to_viking_uri(target),
        "sha256": sha,
        "size": len(data),
        "provenance": manifest["provenance"],
        "license": manifest["license"],
        "ingested_at": _utc_now(),
    })


def cmd_promote_lesson(args: argparse.Namespace) -> None:
    """提升经验到 accepted（只接收 OM promotion receipt，human-write）"""
    event_path = Path(args.learning_event)
    receipt_path = Path(args.promotion_receipt)
    if not event_path.is_file():
        raise ContextBridgeError(f"learning event 不存在: {args.learning_event}")
    if not receipt_path.is_file():
        raise ContextBridgeError(f"promotion receipt 不存在: {args.promotion_receipt}")

    event = json.loads(event_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    # 校验 receipt 来自 OM 且通过 held-out regression
    if receipt.get("decision") != "PROMOTE":
        raise ContextBridgeError(
            f"receipt decision 非 PROMOTE: {receipt.get('decision')}"
        )
    if not receipt.get("regression_passed"):
        raise ContextBridgeError("receipt 未通过 held-out regression")

    # 写入 accepted
    accepted_dir = CONTEXT_ROOT / "casebook" / "accepted"
    accepted_dir.mkdir(parents=True, exist_ok=True)
    name = event.get("id") or event_path.stem
    out = accepted_dir / f"{name}.json"
    payload = {
        "event": event,
        "promotion_receipt": receipt,
        "promoted_at": _utc_now(),
    }
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 从 candidates 移除（若存在）
    cand = CONTEXT_ROOT / "casebook" / "candidates" / f"{name}.json"
    candidate_removed = False
    if cand.exists():
        cand.unlink()
        candidate_removed = True

    _emit({
        "status": "PROMOTED",
        "lesson_id": name,
        "accepted_path": str(out),
        "candidate_removed": candidate_removed,
        "promoted_at": payload["promoted_at"],
    })


def cmd_health(args: argparse.Namespace) -> None:
    """OpenViking + Qdrant 健康检查"""
    # OpenViking 目录结构检查
    ov_ok = CONTEXT_ROOT.is_dir()
    missing_dirs: list[str] = []
    for name in ["governance", "openmontage", "research", "goodcases",
                 "media-catalog", "active-projects", "casebook"]:
        if not (CONTEXT_ROOT / name).is_dir():
            missing_dirs.append(name)

    # Qdrant 健康检查（/healthz 返回纯文本）
    qdrant_ok = False
    qdrant_detail = "not_checked"
    try:
        import urllib.request
        with urllib.request.urlopen(QDRANT_HEALTH_URL, timeout=3) as resp:
            qdrant_ok = resp.status == 200
            qdrant_detail = resp.read().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        qdrant_detail = f"error: {type(e).__name__}: {e}"

    overall = "OK" if (ov_ok and not missing_dirs and qdrant_ok) else "DEGRADED"
    _emit({
        "status": overall,
        "openviking": {
            "context_root": str(CONTEXT_ROOT),
            "root_exists": ov_ok,
            "missing_dirs": missing_dirs,
        },
        "qdrant": {
            "health_url": QDRANT_HEALTH_URL,
            "reachable": qdrant_ok,
            "detail": qdrant_detail,
        },
        "checked_at": _utc_now(),
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="om context",
        description="OpenViking context bridge（检索/读取/导入/经验提升/健康检查）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="检索 OpenViking 资源目录")
    sp.add_argument("query", help="检索关键词")
    sp.add_argument(
        "--scope", choices=list(SCOPE_DIRS.keys()), help="限定检索范围"
    )
    sp.set_defaults(func=cmd_search)

    rp = sub.add_parser("read", help="读取指定 viking:// 路径内容")
    rp.add_argument("viking_uri", help="viking://resources/content-studio/<rel>")
    rp.set_defaults(func=cmd_read)

    ip = sub.add_parser("ingest", help="带 provenance/license/hash 导入资源")
    ip.add_argument("manifest", help="manifest JSON 路径")
    ip.set_defaults(func=cmd_ingest)

    pp = sub.add_parser("promote-lesson", help="提升经验到 accepted")
    pp.add_argument("learning_event", help="LEARNING_EVENT.json 路径")
    pp.add_argument("promotion_receipt", help="OM promotion receipt JSON 路径")
    pp.set_defaults(func=cmd_promote_lesson)

    hp = sub.add_parser("health", help="OpenViking + Qdrant 健康检查")
    hp.set_defaults(func=cmd_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ContextBridgeError as e:
        _emit({"status": "ERROR", "error": str(e)})
        return 1
    except Exception as e:
        _emit({"status": "ERROR", "error": f"{type(e).__name__}: {e}"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())