"""Prime-internal reasoning failover for one-shot foreman sessions.

Keeps one Prime RPC process (IPython/skills stay up). If the configured
primary model never produces a first token, abort that turn and switch to
the next configured model. Does not call OM production actions itself.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TextIO

DEFAULT_CHAIN = (
    "longcat/LongCat-2.0",
    "mimo/mimo-v2.5",
)
DEFAULT_FIRST_TOKEN_TIMEOUT_MS = 90_000
PROGRESS_EVENT_TYPES = frozenset(
    {
        "start",
        "text_start",
        "text_delta",
        "thinking_start",
        "thinking_delta",
        "toolcall_start",
        "toolcall_delta",
    }
)


class ControlPlaneError(RuntimeError):
    """Control-plane failure. Prime process may still be alive."""


def parse_model_ref(ref: str) -> tuple[str, str]:
    token = str(ref or "").strip()
    if "/" not in token:
        raise ControlPlaneError(f"model ref must be provider/id: {ref!r}")
    provider, model_id = token.split("/", 1)
    provider = provider.strip()
    model_id = model_id.strip()
    if not provider or not model_id:
        raise ControlPlaneError(f"model ref must be provider/id: {ref!r}")
    return provider, model_id


def reasoning_chain_from_env(env: dict[str, str] | None = None) -> tuple[str, ...]:
    source = env if env is not None else os.environ
    raw = str(source.get("PRIME_REASONING_CHAIN") or "").strip()
    if not raw:
        return DEFAULT_CHAIN
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        return DEFAULT_CHAIN
    return tuple(parts)


def timeout_ms_from_env(env: dict[str, str] | None = None) -> int:
    source = env if env is not None else os.environ
    raw = str(source.get("PRIME_REASONING_FIRST_TOKEN_TIMEOUT_MS") or "").strip()
    if not raw:
        return DEFAULT_FIRST_TOKEN_TIMEOUT_MS
    value = int(raw)
    if value < 1:
        raise ControlPlaneError("PRIME_REASONING_FIRST_TOKEN_TIMEOUT_MS must be positive")
    return value


def is_progress_event(event: dict[str, Any]) -> bool:
    kind = str(event.get("type") or "")
    if kind in {"tool_execution_start", "tool_execution_end"}:
        return True
    if kind == "message_update":
        ame = event.get("assistantMessageEvent")
        if isinstance(ame, dict) and str(ame.get("type") or "") in PROGRESS_EVENT_TYPES:
            return True
    return False


def is_turn_error(event: dict[str, Any]) -> bool:
    kind = str(event.get("type") or "")
    if kind == "error":
        return True
    if kind == "message_update":
        ame = event.get("assistantMessageEvent")
        if isinstance(ame, dict) and str(ame.get("type") or "") == "error":
            return True
    return False


@dataclass
class FailoverRecord:
    from_ref: str
    to_ref: str
    reason: str
    at_ms: int


@dataclass
class ControlPlaneResult:
    ok: bool
    used_model: str | None
    failovers: list[FailoverRecord] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class JsonlRpc:
    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self.proc = proc
        self._lines: queue.Queue[str | None] = queue.Queue()
        self.stderr_tail: list[str] = []
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._err = threading.Thread(target=self._pump_err, daemon=True)
        self._reader.start()
        self._err.start()

    def _pump(self) -> None:
        stdout = self.proc.stdout
        if stdout is None:
            self._lines.put(None)
            return
        try:
            for line in stdout:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def _pump_err(self) -> None:
        stderr = self.proc.stderr
        if stderr is None:
            return
        for line in stderr:
            if len(self.stderr_tail) < 50:
                self.stderr_tail.append(line[:500])

    def send(self, payload: dict[str, Any]) -> None:
        stdin = self.proc.stdin
        if stdin is None:
            raise ControlPlaneError("Prime RPC stdin is closed")
        stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stdin.flush()

    def wait_event(self, timeout_s: float) -> dict[str, Any] | None:
        try:
            line = self._lines.get(timeout=timeout_s)
        except queue.Empty:
            return None
        if line is None:
            raise ControlPlaneError("Prime RPC stdout closed")
        text = line.strip()
        if not text:
            return self.wait_event(timeout_s)
        try:
            event = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ControlPlaneError(f"Prime RPC sent non-JSON: {text[:200]}") from exc
        if not isinstance(event, dict):
            raise ControlPlaneError("Prime RPC event is not an object")
        return event

    def close(self) -> None:
        stdin = self.proc.stdin
        if stdin is not None:
            try:
                stdin.close()
            except OSError:
                pass


def _wait_command(
    rpc: JsonlRpc,
    command: str,
    *,
    timeout_s: float,
    collected: list[dict[str, Any]],
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ControlPlaneError(f"timed out waiting for {command} response")
        event = rpc.wait_event(remaining)
        if event is None:
            raise ControlPlaneError(f"timed out waiting for {command} response")
        collected.append(event)
        if event.get("type") == "response" and event.get("command") == command:
            return event


def _wait_first_progress(
    rpc: JsonlRpc,
    *,
    timeout_s: float,
    collected: list[dict[str, Any]],
) -> str:
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "timeout"
        event = rpc.wait_event(remaining)
        if event is None:
            return "timeout"
        collected.append(event)
        if is_progress_event(event):
            return "progress"
        if is_turn_error(event):
            return "error"
        if event.get("type") == "agent_end":
            return "agent_end"


def _drain_until_agent_end(
    rpc: JsonlRpc,
    *,
    timeout_s: float,
    collected: list[dict[str, Any]],
) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ControlPlaneError("timed out waiting for agent_end")
        event = rpc.wait_event(remaining)
        if event is None:
            raise ControlPlaneError("timed out waiting for agent_end")
        collected.append(event)
        if event.get("type") == "agent_end":
            return


def _abort_turn(rpc: JsonlRpc, collected: list[dict[str, Any]], command_timeout_s: float) -> None:
    rpc.send({"type": "abort"})
    try:
        _wait_command(rpc, "abort", timeout_s=command_timeout_s, collected=collected)
    except ControlPlaneError:
        return
    deadline = time.monotonic() + command_timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        event = rpc.wait_event(remaining)
        if event is None:
            return
        collected.append(event)
        if event.get("type") in {"agent_end", "error"}:
            return
        ame = event.get("assistantMessageEvent")
        if isinstance(ame, dict) and str(ame.get("type") or "") == "error":
            return


def run_foreman_rpc(
    argv: list[str],
    prompt: str,
    *,
    env: dict[str, str],
    chain: tuple[str, ...] | None = None,
    first_token_timeout_ms: int | None = None,
    command_timeout_s: float = 30.0,
    turn_timeout_s: float = 1800.0,
    popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    log: Callable[[str], None] | None = None,
) -> ControlPlaneResult:
    """Drive one Prime RPC process through a prompt with model failover."""
    models = chain or reasoning_chain_from_env(env)
    token_timeout_ms = (
        first_token_timeout_ms if first_token_timeout_ms is not None else timeout_ms_from_env(env)
    )
    emit = log or (lambda _line: None)
    failovers: list[FailoverRecord] = []
    collected: list[dict[str, Any]] = []
    started = time.monotonic()
    proc = popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    rpc = JsonlRpc(proc)
    try:
        for index, ref in enumerate(models):
            provider, model_id = parse_model_ref(ref)
            emit(f"control_plane: try {ref}")
            rpc.send({"id": f"set-{index}", "type": "set_model", "provider": provider, "modelId": model_id})
            set_resp = _wait_command(
                rpc, "set_model", timeout_s=command_timeout_s, collected=collected
            )
            if not set_resp.get("success"):
                err = str(set_resp.get("error") or "set_model failed")
                emit(f"control_plane: {ref} unavailable ({err})")
                if index + 1 < len(models):
                    failovers.append(
                        FailoverRecord(
                            from_ref=ref,
                            to_ref=models[index + 1],
                            reason="provider_unavailable",
                            at_ms=int((time.monotonic() - started) * 1000),
                        )
                    )
                    continue
                return ControlPlaneResult(
                    ok=False,
                    used_model=None,
                    failovers=failovers,
                    events=collected,
                    error=err,
                )
            rpc.send({"id": f"prompt-{index}", "type": "prompt", "message": prompt})
            prompt_resp = _wait_command(
                rpc, "prompt", timeout_s=command_timeout_s, collected=collected
            )
            if not prompt_resp.get("success"):
                err = str(prompt_resp.get("error") or "prompt rejected")
                emit(f"control_plane: prompt rejected on {ref} ({err})")
                if index + 1 < len(models):
                    failovers.append(
                        FailoverRecord(
                            from_ref=ref,
                            to_ref=models[index + 1],
                            reason="prompt_rejected",
                            at_ms=int((time.monotonic() - started) * 1000),
                        )
                    )
                    continue
                return ControlPlaneResult(
                    ok=False,
                    used_model=None,
                    failovers=failovers,
                    events=collected,
                    error=err,
                )
            outcome = _wait_first_progress(
                rpc,
                timeout_s=token_timeout_ms / 1000,
                collected=collected,
            )
            if outcome == "progress":
                emit(f"control_plane: first token on {ref}")
                _drain_until_agent_end(rpc, timeout_s=turn_timeout_s, collected=collected)
                return ControlPlaneResult(
                    ok=True,
                    used_model=ref,
                    failovers=failovers,
                    events=collected,
                )
            reason = "first_token_timeout" if outcome == "timeout" else "turn_error"
            emit(f"control_plane: {ref} failed ({reason})")
            already_ended = any(row.get("type") == "agent_end" for row in collected)
            if outcome == "timeout" or not already_ended:
                _abort_turn(rpc, collected, min(command_timeout_s, 15.0))
            if index + 1 >= len(models):
                return ControlPlaneResult(
                    ok=False,
                    used_model=None,
                    failovers=failovers,
                    events=collected,
                    error=reason,
                )
            failovers.append(
                FailoverRecord(
                    from_ref=ref,
                    to_ref=models[index + 1],
                    reason=reason,
                    at_ms=int((time.monotonic() - started) * 1000),
                )
            )
        return ControlPlaneResult(
            ok=False,
            used_model=None,
            failovers=failovers,
            events=collected,
            error="reasoning_chain_exhausted",
        )
    finally:
        rpc.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def print_control_plane_summary(result: ControlPlaneResult, sink: TextIO) -> None:
    payload = {
        "ok": result.ok,
        "used_model": result.used_model,
        "error": result.error,
        "failovers": [
            {
                "from": row.from_ref,
                "to": row.to_ref,
                "reason": row.reason,
                "at_ms": row.at_ms,
            }
            for row in result.failovers
        ],
    }
    sink.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
