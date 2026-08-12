"""JSON Schema for adapter I/O. Keep payloads small and fail closed."""

from __future__ import annotations

JOB_REF_SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "job_id",
        "scenario_id",
        "pipeline_type",
        "stage",
        "status",
        "checkpoint_hash",
        "project_dir",
        "authorized_root",
    ],
    "additionalProperties": True,
    "properties": {
        "schema_version": {"type": "string"},
        "job_id": {"type": "string", "minLength": 1},
        "scenario_id": {"type": ["string", "null"]},
        "pipeline_type": {"type": ["string", "null"]},
        "stage": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "checkpoint_hash": {"type": ["string", "null"]},
        "project_dir": {"type": "string"},
        "authorized_root": {"type": "string"},
    },
}

STAGE_PACK_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "job_id", "stage", "artifact_name", "source"],
    "additionalProperties": True,
    "properties": {
        "schema_version": {"type": "string"},
        "job_id": {"type": "string"},
        "stage": {"type": "string"},
        "artifact_name": {"type": ["string", "null"]},
        "source": {
            "type": "object",
            "required": ["path", "hash", "bytes", "loaded_at", "reload_method"],
            "properties": {
                "path": {"type": "string"},
                "hash": {"type": "string"},
                "bytes": {"type": "integer"},
                "loaded_at": {"type": "string"},
                "reload_method": {"type": "string"},
            },
        },
    },
}

LESSON_SCHEMA = {
    "type": "object",
    "required": ["error_class", "summary", "evidence_paths", "status"],
    "additionalProperties": True,
    "properties": {
        "error_class": {"type": "string", "minLength": 1},
        "summary": {"type": "string", "minLength": 1},
        "evidence_paths": {"type": "array", "items": {"type": "string"}},
        "status": {"type": "string", "enum": ["candidate", "accepted", "rejected"]},
        "scenario_id": {"type": "string"},
        "repair": {"type": "string"},
    },
}
