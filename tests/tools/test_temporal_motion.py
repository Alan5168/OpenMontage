from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from lib.creative_loop import CreativeLoopError, see_mp4
from lib.temporal_motion import (
    analyze_temporal_motion,
    assert_temporal_see,
    write_temporal_motion_report,
)


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        pytest.skip("ffmpeg required")
    return exe


def _still_concat(tmp_path: Path) -> Path:
    ffmpeg = _ffmpeg()
    red = tmp_path / "red.mp4"
    blue = tmp_path / "blue.mp4"
    out = tmp_path / "holds.mp4"
    for color, dest, seconds in (("red", red, 2), ("blue", blue, 2)):
        subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s=320x180:d={seconds}:r=30",
                "-pix_fmt", "yuv420p", str(dest),
            ],
            check=True,
        )
    lst = tmp_path / "list.txt"
    lst.write_text(f"file '{red.as_posix()}'\nfile '{blue.as_posix()}'\n", encoding="utf-8")
    subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out),
        ],
        check=True,
    )
    return out


def test_two_static_holds_are_measured_not_failed(tmp_path: Path):
    mp4 = _still_concat(tmp_path)
    report = analyze_temporal_motion(mp4, work_dir=tmp_path / "work")
    assert report["judgment"] == "measurement_only"
    assert report["scene_changes"] >= 1
    assert report["longest_static_run"] >= 1.2
    types = set(report["motion_type"].values())
    assert types <= {"STATIC_HOLD", "LIMITED_LOCAL_MOTION"}
    assert "STATIC_HOLD" in types
    path = write_temporal_motion_report(tmp_path / "report.json", report)
    assert path.is_file()


def test_visual_judgment_without_temporal_report_is_incomplete():
    with pytest.raises(CreativeLoopError, match="temporal motion report"):
        assert_temporal_see(None)


def test_see_writes_temporal_report_with_frames(tmp_path: Path):
    mp4 = _still_concat(tmp_path)
    result = see_mp4(mp4, tmp_path / "see", interval=1.0)
    assert (tmp_path / "see" / "temporal_motion_report.json").is_file()
    assert (tmp_path / "see" / "frame_packet.json").is_file()
    assert result["temporal_motion_report"]["judgment"] == "measurement_only"
    assert result["frame_packet"]["source_sha256"] == result["temporal_motion_report"]["source_sha256"]
