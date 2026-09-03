#!/usr/bin/env python3
"""codex-mcp-bridge — Expose Codex as an MCP server on Windows.

`codex app-server daemon` is Unix-only. This bridge provides a minimal
MCP server interface over stdio that Pi and other MCP clients can use
to delegate coding tasks to Codex.

Usage:
    python tools/development/codex_mcp_bridge.py

This is NOT a full app-server replacement. It exposes a focused subset:
    - codex_exec: Run a non-interactive Codex task
    - codex_review: Run a code review
    - codex_tui: Launch interactive TUI (non-blocking)

Register in Pi's config (~/.pi/agent/config.json or similar) as an MCP server.
"""

import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Any

# MCP SDK is optional — fall back to raw JSON-RPC if not available
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


OM_REPO = Path(__file__).resolve().parent.parent.parent
CODEX_BIN = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"


def _find_codex() -> str | None:
    if CODEX_BIN.exists():
        return str(CODEX_BIN)
    codex_path = subprocess.run(["where", "codex"], capture_output=True, text=True)
    if codex_path.returncode == 0:
        return codex_path.stdout.strip().split("\n")[0]
    return None


def run_codex_exec(prompt: str, cwd: str | None = None, model: str | None = None,
                  sandbox: str = "read-only", timeout: int = 600) -> dict[str, Any]:
    """Run codex exec and return the result."""
    codex = _find_codex()
    if not codex:
        return {"error": "Codex binary not found"}

    cmd = ["node", codex, "exec", "-C", cwd or str(OM_REPO), "-s", sandbox]
    if model:
        cmd.extend(["-m", model])
    cmd.append(prompt)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd or str(OM_REPO))
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Codex exec timed out"}
    except Exception as e:
        return {"error": str(e)}


def run_codex_review(prompt: str, cwd: str | None = None) -> dict[str, Any]:
    """Run codex review and return the result."""
    codex = _find_codex()
    if not codex:
        return {"error": "Codex binary not found"}

    cmd = ["node", codex, "exec", "review", "-C", cwd or str(OM_REPO), prompt]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, cwd=cwd or str(OM_REPO))
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


# ── MCP Server (if SDK available) ──────────────────────────────────────────

if HAS_MCP:
    server = Server("codex-bridge")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="codex_exec",
                description="Run a non-interactive Codex coding task in the OpenMontage workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Task description for Codex"},
                        "cwd": {"type": "string", "description": "Working directory (defaults to OM repo)"},
                        "model": {"type": "string", "description": "Model override (e.g. gpt-5.6-sol)"},
                        "sandbox": {"type": "string", "enum": ["read-only", "workspace-write", "danger-full-access"], "default": "read-only"},
                        "timeout": {"type": "integer", "default": 600},
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="codex_review",
                description="Run a Codex code review on the current workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Review instructions"},
                        "cwd": {"type": "string", "description": "Working directory"},
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "codex_exec":
            result = run_codex_exec(**arguments)
        elif name == "codex_review":
            result = run_codex_review(**arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Raw JSON-RPC fallback (no MCP SDK) ────────────────────────────────────

def handle_jsonrpc_request(request: dict) -> dict:
    """Handle a single JSON-RPC request without MCP SDK."""
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "codex_exec",
                    "description": "Run a non-interactive Codex coding task",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "cwd": {"type": "string"},
                            "model": {"type": "string"},
                            "sandbox": {"type": "string", "default": "read-only"},
                        },
                        "required": ["prompt"],
                    },
                },
                {
                    "name": "codex_review",
                    "description": "Run a Codex code review",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "cwd": {"type": "string"},
                        },
                        "required": ["prompt"],
                    },
                },
            ]
        }
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        if tool_name == "codex_exec":
            return run_codex_exec(**arguments)
        elif tool_name == "codex_review":
            return run_codex_review(**arguments)
        return {"error": f"Unknown tool: {tool_name}"}

    return {"error": f"Unknown method: {method}"}


async def stdio_main():
    """Run as stdio MCP server."""
    if HAS_MCP:
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    else:
        # Raw JSON-RPC over stdio
        import sys
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = handle_jsonrpc_request(request)
                print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": response}), flush=True)
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    print(f"[codex-bridge] Codex binary: {_find_codex() or 'NOT FOUND'}", file=sys.stderr)
    print(f"[codex-bridge] MCP SDK: {'available' if HAS_MCP else 'not available (using JSON-RPC fallback)'}", file=sys.stderr)
    print(f"[codex-bridge] Workspace: {OM_REPO}", file=sys.stderr)

    if HAS_MCP:
        asyncio.run(stdio_main())
    else:
        # Synchronous stdio loop for JSON-RPC fallback
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = handle_jsonrpc_request(request)
                print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": response}), flush=True)
            except json.JSONDecodeError:
                pass
