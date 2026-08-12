#!/usr/bin/env python3
"""项目绑定的 Prime Agent 交互式入口 (Direct Prime Console)。

从当前 OM project 的 working/prime_rlm/SESSION_POINTER.json 解析完整 .jsonl 路径，
禁止 global-latest fallback；找不到 pointer 时 fail closed。
使用隔离的 PRIME_AGENT_CODING_AGENT_DIR 和 --session-dir，
通过 --resume 恢复会话。不回显任何 credential。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
REPO = Path(os.environ.get("CONTENT_STUDIO_OM_REPO", r"C:\ContentStudio\repos\OpenMontage"))
JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
DEFAULT_KERNEL = Path(
    os.environ.get(
        "CONTENT_STUDIO_PRIME_KERNEL_PYTHON",
        r"C:\ContentStudio\runtime\Prime-kernel-venv\Scripts\python.exe",
    )
)
PRIME_CLI = Path(
    os.environ.get(
        "PRIME_AGENT_CLI_JS",
        str(Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "prime-agent" / "dist" / "bundle" / "cli.js"),
    )
)
# repo-local adapter skill（显式加载，不走全局 skill 目录）
ADAPTER_SKILL = REPO / "integrations" / "prime-om-adapter"

# 禁止的 CLI flag
FORBIDDEN_FLAGS = {"--no-session", "--no-tools"}

# 默认 provider/model（仅当项目配置中完全缺失时作为最后手段）
DEFAULT_PROVIDER = "bailian"
DEFAULT_MODEL = "qwen3.8-max"


class PrimeChatError(RuntimeError):
    """Prime Chat 启动错误。"""


# ---------------------------------------------------------------------------
# JSON 读取
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> dict[str, Any]:
    """安全读取 JSON 文件，容错 BOM。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrimeChatError(f"无法读取 JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PrimeChatError(f"JSON 不是对象: {path}")
    return data


# ---------------------------------------------------------------------------
# SESSION_POINTER 解析
# ---------------------------------------------------------------------------
def load_session_pointer(project_id: str) -> dict[str, Any]:
    """从项目 working/prime_rlm/SESSION_POINTER.json 加载会话指针。

    禁止 global-latest fallback；找不到 pointer 时 fail closed。
    """
    project_dir = JOBS_DIR / project_id
    pointer_path = project_dir / "working" / "prime_rlm" / "SESSION_POINTER.json"
    if not pointer_path.is_file():
        raise PrimeChatError(
            f"项目绑定的 SESSION_POINTER.json 不存在: {pointer_path}\n"
            "禁止 global-latest fallback。请先为此项目创建 Director 会话并写入 pointer。"
        )

    pointer = _read_json(pointer_path)

    # 校验 project_id 一致性
    pointer_pid = pointer.get("project_id")
    if pointer_pid and pointer_pid != project_id:
        raise PrimeChatError(
            f"SESSION_POINTER project_id 不匹配: {pointer_pid!r} != {project_id!r}"
        )

    # 解析完整 .jsonl 路径
    session_file = pointer.get("session_file") or pointer.get("session_path")
    if not session_file:
        raise PrimeChatError("SESSION_POINTER.json 缺少 session_file 字段")

    session_path = Path(session_file)
    if not session_path.is_absolute():
        session_dir = pointer.get("session_dir")
        if session_dir:
            session_path = Path(session_dir) / session_path
    session_path = session_path.resolve()

    if not str(session_path).lower().endswith(".jsonl"):
        raise PrimeChatError(f"session_file 必须是完整 .jsonl 路径: {session_path}")
    if not session_path.is_file():
        raise PrimeChatError(f"会话 .jsonl 文件不存在: {session_path}")

    # 回写解析后的绝对路径，方便后续使用
    pointer["_resolved_session_file"] = str(session_path)
    return pointer


# ---------------------------------------------------------------------------
# provider / model 解析（从项目配置读取，不写死）
# ---------------------------------------------------------------------------
def resolve_provider_model(pointer: dict[str, Any], project_id: str) -> tuple[str, str]:
    """从项目配置读取 provider 和 model。

    优先级: SESSION_POINTER.json > project.json > 环境变量 > 默认值
    """
    provider = pointer.get("provider")
    model = pointer.get("model")

    # 从 project.json 补充
    if not provider or not model:
        project_path = JOBS_DIR / project_id / "project.json"
        if project_path.is_file():
            cfg = _read_json(project_path)
            provider = provider or cfg.get("prime_provider")
            model = model or cfg.get("prime_model")

    # 从环境变量补充
    provider = provider or os.environ.get("CONTENT_STUDIO_PRIME_PROVIDER")
    model = model or os.environ.get("CONTENT_STUDIO_PRIME_MODEL")

    # 最后手段默认值
    provider = provider or DEFAULT_PROVIDER
    model = model or DEFAULT_MODEL
    return provider, model


# ---------------------------------------------------------------------------
# 环境变量构建
# ---------------------------------------------------------------------------
def build_launch_env(pointer: dict[str, Any], project_id: str) -> dict[str, str]:
    """构建隔离的 Prime Agent 启动环境变量。

    使用 PRIME_AGENT_CODING_AGENT_DIR 隔离 agent 状态。
    不包含任何 credential。
    """
    env = os.environ.copy()

    # 设置隔离的 agent 目录
    agent_dir = pointer.get("agent_dir")
    if agent_dir:
        env["PRIME_AGENT_CODING_AGENT_DIR"] = str(agent_dir)
    else:
        env["PRIME_AGENT_CODING_AGENT_DIR"] = str(
            JOBS_DIR / project_id / "working" / "prime_rlm" / "agent"
        )

    # OM adapter root
    env["OM_PRIME_ADAPTER_ROOT"] = r"C:\ContentStudio"
    env["OPENMONTAGE_PROJECTS_DIR"] = str(JOBS_DIR)

    # kernel python
    kernel = pointer.get("kernel_python") or str(DEFAULT_KERNEL)
    env["PRIME_AGENT_KERNEL_PYTHON"] = kernel

    return env


# ---------------------------------------------------------------------------
# Prime CLI 命令构造
# ---------------------------------------------------------------------------
def build_prime_command(
    session_file: str,
    session_dir: str,
    provider: str,
    model: str,
) -> list[str]:
    """构造 Prime Agent 启动命令。

    使用 --resume <完整.jsonl>；禁止 --no-session / --no-tools。
    显式加载 repo-local integrations/prime-om-adapter。
    """
    args = [
        "node",
        str(PRIME_CLI),
        "--provider", provider,
        "--model", model,
        "--thinking", "low",
        "--cwd", str(REPO),
        "--skill", str(ADAPTER_SKILL),
        "--no-extensions",
        "--no-prompt-templates",
        "--no-context-files",
        "--session-dir", session_dir,
        "--resume", session_file,
    ]

    # 校验禁止的 flag 不存在
    joined = " ".join(args)
    for flag in FORBIDDEN_FLAGS:
        if flag in joined:
            raise PrimeChatError(f"禁止的 flag 出现在命令中: {flag}")

    return args


# ---------------------------------------------------------------------------
# 窗口标题 & 脱敏输出
# ---------------------------------------------------------------------------
def set_window_title(project_id: str, provider: str, model: str, session_id: str) -> None:
    """设置窗口标题: project_id / provider / model / session_id。"""
    if sys.platform == "win32":
        title = f"Content Studio Prime | {project_id} | {provider}/{model} | {session_id}"
        try:
            os.system(f'title {title}')
        except Exception:
            pass


def print_sanitized_info(
    project_id: str,
    provider: str,
    model: str,
    session_id: str,
    session_file: str,
    agent_dir: str,
) -> None:
    """打印脱敏的启动信息（不回显任何 credential）。"""
    print("=" * 64)
    print("  Content Studio Prime - Direct Console")
    print("=" * 64)
    print(f"  project_id            : {project_id}")
    print(f"  provider              : {provider}")
    print(f"  model                 : {model}")
    print(f"  session_id            : {session_id}")
    print(f"  session_file          : {session_file}")
    print(f"  agent_dir             : {agent_dir}")
    print(f"  skill                 : {ADAPTER_SKILL}")
    print("-" * 64)
    print(f"  credentials           : [redacted]")
    print(f"  global_latest_fallback: false")
    print(f"  forbidden_flags       : --no-session, --no-tools (absent)")
    print("=" * 64)
    print()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run_prime_chat(project_id: str) -> int:
    """启动 Prime 交互式会话。"""
    # 1. 加载 session pointer（fail closed，无 global fallback）
    pointer = load_session_pointer(project_id)

    session_file = pointer["_resolved_session_file"]
    session_dir = str(pointer.get("session_dir") or str(Path(session_file).parent))
    session_id = pointer.get("session_id") or Path(session_file).stem
    agent_dir = pointer.get("agent_dir") or str(
        JOBS_DIR / project_id / "working" / "prime_rlm" / "agent"
    )

    # 2. 从项目配置读取 provider/model
    provider, model = resolve_provider_model(pointer, project_id)

    # 3. 设置窗口标题
    set_window_title(project_id, provider, model, session_id)

    # 4. 打印脱敏信息
    print_sanitized_info(project_id, provider, model, session_id, session_file, agent_dir)

    # 5. 构造启动命令
    args = build_prime_command(session_file, session_dir, provider, model)

    # 6. 构建隔离环境
    env = build_launch_env(pointer, project_id)

    # 7. 启动 Prime 交互式会话
    try:
        proc = subprocess.run(args, env=env)
        return proc.returncode
    except KeyboardInterrupt:
        print("\n[Prime Chat] 用户中断")
        return 130
    except FileNotFoundError:
        print(f"[Prime Chat] 找不到 Prime CLI: {PRIME_CLI}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Content Studio Direct Prime Console - 项目绑定的 Prime Agent 入口"
    )
    parser.add_argument("--project-id", required=True, help="OM project ID")
    args = parser.parse_args()

    try:
        return run_prime_chat(args.project_id)
    except PrimeChatError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
