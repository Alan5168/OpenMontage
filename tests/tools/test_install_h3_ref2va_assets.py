from __future__ import annotations

from tools.install_h3_ref2va_assets import REF2VA_NAME, UPSTREAM_MODEL, replace_model_name


def test_replaces_nested_workflow_model_name_only():
    source = {
        "nodes": [
            {"widgets_values": [UPSTREAM_MODEL, "unchanged"]},
            {"nested": {"model": UPSTREAM_MODEL}},
        ]
    }
    replaced, count = replace_model_name(source)
    assert count == 2
    assert replaced["nodes"][0]["widgets_values"][0] == REF2VA_NAME
    assert replaced["nodes"][0]["widgets_values"][1] == "unchanged"
