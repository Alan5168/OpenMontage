#!/usr/bin/env python3
"""Scan newly tracked/report files for secrets. Prints names only, never values."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS = Path(r"C:\ContentStudio\reports\windows-trae-native-content-harness-v1")

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._]{12,}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
]

SKIP_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "renders",
    "models",
    "__pycache__",
    ".agents",
    ".claude",
    ".pytest_cache",
}

# Goal T8: 新增 tracked/report 文件，不是扫整个上游 skill 文档。
SCAN_GLOBS = [
    "tools/content_studio_*.py",
    "tools/om_context_bridge.py",
    "tools/om_media_bridge.py",
    "tools/resource_governor.py",
    "tools/learning_system.py",
    "tools/visual_qa.py",
    "tools/review_packet_builder.py",
    "tools/content_studio_async_console.py",
    "scripts/windows/*.cmd",
    "tests/tools/test_content_studio_r2_contracts.py",
    "tests/fixtures/content_studio/**/*",
    "docs/LICENSE_BOUNDARY.md",
]


def _iter_scan_paths() -> list[Path]:
    paths: list[Path] = []
    for glob in SCAN_GLOBS:
        paths.extend(REPO.glob(glob))
    if REPORTS.is_dir():
        for path in REPORTS.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".py", ".txt"}:
                paths.append(path)
    uniq = []
    seen = set()
    for path in paths:
        if not path.is_file():
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        uniq.append(path)
    return uniq


def main() -> int:
    hits = []
    scanned = []
    for path in _iter_scan_paths():
        if path.stat().st_size > 2_000_000:
            continue
        scanned.append(str(path))
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in PATTERNS:
            if pat.search(text):
                hits.append({"path": str(path), "pattern": pat.pattern})
                break
    payload = {
        "schema_version": "content-studio-secret-scan/v1",
        "status": "OK" if not hits else "FAIL",
        "hit_count": len(hits),
        "hits": hits,
        "scanned_count": len(scanned),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "note": "hits list paths only; secret values are never printed; scope=r2 new files + reports",
    }
    if REPORTS.is_dir():
        (REPORTS / "SECRET_SCAN.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
