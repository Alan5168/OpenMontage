from __future__ import annotations

import json
from pathlib import Path

from tools.content_studio_acceptance import GOAL_T1_T14, contract_sha256, locked_manifest
from tools.resource_governor import cmd_gc, _quarantine_move


def test_contracts_are_original_t1_t14():
    names = [t["name"] for t in GOAL_T1_T14]
    assert names == [
        "Read-only",
        "Async",
        "No overreach",
        "Visual",
        "Direct Prime",
        "Isolation",
        "Memory",
        "Secret",
        "Evolution",
        "OpenViking",
        "Media",
        "Real Go-Live",
        "Git/Secrets",
        "Resource/GC",
    ]
    assert GOAL_T1_T14[9]["name"] == "OpenViking"
    assert "20 条" in GOAL_T1_T14[9]["input"]
    assert GOAL_T1_T14[11]["name"] == "Real Go-Live"
    assert "READY_FOR_ALAN_FINAL_REVIEW" in GOAL_T1_T14[11]["acceptance"]


def test_contract_hash_stable():
    first = locked_manifest()
    second = locked_manifest()
    for a, b in zip(first["tests"], second["tests"]):
        assert a["contract_sha256"] == b["contract_sha256"]
        assert a["contract_sha256"] == contract_sha256(a)


def test_gc_quarantine_not_delete(tmp_path, monkeypatch):
    src = tmp_path / "jobcache"
    src.mkdir()
    f = src / "tmp.bin"
    f.write_bytes(b"hello-gc")
    monkeypatch.setattr("tools.resource_governor.QUARANTINE_ROOT", tmp_path / "quarantine")
    receipt = _quarantine_move(src, "test")
    assert not src.exists()
    q = Path(receipt["quarantine_path"])
    assert q.exists()
    assert (q / "tmp.bin").read_bytes() == b"hello-gc"
    assert "unlink" not in json.dumps(receipt)


def test_media_bridge_default_port():
    text = Path("tools/om_media_bridge.py").read_text(encoding="utf-8")
    assert "127.0.0.1:18889" in text
    assert "127.0.0.1:8001/embed" not in text


def test_context_bridge_uses_openviking_cli():
    text = Path("tools/om_context_bridge.py").read_text(encoding="utf-8")
    assert "openviking-0.4.13" in text
    assert "grep_fallback" in text
    assert "sys.exit(1)" in text


def test_learning_no_hash_simulation():
    text = Path("tools/learning_system.py").read_text(encoding="utf-8")
    assert "held_out_deterministic_simulation" not in text or "已禁用" in text
    assert "_run_held_out_regression" in text
