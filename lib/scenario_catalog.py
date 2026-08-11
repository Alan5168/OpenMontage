"""Declarative scenario/profile resolution for OpenMontage distributions.

This module validates and freezes a user's scenario choice. It deliberately
does not execute stages, choose creative treatments, or review outputs; those
responsibilities remain in the selected pipeline manifest and director skills.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from lib.pipeline_loader import load_pipeline

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "scenarios" / "catalog.yaml"
DEFAULT_PROFILES_DIR = ROOT / "profiles"
CATALOG_SCHEMA = ROOT / "schemas" / "scenarios" / "scenario_catalog.schema.json"
PROFILE_SCHEMA = ROOT / "schemas" / "profiles" / "content_profile.schema.json"


class ScenarioCatalogError(ValueError):
    """Raised when a scenario catalog cannot resolve to a valid frozen job choice."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ScenarioCatalogError(f"Expected object in {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = (path or DEFAULT_CATALOG).resolve()
    catalog = _load_yaml(catalog_path)
    jsonschema.validate(catalog, _load_json(CATALOG_SCHEMA))
    ids = [item["id"] for item in catalog["scenarios"]]
    if len(ids) != len(set(ids)):
        raise ScenarioCatalogError("Scenario ids must be unique")
    return catalog


def load_profile(profile_id: str, profiles_dir: Path | None = None) -> tuple[dict[str, Any], Path]:
    if not profile_id or Path(profile_id).name != profile_id:
        raise ScenarioCatalogError(f"Unsafe profile id: {profile_id!r}")
    profile_path = ((profiles_dir or DEFAULT_PROFILES_DIR) / f"{profile_id}.yaml").resolve()
    profile = _load_yaml(profile_path)
    jsonschema.validate(profile, _load_json(PROFILE_SCHEMA))
    if profile["id"] != profile_id:
        raise ScenarioCatalogError(
            f"Profile id mismatch: requested {profile_id!r}, file declares {profile['id']!r}"
        )
    if profile["duration_seconds"]["minimum"] > profile["duration_seconds"]["maximum"]:
        raise ScenarioCatalogError(f"Invalid duration range in profile {profile_id!r}")
    return profile, profile_path


def resolve_scenario(
    scenario_id: str,
    *,
    catalog_path: Path | None = None,
    profiles_dir: Path | None = None,
) -> dict[str, Any]:
    """Resolve one user-facing scenario to validated pipeline/profile data."""
    path = (catalog_path or DEFAULT_CATALOG).resolve()
    catalog = load_catalog(path)
    matches = [item for item in catalog["scenarios"] if item["id"] == scenario_id]
    if not matches:
        raise ScenarioCatalogError(f"Unknown scenario: {scenario_id!r}")
    scenario = deepcopy(matches[0])
    pipeline = load_pipeline(scenario["pipeline"])
    profile, profile_path = load_profile(scenario["profile"], profiles_dir)
    if scenario["source_policy"] != profile["source_policy"]:
        raise ScenarioCatalogError(
            f"source_policy mismatch for {scenario_id!r}: "
            f"catalog={scenario['source_policy']} profile={profile['source_policy']}"
        )
    return {
        "scenario": scenario,
        "pipeline": {"name": pipeline["name"], "version": pipeline["version"]},
        "profile": profile,
        "provenance": {
            "catalog_path": str(path),
            "catalog_sha256": _sha256(path),
            "profile_path": str(profile_path),
            "profile_sha256": _sha256(profile_path),
        },
    }


def freeze_scenario_for_job(
    project_dir: Path,
    scenario_id: str,
    *,
    catalog_path: Path | None = None,
    profiles_dir: Path | None = None,
) -> Path:
    """Persist an immutable scenario selection in the OM job root."""
    resolved = resolve_scenario(
        scenario_id,
        catalog_path=catalog_path,
        profiles_dir=profiles_dir,
    )
    target = project_dir / "job_manifest.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        existing_id = existing.get("scenario", {}).get("id")
        if existing_id != scenario_id:
            raise ScenarioCatalogError(
                f"Job scenario already frozen as {existing_id!r}; cannot replace with {scenario_id!r}"
            )
        return target
    project_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": "1.0",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        **resolved,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
