"""Quote-before-spend for metered video providers.

StarReel's agent discipline, mapped onto OM tools: estimate, show, confirm.
Does not execute, does not reserve credits, does not touch dispatch_cut.
Local H3 estimate_cost is 0.0 — quoting it is a no-op.
"""

from __future__ import annotations

from typing import Any

NON_RETRYABLE = frozenset(
    {
        "insufficient_credits",
        "moderation",
        "copyright",
        "quota",
        "402",
        "content_policy",
    }
)


def quote_metered_tool(tool: Any, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = inputs if isinstance(inputs, dict) else {}
    usd = float(tool.estimate_cost(payload) or 0.0)
    runtime_s = float(tool.estimate_runtime(payload) or 0.0)
    policy = getattr(tool, "retry_policy", None)
    retryable = list(getattr(policy, "retryable_errors", None) or [])
    return {
        "quoted": True,
        "tool": getattr(tool, "name", type(tool).__name__),
        "usd": usd,
        "runtime_s": runtime_s,
        "requires_confirm": usd > 0.0,
        "retryable_errors": retryable,
        "not_retryable": sorted(NON_RETRYABLE),
        "execute": False,
    }
