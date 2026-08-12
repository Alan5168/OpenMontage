#!/usr/bin/env python3
"""Create frozen no-media jobs under an authorized Content Studio root."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

OM_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OM_REPO))
sys.path.insert(0, str(OM_REPO / "integrations" / "prime-om-adapter" / "src"))

from lib.checkpoint import init_project, write_checkpoint
from tests.contracts.test_phase0_contracts import sample_artifact

SCENARIO = "comic-nonfiction-short-knowledge-zh"
SKILL_CASEBOOK = OM_REPO / "integrations" / "prime-om-adapter" / "fixtures" / "casebook"


def _architecture(topic: str) -> dict:
    return {
        "version": "1.0",
        "audience_problem": f"把一次模型输出当成「{topic}」已经完成。",
        "thesis": "可靠的内容生产靠阶段门禁，而不是更强模型。",
        "viewer_change": "观众能区分烟雾结果与可发布成片。",
        "hooks": [
            {"text": "有输出不等于过门", "promise": "先看检查点"},
            {"text": "音乐不能盖住口播", "promise": "混音合同可测"},
            {"text": "意图、prompt、结果必须分列", "promise": "八列 sceneplan"},
        ],
        "structure": {
            "opening_promise": "先冻结失败，再谈生成。",
            "evidence_or_conflict": ["缺前置检查点不能前进", "未批准 Gate 不能渲染"],
            "turn": "门禁不是负担，是唯一可信完成定义。",
            "payoff": "同一失败不再整片重做。",
            "takeaway": "没有人工 Gate，就没有发布。",
        },
        "visual_opportunities": [
            {
                "beat": "opening",
                "opportunity": "textless gate closing in front of a result card",
                "provider_decided": False,
            }
        ],
    }


def _heldout_research() -> dict:
    brief = sample_artifact("research_brief")
    brief["topic"] = "为什么字幕时钟必须跟真人 VO 对齐，而不能把可读字交给生成模型"
    brief["data_points"][0]["claim"] = "ASR 只提供时钟，批准稿才是词法真相。"
    brief["data_points"][1]["claim"] = "生成画面里的可读中文会在 Remotion 之外漂移。"
    brief["data_points"][2]["claim"] = "Gate 未通过时提前渲染会污染 canonical checkpoint。"
    brief["audience_insights"]["misconceptions"] = [
        {"myth": "生成模型可以顺便写出清楚字幕。", "reality": "可读字必须确定性叠层。"},
        {"myth": "时钟可以对齐画面后再改词。", "reality": "词法真相是批准稿，不是 ASR。"},
    ]
    return brief


def materialize(root: Path) -> dict[str, str]:
    root = root.resolve()
    jobs = root / "jobs"
    casebook_dst = root / "runtime" / "prime-rlm-pilot" / "fixtures" / "casebook"
    casebook_dst.mkdir(parents=True, exist_ok=True)
    for src in SKILL_CASEBOOK.glob("*.json"):
        shutil.copy2(src, casebook_dst / src.name)

    created = {}
    historical_id = "fixture-prime-rlm-historical"
    heldout_id = "fixture-prime-rlm-heldout"
    for job_id, research, extra_stage in (
        (historical_id, sample_artifact("research_brief"), True),
        (heldout_id, _heldout_research(), False),
    ):
        init_project(
            job_id,
            title=f"Prime RLM {job_id}",
            pipeline_type="unknown",
            pipeline_dir=jobs,
            style_playbook="premium-minimalist",
        )
        project_dir = jobs / job_id
        marker_path = project_dir / "project.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["scenario_id"] = SCENARIO
        marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (project_dir / "artifacts" / "research_brief.json").write_text(
            json.dumps(research, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_checkpoint(
            jobs,
            job_id,
            "research",
            "completed",
            {"research_brief": research},
            pipeline_type="unknown",
            style_playbook="premium-minimalist",
        )
        if extra_stage:
            arch = _architecture(research["topic"])
            (project_dir / "artifacts" / "content_architecture.json").write_text(
                json.dumps(arch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            write_checkpoint(
                jobs,
                job_id,
                "proposal",
                "completed",
                {"proposal_packet": sample_artifact("proposal_packet")},
                pipeline_type="unknown",
                style_playbook="premium-minimalist",
            )
        created[job_id] = str(project_dir)
    return created


def main() -> int:
    root = Path(os.environ.get("OM_PRIME_ADAPTER_ROOT") or r"C:\ContentStudio")
    created = materialize(root)
    print(json.dumps({"root": str(root), "jobs": created}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
