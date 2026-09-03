#!/usr/bin/env python3
"""Qdrant media bridge for OpenMontage.

提供 nf_stock_footage_v2 素材检索/解析/健康检查命令。
调用现有 Windows Qdrant（127.0.0.1:6333），不复制第二份向量。
embedding：火山方舟 CodingPlan doubao-embedding-vision（文本端点，1024 维）。
历史：本地 Qwen3-Embedding-0.6B 服务（18889）已于 2026-09-03 永久下线；
v1 collection（旧 Qwen 向量）保留作回滚，可通过 QDRANT_COLLECTION 环境变量切回。
API key 从 HKCU 用户环境变量 OPENVIKING_ARK_EMBEDDING_API_KEY 读取，不落盘。
HTTP 走 stdlib urllib，无需额外依赖。
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

try:
    import winreg
except ImportError:  # 非 Windows 退化
    winreg = None

# Qdrant 配置（loopback-only）
QDRANT_BASE_URL = os.environ.get("QDRANT_BASE_URL", "http://127.0.0.1:6333")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "nf_stock_footage_v2")

# 素材根目录
MEDIA_STOCK_ROOT = Path(
    os.environ.get("MEDIA_STOCK_ROOT", r"C:\ContentStudio\media\stock")
)

# embedding：火山方舟 CodingPlan doubao-embedding-vision（文本查询端点，与 v2 入库同空间）
ARK_EMBEDDING_URL = os.environ.get(
    "ARK_EMBEDDING_URL",
    "https://ark.cn-beijing.volces.com/api/coding/v3/embeddings",
)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "doubao-embedding-vision")
EMBEDDING_DIMS = 1024
MIN_IMAGE_BYTES = 1024

# license_risk 等级映射，用于 license-policy 过滤
# payload 实测值为 low/medium/high；同时兼容 *-risk 写法。
LICENSE_LEVELS: dict[str, list[str]] = {
    "low-risk": ["low", "low-risk"],
    "medium-risk": ["low", "low-risk", "medium", "medium-risk"],
    "high-risk": ["low", "low-risk", "medium", "medium-risk", "high", "high-risk"],
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


def _extract_vector(resp: Any) -> list[float] | None:
    if not isinstance(resp, dict):
        return None
    vec = resp.get("embedding") or resp.get("vector")
    if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
        return [float(v) for v in vec]
    data = resp.get("data")
    if isinstance(data, list) and data:
        inner = data[0].get("embedding") if isinstance(data[0], dict) else None
        if isinstance(inner, list):
            return [float(v) for v in inner]
    embeddings = resp.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list):
            return [float(v) for v in first]
    return None


def _get_api_key() -> str | None:
    """读取火山方舟 API key：HKCU 用户环境变量优先，进程环境变量兜底。"""
    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _ = winreg.QueryValueEx(k, "OPENVIKING_ARK_EMBEDDING_API_KEY")
                if v:
                    return v
        except OSError:
            pass
    return os.environ.get("OPENVIKING_ARK_EMBEDDING_API_KEY")


def _embed_query(query: str) -> list[float]:
    """调用火山方舟文本 embedding 端点（doubao-embedding-vision, 1024 维）。"""
    key = _get_api_key()
    if not key:
        raise MediaBridgeError(
            "缺少 OPENVIKING_ARK_EMBEDDING_API_KEY（HKCU 用户环境变量或进程环境变量）"
        )
    body = {
        "model": EMBEDDING_MODEL,
        "input": [query],
        "dimensions": EMBEDDING_DIMS,
    }
    req = urlrequest.Request(
        ARK_EMBEDDING_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        raise MediaBridgeError(
            f"火山方舟 embedding 调用失败: {type(e).__name__}: {e}"
        )
    vec = _extract_vector(payload)
    if not vec or len(vec) != EMBEDDING_DIMS:
        raise MediaBridgeError(
            f"embedding 返回异常: dims={len(vec) if vec else 0}, expected={EMBEDDING_DIMS}"
        )
    return vec


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

    results: list[dict[str, Any]] = []
    missing = 0
    for h in hits:
        payload = h.get("payload", {}) or {}
        rel = payload.get("relative_path")
        abs_path = (MEDIA_STOCK_ROOT / rel).resolve() if rel else None
        exists = bool(abs_path and abs_path.is_file())
        if not exists:
            missing += 1
        results.append({
            "content_id": payload.get("content_id"),
            "relative_path": rel,
            "absolute_path": str(abs_path) if abs_path else None,
            "file_exists": exists,
            "file_bytes": abs_path.stat().st_size if exists else None,
            "license_risk": payload.get("license_risk"),
            "has_subtitle": payload.get("has_subtitle"),
            "ip_owner": payload.get("ip_owner"),
            "media_library_id": payload.get("media_library_id"),
            "downweight": payload.get("downweight"),
            "media_root_key": payload.get("media_root_key"),
            "rerank_score": payload.get("rerank_score") or payload.get("rerank") or h.get("rerank_score"),
            "score": h.get("score"),
        })
    exist_rate = (len(results) - missing) / len(results) if results else 0.0
    status = "OK" if results and missing == 0 else "FAIL"
    _emit({
        "status": status,
        "query": args.query,
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "top_k": args.top_k,
        "license_policy": args.license_policy,
        "match_count": len(results),
        "file_exists_rate": round(exist_rate, 4),
        "missing_files": missing,
        "results": results,
        "second_index_written": False,
        "reembedded": False,
    })
    if status != "OK":
        sys.exit(1)


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

    embed_ok, embed_detail = False, ""
    try:
        vec = _embed_query("health probe")
        embed_ok = len(vec) == EMBEDDING_DIMS
        embed_detail = f"ark text endpoint OK, dims={len(vec)}"
    except MediaBridgeError as e:
        embed_detail = str(e)
    except Exception as e:
        embed_detail = f"{type(e).__name__}: {e}"

    overall = "OK" if (healthz_ok and coll_ok and media_ok and embed_ok) else "FAIL"
    _emit({
        "status": overall,
        "fail_closed": True,
        "qdrant": {
            "base_url": QDRANT_BASE_URL,
            "healthz_reachable": healthz_ok,
            "healthz_detail": healthz_detail,
            "collection": COLLECTION_NAME,
            "collection_ok": coll_ok,
            "point_count": point_count,
            "coll_detail": coll_detail,
            "expected_points": 14133,
        },
        "embedding": {
            "provider": "volcengine-ark-codingplan",
            "url": ARK_EMBEDDING_URL,
            "model": EMBEDDING_MODEL,
            "dims": EMBEDDING_DIMS,
            "reachable": embed_ok,
            "detail": embed_detail,
        },
        "media": {
            "stock_root": str(MEDIA_STOCK_ROOT),
            "root_exists": media_ok,
        },
        "checked_at": _utc_now(),
    })
    if overall != "OK":
        sys.exit(1)


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
    except SystemExit as e:
        return int(e.code or 1)
    except Exception as e:
        _emit({"status": "ERROR", "error": f"{type(e).__name__}: {e}"})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())