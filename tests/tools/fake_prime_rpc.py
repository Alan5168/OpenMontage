"""Fake Prime RPC process for control-plane failover tests.

Primary model hangs until abort. Fallback model emits IPython progress then agent_end.
Does not call OpenMontage.
"""

from __future__ import annotations

import json
import sys
import threading


def main() -> int:
    current = {"provider": "bailian", "modelId": "qwen3.8-max"}
    aborted = threading.Event()

    def emit(payload: dict) -> None:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    emit({"type": "session_state", "state": {"status": "active"}})
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        cmd = json.loads(line)
        kind = cmd.get("type")
        req_id = cmd.get("id")
        if kind == "set_model":
            current["provider"] = cmd.get("provider")
            current["modelId"] = cmd.get("modelId")
            emit(
                {
                    "id": req_id,
                    "type": "response",
                    "command": "set_model",
                    "success": True,
                    "data": dict(current),
                }
            )
        elif kind == "prompt":
            emit({"id": req_id, "type": "response", "command": "prompt", "success": True})
            if current["modelId"] != "qwen3.8-max":
                emit(
                    {
                        "type": "tool_execution_start",
                        "toolCallId": "call_ipython",
                        "toolName": "ipython",
                        "args": {"code": "import om_prime_adapter"},
                    }
                )
                emit({"type": "agent_end", "messages": []})
        elif kind == "abort":
            aborted.set()
            emit({"id": req_id, "type": "response", "command": "abort", "success": True})
            emit(
                {
                    "type": "message_update",
                    "assistantMessageEvent": {"type": "error", "reason": "aborted"},
                }
            )
            emit({"type": "agent_end", "messages": []})
        else:
            emit(
                {
                    "id": req_id,
                    "type": "response",
                    "command": kind,
                    "success": False,
                    "error": f"unknown {kind}",
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
