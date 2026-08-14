#!/usr/bin/env python3
"""Mechanical checks for the Trae project harness (GOAL §4). No MCP, ≤2KB rule/memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RULE = REPO / ".trae" / "rules" / "content-studio-control-plane.md"
SKILL = REPO / ".trae" / "skills" / "content-studio-director" / "SKILL.md"
MEMORY = REPO / ".trae" / "memory" / "project_memory.md"
COMMAND_MAP = (
    REPO / ".trae" / "skills" / "content-studio-director" / "fixtures" / "command_map.json"
)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"status": "FAIL", "reason": reason, **extra}


def check() -> dict[str, Any]:
    missing = [str(p) for p in (RULE, SKILL, MEMORY, COMMAND_MAP) if not p.is_file()]
    if missing:
        return _fail("harness 文件缺失", missing=missing)

    rule_text = RULE.read_text(encoding="utf-8")
    skill_text = SKILL.read_text(encoding="utf-8")
    memory_text = MEMORY.read_text(encoding="utf-8")
    rule_bytes = RULE.stat().st_size
    memory_bytes = MEMORY.stat().st_size

    if rule_bytes > 2048:
        return _fail("规则超过 2KB", bytes=rule_bytes)
    if memory_bytes > 2048:
        return _fail("project_memory 超过 2KB", bytes=memory_bytes)
    if "MCP" not in rule_text and "mcp" not in rule_text.lower():
        # Rule must explicitly forbid MCP.
        return _fail("规则未禁止 MCP")
    if "只读" not in rule_text or "异步" not in rule_text:
        return _fail("规则缺少只读/异步约束")
    if "checkpoint" not in rule_text.lower() and "checkpoint" not in rule_text:
        return _fail("规则未禁止写 checkpoint")
    if "中文" not in memory_text or "异步" not in memory_text:
        return _fail("memory 未找回中文/异步偏好")
    if "INITIALIZED" in memory_text or "zh-comic-nonfiction-v1" in memory_text:
        return _fail("project memory 写入了临时 job 状态")
    if "content_studio_gateway.py" not in skill_text:
        return _fail("skill 未指向固定 gateway CLI")
    if "run_content_studio_prime_chat.py" not in skill_text:
        return _fail("skill 未指向 Direct Prime 入口")
    cmap = json.loads(COMMAND_MAP.read_text(encoding="utf-8"))
    classes = cmap.get("classes") or {}
    if not {"read-only", "submit-job", "human-write"} <= set(classes):
        return _fail("command_map 缺三类命令", classes=list(classes))
    return {
        "status": "OK",
        "rule_bytes": rule_bytes,
        "memory_bytes": memory_bytes,
        "skill_bytes": SKILL.stat().st_size,
        "mcp_enabled": False,
    }


def main() -> int:
    argparse.ArgumentParser(description="Check Trae Content Studio harness files").parse_args()
    payload = check()
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0 if payload.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
