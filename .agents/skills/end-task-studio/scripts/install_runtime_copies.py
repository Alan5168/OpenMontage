#!/usr/bin/env python3
"""Install and hash-verify the canonical skill into Windows frontend skill roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TARGETS = [
    Path(r"C:\Users\ligua\.cursor\skills\end-task-studio"),
    Path(r"C:\Users\ligua\.gemini\config\skills\end-task"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", action="append", type=Path)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path(r"C:\ContentStudio\reports\windows-end-task-v2\INSTALL_RECEIPT.json"),
    )
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    files = [Path("SKILL.md"), Path("scripts/end_task.py")]
    expected = {str(rel).replace("\\", "/"): digest(source / rel) for rel in files}
    installed = []
    for target in args.target or DEFAULT_TARGETS:
        for rel in files:
            destination = target / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, destination)
        actual = {str(rel).replace("\\", "/"): digest(target / rel) for rel in files}
        if actual != expected:
            raise SystemExit(f"runtime hash mismatch: {target}")
        manifest = {
            "schema_version": 1,
            "canonical_source": str(source),
            "installed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "files": actual,
        }
        (target / "SOURCE_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        installed.append({"target": str(target), "files": actual})

    receipt = {"status": "PASS_RUNTIME_SKILL_SYNC", "canonical_source": str(source), "installed": installed}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

