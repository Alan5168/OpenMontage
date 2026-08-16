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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

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

# OpenViking 0.4.13 CLI / HTTP（loopback-only）
OV_BIN = Path(
    os.environ.get(
        "OPENVIKING_CLI",
        r"C:\ContentStudio\runtime\openviking-0.4.13\Scripts\ov.exe",
    )
)
OV_HTTP = os.environ.get("OPENVIKING_HTTP", "http://127.0.0.1:1933")
OV_ACCOUNT = os.environ.get("OPENVIKING_ACCOUNT", "content-studio")
VIKING_SCOPE_URI = "viking://resources/content-studio/"

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


def _http_ok(url: str, timeout: int = 3) -> tuple[bool, str]:
    try:
        req = Request(url, headers={"Accept": "application/json, text/plain"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")[:500]
            return 200 <= resp.status < 300, body.strip()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _ov_cli(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    if not OV_BIN.is_file():
        raise ContextBridgeError(f"OpenViking CLI 不存在: {OV_BIN}")
    cmd = [str(OV_BIN), "-o", "json", "--account", OV_ACCOUNT, *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _parse_ov_json(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        start_arr = text.find("[")
        idx = min([i for i in (start, start_arr) if i >= 0], default=-1)
        if idx < 0:
            return {"raw": text[:2000]}
        try:
            return json.loads(text[idx:])
        except json.JSONDecodeError:
            return {"raw": text[:2000]}


def _ov_scope_exists(viking_uri: str) -> tuple[bool, dict[str, Any]]:
    """Verify a server-side scope; local folders are not semantic-index proof."""
    try:
        code, stdout, stderr = _ov_cli(["ls", viking_uri], timeout=20)
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}"}
    parsed = _parse_ov_json(stdout)
    ok = code == 0 and isinstance(parsed, dict) and parsed.get("ok") is True
    return ok, {
        "uri": viking_uri,
        "exit_code": code,
        "stderr": stderr[-500:],
        "response": parsed,
    }


def cmd_search(args: argparse.Namespace) -> None:
    """真实调用 OpenViking 0.4.13 `ov find`，禁止用目录 grep 冒充。"""
    ov_ok, ov_detail = _http_ok(f"{OV_HTTP}/health")
    if not ov_ok:
        _emit({
            "status": "FAIL",
            "error": "OpenViking HTTP 不可达，拒绝降级为本地 grep",
            "health": ov_detail,
            "http": OV_HTTP,
        })
        sys.exit(1)

    uri = VIKING_SCOPE_URI
    if args.scope:
        sub = SCOPE_DIRS.get(args.scope)
        if sub:
            uri = f"{VIKING_PREFIX}{sub}/"
    cli_args = ["find", args.query, "-u", uri, "-n", str(getattr(args, "top_k", 20) or 20)]
    code, stdout, stderr = _ov_cli(cli_args)
    parsed = _parse_ov_json(stdout)
    if isinstance(parsed, dict) and isinstance(parsed.get("result"), dict) and parsed.get("ok") is True:
        parsed = parsed["result"]
    results: list[dict[str, Any]] = []
    if isinstance(parsed, dict):
        raw_hits = (
            parsed.get("resources")
            or parsed.get("results")
            or parsed.get("items")
            or parsed.get("data")
            or parsed.get("hits")
            or []
        )
        if isinstance(raw_hits, dict):
            raw_hits = raw_hits.get("items") or raw_hits.get("results") or []
        if isinstance(raw_hits, list):
            for hit in raw_hits:
                if not isinstance(hit, dict):
                    continue
                results.append({
                    "viking_uri": hit.get("uri") or hit.get("path") or hit.get("viking_uri"),
                    "score": hit.get("score") or hit.get("relevance"),
                    "level": hit.get("level"),
                    "title": hit.get("title") or hit.get("name"),
                    "snippet": hit.get("snippet") or hit.get("abstract") or hit.get("overview"),
                    "source_pointer": hit.get("source") or hit.get("source_pointer") or hit.get("uri"),
                })
    trajectory = {
        "backend": "openviking-0.4.13-cli",
        "cli": str(OV_BIN),
        "argv": cli_args,
        "exit_code": code,
        "stderr": stderr[-1000:],
        "http": OV_HTTP,
        "uri": uri,
        "grep_fallback": False,
    }
    status = "OK" if code == 0 else "FAIL"
    _emit({
        "status": status,
        "query": args.query,
        "scope": args.scope or "all",
        "match_count": len(results),
        "results": results,
        "trajectory": trajectory,
        "raw": parsed if not results else None,
        "session_auto_commit": False,
    })
    if status != "OK":
        sys.exit(1)


def cmd_read(args: argparse.Namespace) -> None:
    """优先 ov read；失败才读本地 workspace 文件，并标明降级。"""
    ov_ok, _ = _http_ok(f"{OV_HTTP}/health")
    if ov_ok:
        code, stdout, stderr = _ov_cli(["read", args.viking_uri])
        parsed = _parse_ov_json(stdout)
        if code == 0:
            _emit({
                "status": "OK",
                "viking_uri": args.viking_uri,
                "backend": "openviking-0.4.13-cli",
                "content": parsed if parsed is not None else stdout,
                "stderr": stderr[-500:],
            })
            return
        # add-resource represents one imported file as an asset directory,
        # e.g. foo.json/foo.md. Resolve the only materialized child instead
        # of silently falling back to the workspace mirror.
        asset_root = args.viking_uri.rstrip("/") + "/"
        ls_code, ls_stdout, ls_stderr = _ov_cli(["ls", asset_root])
        ls_parsed = _parse_ov_json(ls_stdout)
        children = []
        if isinstance(ls_parsed, dict) and ls_parsed.get("ok") is True:
            result = ls_parsed.get("result")
            if isinstance(result, list):
                children = [
                    row for row in result
                    if isinstance(row, dict) and not row.get("isDir") and row.get("uri")
                ]
        preferred = [
            row for row in children
            if not str(row.get("uri") or "").endswith("/.abstract.md")
        ]
        if len(preferred) == 1:
            resolved_uri = str(preferred[0]["uri"])
            child_code, child_stdout, child_stderr = _ov_cli(["read", resolved_uri])
            child_parsed = _parse_ov_json(child_stdout)
            if child_code == 0:
                _emit({
                    "status": "OK",
                    "viking_uri": args.viking_uri,
                    "resolved_viking_uri": resolved_uri,
                    "backend": "openviking-0.4.13-cli",
                    "content": child_parsed if child_parsed is not None else child_stdout,
                    "stderr": child_stderr[-500:],
                    "asset_root_resolved": True,
                })
                return
    path = _resolve_viking_uri(args.viking_uri)
    if not path.exists():
        _emit({"status": "NOT_FOUND", "viking_uri": args.viking_uri})
        sys.exit(1)
    if path.is_dir():
        _emit({
            "status": "OK",
            "viking_uri": args.viking_uri,
            "type": "directory",
            "backend": "workspace-fallback",
            "entries": sorted(p.name for p in path.iterdir()),
        })
        return
    raw = path.read_bytes()
    _emit({
        "status": "OK",
        "viking_uri": args.viking_uri,
        "type": "file",
        "backend": "workspace-fallback",
        "sha256": _sha256_bytes(raw),
        "size": len(raw),
        "content": raw.decode("utf-8", errors="ignore"),
    })


def cmd_ingest(args: argparse.Namespace) -> None:
    """Import a verified card into both the workspace and semantic index."""
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

    viking_uri = _to_viking_uri(target)
    # `target.write_bytes` alone only creates a workspace mirror. It does not
    # create OpenViking semantic/vector artifacts. Index the immutable source
    # first and fail closed before claiming INGESTED.
    code, stdout, stderr = _ov_cli(
        [
            "add-resource",
            str(src),
            "--to",
            viking_uri,
            "--wait",
            "--timeout",
            "120",
        ],
        timeout=150,
    )
    index_result = _parse_ov_json(stdout)
    if code != 0 or not (
        isinstance(index_result, dict) and index_result.get("ok") is True
    ):
        raise ContextBridgeError(
            "OpenViking add-resource 失败，拒绝把本地复制冒充语义入库: "
            f"exit={code} stderr={stderr[-500:]} result={index_result}"
        )

    target.write_bytes(data)
    _emit({
        "status": "INGESTED",
        "source": str(src),
        "target": str(target),
        "viking_uri": viking_uri,
        "semantic_indexed": True,
        "openviking_result": index_result,
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
    """OpenViking HTTP + CLI + Qdrant。DEGRADED/FAIL 一律非 0 退出。"""
    ov_ok = CONTEXT_ROOT.is_dir()
    missing_dirs: list[str] = []
    for name in ["governance", "openmontage", "research", "goodcases",
                 "media-catalog", "active-projects", "casebook"]:
        if not (CONTEXT_ROOT / name).is_dir():
            missing_dirs.append(name)

    http_ok, http_detail = _http_ok(f"{OV_HTTP}/health")
    cli_ok = False
    cli_detail = "not_run"
    try:
        code, stdout, stderr = _ov_cli(["health"], timeout=20)
        cli_ok = code == 0
        cli_detail = (stdout or stderr)[:400]
    except Exception as e:
        cli_detail = f"{type(e).__name__}: {e}"

    qdrant_ok, qdrant_detail = _http_ok(
        os.environ.get("QDRANT_HEALTH_URL", "http://127.0.0.1:6333/healthz")
    )

    semantic_scopes: dict[str, Any] = {}
    required_semantic_scopes = {"goodcase"}
    semantic_scopes_ok = True
    for scope, subdir in SCOPE_DIRS.items():
        uri = f"{VIKING_PREFIX}{subdir}/"
        scope_ok, detail = _ov_scope_exists(uri)
        semantic_scopes[scope] = {
            "exists": scope_ok,
            "required": scope in required_semantic_scopes,
            **detail,
        }
        if scope in required_semantic_scopes:
            semantic_scopes_ok = semantic_scopes_ok and scope_ok

    overall = "OK" if (
        ov_ok
        and not missing_dirs
        and http_ok
        and cli_ok
        and qdrant_ok
        and semantic_scopes_ok
    ) else "FAIL"
    _emit({
        "status": overall,
        "fail_closed": True,
        "openviking": {
            "version_required": "0.4.13",
            "context_root": str(CONTEXT_ROOT),
            "root_exists": ov_ok,
            "missing_dirs": missing_dirs,
            "http": OV_HTTP,
            "http_ok": http_ok,
            "http_detail": http_detail,
            "cli": str(OV_BIN),
            "cli_ok": cli_ok,
            "cli_detail": cli_detail,
            "session_auto_commit_default_enabled": False,
            "grep_search_disabled": True,
            "semantic_scopes": semantic_scopes,
            "semantic_scopes_ok": semantic_scopes_ok,
        },
        "qdrant": {
            "reachable": qdrant_ok,
            "detail": qdrant_detail,
        },
        "checked_at": _utc_now(),
    })
    if overall != "OK":
        sys.exit(1)


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
    sp.add_argument("--top-k", type=int, default=20, help="返回数量")
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
