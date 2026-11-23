"""Optional bridge to Blender's background renderer; Blender is not a pip dependency."""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path

def build_blender_manifest(project_dir: Path) -> Path:
    episode_path = project_dir / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(episode_path)
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1, "episode_id": episode["id"], "format": episode["format"],
        "locations": episode.get("locations", []), "characters": episode.get("characters", []),
        "shots": episode.get("shots", []), "assets_root": str((project_dir / "assets").resolve()),
        "output_root": str((project_dir / "renders" / "blender").resolve()),
        "backend": "blender_optional",
        "limitations": ["layered puppet import requires a layered character asset manifest",
                       "flat PNG references are image planes, not automatically skeletal rigs"]
    }
    target = project_dir / "production" / "blender_scene_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target

def render_with_blender(project_dir: Path, *, blender: str = "blender",
                        script: Path | None = None) -> Path:
    binary = shutil.which(blender) if not Path(blender).is_file() else blender
    if not binary:
        raise RuntimeError("Blender executable not found. Install Blender and add it to PATH.")
    script = script or Path(__file__).resolve().parent.parent / "tools" / "blender_scene.py"
    if not script.is_file():
        raise FileNotFoundError(f"Blender scene script missing: {script}")
    manifest = build_blender_manifest(project_dir)
    command = [str(binary), "--background", "--python", str(script), "--", "--manifest", str(manifest)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(f"Blender render failed ({completed.returncode}): {completed.stderr[-3000:]}")
    return project_dir / "renders" / "blender"
