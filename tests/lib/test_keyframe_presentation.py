from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from lib.keyframe_presentation import evaluate_keyframe_presentation

JOB = Path(r"C:\ContentStudio\jobs\vid3-blacklisted-chef-90s-v1")


def _mcu(path: Path) -> None:
    image = Image.new("RGB", (1280, 720), (150, 150, 155))
    draw = ImageDraw.Draw(image)
    draw.ellipse((520, 80, 760, 380), fill=(210, 170, 145))
    draw.rectangle((500, 360, 780, 700), fill=(40, 42, 48))
    draw.rectangle((560, 400, 600, 430), fill=(180, 160, 90))
    image.save(path)


def _silhouette(path: Path) -> None:
    image = Image.new("RGB", (1280, 720), (32, 36, 42))
    draw = ImageDraw.Draw(image)
    draw.rectangle((560, 220, 720, 500), fill=(255, 140, 40))
    draw.rectangle((632, 250, 648, 430), fill=(4, 4, 6))
    image.save(path)


def test_b1_silhouette_is_unusable_performance_start():
    b1 = JOB / "working" / "prime_rlm" / "keyframes" / "B1.png"
    report = evaluate_keyframe_presentation(b1, framing="full_body")
    assert report["usable"] is False
    assert "body_silhouette_only" in report["blockers"]
    assert "identity_not_visible" in report["blockers"]
    assert report["measurements"]["far_silhouette_figure"]


def test_lucien_identity_plate_is_readable():
    plate = JOB / "bible" / "lucien" / "master_sheet.png"
    report = evaluate_keyframe_presentation(plate, framing="medium_close")
    assert report["usable"] is True
    assert report["identity_visible"] is True
    assert report["body_not_silhouette_only"] is True


def test_synthetic_mcu_passes_and_stick_figure_fails(tmp_path):
    good = tmp_path / "mcu.png"
    bad = tmp_path / "sil.png"
    _mcu(good)
    _silhouette(bad)
    assert evaluate_keyframe_presentation(good, framing="medium_close")["usable"] is True
    bad_report = evaluate_keyframe_presentation(bad, framing="full_body")
    assert bad_report["usable"] is False
    assert "body_silhouette_only" in bad_report["blockers"]
