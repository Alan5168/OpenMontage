#!/usr/bin/env python3
"""Score frozen no-media architecture/sceneplan candidates against known error families."""

from __future__ import annotations

import json
import re
from typing import Any

ERROR_PATTERNS = {
    "music_covers_vo": re.compile(r"bgm[^\\n]{0,40}(0\\.3[2-9]|0\\.[4-9]|1\\.0)|music covering|盖住口播", re.I),
    "intent_prompt_result_mixed": re.compile(r"intent[^\\n]{0,20}prompt[^\\n]{0,20}result|one column|混为一列", re.I),
    "render_before_gate": re.compile(r"render (now|before gate)|提前渲染|skip gate", re.I),
    "generated_readable_text": re.compile(r"generate readable (chinese|text)|生成可读字|burn text in image model", re.I),
}


def score_candidate(candidate: dict[str, Any], known_errors: list[str] | None = None) -> dict[str, Any]:
    known_errors = known_errors or list(ERROR_PATTERNS)
    blob = json.dumps(candidate, ensure_ascii=False)
    recurrences = []
    for error_class in known_errors:
        pattern = ERROR_PATTERNS.get(error_class)
        if pattern and pattern.search(blob):
            recurrences.append(error_class)
    om_hard_fail = False
    if candidate.get("schema_valid") is False:
        om_hard_fail = True
    if candidate.get("provider_decided") is True:
        recurrences.append("provider_decided_too_early")
    return {
        "om_hard_gate": "FAIL" if om_hard_fail else "PASS",
        "known_error_recurrences": recurrences,
        "recurrence_count": len(recurrences),
        "first_pass_accepted": (not om_hard_fail) and not recurrences,
        "repeated_full_file_injections": int(candidate.get("repeated_full_file_injections") or 0),
    }
