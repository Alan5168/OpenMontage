from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from lib.scenario_catalog import (
    ScenarioCatalogError,
    freeze_scenario_for_job,
    load_catalog,
    resolve_scenario,
)


def test_shipped_catalog_resolves_every_scenario() -> None:
    catalog = load_catalog()
    assert len(catalog["scenarios"]) >= 7
    for item in catalog["scenarios"]:
        resolved = resolve_scenario(item["id"])
        assert resolved["pipeline"]["name"] == item["pipeline"]
        assert resolved["profile"]["source_policy"] == item["source_policy"]
        assert item["maturity"] in {"FIXTURE_PASS", "PILOT_PASS", "PRODUCTION_ACCEPTED"}


def test_unknown_scenario_fails_closed() -> None:
    with pytest.raises(ScenarioCatalogError, match="Unknown scenario"):
        resolve_scenario("not-registered")


def test_source_policy_mismatch_is_rejected(tmp_path: Path) -> None:
    catalog = load_catalog()
    catalog["scenarios"][0]["source_policy"] = "SOURCE_MEDIA_REQUIRED"
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    with pytest.raises(ScenarioCatalogError, match="source_policy mismatch"):
        resolve_scenario(catalog["scenarios"][0]["id"], catalog_path=path)


def test_job_selection_is_frozen_and_cannot_switch(tmp_path: Path) -> None:
    path = freeze_scenario_for_job(tmp_path, "comic_nonfiction_short_knowledge_zh")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["scenario"]["id"] == "comic_nonfiction_short_knowledge_zh"
    assert payload["profile"]["sceneplan_contract"] == "seven-column-v1"

    with pytest.raises(ScenarioCatalogError, match="already frozen"):
        freeze_scenario_for_job(tmp_path, "comic_nonfiction_short_news_zh")


def test_knowledge_short_uses_fixture_validated_sota_image_policy() -> None:
    resolved = resolve_scenario("comic_nonfiction_short_knowledge_zh")
    policy = resolved["profile"]["provider_policy"]

    assert policy["image_selection_mode"] == "validated_sota"
    assert policy["model_change_requires_revalidation"] is True
    assert policy["image_allowlist"] == ["dashscope", "volcengine"]
    assert policy["image_preferences"] == [
        {
            "provider": "dashscope",
            "model": "wan2.7-image-pro",
            "role": "primary",
            "requires_fixture_validation": True,
        },
        {
            "provider": "volcengine",
            "model": "doubao-seedream-5.0-lite",
            "role": "fallback",
            "requires_fixture_validation": True,
        },
    ]


def test_knowledge_short_uses_fixture_validated_asr_ranking() -> None:
    resolved = resolve_scenario("comic_nonfiction_short_knowledge_zh")
    policy = resolved["profile"]["asr_policy"]

    assert policy == {
        "selection_mode": "validated_primary_with_precision_backup",
        "primary": {
            "provider": "funasr",
            "model": "iic/SenseVoiceSmall",
            "device": "cuda",
            "compute_type": "float32",
            "role": "primary_clock",
            "requires_fixture_validation": True,
        },
        "backup": {
            "provider": "faster-whisper",
            "model": "large-v3-turbo",
            "device": "cpu",
            "compute_type": "int8",
            "role": "precision_backup",
            "requires_fixture_validation": True,
        },
        "approved_script_is_lexical_truth": True,
        "model_change_requires_revalidation": True,
    }
