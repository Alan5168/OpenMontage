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
