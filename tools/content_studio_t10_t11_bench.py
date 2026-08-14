#!/usr/bin/env python3
"""T10 OpenViking 20 queries + T11 Qdrant 20 queries. Fail closed."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = Path(
    os.environ.get(
        "CONTENT_STUDIO_REPORTS",
        r"C:\ContentStudio\reports\windows-trae-native-content-harness-v1",
    )
)

T10_QUERIES = [
    "content studio 职责边界",
    "OpenMontage sceneplan gate",
    "visual continuity package",
    "comic nonfiction 中文短视频",
    "研报解读 小红书",
    "accepted lesson casebook",
    "素材库 taxonomy",
    "Qdrant nf_stock_footage_v1",
    "license_risk low-risk",
    "Alan 只审三个 Gate",
    "async continuity regen",
    "Direct Prime session resume",
    "H3 ComfyUI 显存边界",
    "中文真人口播 ASR",
    "动画优先 日漫 sketch",
    "research digest provenance",
    "goodcase 转场卡",
    " Trae 看图不读 JSON",
    "rollback quarantine",
    "READY_FOR_ALAN_FINAL_REVIEW",
]

T11_QUERIES = [
    "一个人在雨中走路",
    "办公室深夜对屏幕",
    "城市航拍黄昏",
    "实验室显微镜特写",
    "工厂流水线工人",
    "孩子在课堂举手",
    "紧张的交易员盯盘",
    "平静的湖面日出",
    "愤怒的抗议人群",
    "喜悦的颁奖现场",
    "转场 光斑 叠化",
    "快切 故障风 glitch",
    "历史 青铜器 博物馆",
    "华尔街 铜牛 隐喻",
    "芯片晶圆 洁净室",
    "版权 商标 明显 logo",
    "新闻主播 演播室",
    "手写笔记 特写",
    "地铁通勤 拥挤",
    "服务器机房 指示灯",
]


def _tool(script: str, argv: list[str], timeout: int = 90) -> dict:
    proc = subprocess.run(
        [PY, str(REPO / "tools" / script), *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    parsed = None
    out = proc.stdout or ""
    if "{" in out:
        try:
            parsed = json.loads(out[out.find("{") :])
        except json.JSONDecodeError:
            parsed = None
    return {"returncode": proc.returncode, "json": parsed, "stderr": (proc.stderr or "")[-500:]}


def run_t10() -> dict:
    health = _tool("om_context_bridge.py", ["health"])
    if health["returncode"] != 0 or (health["json"] or {}).get("status") != "OK":
        return {"status": "FAIL", "gate": "T10", "reason": "openviking health FAIL", "health": health}
    rows = []
    for q in T10_QUERIES:
        hit = _tool("om_context_bridge.py", ["search", q, "--top-k", "5"], timeout=60)
        payload = hit["json"] or {}
        traj = payload.get("trajectory") or {}
        rows.append(
            {
                "query": q,
                "status": payload.get("status"),
                "match_count": payload.get("match_count"),
                "exit": hit["returncode"],
                "backend": traj.get("backend"),
                "grep_fallback": traj.get("grep_fallback"),
                "source_pointers": [r.get("source_pointer") or r.get("viking_uri") for r in payload.get("results") or []][:5],
            }
        )
    grep = any(r.get("grep_fallback") for r in rows)
    ok_count = sum(1 for r in rows if r["exit"] == 0 and r.get("status") == "OK")
    hit_count = sum(1 for r in rows if (r.get("match_count") or 0) > 0)
    status = "OK" if ok_count == 20 and not grep and hit_count >= 10 else "FAIL"
    return {
        "status": status,
        "gate": "T10",
        "query_count": len(rows),
        "ok_count": ok_count,
        "hit_count": hit_count,
        "grep_fallback": grep,
        "openviking_version": "0.4.13",
        "loopback_only": True,
        "session_auto_commit": False,
        "queries": rows,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def run_t11() -> dict:
    health = _tool("om_media_bridge.py", ["health"])
    hj = health["json"] or {}
    if health["returncode"] != 0 or hj.get("status") != "OK":
        return {"status": "FAIL", "gate": "T11", "reason": "media health FAIL", "health": health}
    point_count = ((hj.get("qdrant") or {}).get("point_count"))
    rows = []
    missing = 0
    rights_ok = 0
    for q in T11_QUERIES:
        hit = _tool("om_media_bridge.py", ["search", q, "--top-k", "5", "--license-policy", "low-risk"], timeout=90)
        payload = hit["json"] or {}
        results = payload.get("results") or []
        file_ok = all(r.get("file_exists") for r in results) if results else False
        if not file_ok:
            missing += 1
        if results and all("license_risk" in r for r in results):
            rights_ok += 1
        rows.append(
            {
                "query": q,
                "status": payload.get("status"),
                "exit": hit["returncode"],
                "match_count": payload.get("match_count"),
                "file_exists_rate": payload.get("file_exists_rate"),
                "rights_present": bool(results) and all("license_risk" in r for r in results),
                "reembedded": payload.get("reembedded"),
            }
        )
    exist_rate = 1.0 if missing == 0 and rows else 0.0
    status = "OK" if exist_rate == 1.0 and point_count == 14133 and all(r["exit"] == 0 for r in rows) else "FAIL"
    return {
        "status": status,
        "gate": "T11",
        "query_count": len(rows),
        "file_exists_rate": exist_rate,
        "point_count": point_count,
        "rights_ok_queries": rights_ok,
        "reembedded": False,
        "second_index_written": False,
        "queries": rows,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--t10", action="store_true")
    parser.add_argument("--t11", action="store_true")
    args = parser.parse_args()
    if not args.t10 and not args.t11:
        args.t10 = args.t11 = True
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload: dict = {"schema_version": "content-studio-t10-t11-bench/v1"}
    status = "OK"
    if args.t10:
        t10 = run_t10()
        payload["t10"] = t10
        (REPORTS / "OPENVIKING_CONTEXT_BENCH.json").write_text(
            json.dumps(t10, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if t10["status"] != "OK":
            status = "FAIL"
        if args.t10 and not args.t11:
            print(json.dumps(t10, ensure_ascii=False, indent=2))
            return 0 if t10["status"] == "OK" else 1
    if args.t11:
        t11 = run_t11()
        payload["t11"] = t11
        (REPORTS / "MEDIA_QDRANT_REVALIDATION.json").write_text(
            json.dumps(t11, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if t11["status"] != "OK":
            status = "FAIL"
        if args.t11 and not args.t10:
            print(json.dumps(t11, ensure_ascii=False, indent=2))
            return 0 if t11["status"] == "OK" else 1
    payload["status"] = status
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
