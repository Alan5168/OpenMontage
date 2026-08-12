#!/usr/bin/env python3
"""Review Packet Builder - 构建 review_packet 目录结构。

在 C:\\ContentStudio\\jobs\\<project_id>\\working\\ 下创建:
  review_packet/
    manifest.json          - 项目元数据 + cuts + images 列表
    VISUAL_QA.schema.json  - 统一 VISUAL_QA schema 定义
    images/                - 关键帧副本
    contact_sheet.jpg      - 帧编号标注占位图

用法:
  python review_packet_builder.py --project-id <id>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
VISUAL_QA_SCHEMA_VERSION = "content-studio-visual-qa/v1"
REVIEW_PACKET_SCHEMA_VERSION = "content-studio-review-packet/v1"
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
CONTACT_SHEET_COLS = 4  # contact_sheet 每行列数
CONTACT_SHEET_THUMB_W = 320  # 缩略图宽度
CONTACT_SHEET_THUMB_H = 240  # 缩略图高度


class PacketError(RuntimeError):
    """Review packet 构建错误。"""


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    """UTC ISO8601 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    """安全读取 JSON 文件。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"无法读取 JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PacketError(f"JSON 不是对象: {path}")
    return data


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """原子写入 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def _job_dir(project_id: str) -> Path:
    """获取项目目录。"""
    return JOBS_DIR / project_id


def _load_scene_plan(project_dir: Path) -> dict[str, Any]:
    """加载 scene_plan.json。"""
    artifact_path = project_dir / "artifacts" / "scene_plan.json"
    if not artifact_path.is_file():
        raise PacketError(f"scene_plan.json 不存在: {artifact_path}")
    return _read_json(artifact_path)


# ---------------------------------------------------------------------------
# VISUAL_QA schema 构建
# ---------------------------------------------------------------------------
def build_visual_qa_schema(project_id: str) -> dict[str, Any]:
    """构建 VISUAL_QA.schema.json 统一定义。"""
    return {
        "schema_version": VISUAL_QA_SCHEMA_VERSION,
        "description": "统一视觉质量评估 schema，用于 review_packet 中的关键帧检查",
        "project_id": project_id,
        "fields": {
            "image_id": {
                "type": "string",
                "description": "图片唯一标识，对应 cut_id 或帧编号",
            },
            "path": {
                "type": "string",
                "description": "相对于 review_packet/ 的图片路径",
            },
            "continuity": {
                "type": "enum",
                "values": ["PASS", "FAIL", "WARNING"],
                "description": "视觉连续性评估",
            },
            "continuity_notes": {
                "type": "string",
                "description": "连续性中文说明",
            },
            "style_match": {
                "type": "enum",
                "values": ["PASS", "FAIL", "WARNING"],
                "description": "风格匹配评估",
            },
            "style_notes": {
                "type": "string",
                "description": "风格中文说明",
            },
            "composition": {
                "type": "enum",
                "values": ["PASS", "FAIL", "WARNING"],
                "description": "构图评估",
            },
            "composition_notes": {
                "type": "string",
                "description": "构图中中文说明",
            },
            "overall": {
                "type": "enum",
                "values": ["PASS", "FAIL", "WARNING"],
                "description": "总体评估",
            },
            "action_required": {
                "type": "enum",
                "values": ["keep", "regenerate", "merge", "omit"],
                "description": "建议操作",
            },
        },
        "summary_fields": {
            "total": {"type": "integer", "description": "总图片数"},
            "pass": {"type": "integer", "description": "通过数"},
            "fail": {"type": "integer", "description": "失败数"},
            "warning": {"type": "integer", "description": "警告数"},
            "awaiting_human": {"type": "boolean", "description": "是否等待人工确认"},
        },
        "created_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# 关键帧收集与复制
# ---------------------------------------------------------------------------
def _collect_keyframes(
    project_dir: Path,
    scene_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    """从 scene_plan 中收集关键帧信息。

    返回每帧的 cut_id、源路径、目标文件名。
    """
    frames: list[dict[str, Any]] = []
    scenes = scene_plan.get("scenes", [])
    for scene in scenes:
        cut_id = scene.get("id", "")
        visual_ref = scene.get("visual_ref") or {}
        ref_path = visual_ref.get("path", "")
        if not ref_path:
            # 如果没有 visual_ref，尝试 reuse 链
            continue
        # 解析源路径（可能是相对 project_dir 的路径）
        source = project_dir / ref_path
        if not source.is_file():
            # 尝试 assets/images/ 下的同名文件
            source = project_dir / "assets" / "images" / Path(ref_path).name
        ext = Path(ref_path).suffix or ".png"
        target_name = f"{cut_id}{ext}"
        frames.append({
            "cut_id": cut_id,
            "source_path": source,
            "target_name": target_name,
            "original_ref": ref_path,
            "visual_intent": scene.get("visual_intent", ""),
        })
    return frames


def _copy_keyframes(
    frames: list[dict[str, Any]],
    images_dir: Path,
) -> list[dict[str, Any]]:
    """复制关键帧到 images/ 目录，返回 manifest images 条目。"""
    images_dir.mkdir(parents=True, exist_ok=True)
    images_manifest: list[dict[str, Any]] = []
    for frame in frames:
        source = frame["source_path"]
        target = images_dir / frame["target_name"]
        if source.is_file():
            shutil.copy2(source, target)
            sha256 = _sha256_file(target)
        else:
            # 源文件不存在，创建占位文件
            target.write_bytes(b"")
            sha256 = ""
        images_manifest.append({
            "image_id": frame["cut_id"],
            "filename": frame["target_name"],
            "path": f"images/{frame['target_name']}",
            "source_ref": frame["original_ref"],
            "sha256": sha256,
            "exists": source.is_file(),
            "visual_intent": frame["visual_intent"],
        })
    return images_manifest


def _build_cuts_manifest(scene_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """从 scene_plan 构建 cuts 列表。"""
    cuts = []
    for scene in scene_plan.get("scenes", []):
        visual_ref = scene.get("visual_ref") or {}
        reuse = scene.get("reuse") or {}
        duration = round(
            float(scene.get("end_seconds", 0)) - float(scene.get("start_seconds", 0)), 3
        )
        cuts.append({
            "cut_id": scene.get("id", ""),
            "scene_number": scene.get("script_section_id", ""),
            "visual_intent": scene.get("visual_intent", ""),
            "dialogue": scene.get("dialogue", ""),
            "duration_seconds": duration,
            "visual_ref_kind": visual_ref.get("kind", ""),
            "visual_ref_path": visual_ref.get("path", ""),
            "reuse_source": reuse.get("source_cut_id", ""),
            "review_decision": scene.get("review_decision", "pending"),
        })
    return cuts


# ---------------------------------------------------------------------------
# Contact sheet 生成
# ---------------------------------------------------------------------------
def _generate_contact_sheet(
    images_dir: Path,
    output_path: Path,
    frames: list[dict[str, Any]],
) -> None:
    """生成 contact_sheet.jpg 占位图，标注每帧编号。

    使用 PIL 绘制网格，每格标注 cut_id。
    如果 PIL 不可用，回退到最小 JPEG 占位。
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # PIL 不可用，创建最小 JPEG 占位
        output_path.write_bytes(b"\xff\xd8\xff\xd9")
        return

    # 收集实际存在的图片
    thumbnails: list[tuple[str, Path | None]] = []
    for frame in frames:
        target = images_dir / frame["target_name"]
        if target.is_file() and target.stat().st_size > 0:
            thumbnails.append((frame["cut_id"], target))
        else:
            thumbnails.append((frame["cut_id"], None))

    if not thumbnails:
        # 无帧时生成空白占位
        thumbnails = [("empty", None)]

    cols = CONTACT_SHEET_COLS
    rows = (len(thumbnails) + cols - 1) // cols
    sheet_w = cols * CONTACT_SHEET_THUMB_W
    sheet_h = rows * CONTACT_SHEET_THUMB_H
    # 浅灰背景
    sheet = Image.new("RGB", (sheet_w, sheet_h), color=(240, 240, 240))
    draw = ImageDraw.Draw(sheet)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for idx, (cut_id, img_path) in enumerate(thumbnails):
        col = idx % cols
        row = idx // cols
        x = col * CONTACT_SHEET_THUMB_W
        y = row * CONTACT_SHEET_THUMB_H
        # 绘制边框
        draw.rectangle(
            [x, y, x + CONTACT_SHEET_THUMB_W, y + CONTACT_SHEET_THUMB_H],
            outline=(180, 180, 180),
            width=2,
        )
        if img_path is not None:
            try:
                thumb = Image.open(img_path)
                thumb.thumbnail((CONTACT_SHEET_THUMB_W - 20, CONTACT_SHEET_THUMB_H - 40))
                # 居中粘贴
                offset_x = x + (CONTACT_SHEET_THUMB_W - thumb.width) // 2
                offset_y = y + 10
                sheet.paste(thumb, (offset_x, offset_y))
            except Exception:
                draw.text(
                    (x + 10, y + 60),
                    "[decode error]",
                    fill=(200, 0, 0),
                    font=font,
                )
        else:
            draw.text(
                (x + 60, y + 80),
                "[missing]",
                fill=(200, 0, 0),
                font=font,
            )
        # 标注帧编号
        label = f"#{idx + 1} {cut_id}"
        draw.text((x + 10, y + CONTACT_SHEET_THUMB_H - 30), label, fill=(0, 0, 0), font=font)

    sheet.save(str(output_path), "JPEG", quality=85)


# ---------------------------------------------------------------------------
# 主命令
# ---------------------------------------------------------------------------
def build_review_packet(project_id: str) -> dict[str, Any]:
    """构建 review_packet 目录结构。

    生成 manifest.json、VISUAL_QA.schema.json、images/、contact_sheet.jpg。
    """
    project_dir = _job_dir(project_id)
    if not project_dir.is_dir():
        raise PacketError(f"项目目录不存在: {project_dir}")

    packet_dir = project_dir / "working" / "review_packet"
    images_dir = packet_dir / "images"

    # 创建目录
    packet_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # 加载 scene_plan
    scene_plan = _load_scene_plan(project_dir)

    # 收集并复制关键帧
    frames = _collect_keyframes(project_dir, scene_plan)
    images_manifest = _copy_keyframes(frames, images_dir)

    # 构建 cuts 列表
    cuts_manifest = _build_cuts_manifest(scene_plan)

    # 生成 VISUAL_QA.schema.json
    qa_schema = build_visual_qa_schema(project_id)
    qa_path = packet_dir / "VISUAL_QA.schema.json"
    _atomic_write_json(qa_path, qa_schema)

    # 生成 contact_sheet.jpg
    contact_sheet_path = packet_dir / "contact_sheet.jpg"
    _generate_contact_sheet(images_dir, contact_sheet_path, frames)

    # 生成 manifest.json
    manifest = {
        "schema_version": REVIEW_PACKET_SCHEMA_VERSION,
        "project_id": project_id,
        "created_at": _utc_now(),
        "visual_qa_schema_version": VISUAL_QA_SCHEMA_VERSION,
        "cuts": cuts_manifest,
        "images": images_manifest,
        "contact_sheet": {
            "path": "contact_sheet.jpg",
            "sha256": _sha256_file(contact_sheet_path) if contact_sheet_path.is_file() else "",
            "type": "annotated_grid",
        },
        "visual_qa_schema_path": "VISUAL_QA.schema.json",
    }
    manifest_path = packet_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)

    # 构建 receipt
    receipt = {
        "status": "BUILT",
        "project_id": project_id,
        "packet_dir": str(packet_dir),
        "files": {
            "manifest": str(manifest_path),
            "visual_qa_schema": str(qa_path),
            "contact_sheet": str(contact_sheet_path),
            "images_dir": str(images_dir),
        },
        "summary": {
            "cut_count": len(cuts_manifest),
            "image_count": len(images_manifest),
            "images_found": sum(1 for img in images_manifest if img["exists"]),
            "images_missing": sum(1 for img in images_manifest if not img["exists"]),
        },
        "manifest_sha256": _sha256_file(manifest_path),
        "built_at": _utc_now(),
    }
    return receipt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review Packet Builder - 构建 review_packet 目录结构"
    )
    parser.add_argument("--project-id", required=True, help="OM project ID")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        receipt = build_review_packet(args.project_id)
    except (PacketError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
