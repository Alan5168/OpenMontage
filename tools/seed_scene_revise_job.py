"""One-shot: copy lights-out v1 hashes into vid-scene-revise-v1. Does not dispatch."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

JOBS = Path(r"C:\ContentStudio\jobs")
SRC = JOBS / "vid-lights-out-scene-v1"
DST = JOBS / "vid-scene-revise-v1"
JOB_ID = "vid-scene-revise-v1"
SCENE_ID = "scene_revise"
PARENT_HASH = "606c7f5ac71354b1494af823dedbae8239e7a9e3b8af8b88117b7a40db1ef210"
SHOT_HASHES = {
    "S1": "fbf712f393f794408d3dcfcde5286ece6e9813b51d5c0397941cd50c20f5b7ef",
    "S2": "1dabb032629cb96c2f2924f165b63492862d134e4393d356d88ef0b46bea61e5",
    "S3": "dbaeddec830714a5f3a0302f0272eaec432710960fc78589a2b84e00fed873f0",
    "S4": "4e07715db4bcf20a43d75785f0e6eeb8197da28b0e897966608e422e0a3c51fa",
}
SKIP_DIR_NAMES = {"sessions", "session-artifacts"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rewrite(value):
    if isinstance(value, dict):
        return {key: _rewrite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite(item) for item in value]
    if isinstance(value, str):
        return (
            value.replace("vid-lights-out-scene-v1", JOB_ID)
            .replace("scene_lights_out", SCENE_ID)
        )
    return value


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not (SRC / "project.json").is_file():
        raise SystemExit(f"source missing: {SRC}")
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    copy_dirs = [
        SRC / "bible",
        SRC / "artifacts",
        SRC / "working" / "identity",
        SRC / "working" / "prime_rlm" / "keyframes",
        SRC / "working" / "prime_rlm" / "rollouts",
        SRC / "working" / "prime_rlm" / "execution_requests",
    ]
    for folder in copy_dirs:
        if folder.is_dir():
            shutil.copytree(folder, DST / folder.relative_to(SRC))
    src_mp4 = SRC / "working" / "prime_rlm" / "composed" / "scene_lights_out.mp4"
    dst_v1 = DST / "working" / "prime_rlm" / "composed" / "scene_v1.mp4"
    dst_v1.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_mp4, dst_v1)
    v1_receipt_dir = DST / "working" / "prime_rlm" / "composed" / "v1"
    v1_receipt_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        SRC / "working" / "prime_rlm" / "composed" / "COMPOSE_RECEIPT.json",
        v1_receipt_dir / "COMPOSE_RECEIPT.json",
    )
    for path in DST.rglob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        rewritten = _rewrite(payload)
        if path.name == "RECEIPT.json" and isinstance(rewritten, dict):
            rewritten.setdefault("revision_number", 1)
        path.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for shot_id in ("S3", "S4"):
        req = DST / "working" / "prime_rlm" / "execution_requests" / f"{shot_id}.json"
        req.unlink(missing_ok=True)
    proposal_src = SRC / "working" / "prime_rlm" / "scene_proposals" / "scene_lights_out.json"
    proposal = _rewrite(json.loads(proposal_src.read_text(encoding="utf-8-sig")))
    proposal["scene_id"] = SCENE_ID
    proposal["job_id"] = JOB_ID
    proposal["audience_state_change"] = (
        "Keep S1 hold and accepted S2 H3. Revise the 10s-onward stills: S3 steam insert and S4 reaction hold."
    )
    out_proposal = DST / "working" / "prime_rlm" / "scene_proposals" / f"{SCENE_ID}.json"
    _write(out_proposal, proposal)
    _write(
        DST / "working" / "prime_rlm" / "scene_proposals" / "CURRENT.json",
        {"scene_id": SCENE_ID, "path": f"jobs/{JOB_ID}/working/prime_rlm/scene_proposals/{SCENE_ID}.json"},
    )
    _write(
        DST / "project.json",
        {
            "version": "1.0",
            "created_at": _utc_now(),
            "project_id": JOB_ID,
            "title": "Scene REVISE propagation proof — targeted S3/S4",
            "pipeline_type": "unknown",
            "style_playbook": "premium-minimalist",
            "scenario_id": "fiction_anime_episode",
            "generate": False,
            "note": "SCENE_REVISE_PROPAGATION_PROOF. Cursor is not the foreman. V1 copied from lights-out. Do not redispatch S2.",
        },
    )
    _write(
        DST / "JOB_SKELETON.json",
        {
            "schema_version": "content-studio-scene-revise-job-skeleton/v1",
            "project_id": JOB_ID,
            "pipeline": "anime-hybrid",
            "profile": "fiction_anime_episode",
            "status": "SCENE_REVISE_PROPAGATION_PROOF",
            "foreman_proven": False,
            "studio_v1": False,
            "render_allowed": True,
            "generate": False,
            "frozen": False,
            "ip": "Blacklisted Chef",
            "scene_id": SCENE_ID,
            "h3_only": "S2",
            "parent_job": "vid-lights-out-scene-v1",
            "identity": {
                "avery": "bible/avery/master_sheet.png",
                "lucien": "bible/lucien/master_sheet.png",
                "inherited_from": "vid-lights-out-scene-v1",
                "source_lock": "vid3-blacklisted-chef-90s-v1",
                "do_not_relock": True,
            },
            "acceptance": [
                "REVISE is not a terminal stop.",
                "Prime maps scene-level feedback to affected shots.",
                "Unnamed shots do not move. S1 hash unchanged. S2 H3 hash unchanged.",
                "OM executes only affected cuts, composes scene_v2 with a new hash and parent_scene_hash.",
                "Return to scene-level review only. Cursor does not dispatch.",
            ],
            "waiting_on": [
                "Prime: submit_revision_proposal then dispatch only affected cuts, then compose_scene.",
                "Do not redispatch S2 H3. Do not polish for art.",
                "Cursor must not impersonate Prime.",
            ],
        },
    )
    _write(
        DST / "working" / "prime_rlm" / "composed" / "PARENT_COMPOSE.json",
        {
            "parent_scene_hash": PARENT_HASH,
            "shot_hashes": SHOT_HASHES,
            "composed_path": f"jobs/{JOB_ID}/working/prime_rlm/composed/scene_v1.mp4",
            "source_job": "vid-lights-out-scene-v1",
            "source_scene_id": "scene_lights_out",
            "review_id": "2026-08-17T12:05:19.483108+00:00",
        },
    )
    _write(
        DST / "working" / "prime_rlm" / "HUMAN_PREFERENCE.json",
        {
            "schema_version": "om-human-preference/v1",
            "action": "record_human_preference",
            "job_id": JOB_ID,
            "label": "REVISE",
            "target": SCENE_ID,
            "caller": "human",
            "canonical_owner": "openmontage",
            "promoted_to_hard_rule": False,
            "approved": False,
            "created_at": "2026-08-17T12:05:19.483108+00:00",
            "note": "Seeded from lights-out scene review. After ~10s two stills look bad; pot smoke does not rise.",
        },
    )
    intent = DST / "working" / "source" / "REVISE_INTENT.md"
    intent.parent.mkdir(parents=True, exist_ok=True)
    intent.write_text(
        """# Scene REVISE → revision propagation

New job. Lights-out execution is already proven and frozen. Do not polish that job.

**Capability:** scene-level REVISE is not a terminal stop. Prime names affected cuts. OM executes only those cuts, composes `scene_v2` with a new hash and `parent_scene_hash`, and returns to scene-level review.

Real feedback copied from `vid-lights-out-scene-v1`:

- after ~10s, two stills look bad
- pot smoke does not rise

Expected:

```text
affected = S3, S4
unchanged = S1, S2
```

Do **not** redispatch S2 H3. V1 is immutable. Proof is propagation, not art.
""",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "job_id": JOB_ID, "parent_scene_hash": PARENT_HASH}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
