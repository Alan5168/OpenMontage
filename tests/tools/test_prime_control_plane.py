from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.prime_rpc_control_plane import (
    ControlPlaneResult,
    is_progress_event,
    parse_model_ref,
    reasoning_chain_from_env,
    run_foreman_rpc,
)


FAKE = Path(__file__).resolve().parent / "fake_prime_rpc.py"


def test_parse_model_ref():
    assert parse_model_ref("bailian/qwen3.8-max") == ("bailian", "qwen3.8-max")


def test_default_content_chain_is_longcat_then_mimo():
    assert reasoning_chain_from_env({}) == (
        "longcat/LongCat-2.0",
        "mimo/mimo-v2.5",
    )


def test_tool_start_is_progress_agent_start_is_not():
    assert is_progress_event({"type": "tool_execution_start", "toolName": "ipython"})
    assert not is_progress_event({"type": "agent_start"})
    assert not is_progress_event({"type": "session_state"})


def test_hanging_primary_fails_over_inside_same_process():
    result = run_foreman_rpc(
        [sys.executable, "-u", str(FAKE)],
        "call propose_identity_candidates",
        env={},
        chain=("bailian/qwen3.8-max", "minimax/MiniMax-M3"),
        first_token_timeout_ms=400,
        command_timeout_s=5,
        turn_timeout_s=5,
    )
    assert result.ok is True
    assert result.used_model == "minimax/MiniMax-M3"
    assert result.failovers
    assert result.failovers[0].from_ref == "bailian/qwen3.8-max"
    assert result.failovers[0].reason == "first_token_timeout"
    tools = [row.get("toolName") for row in result.events if row.get("type") == "tool_execution_start"]
    assert "ipython" in tools


def test_unavailable_primary_fails_over(monkeypatch):
    class FakeRpc:
        def __init__(self) -> None:
            self.sent: list[dict] = []
            self._queue: list[dict] = []

        def send(self, payload: dict) -> None:
            self.sent.append(payload)
            kind = payload.get("type")
            if kind == "set_model" and payload.get("modelId") == "missing":
                self._queue.append(
                    {
                        "id": payload.get("id"),
                        "type": "response",
                        "command": "set_model",
                        "success": False,
                        "error": "Model not found",
                    }
                )
            elif kind == "set_model":
                self._queue.append(
                    {
                        "id": payload.get("id"),
                        "type": "response",
                        "command": "set_model",
                        "success": True,
                    }
                )
            elif kind == "prompt":
                self._queue.append(
                    {
                        "id": payload.get("id"),
                        "type": "response",
                        "command": "prompt",
                        "success": True,
                    }
                )
                self._queue.append({"type": "tool_execution_start", "toolName": "ipython"})
                self._queue.append({"type": "agent_end"})

        def wait_event(self, timeout_s: float):
            if not self._queue:
                return None
            return self._queue.pop(0)

        def close(self) -> None:
            return None

    fake = FakeRpc()

    class FakeProc:
        stdin = None
        stdout = None
        stderr = None

        def wait(self, timeout=None):
            return 0

        def kill(self) -> None:
            return None

    import tools.prime_rpc_control_plane as mod

    monkeypatch.setattr(mod, "JsonlRpc", lambda proc: fake)
    result = run_foreman_rpc(
        ["unused"],
        "hello",
        env={},
        chain=("bailian/missing", "minimax/MiniMax-M3"),
        first_token_timeout_ms=1000,
        command_timeout_s=2,
        turn_timeout_s=2,
        popen=lambda *args, **kwargs: FakeProc(),
    )
    assert isinstance(result, ControlPlaneResult)
    assert result.ok is True
    assert result.used_model == "minimax/MiniMax-M3"
    assert result.failovers[0].reason == "provider_unavailable"
    assert json.dumps(result.failovers[0].__dict__)
