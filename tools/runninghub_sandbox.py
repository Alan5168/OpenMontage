"""Sandbox: pack a shot, quote RunningHub, optionally submit.

Does not call dispatch_cut / produce_keyframe / compose_scene.
Does not touch Xiaoyunque or LibTV APIs.
Submit spends coins — default is quote_only.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from lib.h3_turbo_quality import MCU_STILL_SRC
from lib.runninghub_adapter import (
    RunningHubError,
    compile_runninghub,
    quote_runninghub,
    run_lifecycle,
    write_observation,
    write_receipt,
    write_review_queue,
)
from lib.shot_render_package import frame_ref, pack_shot, write_package

JOBS = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
JOB_DIR = JOBS / "h3-capability-sandbox-v1"
OUT = JOB_DIR / "working" / "runninghub"
RH001_OUT = JOBS / "rh-001-provider-lifecycle-v1" / "working" / "runninghub"
RH001_REVIEW = JOBS / "rh-001-provider-lifecycle-v1" / "working" / "review_queue"


def _picture1() -> Path:
    copied = JOB_DIR / "working" / "turbo_quality" / "picture1_a2_mcu.png"
    if copied.is_file():
        return copied
    return MCU_STILL_SRC


def build_sandbox_package() -> dict:
    picture = _picture1()
    first = frame_ref(kind="DIRECTED_MCU_COPY", path=picture)
    return pack_shot(
        project_id="h3-capability-sandbox-v1",
        scene_id="sandbox_a2",
        shot_id="sandbox_a2_mcu",
        shot_intent=(
            "Kitchen MCU. The figure in the black hoodie holds the blue lunchbox. "
            "Steam at the lid. One shallow breath. No smile. No walk."
        ),
        duration_s=5.0,
        aspect_ratio="16:9",
        motion_obligation="PERFORMANCE",
        first_frame=first,
        render_policy={
            "stage": "DRAFT",
            "preferred_target": "local_h3",
            "fallback_targets": ["runninghub"],
            "target_resolution": "720p-ish",
            "profile": "rh_h3_fl2va_final_v1",
        },
        acceptance={
            "identity": "same face and hoodie as Picture 1",
            "composition": "MCU, lunchbox readable",
            "motion": "hold + one breath; lid stays closed; no grin",
            "continuity": "steam may drift; no walk",
        },
        shot_size="MCU",
        temporal_beats=[
            {"t": "0.0-1.0", "actor": "figure", "action": "hold, gaze off-axis"},
            {"t": "1.0-5.0", "actor": "figure", "action": "one shallow breath; no smile"},
        ],
        audio={"dialogue": [], "sfx": ["quiet kitchen room tone"], "music_intent": None},
        provider_prompt={
            "neutral_prompt": (
                "Limited TV anime. Kitchen MCU from the first frame. "
                "Black hoodie, blue lunchbox, steam at the lid. Locked-off. "
                "One breath. No smile. No walk. Lid closed."
            ),
            "negative_constraints": ["smile", "grin", "walk", "open lid", "push-in"],
        },
    )


def run_package() -> dict:
    package = build_sandbox_package()
    path = write_package(package, OUT / "SHOT_RENDER_PACKAGE.json")
    compiled = compile_runninghub(package)
    quote = quote_runninghub(package)
    receipt = write_receipt(
        dest=OUT / "RECEIPT.json",
        package=package,
        profile_id="rh_h3_fl2va_final_v1",
        status="QUOTED_AWAITING_SUBMIT",
    )
    observation = write_observation(
        OUT / "OBSERVATION.json",
        status="PACKAGE_READY",
        receipt_path=OUT / "RECEIPT.json",
        note=(
            "Package + quote only. Not OUTPUT_RECEIVED. Not FIRST_TAKE_ACCEPTABLE. "
            "Submit needs RUNNINGHUB_API_KEY + workflow_id + --submit."
        ),
    )
    review = write_review_queue(
        JOB_DIR / "working" / "review_queue" / "sandbox_a2_mcu.json",
        shot_id="sandbox_a2_mcu",
        receipt_status="QUOTED_AWAITING_SUBMIT",
    )
    return {
        "package_path": str(path),
        "package_sha256": package.get("package_sha256"),
        "first_frame_kind": package["frames"]["first_frame"]["kind"],
        "legal_9x16_shot_keyframe": False,
        "compiled": compiled,
        "quote": quote,
        "receipt": receipt,
        "observation": observation,
        "review_queue": review,
        "submit": False,
        "dispatch_cut": False,
    }


def run_rh001(*, submit: bool) -> dict:
    package = build_sandbox_package()
    write_package(package, RH001_OUT / "SHOT_RENDER_PACKAGE.json")
    compiled = compile_runninghub(package)
    try:
        result = run_lifecycle(
            package,
            dest_dir=RH001_OUT,
            confirm=submit,
            submit=submit,
        )
    except RunningHubError as exc:
        write_receipt(
            dest=RH001_OUT / "RECEIPT.json",
            package=package,
            profile_id="rh_h3_fl2va_final_v1",
            status="SUBMIT_BLOCKED",
            error=str(exc),
        )
        write_observation(
            RH001_OUT / "OBSERVATION.json",
            status="SUBMIT_BLOCKED",
            receipt_path=RH001_OUT / "RECEIPT.json",
            note=str(exc),
        )
        return {
            "ok": False,
            "error": str(exc),
            "blockers": compiled.get("blockers"),
            "submit": False,
            "dispatch_cut": False,
        }
    status = result["receipt"]["status"]
    review = write_review_queue(
        RH001_REVIEW / "sandbox_a2_mcu.json",
        shot_id="sandbox_a2_mcu",
        receipt_status=status,
    )
    result["package_sha256"] = package.get("package_sha256")
    result["compiled"] = compiled
    result["review_queue"] = review
    result["dispatch_cut"] = False
    result["om_pass"] = False
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["package", "quote", "lifecycle"])
    parser.add_argument(
        "--submit",
        action="store_true",
        help="RH-001 only on lifecycle. Refused until workflow_id + nodeIds + key.",
    )
    args = parser.parse_args(argv)
    if args.command in {"package", "quote"}:
        if args.submit:
            print(json.dumps({"ok": False, "error": "use: python tools/runninghub_sandbox.py lifecycle --submit"}, indent=2))
            return 2
        payload = run_package()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    payload = run_rh001(submit=args.submit)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
