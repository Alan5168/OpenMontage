#!/usr/bin/env python3
"""Qdrant media bridge for OpenMontage.

提供 nf_stock_footage_v1 素材检索/解析/健康检查命令。
调用现有 Windows Qdrant（127.0.0.1:6333），不重嵌入、不复制第二份向量。
embedding 使用本地 Qwen3-Embedding-0.6B 服务；HTTP 走 stdlib urllib，无需额外依赖。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import URLError

# Qdrant 配置（loopback-only）
QDRANT_BASE_URL = os.environ.get("QDRANT_BASE_URL", "http://127.0.0.1:6333")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "nf_stock_footage_v1")

# 素材根目录
MEDIA_STOCK_ROOT = Path(
    os.environ.get("MEDIA_STOCK_ROOT", r"C:\ContentStudio\media\stock")
)

# embedding 服务端点（本地）
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://127.0.0.1:8001/embed")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")

# license_risk 等级映射，用于 license-policy 过滤
LICENSE_LEVELS: dict[str, list[str]] = {
    "low-risk": ["low-risk"],
    "medium-risk": ["low-risk", "medium-risk"],
    "high-risk": ["low-risk", "medium-risk", "high-risk"],
}


class MediaBridgeError(RuntimeError):
    """media bridge 业务错误"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(payload: dict[str, Any]) -> None:
    """统一 JSON 输出"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _http_get(url: str, timeout: int = 5) -> tuple[int, str]:
    """GET 请求，返回 (status, body_text)"""
    req = urlrequest.Request(url, headers={"Accept": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="ignore")


def _http_post_json(url: str, body: dict, timeout: int = 30) -> Any:
    """POST JSON 请求，返回解析后的 JSON"""
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _embed_query(query: str) -> list[float]:
    """调用本地 embedding 服务向量化 query"""
    try:
        resp = _http_post_json(
            EMBEDDING_URL, {"text": query, "model": EMBEDDING_MODEL}
        )
    except (URLError, OSError) as e:
        raise MediaBridgeError(
            f"embedding 服务不可用 ({EMBEDDING_URL}): {type(e).__name__}: {e}"
        )
    vec = resp.get("embedding") or resp.get("vector")
    if not vec or not isinstance(vec, list):
        raise MediaBridgeError(f"embedding 返回异常: {resp}")
    return [float(v) for v in vec]


def _qdrant_search(
    vector: list[float], top_k: int, license_filter: list[str]
) -> list[dict]:
    """调用 Qdrant /points/search 检索"""
    url = f"{QDRANT_BASE_URL}/collections/{COLLECTION_NAME}/points/search"
    body: dict[str, Any] = {
        "vector": vector,
        "limit": top_k,
        "with_payload": True,
    }
    # 构造 license_risk 过滤条件（should = OR）
    if license_filter:
        body["filter"] = {
            "should": [
                {"key": "license_risk", "match": {"value": v}}
                for v in license_filter
            ]
        }
    try:
        resp = _http_post_json(url, body)
    except (URLError, OSError) as e:
        raise MediaBridgeError(f"Qdrant 检索失败: {type(e).__name__}: {e}")
    return resp.get("result", [])


def cmd_search(args: argparse.Namespace) -> None:
    """调用 Qdrant nf_stock_footage_v1 检索"""
    license_filter = LICENSE_LEVELS.get(
        args.license_policy, LICENSE_LEVELS["low-risk"]
    )
    vector = _embed_query(args.query)
    hits = _qdrant_search(vector, args.top_k, license_filter)

    # 只提取 payload schema 相关字段
    results: list[dict[str, Any]] = []
    for h in hits:
        payload = h.get("payload", {})
        results.append({
            "content_id": payload.get("content_id"),
            "relative_path": payload.get("relative_path"),
            "license_risk": payload.get("license_risk"),
            "has_subtitle": payload.get("has_subtitle"),
            "ip_owner": payload.get("ip_owner"),
            "media_library_id": payload.get("media_library_id"),
            "downweight": payload.get("downweight"),
            "media_root_key": payload.get("media_root_key"),
            "score": h.get("score"),
        })
    _emit({
        "status": "OK",
        "query": args.query,
        "collection": COLLECTION_NAME,
        "top_k": args.top_k,
        "license_policy": args.license_policy,
        "match_count": len(results),
        "results": results,
    })


def cmd_resolve(args: argparse.Namespace) -> None:
    r"""解析 content_id 到 media\stock 下的真实文件"""
    url = f"{QDRANT_BASE_URL}/collections/{COLLECTION_NAME}/points/scroll"
    body = {
        "filter": {
            "must": [
                {"key": "content_id", "match": {"value": args.content_id}}
            ]
        },
        "limit": 1,
        "with_payload": True,
    }
    try:
        resp = _http_post_json(url, body, timeout=10)
    except (URLError, OSError) as e:
        raise MediaBridgeError(f"Qdrant scroll 失败: {type(e).__name__}: {e}")

    points = resp.get("result", {}).get("points", [])
    if not points:
        _emit({"status": "NOT_FOUND", "content_id": args.content_id})
        sys.exit(1)

    payload = points[0].get("payload", {})
    rel = payload.get("relative_path")
    if not rel:
        raise MediaBridgeError(
            f"content_id {args.content_id} 缺少 relative_path"
        )

    abs_path = (MEDIA_STOCK_ROOT / rel).resolve()
    exists = abs_path.is_file()
    _emit({
        "status": "OK" if exists else "FILE_MISSING",
        "content_id": args.content_id,
        "relative_path": rel,
        "absolute_path": str(abs_path),
        "file_exists": exists,
        "license_risk": payload.get("license_risk"),
        "ip_owner": payload.get("ip_owner"),
        "has_subtitle": payload.get("has_subtitle"),
        "media_library_id": payload.get("media_library_id"),
        "size": abs_path.stat().st_size if exists else None,
    })


def cmd_health(args: argparse.Namespace) -> None:
    """Qdrant 健康检查（/healthz + collection 信息 + media 根目录）"""
    # /healthz 返回纯文本
    healthz_ok = False
    healthz_detail = ""
    try:
        status, body = _http_get(f"{QDRANT_BASE_URL}/healthz", timeout=3)
        healthz_ok = status == 200
        healthz_detail = body.strip()
    except Exception as e:
        healthz_detail = f"{type(e).__name__}: {e}"

    # collection 信息
    coll_ok = False
    point_count: int | None = None
    coll_detail = ""
    try:
        _, body = _http_get(
            f"{QDRANT_BASE_URL}/collections/{COLLECTION_NAME}", timeout=5
        )
        info = json.loads(body).get("result", {})
        point_count = info.get("points_count")
        coll_ok = True
        coll_detail = f"points_count={point_count}"
    except Exception as e:
        coll_detail = f"{type(e).__name__}: {e}"

    # media stock 根目录
    media_ok = MEDIA_STOCK_ROOT.is_dir()

    overall = "OK" if (healthz_ok and coll_ok and media_ok) else "DEGRADED"
    _emit({
        "status": overall,
        "qdrant": {
            "base_url": QDRANT_BASE_URL,
            "healthz_reachable": healthz_ok,
            "healthz_detail": healthz_detail,
            "collection": COLLECTION_NAME,
            "collection_ok": coll_ok,
            "point_count": point_count,
            "coll_detail": coll_detail,
        },
        "media": {
            "stock_root": str(MEDIA_STOCK_ROOT),
            "root_exists": media_ok,
        },
        "checked_at": _utc_now(),
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="om media",
        description="Qdrant 素材检索/解析/健康检查（nf_stock_footage_v1）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="调用 Qdrant 检索素材")
    sp.add_argument("query", help="检索 query（自然语言镜头意图）")
    sp.add_argument("--top-k", type=int, default=20, help="返回数量（默认 20）")
    sp.add_argument(
        "--license-policy",
        choices=list(LICENSE_LEVELS.keys()),
        default="low-risk",
        help="license 风险策略（默认 low-risk）",
    )
    sp.set_defaults(func=cmd_search)

    rp = sub.add_parser("resolve", help="解析 content_id 到真实文件")
    rp.add_argument("content_id", help="素材 content_id")
    rp.set_defaults(func=cmd_resolve)

    hp = sub.add_parser("health", help="Qdrant 健康检查")
    hp.set_defaults(func=cmd_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except MediaBridgeError as e:
        _emit({"status": "ERROR", "error": str(e)})
        return 1
    except Exception as e:
        _emit({"status": "ERROR", "error": f"{type(e).__name__}: {e}"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())