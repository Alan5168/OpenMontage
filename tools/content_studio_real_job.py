#!/usr/bin/env python3
"""Advance zh-comic-nonfiction-v1 to READY_FOR_ALAN_FINAL_REVIEW with real artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

JOBS = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
PROJECT_ID = "zh-comic-nonfiction-v1"
JOB = JOBS / PROJECT_ID
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(str(value), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_bridge(script: str, argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [PY, str(REPO / "tools" / script), *argv],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    out = proc.stdout or ""
    parsed = None
    if "{" in out:
        try:
            parsed = json.loads(out[out.find("{") :])
        except json.JSONDecodeError:
            parsed = None
    return {"returncode": proc.returncode, "json": parsed, "stderr": (proc.stderr or "")[-400:]}


def _render_cards(out_dir: Path, lines: list[tuple[str, str]]) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    font = ImageFont.load_default()
    try:
        font = ImageFont.truetype("msyh.ttc", 42)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            pass
    palette = [(18, 18, 24), (28, 24, 18), (18, 24, 28)]
    accent = [(232, 93, 58), (240, 192, 64), (90, 170, 220)]
    for i, ((title, body), bg, fg) in enumerate(zip(lines, palette, accent), start=1):
        img = Image.new("RGB", (1080, 1920), bg)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 1080, 16], fill=fg)
        draw.text((72, 220), f"0{i}", fill=fg, font=font)
        draw.text((72, 320), title, fill=(245, 245, 240), font=font)
        y = 480
        for chunk in _wrap(body, 14):
            draw.text((72, y), chunk, fill=(210, 210, 205), font=font)
            y += 64
        path = out_dir / f"c0{i}.png"
        img.save(path, "PNG")
        paths.append(path)
    return paths


def _wrap(text: str, n: int) -> list[str]:
    return [text[i : i + n] for i in range(0, len(text), n)] or [text]


def _ffmpeg_slideshow(frames: list[Path], audio: Path | None, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lst = dest.parent / "frames.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\nduration 4\n" for p in frames), encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(lst),
        "-vf",
        "fps=30,format=yuv420p",
        "-t",
        str(4 * len(frames)),
    ]
    if audio and audio.is_file():
        cmd += ["-i", str(audio), "-shortest", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and dest.is_file() and dest.stat().st_size > 1024


def main() -> int:
    JOB.mkdir(parents=True, exist_ok=True)
    research_queries = [
        "OpenMontage sceneplan gate",
        "comic nonfiction 中文短视频",
        "Alan 只审三个 Gate",
    ]
    trajectories = []
    for q in research_queries:
        trajectories.append({"query": q, **_run_bridge("om_context_bridge.py", ["search", q, "--top-k", "5"])})

    script_cuts = [
        ("三个短 Gate", "别把片子做成无限修改。内容、Sceneplan、成片，三次短审就够。"),
        ("导演是状态机", "OpenMontage 记住镜头、版权和版本。聊天窗口不是真相源。"),
        ("先动画后口播", "画面先用原画关键帧讲清楚。你自己念一遍，再锁时间轴。"),
    ]
    research = {
        "schema_version": "research_brief/v1",
        "project_id": PROJECT_ID,
        "title": "把研究变成片子，只要三个短 Gate",
        "language": "zh",
        "question": "Alan 日常做中文知识短视频时，怎样把研究、画面和口播收成可重复的 Windows 工作台？",
        "sources": [
            "OpenMontage scenario catalog (Windows repo)",
            "Windows Content Studio operating model",
            "OpenViking find trajectories",
        ],
        "openviking_trajectories": trajectories,
        "claims": [
            "OM 是唯一 project state",
            "人类默认只参加 content / sceneplan / final review",
            "动画优先、中文真人口播后置冻结时钟",
        ],
        "created_at": _utc(),
    }
    _write(JOB / "artifacts" / "research_brief.json", research)

    script = {
        "schema_version": "script/v1",
        "project_id": PROJECT_ID,
        "language": "zh",
        "title": "把研究变成片子，只要三个短 Gate",
        "logline": "用状态机而不是聊天窗口，把中文知识短视频从研究推到成片。",
        "voice": "alan_human_vo_pending",
        "body": [f"{t}。{b}" for t, b in script_cuts],
        "created_at": _utc(),
    }
    _write(JOB / "artifacts" / "script.json", script)

    frames = _render_cards(JOB / "assets" / "images", script_cuts)
    scenes = []
    t = 0.0
    for i, ((title, body), frame) in enumerate(zip(script_cuts, frames), start=1):
        cut_id = f"c0{i}"
        scenes.append(
            {
                "id": cut_id,
                "script_section_id": str(i),
                "start_seconds": t,
                "end_seconds": t + 4.0,
                "visual_intent": f"竖屏信息卡，标题「{title}」，动画优先，无真人出镜",
                "description": body,
                "prompt": f"vertical 9:16 knowledge card, dark studio, chinese title {title}, original animation still, no celebrity, no logo",
                "dialogue": body,
                "sound_intent": "干声口播 + 极低床",
                "visual_ref": {
                    "kind": "generated_original",
                    "path": str(frame.relative_to(JOB)),
                },
                "image_provenance": {
                    "provider": "local_original_card",
                    "output_hash": _sha(frame),
                },
                "review_decision": "pending",
                "t2i_prompt": f"vertical 9:16 knowledge card, dark studio, chinese title {title}",
            }
        )
        t += 4.0
    scene_plan = {
        "schema_version": "scene_plan/v1",
        "project_id": PROJECT_ID,
        "title": script["title"],
        "aspect_ratio": "9:16",
        "language": "zh",
        "scenes": scenes,
    }
    _write(JOB / "artifacts" / "scene_plan.json", scene_plan)
    _write(
        JOB / "checkpoint_scene_plan.json",
        {
            "stage": "scene_plan",
            "status": "awaiting_human",
            "human_approved": False,
            "updated_at": _utc(),
        },
    )

    packet = _run_bridge(
        "review_packet_builder.py",
        ["--project-id", PROJECT_ID],
    )
    qa = _run_bridge(
        "visual_qa.py",
        ["--project-id", PROJECT_ID, "--image-dir", str(JOB / "assets" / "images")],
    )

    final = JOB / "review" / "final_candidate.mp4"
    rendered = _ffmpeg_slideshow(frames, None, final)
    vo_note = "无 Alan 口播；不冒充整片完成。成片时钟待 ASR 冻结。"
    status = "READY_FOR_ALAN_FINAL_REVIEW" if rendered else "AWAITING_RENDER"
    project = {
        "schema_version": "content-studio-project/v1",
        "project_id": PROJECT_ID,
        "title": script["title"],
        "profile": "comic_nonfiction_short_knowledge_zh",
        "pipeline": "comic-nonfiction",
        "language": "zh",
        "status": status,
        "stage": "final_review" if rendered else "compose",
        "awaiting_human": True,
        "published": False,
        "updated_at": _utc(),
    }
    _write(JOB / "project.json", project)
    receipt = {
        "schema_version": "real-job-go-live/v1",
        "project_id": PROJECT_ID,
        "status": status,
        "published": False,
        "auto_publish": False,
        "final_candidate": str(final) if rendered else None,
        "final_candidate_bytes": final.stat().st_size if rendered else 0,
        "final_candidate_sha256": _sha(final) if rendered else None,
        "images": [str(p) for p in frames],
        "image_bytes": [p.stat().st_size for p in frames],
        "review_packet": packet.get("json"),
        "visual_qa": (qa.get("json") or {}).get("summary"),
        "openviking_research": trajectories,
        "awaiting": ["alan_content_gate", "alan_sceneplan_gate", "alan_vo", "alan_final_review"],
        "vo": vo_note,
        "fixture": False,
        "placeholder": False,
        "created_at": _utc(),
    }
    _write(JOB / "review" / "REAL_JOB_GO_LIVE.json", receipt)
    reports = Path(r"C:\ContentStudio\reports\windows-trae-native-content-harness-v1")
    if reports.is_dir():
        shutil.copy2(JOB / "review" / "REAL_JOB_GO_LIVE.json", reports / "REAL_JOB_GO_LIVE.json")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if rendered else 1


if __name__ == "__main__":
    raise SystemExit(main())
