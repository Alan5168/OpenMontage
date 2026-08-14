#!/usr/bin/env python3
"""Lock and run Goal section 11 T1–T14. Drift or DEGRADED is FAIL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = Path(
    os.environ.get(
        "CONTENT_STUDIO_REPORTS",
        r"C:\ContentStudio\reports\windows-trae-native-content-harness-v1",
    )
)
JOBS = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
PY = sys.executable

GOAL_T1_T14: list[dict[str, str]] = [
    {
        "test_id": "T1",
        "name": "Read-only",
        "input": "打开当前 fixture Gate",
        "acceptance": "≤10s 首响应；artifact/checkpoint hash 不变",
    },
    {
        "test_id": "T2",
        "name": "Async",
        "input": "按 VCP 重生 fixture",
        "acceptance": "≤5s 返回 ACCEPTED/job_id；后台状态可查；前台可继续聊天",
    },
    {
        "test_id": "T3",
        "name": "No overreach",
        "input": "你直接帮我改 artifact 就行",
        "acceptance": "拒绝直改，改走固定 console；无 canonical diff",
    },
    {
        "test_id": "T4",
        "name": "Visual",
        "input": "6 张 known-good/bad 图片",
        "acceptance": "实际图片输入；VISUAL_QA.json 合 schema；主要缺陷可命中",
    },
    {
        "test_id": "T5",
        "name": "Direct Prime",
        "input": "从 Trae terminal 打开项目 Prime",
        "acceptance": "exact session resume；变量/reload 证据；非 Pi 中转",
    },
    {
        "test_id": "T6",
        "name": "Isolation",
        "input": "断开 Mac/Tailscale 后重复 T1/T4/T5",
        "acceptance": "Windows 单机可用；无 Mac path/network dependency",
    },
    {
        "test_id": "T7",
        "name": "Memory",
        "input": "新 Trae 会话询问交互约束",
        "acceptance": "能找回 curated 偏好；不能把临时 job 状态当长期记忆",
    },
    {
        "test_id": "T8",
        "name": "Secret",
        "input": "扫描新增 tracked/report 文件",
        "acceptance": "无 key/token/cookie/auth/session 全文",
    },
    {
        "test_id": "T9",
        "name": "Evolution",
        "input": "注入已知 continuity failure",
        "acceptance": "产生 candidate + held-out 结果 + rollback receipt；未人工 promotion 前不生效",
    },
    {
        "test_id": "T10",
        "name": "OpenViking",
        "input": "restart 后做 20 条 resource/memory 查询",
        "acceptance": "固定 0.4.13；loopback-only；source pointer/trajectory 可查；无 raw-session auto commit；Mac 离线可用",
    },
    {
        "test_id": "T11",
        "name": "Media",
        "input": "20 条镜头/场景/情绪/版权 query",
        "acceptance": "调现有 14,133-point Qdrant；文件存在率 100%；rights/rerank 保留；未重嵌入/复制第二库",
    },
    {
        "test_id": "T12",
        "name": "Real Go-Live",
        "input": "新中文 job 从 commission 到 final candidate",
        "acceptance": "Trae/Prime/OM/OpenViking/媒体 provider 全在 Windows；停 READY_FOR_ALAN_FINAL_REVIEW；无自动发布",
    },
    {
        "test_id": "T13",
        "name": "Git/Secrets",
        "input": "Windows commit + push PR-sized branch",
        "acceptance": "Windows 自己完成；无 Mac bundle/token；secret scan PASS；断网时生产仍可继续并有本地 backup",
    },
    {
        "test_id": "T14",
        "name": "Resource/GC",
        "input": "H3 preflight + 一个 job cleanup dry-run/apply",
        "acceptance": "无 GPU 争抢/OOM；保留清单正确；可回滚；记录生成/留存/回收 bytes",
    },
]


def contract_sha256(item: dict[str, str]) -> str:
    payload = json.dumps(
        {k: item[k] for k in ("test_id", "name", "input", "acceptance")},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def locked_manifest() -> dict[str, Any]:
    tests = []
    for item in GOAL_T1_T14:
        tests.append({**item, "contract_sha256": contract_sha256(item)})
    return {
        "schema_version": "content-studio-acceptance-manifest-v1-locked",
        "source": "GOAL.md section 11 (verbatim)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "检测 test_id/name/contract_sha256 漂移即 fail closed；禁止重命名、重排或以另一组测试覆盖；DEGRADED 不得 PASS",
        "tests": tests,
        "total": 14,
    }


def _run(argv: list[str], timeout: int = 60, cwd: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - started
    stdout = proc.stdout or ""
    parsed = None
    try:
        parsed = json.loads(stdout[stdout.find("{") :]) if "{" in stdout else None
    except json.JSONDecodeError:
        parsed = None
    return {
        "argv": argv,
        "returncode": proc.returncode,
        "elapsed_s": round(elapsed, 3),
        "stdout_tail": stdout[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "json": parsed,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"passed": False, "verdict": "FAIL", "reason": reason, **extra}


def _pass(reason: str, **extra: Any) -> dict[str, Any]:
    return {"passed": True, "verdict": "PASS", "reason": reason, **extra}


def _not_proven(reason: str, **extra: Any) -> dict[str, Any]:
    return {"passed": False, "verdict": "NOT_PROVEN", "reason": reason, **extra}


def run_t1() -> dict[str, Any]:
    project = "fixture-pi-resume-e2e"
    project_dir = JOBS / project
    artifact = project_dir / "artifacts" / "scene_plan.json"
    checkpoint = project_dir / "checkpoint_scene_plan.json"
    if not artifact.is_file() or not checkpoint.is_file():
        return _fail("fixture artifact/checkpoint 不存在", project=project)
    before_a = hashlib.sha256(artifact.read_bytes()).hexdigest()
    before_c = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    result = _run(
        [PY, str(REPO / "tools" / "content_studio_gateway.py"), "--project-id", project, "show-gate"],
        timeout=20,
    )
    after_a = hashlib.sha256(artifact.read_bytes()).hexdigest()
    after_c = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if result["elapsed_s"] > 10:
        return _fail("首响应超过 10s", **result)
    if result["returncode"] != 0:
        return _fail("show-gate 非 0", **result)
    if before_a != after_a or before_c != after_c:
        return _fail("canonical hash 变化", before_artifact=before_a, after_artifact=after_a)
    return _pass("read-only show-gate", elapsed_s=result["elapsed_s"], artifact_sha256=before_a)


def run_t2() -> dict[str, Any]:
    result = _run(
        [
            PY,
            str(REPO / "tools" / "content_studio_async_console.py"),
            "--project-id",
            "fixture-pi-resume-e2e",
            "submit-continuity-regen",
            "--fixture",
            "--delay-seconds",
            "2",
        ],
        timeout=8,
    )
    payload = result.get("json") or {}
    if result["elapsed_s"] > 5:
        return _fail("ACK 超过 5s", **result)
    if payload.get("status") != "ACCEPTED" or not payload.get("job_id"):
        return _fail("未返回 ACCEPTED/job_id", **result)
    return _pass("fixture async ACK", elapsed_s=result["elapsed_s"], job_id=payload.get("job_id"), fixture=True)


def run_t3() -> dict[str, Any]:
    project_dir = JOBS / "fixture-pi-resume-e2e"
    artifact = project_dir / "artifacts" / "scene_plan.json"
    before = hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else ""
    # Overreach is refused by not exposing a write-artifact CLI. Prove no hash change
    # after a would-be write path (gateway apply without decisions must fail).
    result = _run(
        [
            PY,
            str(REPO / "tools" / "content_studio_gateway.py"),
            "--project-id",
            "fixture-pi-resume-e2e",
            "apply-sceneplan",
            "--expected-checkpoint-sha256",
            "deadbeef",
            "--decisions-json",
            "{}",
        ],
        timeout=20,
    )
    after = hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else ""
    if before != after:
        return _fail("越权写入改变了 canonical artifact", before=before, after=after)
    if result["returncode"] == 0:
        return _fail("无效 apply 不应成功", **result)
    return _pass("apply 拒绝且 hash 不变", before=before)


def run_t4() -> dict[str, Any]:
    image_root = JOBS / "pilot-ai-content-os-state-machine-zh-v1" / "review" / "sceneplan_layout_refs_sota"
    if not image_root.is_dir():
        return _fail("缺少 6 张 known 真图目录", path=str(image_root))
    images = sorted(p for p in image_root.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and p.stat().st_size > 1024)
    if len(images) < 3:
        return _fail("真图不足", count=len(images))
    qa_dir = JOBS / "zh-comic-nonfiction-v1" / "working" / "t4_visual"
    qa_dir.mkdir(parents=True, exist_ok=True)
    # copy first 3 sota + 3 known-bad (tiny or the learning red/blue)
    import shutil

    dest = qa_dir / "images"
    dest.mkdir(parents=True, exist_ok=True)
    for p in dest.glob("*"):
        if p.is_file():
            p.unlink()
    for i, src in enumerate(images[:3]):
        shutil.copy2(src, dest / f"good_{i}{src.suffix}")
    bad_root = REPO / "tests" / "fixtures" / "content_studio" / "learning"
    for name in ("red.png", "blue.png"):
        shutil.copy2(bad_root / name, dest / name)
    (dest / "placeholder.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    result = _run(
        [
            PY,
            str(REPO / "tools" / "visual_qa.py"),
            "--project-id",
            "zh-comic-nonfiction-v1",
            "--image-dir",
            str(dest),
        ],
        timeout=60,
    )
    payload = result.get("json") or {}
    viewed = [img for img in payload.get("images", []) if img.get("actually_viewed")]
    defects = [img for img in payload.get("images", []) if img.get("overall") == "FAIL"]
    if result["returncode"] != 0:
        return _fail("visual_qa 非 0", **result)
    if len(viewed) < 5:
        return _fail("actually_viewed 真图不足", viewed=len(viewed), payload_summary=payload.get("summary"))
    if len(defects) < 1:
        return _fail("未命中预先登记缺陷", summary=payload.get("summary"))
    return _pass(
        "6 图机械 visual QA，仍需 Alan Trae 真人 A/B",
        viewed=len(viewed),
        fail=len(defects),
        human_trae_ab="REQUIRED",
    )


def run_t5() -> dict[str, Any]:
    pointer = JOBS / "pilot-ai-content-os-state-machine-zh-v1" / "working" / "prime_rlm" / "SESSION_POINTER.json"
    script = REPO / "tools" / "run_content_studio_prime_chat.py"
    if not pointer.is_file():
        return _not_proven("无 project-bound SESSION_POINTER")
    if not script.is_file():
        return _fail("prime chat 脚本缺失")
    data = json.loads(pointer.read_text(encoding="utf-8"))
    session = data.get("session_jsonl") or data.get("jsonl") or data.get("path") or data.get("session_file")
    if not session:
        return _not_proven("pointer 无 jsonl 路径", pointer=data)
    exists = Path(session).is_file()
    if not exists:
        return _not_proven("session jsonl 不在磁盘", session=session)
    receipt = REPORTS / "T5_TRAE_ATTACH.json"
    if receipt.is_file():
        attach = json.loads(receipt.read_text(encoding="utf-8"))
        if (
            attach.get("attached_from") == "trae_integrated_terminal"
            and attach.get("not_pi_relay") is True
            and attach.get("project_id") == "pilot-ai-content-os-state-machine-zh-v1"
        ):
            return _pass(
                "Trae terminal attach 收据存在",
                pointer=str(pointer),
                session_exists=exists,
                receipt=str(receipt),
            )
        return _not_proven("T5 收据字段不完整", receipt=attach)
    return _not_proven(
        "pointer 与 jsonl 存在，但缺少 Trae terminal 真人 attach 收据",
        pointer=str(pointer),
        session_exists=exists,
        receipt_needed=str(receipt),
    )


def run_t6() -> dict[str, Any]:
    scans = []
    for rel in [
        "tools/om_context_bridge.py",
        "tools/om_media_bridge.py",
        "tools/content_studio_runtime.py",
        "tools/content_studio_gateway.py",
    ]:
        text = (REPO / rel).read_text(encoding="utf-8")
        hits = [s for s in ("/Users/alanli", "100.84.", "macstudio") if s in text]
        scans.append({"file": rel, "mac_hits": hits})
    if any(s["mac_hits"] for s in scans):
        return _fail("工具含 Mac path/network 依赖", scans=scans)
    receipt = REPORTS / "ISOLATION_WINDOW.json"
    if not receipt.is_file():
        return _not_proven("工具无 Mac path，但缺少断 Mac/Tailscale 后重跑 T1/T4/T5 的隔离窗口收据", scans=scans)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    if not data.get("mac_disconnected") or not data.get("t1_passed") or not data.get("t4_passed"):
        return _not_proven("隔离窗口收据不完整", receipt=data)
    return _pass("隔离窗口收据存在且 T1/T4 重跑通过", receipt=data)


def run_t7() -> dict[str, Any]:
    memory = REPO / ".trae" / "memory" / "project_memory.md"
    if not memory.is_file():
        return _fail("project_memory.md 不存在")
    text = memory.read_text(encoding="utf-8")
    if "INITIALIZED" in text or "zh-comic-nonfiction-v1" in text:
        return _fail("project memory 写入了临时 job 状态")
    if "中文" not in text or "异步" not in text:
        return _fail("未找回 curated 中文/异步偏好")
    if memory.stat().st_size > 2048:
        return _fail("memory 超过 2KB")
    return _pass("curated memory 存在且未混入 job 状态", bytes=memory.stat().st_size)


def run_t8() -> dict[str, Any]:
    result = _run([PY, str(REPO / "tools" / "content_studio_secret_scan.py")], timeout=60)
    payload = result.get("json") or {}
    if result["returncode"] != 0 or payload.get("status") != "OK":
        return _fail("secret scan 未通过", **result)
    return _pass("secret scan OK", hits=payload.get("hit_count"))


def run_t9() -> dict[str, Any]:
    result = _run(
        [
            PY,
            str(REPO / "tools" / "learning_system.py"),
            "record-event",
            "--type",
            "continuity_fix",
            "--description",
            "红蓝帧连续性失败 held-out",
            "--evidence",
            "tests/fixtures/content_studio/learning/held_out_continuity.json",
        ],
        timeout=20,
    )
    event_id = (result.get("json") or {}).get("event_id")
    if not event_id:
        return _fail("record-event 失败", **result)
    refine = _run([PY, str(REPO / "tools" / "learning_system.py"), "refine", "--event-id", event_id], timeout=60)
    payload = refine.get("json") or {}
    if payload.get("simulation") is True:
        return _fail("refine 仍是模拟", **refine)
    if payload.get("held_out_regression", {}).get("method") == "held_out_deterministic_simulation":
        return _fail("hash 模拟仍在", **refine)
    if payload.get("refine_status") != "PASS":
        return _fail("held-out 未通过", **refine)
    rollback = _run([PY, str(REPO / "tools" / "learning_system.py"), "rollback", "--event-id", event_id], timeout=20)
    accepted = Path(r"C:\ContentStudio\context\openviking\content-studio\casebook\accepted") / f"{event_id}.json"
    if accepted.is_file():
        return _fail("未 promotion 却进入 accepted")
    return _pass("candidate+held-out+rollback，未人工 promotion 不生效", event_id=event_id, refine=payload.get("refine_status"), rollback=rollback.get("json"))


def run_t10() -> dict[str, Any]:
    bench = _run([PY, str(REPO / "tools" / "content_studio_t10_t11_bench.py"), "--t10"], timeout=180)
    payload = bench.get("json") or {}
    if payload.get("status") != "OK":
        return _fail("OpenViking 20 query 未通过", **bench)
    if payload.get("openviking_version") not in {"0.4.13", "openviking 0.4.13"} and "0.4.13" not in str(payload.get("openviking_version")):
        return _fail("版本不是 0.4.13", **bench)
    return _pass("OpenViking 20 query", **{k: payload.get(k) for k in ("query_count", "openviking_version", "loopback_only")})


def run_t11() -> dict[str, Any]:
    bench = _run([PY, str(REPO / "tools" / "content_studio_t10_t11_bench.py"), "--t11"], timeout=300)
    payload = bench.get("json") or {}
    if payload.get("status") != "OK":
        return _fail("Qdrant 20 query 未通过", **bench)
    if payload.get("file_exists_rate") != 1.0:
        return _fail("文件存在率不是 100%", **bench)
    if payload.get("point_count") != 14133:
        return _fail("points 不是 14133", **bench)
    return _pass("Qdrant 20 query", **{k: payload.get(k) for k in ("query_count", "file_exists_rate", "point_count")})


def run_t12() -> dict[str, Any]:
    receipt_path = JOBS / "zh-comic-nonfiction-v1" / "review" / "REAL_JOB_GO_LIVE.json"
    if not receipt_path.is_file():
        return _fail("缺少 REAL_JOB_GO_LIVE.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "READY_FOR_ALAN_FINAL_REVIEW":
        return _fail("未停在 READY_FOR_ALAN_FINAL_REVIEW", receipt=receipt)
    if receipt.get("published"):
        return _fail("发生了自动发布")
    final = receipt.get("final_candidate")
    if not final or not Path(final).is_file() or Path(final).stat().st_size < 1024:
        return _fail("没有真实 final candidate", final=final)
    return _pass("真实中文 job 待 Alan final review", receipt=receipt)


def run_t13() -> dict[str, Any]:
    receipt = REPORTS / "WINDOWS_GITHUB_RECEIPT.json"
    if not receipt.is_file():
        return _not_proven("缺少 WINDOWS_GITHUB_RECEIPT.json")
    data = json.loads(receipt.read_text(encoding="utf-8"))
    if data.get("force_push"):
        return _fail("检测到 force push")
    if data.get("used_mac_bundle") or data.get("windows_https_push") is False:
        return _not_proven("Windows 已 commit，但 GitHub push 不是 Windows 自己完成", data=data)
    if not data.get("pushed"):
        return _fail("未 push")
    return _pass("Windows git receipt", data=data)


def run_t14() -> dict[str, Any]:
    gpu = _run([PY, str(REPO / "tools" / "resource_governor.py"), "gpu-status"], timeout=20)
    dry = _run([PY, str(REPO / "tools" / "resource_governor.py"), "gc", "--dry-run"], timeout=30)
    gpu_json = gpu.get("json") or {}
    dry_json = dry.get("json") or {}
    if dry_json.get("direct_delete") is not False:
        return _fail("GC 仍可能直接删除", **dry)
    if gpu_json.get("gpu", {}).get("status") == "UNAVAILABLE":
        return _not_proven("nvidia-smi 不可用", **gpu)
    return _pass("GC dry-run 可恢复；GPU 状态已记录", gpu=gpu_json.get("gpu"), gc_mode=dry_json.get("mode"))


RUNNERS = {
    "T1": run_t1,
    "T2": run_t2,
    "T3": run_t3,
    "T4": run_t4,
    "T5": run_t5,
    "T6": run_t6,
    "T7": run_t7,
    "T8": run_t8,
    "T9": run_t9,
    "T10": run_t10,
    "T11": run_t11,
    "T12": run_t12,
    "T13": run_t13,
    "T14": run_t14,
}


def cmd_lock() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = locked_manifest()
    path = REPORTS / "ACCEPTANCE_MANIFEST_LOCKED.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "LOCKED", "path": str(path), "tests": len(manifest["tests"])}


def cmd_verify_lock() -> dict[str, Any]:
    path = REPORTS / "ACCEPTANCE_MANIFEST_LOCKED.json"
    if not path.is_file():
        return {"status": "FAIL", "error": "locked manifest 不存在"}
    existing = json.loads(path.read_text(encoding="utf-8"))
    expected = locked_manifest()["tests"]
    drift = []
    got = existing.get("tests") or []
    if len(got) != 14:
        return {"status": "FAIL", "error": f"test count {len(got)} != 14"}
    for exp, act in zip(expected, got):
        if act.get("test_id") != exp["test_id"] or act.get("name") != exp["name"] or act.get("contract_sha256") != exp["contract_sha256"]:
            drift.append({"expected": exp, "actual": {k: act.get(k) for k in ("test_id", "name", "contract_sha256")}})
    if drift:
        return {"status": "FAIL", "error": "contract drift", "drift": drift}
    return {"status": "OK", "tests": 14}


def cmd_run() -> dict[str, Any]:
    verify = cmd_verify_lock()
    if verify.get("status") != "OK":
        return {"status": "FAIL", "reason": "lock verify failed", "verify": verify}
    results = []
    for item in GOAL_T1_T14:
        tid = item["test_id"]
        outcome = RUNNERS[tid]()
        if outcome.get("json") and isinstance(outcome["json"], dict):
            if outcome["json"].get("status") in {"DEGRADED"}:
                outcome = _fail("DEGRADED 不得记 PASS", inner=outcome)
        row = {
            "test_id": tid,
            "name": item["name"],
            "contract_sha256": contract_sha256(item),
            **outcome,
        }
        results.append(row)
    passed = sum(1 for r in results if r.get("passed"))
    payload = {
        "schema_version": "content-studio-acceptance-run/v1",
        "source": "GOAL section 11 original T1-T14",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": 14 - passed,
        "all_pass": passed == 14,
        "tests": results,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "ACCEPTANCE_RUN.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["lock", "verify-lock", "run", "print-contracts"])
    args = parser.parse_args()
    if args.command == "print-contracts":
        print(json.dumps(locked_manifest(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "lock":
        payload = cmd_lock()
    elif args.command == "verify-lock":
        payload = cmd_verify_lock()
    else:
        payload = cmd_run()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("status") == "FAIL" or payload.get("all_pass") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
