"""Resolve Prime session resume targets. Always prefer a full .jsonl path."""

from __future__ import annotations

from pathlib import Path


class SessionPathError(ValueError):
    """Raised when a resume target cannot be resolved safely."""


def latest_session_jsonl(session_dir: Path) -> Path | None:
    if not session_dir.is_dir():
        return None
    files = sorted(session_dir.glob("*.jsonl"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    if not files:
        files = sorted(
            (path for path in session_dir.rglob("*.jsonl") if path.is_file()),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
    return files[0] if files else None


def resolve_session_jsonl(candidate: str | Path, *, session_dir: Path | None = None) -> Path:
    """Resolve a resume target to an absolute .jsonl file path.

    Accepts an absolute/relative .jsonl path. A bare stem is only accepted when
    ``session_dir / f"{stem}.jsonl"`` exists; the returned value is always the
    full path. Bare stems that do not resolve fail closed.
    """
    raw = Path(candidate)
    if raw.suffix == ".jsonl":
        path = raw.expanduser()
        if not path.is_absolute() and session_dir is not None:
            path = session_dir / path.name
        path = path.resolve()
        if not path.is_file():
            raise SessionPathError(f"Session jsonl not found: {path}")
        return path

    stem = raw.name
    if session_dir is None:
        raise SessionPathError(
            f"Refusing stem-only resume {stem!r} without session_dir; pass the full .jsonl path"
        )
    path = (session_dir / f"{stem}.jsonl").resolve()
    if not path.is_file():
        raise SessionPathError(
            f"No session jsonl for stem {stem!r} under {session_dir}; pass the full .jsonl path"
        )
    return path


def resume_cli_args(session_file: str | Path, *, session_dir: Path | None = None) -> list[str]:
    path = resolve_session_jsonl(session_file, session_dir=session_dir)
    return ["--resume", str(path)]
