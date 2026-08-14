#!/usr/bin/env python3
"""VISUAL_QA 评估模块 - 使用 PIL/Pillow 实际读取图片并分析。

对 review_packet/images/ 下的关键帧执行:
  - continuity:  连续性检查（色调/亮度一致性，帧间差异）
  - style_match: 风格匹配（饱和度/色温一致性）
  - composition: 构图评估（宽高比、亮度分布、三分法启发式）

支持 A/B 对比模式（--baseline-image）。

用法:
  python visual_qa.py --project-id <id> --image-dir <path>
  python visual_qa.py --project-id <id> --image-dir <path> --baseline-image <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
JOBS_DIR = Path(os.environ.get("OPENMONTAGE_PROJECTS_DIR", r"C:\ContentStudio\jobs"))
VISUAL_QA_SCHEMA_VERSION = "content-studio-visual-qa/v1"
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# 连续性色调差异阈值（平均 RGB 差值）
CONTINUITY_HUE_THRESHOLD = 40.0
CONTINUITY_WARN_THRESHOLD = 20.0
# 饱和度一致性阈值
STYLE_SAT_THRESHOLD = 0.15
# 标准宽高比列表
STANDARD_ASPECT_RATIOS = [16 / 9, 4 / 3, 1.0, 9 / 16, 3 / 4]
ASPECT_TOLERANCE = 0.05
# 亮度分布阈值（用于构图评估）
BRIGHTNESS_BALANCE_THRESHOLD = 0.35


class QAError(RuntimeError):
    """VISUAL_QA 评估错误。"""


# ---------------------------------------------------------------------------
# 通用辅助函数
# ---------------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _ensure_pil() -> Any:
    """确保 PIL 可用，返回 PIL 模块。"""
    try:
        from PIL import Image, ImageStat
        return Image, ImageStat
    except ImportError:
        raise QAError(
            "PIL/Pillow 未安装。请运行: pip install Pillow"
        )


# ---------------------------------------------------------------------------
# 图片分析核心
# ---------------------------------------------------------------------------
def _load_image(path: Path) -> tuple[Any, Any]:
    """加载图片，返回 (Image, ImageStat)。"""
    Image, ImageStat = _ensure_pil()
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        stat = ImageStat.Stat(img)
        return img, stat
    except Exception as exc:
        raise QAError(f"无法读取图片 {path}: {exc}") from exc


def _avg_rgb(stat: Any) -> tuple[float, float, float]:
    """获取平均 RGB 值。"""
    means = stat.mean  # [R, G, B] 列表
    return (means[0], means[1], means[2])


def _avg_brightness(stat: Any) -> float:
    """获取平均亮度（0-255）。"""
    return sum(stat.mean) / len(stat.mean)


def _saturation(stat: Any) -> float:
    """计算平均饱和度（0-1）。"""
    r, g, b = _avg_rgb(stat)
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    if max_val == 0:
        return 0.0
    return (max_val - min_val) / max_val


def _color_temperature(stat: Any) -> float:
    """估算色温偏移（正值偏暖，负值偏冷）。"""
    r, g, b = _avg_rgb(stat)
    return (r - b) / 255.0


def _rgb_distance(c1: tuple, c2: tuple) -> float:
    """计算两组 RGB 平均值的欧氏距离。"""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def _aspect_ratio(img: Any) -> float:
    """获取宽高比。"""
    w, h = img.size
    if h == 0:
        return 0.0
    return w / h


def _brightness_distribution(img: Any) -> dict[str, float]:
    """分析亮度分布，返回四象限平均亮度。

    用于三分法/构图启发式评估。
    """
    Image, ImageStat = _ensure_pil()
    w, h = img.size
    # 切分为 2x2 四象限
    regions = {
        "top_left": (0, 0, w // 2, h // 2),
        "top_right": (w // 2, 0, w, h // 2),
        "bottom_left": (0, h // 2, w // 2, h),
        "bottom_right": (w // 2, h // 2, w, h),
    }
    result = {}
    for name, box in regions.items():
        crop = img.crop(box)
        stat = ImageStat.Stat(crop)
        result[name] = _avg_brightness(stat)
    return result


# ---------------------------------------------------------------------------
# 评估函数
# ---------------------------------------------------------------------------
def evaluate_continuity(
    stat: Any,
    prev_stat: Any | None,
    baseline_stat: Any | None,
) -> tuple[str, str]:
    """评估连续性：对比前一帧或 baseline 的色调/亮度。

    返回 (verdict, notes)。
    """
    if prev_stat is None and baseline_stat is None:
        return "PASS", "首帧或无对比基准，连续性默认通过"

    ref_stat = baseline_stat if baseline_stat is not None else prev_stat
    ref_label = "baseline" if baseline_stat is not None else "前一帧"

    curr_rgb = _avg_rgb(stat)
    ref_rgb = _avg_rgb(ref_stat)
    distance = _rgb_distance(curr_rgb, ref_rgb)
    curr_bright = _avg_brightness(stat)
    ref_bright = _avg_brightness(ref_stat)
    bright_diff = abs(curr_bright - ref_bright)

    if distance > CONTINUITY_HUE_THRESHOLD or bright_diff > 60:
        return (
            "FAIL",
            f"与{ref_label}色调差异过大：RGB距离={distance:.1f}，亮度差={bright_diff:.1f}",
        )
    if distance > CONTINUITY_WARN_THRESHOLD or bright_diff > 30:
        return (
            "WARNING",
            f"与{ref_label}色调略有偏差：RGB距离={distance:.1f}，亮度差={bright_diff:.1f}",
        )
    return (
        "PASS",
        f"与{ref_label}色调一致：RGB距离={distance:.1f}，亮度差={bright_diff:.1f}",
    )


def evaluate_style_match(stat: Any, baseline_stat: Any | None) -> tuple[str, str]:
    """评估风格匹配：饱和度和色温一致性。

    返回 (verdict, notes)。
    """
    sat = _saturation(stat)
    temp = _color_temperature(stat)

    if baseline_stat is not None:
        base_sat = _saturation(baseline_stat)
        base_temp = _color_temperature(baseline_stat)
        sat_diff = abs(sat - base_sat)
        temp_diff = abs(temp - base_temp)
        if sat_diff > STYLE_SAT_THRESHOLD * 2 or temp_diff > 0.2:
            return (
                "FAIL",
                f"与baseline风格差异大：饱和度差={sat_diff:.3f}，色温差={temp_diff:.3f}",
            )
        if sat_diff > STYLE_SAT_THRESHOLD or temp_diff > 0.1:
            return (
                "WARNING",
                f"与baseline风格略有偏差：饱和度差={sat_diff:.3f}，色温差={temp_diff:.3f}",
            )
        return "PASS", f"与baseline风格一致：饱和度={sat:.3f}，色温偏移={temp:.3f}"

    # 无 baseline 时，检查绝对值是否在合理范围
    if sat < 0.02:
        return "WARNING", f"饱和度过低({sat:.3f})，画面可能偏灰"
    if sat > 0.8:
        return "WARNING", f"饱和度过高({sat:.3f})，色彩可能过浓"
    return "PASS", f"饱和度正常({sat:.3f})，色温偏移={temp:.3f}"


def evaluate_composition(img: Any, stat: Any) -> tuple[str, str]:
    """评估构图：宽高比 + 亮度分布平衡性。

    返回 (verdict, notes)。
    """
    # 宽高比检查
    ar = _aspect_ratio(img)
    ar_match = any(abs(ar - std) < ASPECT_TOLERANCE for std in STANDARD_ASPECT_RATIOS)

    # 亮度分布检查
    dist = _brightness_distribution(img)
    values = list(dist.values())
    bright_range = max(values) - min(values)
    balanced = bright_range < 128 * (1 - BRIGHTNESS_BALANCE_THRESHOLD)

    issues = []
    if not ar_match:
        issues.append(f"非标准宽高比({ar:.2f})")
    if not balanced:
        issues.append(f"亮度分布不均(极差={bright_range:.1f})")

    if not ar_match and not balanced:
        return "FAIL", "；".join(issues)
    if issues:
        return "WARNING", "；".join(issues)
    return "PASS", f"宽高比={ar:.2f}，亮度分布均衡"


def _compute_overall(
    continuity: str, style_match: str, composition: str
) -> str:
    """综合三项评估得出总体结果。FAIL 优先于 WARNING 优先于 PASS。"""
    verdicts = [continuity, style_match, composition]
    if "FAIL" in verdicts:
        return "FAIL"
    if "WARNING" in verdicts:
        return "WARNING"
    return "PASS"


def _suggest_action(overall: str, continuity: str) -> str:
    """根据评估结果建议操作。"""
    if overall == "FAIL":
        if continuity == "FAIL":
            return "regenerate"
        return "regenerate"
    if overall == "WARNING":
        return "keep"
    return "keep"


# ---------------------------------------------------------------------------
# 主评估流程
# ---------------------------------------------------------------------------
def run_visual_qa(
    project_id: str,
    image_dir: Path,
    baseline_image: Path | None = None,
) -> dict[str, Any]:
    """执行 VISUAL_QA 评估。

    读取 image_dir 下所有图片，分析 continuity/style/composition，
    输出 VISUAL_QA.json。
    """
    if not image_dir.is_dir():
        return _fail_receipt(project_id, f"图片目录不存在: {image_dir}")

    # 收集图片文件
    image_files = sorted(
        [f for f in image_dir.iterdir() if f.suffix.lower() in SUPPORTED_IMAGE_EXTS],
        key=lambda f: f.name,
    )
    if not image_files:
        return _fail_receipt(project_id, f"图片目录中无支持的图片文件: {image_dir}")

    # 加载 baseline 图片（如果提供）
    baseline_stat = None
    if baseline_image is not None:
        if not baseline_image.is_file():
            return _fail_receipt(project_id, f"baseline 图片不存在: {baseline_image}")
        _, baseline_stat = _load_image(baseline_image)

    # 逐帧评估
    images_result: list[dict[str, Any]] = []
    prev_stat = None
    for img_path in image_files:
        if img_path.stat().st_size <= 16 or img_path.read_bytes()[:4] == b"\xff\xd8\xff\xd9":
            images_result.append({
                "image_id": img_path.stem,
                "path": str(img_path),
                "image_hash": "",
                "actually_viewed": False,
                "bytes": img_path.stat().st_size,
                "continuity": "FAIL",
                "legibility": "FAIL",
                "composition": "FAIL",
                "style_match": "FAIL",
                "defects": ["placeholder_or_tiny_file"],
                "confidence": 1.0,
                "human_review_required": True,
                "continuity_notes": f"文件过小 ({img_path.stat().st_size} bytes)，拒绝占位图",
                "style_notes": "placeholder",
                "composition_notes": "placeholder",
                "overall": "FAIL",
                "action_required": "regenerate",
            })
            continue
        try:
            img, stat = _load_image(img_path)
        except QAError as exc:
            # 图片无法读取，标记 FAIL
            images_result.append({
                "image_id": img_path.stem,
                "path": str(img_path),
                "continuity": "FAIL",
                "continuity_notes": f"图片读取失败: {exc}",
                "style_match": "FAIL",
                "style_notes": "图片读取失败，无法评估风格",
                "composition": "FAIL",
                "composition_notes": "图片读取失败，无法评估构图",
                "overall": "FAIL",
                "action_required": "regenerate",
            })
            continue

        cont_verdict, cont_notes = evaluate_continuity(stat, prev_stat, baseline_stat)
        style_verdict, style_notes = evaluate_style_match(stat, baseline_stat)
        comp_verdict, comp_notes = evaluate_composition(img, stat)
        overall = _compute_overall(cont_verdict, style_verdict, comp_verdict)
        action = _suggest_action(overall, cont_verdict)

        images_result.append({
            "image_id": img_path.stem,
            "path": str(img_path),
            "image_hash": hashlib.sha256(img_path.read_bytes()).hexdigest(),
            "actually_viewed": True,
            "bytes": img_path.stat().st_size,
            "width": img.size[0],
            "height": img.size[1],
            "continuity": cont_verdict,
            "legibility": "UNCERTAIN",
            "composition": comp_verdict,
            "style_match": style_verdict,
            "defects": [] if overall == "PASS" else [cont_notes, style_notes, comp_notes],
            "confidence": 0.55,
            "human_review_required": True,
            "continuity_notes": cont_notes,
            "style_notes": style_notes,
            "composition_notes": comp_notes,
            "overall": overall,
            "action_required": action,
        })
        prev_stat = stat

    # 统计汇总
    total = len(images_result)
    pass_count = sum(1 for r in images_result if r["overall"] == "PASS")
    fail_count = sum(1 for r in images_result if r["overall"] == "FAIL")
    warning_count = sum(1 for r in images_result if r["overall"] == "WARNING")

    result = {
        "schema_version": VISUAL_QA_SCHEMA_VERSION,
        "project_id": project_id,
        "evaluated_at": _utc_now(),
        "baseline_image": str(baseline_image) if baseline_image else None,
        "images": images_result,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "warning": warning_count,
            "awaiting_human": fail_count > 0 or warning_count > 0,
        },
    }

    # 写入 VISUAL_QA.json
    project_dir = JOBS_DIR / project_id
    qa_path = project_dir / "working" / "review_packet" / "VISUAL_QA.json"
    _atomic_write_json(qa_path, result)
    result["output_path"] = str(qa_path)
    return result


def _fail_receipt(project_id: str, reason: str) -> dict[str, Any]:
    """生成 FAIL receipt。"""
    return {
        "schema_version": VISUAL_QA_SCHEMA_VERSION,
        "project_id": project_id,
        "evaluated_at": _utc_now(),
        "status": "FAIL",
        "error": reason,
        "images": [],
        "summary": {
            "total": 0,
            "pass": 0,
            "fail": 0,
            "warning": 0,
            "awaiting_human": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VISUAL_QA 评估 - 使用 PIL/Pillow 实际读取图片并分析"
    )
    parser.add_argument("--project-id", required=True, help="OM project ID")
    parser.add_argument("--image-dir", required=True, help="图片目录路径")
    parser.add_argument(
        "--baseline-image",
        default=None,
        help="A/B 对比模式的 baseline 图片路径",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        image_dir = Path(args.image_dir)
        baseline = Path(args.baseline_image) if args.baseline_image else None
        result = run_visual_qa(args.project_id, image_dir, baseline)
    except (QAError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
