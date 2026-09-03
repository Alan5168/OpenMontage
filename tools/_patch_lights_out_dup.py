"""One-shot: drop duplicate preference helpers. Do not keep this script."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "integrations" / "prime-om-adapter" / "src" / "om_prime_adapter" / "production.py"
text = path.read_text(encoding="utf-8")
block = (
    "def _skeleton_scene_id(project_dir: Path) -> str | None:\n"
    "    skeleton = _read_json_if(project_dir / \"JOB_SKELETON.json\") or {}\n"
    "    scene_id = str(skeleton.get(\"scene_id\") or \"\").strip()\n"
    "    return scene_id or None\n"
    "\n"
    "\n"
    "def _preference_target(project_dir: Path, target: str | None) -> str | None:\n"
    "    if target:\n"
    "        return str(target)\n"
    "    proposal = _current_scene_proposal(project_dir) or {}\n"
    "    scene_id = str(proposal.get(\"scene_id\") or \"\").strip()\n"
    "    return scene_id or _skeleton_scene_id(project_dir)\n"
    "\n"
    "\n"
)
count = text.count(block)
if count < 2:
    raise SystemExit(f"expected 2 helper blocks, found {count}")
path.write_text(text.replace(block, "", 1), encoding="utf-8", newline="\n")
print("removed duplicate helper block")
