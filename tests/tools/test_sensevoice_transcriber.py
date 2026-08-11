from __future__ import annotations

import sys
import types

from tools.analysis.sensevoice_transcriber import SenseVoiceTranscriber


class _FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def generate(self, **kwargs):
        return [
            {
                "text": "<|zh|><|NEUTRAL|><|Speech|><|woitn|>检查点不是进度条。",
                "words": ["检", "查", "点", "不", "是", "进", "度", "条", "。"],
                "timestamp": [[0, 80], [80, 160], [160, 240], [240, 320], [320, 400], [400, 480], [480, 560], [560, 640], [640, 700]],
            }
        ]


def _install_fakes(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: True)
    fake_funasr = types.ModuleType("funasr")
    fake_funasr.AutoModel = _FakeModel
    fake_utils = types.ModuleType("funasr.utils")
    fake_post = types.ModuleType("funasr.utils.postprocess_utils")
    fake_post.rich_transcription_postprocess = lambda value: "检查点不是进度条。"
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "funasr", fake_funasr)
    monkeypatch.setitem(sys.modules, "funasr.utils", fake_utils)
    monkeypatch.setitem(sys.modules, "funasr.utils.postprocess_utils", fake_post)


def test_sensevoice_transcriber_normalizes_ctc_timestamps(monkeypatch, tmp_path):
    _install_fakes(monkeypatch)
    source = tmp_path / "voice.wav"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(SenseVoiceTranscriber, "_duration", lambda *a: 0.7)

    result = SenseVoiceTranscriber().execute(
        {"input_path": str(source), "output_dir": str(tmp_path), "device": "auto"}
    )

    assert result.success, result.error
    assert result.data["device"] == "cuda:0"
    assert result.data["precision"] == "fp32"
    assert result.data["word_timestamps"][0] == {
        "word": "检", "start": 0.0, "end": 0.08, "probability": None
    }
    assert result.data["segments"][0]["text"] == "检查点不是进度条。"
    assert result.data["license_policy"].endswith("attribution required")
    assert (tmp_path / "voice_sensevoice_transcript.json").is_file()


def test_sensevoice_transcriber_rejects_known_bad_fp16_path(tmp_path):
    source = tmp_path / "voice.wav"
    source.write_bytes(b"fixture")

    result = SenseVoiceTranscriber().execute(
        {"input_path": str(source), "fp16": True}
    )

    assert result.success is False
    assert "Float/Half dtype mismatch" in result.error


def test_sensevoice_segment_grouping_respects_punctuation_and_duration():
    words = [
        {"word": "甲", "start": 0.0, "end": 0.2},
        {"word": "。", "start": 0.2, "end": 0.3},
        {"word": "乙", "start": 0.5, "end": 1.0},
        {"word": "丙", "start": 1.0, "end": 2.1},
    ]

    groups = SenseVoiceTranscriber._group_segments(words, max_seconds=1.0)

    assert [group["text"] for group in groups] == ["甲。", "乙丙"]
    assert groups[1]["start"] == 0.5
    assert groups[1]["end"] == 2.1
