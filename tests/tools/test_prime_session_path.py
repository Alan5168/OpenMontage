from __future__ import annotations

from pathlib import Path

import pytest

from tools.prime_session_path import SessionPathError, latest_session_jsonl, resolve_session_jsonl, resume_cli_args


def test_resume_cli_args_always_use_full_jsonl_path(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    session = sessions / "019ff3ff-demo.jsonl"
    session.write_text('{"type":"session_info"}\n', encoding="utf-8")

    args = resume_cli_args(session, session_dir=sessions)
    assert args[0] == "--resume"
    assert args[1] == str(session.resolve())
    assert args[1].endswith(".jsonl")
    assert Path(args[1]).is_file()
    # Stem-only must not appear as the resume target.
    assert args[1] != session.stem


def test_stem_resolves_only_when_jsonl_exists(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    session = sessions / "named.jsonl"
    session.write_text("{}\n", encoding="utf-8")

    resolved = resolve_session_jsonl("named", session_dir=sessions)
    assert resolved == session.resolve()

    with pytest.raises(SessionPathError, match="full .jsonl path"):
        resolve_session_jsonl("missing", session_dir=sessions)

    with pytest.raises(SessionPathError, match="without session_dir"):
        resolve_session_jsonl("named")


def test_latest_session_jsonl_prefers_newest(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    older = sessions / "a.jsonl"
    newer = sessions / "b.jsonl"
    older.write_text("1\n", encoding="utf-8")
    newer.write_text("2\n", encoding="utf-8")
    assert latest_session_jsonl(sessions) == newer
