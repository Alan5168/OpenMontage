"""Codex CLI bridge — exposes Codex as an OpenMontage development tool.

On Windows, `codex app-server daemon` is Unix-only. This tool wraps
`codex exec` (non-interactive) and `codex` (interactive TUI launcher)
as a standard BaseTool so Pi and OM pipelines can delegate coding tasks.

Three primary use cases:
  1. Debug ComfyUI workflows  — read/modify workflow JSON, run generation
  2. Write/modify skills/pipeline YAML — edit skill files, run tests
  3. Check OM status / advance pipeline — query checkpoints, run OM commands
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    ToolResult,
    ToolRuntime,
    ToolStatus,
    ToolStability,
    ToolTier,
)


class CodexExec(BaseTool):
    """Run Codex non-interactive commands via `codex exec`."""

    name = "codex_exec"
    capability = "development"
    provider = "codex"
    runtime = ToolRuntime.LOCAL
    tier = "GENERATE"
    stability = ToolStability.EXPERIMENTAL
    capabilities = ["code_generation", "code_review", "file_editing", "debugging"]
    best_for = [
        "Debug ComfyUI workflow JSON",
        "Write or modify OM skills / pipeline YAML",
        "Run Python tests on demand",
        "Refactor code with structured output",
    ]
    fallback_tools = []
    cost = "$0.00 (uses existing Codex subscription)"

    def __init__(self) -> None:
        super().__init__()
        self._codex_bin = self._find_codex()

    def _find_codex(self) -> str | None:
        """Locate the codex binary."""
        # Check npm global install
        npm_global = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        if npm_global.exists():
            return str(npm_global)
        # Check PATH
        codex_in_path = shutil.which("codex")
        if codex_in_path:
            return codex_in_path
        return None

    def get_status(self) -> ToolStatus:
        if self._codex_bin is None:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability": self.capability,
            "provider": self.provider,
            "runtime": self.runtime,
            "status": self.get_status().value,
            "codex_binary": self._codex_bin,
            "install_instructions": "npm install -g @openai/codex && npm install -g @openai/codex-win32-x64",
            "notes": [
                "app-server daemon is Unix-only — this tool wraps codex exec instead",
                "codex mcp-server is deprecated — use codex exec for programmatic access",
            ],
        }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute a Codex task.

        Parameters:
            prompt (str): Task description for Codex
            cwd (str): Working directory (defaults to OM repo root)
            model (str): Override model (e.g. "gpt-5.6-sol")
            sandbox (str): Sandbox mode — "read-only" (default), "workspace-write", "danger-full-access"
            output_path (str): Where to write the last message output
            output_schema (str): Path to JSON Schema for structured output
            approve_for_me (bool): Auto-approve with workspace-write sandbox
            operation (str): "exec" (default), "review"
        """
        if self._codex_bin is None:
            return ToolResult(
                success=False,
                error="Codex binary not found. Install: npm install -g @openai/codex @openai/codex-win32-x64",
            )

        prompt = params.get("prompt", "")
        if not prompt:
            return ToolResult(success=False, error="Missing required parameter: prompt")

        cwd = params.get("cwd", str(Path(__file__).resolve().parent.parent.parent))
        model = params.get("model")
        sandbox = params.get("sandbox", "read-only")
        output_path = params.get("output_path")
        output_schema = params.get("output_schema")
        approve_for_me = params.get("approve_for_me", False)
        operation = params.get("operation", "exec")

        cmd = ["node", self._codex_bin, operation]

        # Options (exec-only — review does not support sandbox flags)
        cmd.extend(["-C", cwd])
        if operation != "review":
            cmd.extend(["-s", sandbox])

        if model:
            cmd.extend(["-m", model])
        if output_path:
            cmd.extend(["-o", output_path])
        if output_schema:
            cmd.extend(["--output-schema", output_schema])
        if approve_for_me and operation != "review":
            cmd.append("--approve-for-me")

        # Prompt as argument
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=params.get("timeout", 600),
                cwd=cwd,
                env={**os.environ, "CONTENT_STUDIO_ROOT": os.environ.get("CONTENT_STUDIO_ROOT", "C:\\ContentStudio")},
            )

            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "command": " ".join(cmd[:5]) + " ...",  # truncate for safety
                },
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Codex exec timed out")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CodexTui(BaseTool):
    """Launch Codex interactive TUI (for terminal use, not pipeline dispatch)."""

    name = "codex_tui"
    capability = "development"
    provider = "codex"
    runtime = ToolRuntime.LOCAL
    tier = "GENERATE"
    stability = ToolStability.EXPERIMENTAL
    capabilities = ["interactive_coding", "code_review", "debugging"]
    best_for = [
        "Interactive ComfyUI workflow debugging",
        "Interactive skill/pipeline authoring",
        "Exploratory OM state inspection",
    ]
    fallback_tools = []
    cost = "$0.00 (uses existing Codex subscription)"

    def __init__(self) -> None:
        super().__init__()
        self._codex_bin = CodexExec()._find_codex()

    def get_status(self) -> ToolStatus:
        if self._codex_bin is None:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability": self.capability,
            "provider": self.provider,
            "runtime": self.runtime,
            "status": self.get_status().value,
            "codex_binary": self._codex_bin,
            "install_instructions": "npm install -g @openai/codex && npm install -g @openai/codex-win32-x64",
        }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        """Launch Codex TUI in the OM workspace.

        Parameters:
            cwd (str): Working directory
            model (str): Model to use
        """
        if self._codex_bin is None:
            return ToolResult(
                success=False,
                error="Codex binary not found.",
            )

        cwd = params.get("cwd", str(Path(__file__).resolve().parent.parent.parent))
        model = params.get("model")

        cmd = ["node", self._codex_bin]
        if model:
            cmd.extend(["-m", model])

        try:
            # TUI needs interactive terminal — use Popen for non-blocking
            subprocess.Popen(
                cmd,
                cwd=cwd,
                env={**os.environ, "CONTENT_STUDIO_ROOT": os.environ.get("CONTENT_STUDIO_ROOT", "C:\\ContentStudio")},
            )
            return ToolResult(
                success=True,
                data={"message": f"Codex TUI launched in {cwd}"},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
