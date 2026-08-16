from __future__ import annotations

import argparse
import hashlib
import json

from tools import om_context_bridge as bridge


def test_ingest_calls_add_resource_before_claiming_success(tmp_path, monkeypatch, capsys):
    source = tmp_path / "probe.md"
    source.write_text("semantic probe nonce", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": str(source),
                "target": "viking://resources/content-studio/goodcases/probe.md",
                "provenance": "test",
                "license": "reference_only_not_for_render",
                "sha256": digest,
            }
        ),
        encoding="utf-8",
    )
    context_root = tmp_path / "context"
    monkeypatch.setattr(bridge, "CONTEXT_ROOT", context_root)
    calls = []

    def fake_ov_cli(args, timeout=60):
        calls.append((list(args), timeout))
        return 0, json.dumps({"ok": True, "result": {"status": "success"}}), ""

    monkeypatch.setattr(bridge, "_ov_cli", fake_ov_cli)
    bridge.cmd_ingest(argparse.Namespace(manifest=str(manifest)))

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "INGESTED"
    assert payload["semantic_indexed"] is True
    assert calls[0][0][:2] == ["add-resource", str(source)]
    assert "--wait" in calls[0][0]
    assert calls[0][0][calls[0][0].index("--to") + 1] == (
        "viking://resources/content-studio/goodcases/probe.md"
    )
    assert (context_root / "goodcases" / "probe.md").read_text(encoding="utf-8") == (
        "semantic probe nonce"
    )


def test_ingest_does_not_copy_when_semantic_index_fails(tmp_path, monkeypatch):
    source = tmp_path / "probe.md"
    source.write_text("semantic probe nonce", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": str(source),
                "target": "viking://resources/content-studio/goodcases/probe.md",
                "provenance": "test",
                "license": "reference_only_not_for_render",
            }
        ),
        encoding="utf-8",
    )
    context_root = tmp_path / "context"
    monkeypatch.setattr(bridge, "CONTEXT_ROOT", context_root)
    monkeypatch.setattr(
        bridge,
        "_ov_cli",
        lambda args, timeout=60: (1, json.dumps({"ok": False}), "index failed"),
    )

    try:
        bridge.cmd_ingest(argparse.Namespace(manifest=str(manifest)))
        assert False, "expected ContextBridgeError"
    except bridge.ContextBridgeError:
        pass
    assert not (context_root / "goodcases" / "probe.md").exists()


def test_read_resolves_openviking_asset_directory(monkeypatch, capsys):
    monkeypatch.setattr(bridge, "_http_ok", lambda url: (True, "ok"))
    calls = []

    def fake_ov_cli(args, timeout=60):
        calls.append(list(args))
        if args[0] == "read" and len(calls) == 1:
            return 1, "", "cannot read directory"
        if args[0] == "ls":
            return 0, json.dumps(
                {
                    "ok": True,
                    "result": [
                        {
                            "uri": "viking://resources/content-studio/goodcases/reference-atoms/a.json/a.md",
                            "isDir": False,
                        }
                    ],
                }
            ), ""
        return 0, json.dumps({"ok": True, "result": {"content": "atom"}}), ""

    monkeypatch.setattr(bridge, "_ov_cli", fake_ov_cli)
    bridge.cmd_read(
        argparse.Namespace(
            viking_uri="viking://resources/content-studio/goodcases/reference-atoms/a.json"
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "openviking-0.4.13-cli"
    assert payload["asset_root_resolved"] is True
    assert payload["resolved_viking_uri"].endswith("/a.json/a.md")
