"""Blender-backed 2D scene rendering and verified MP4 encoding."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def build_blender_manifest(project_dir: Path) -> Path:
    episode_path = project_dir / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(episode_path)
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 2,
        "backend": "blender_procedural_2d",
        "episode_id": episode["id"],
        "format": episode["format"],
        "locations": episode.get("locations", []),
        "characters": episode.get("characters", []),
        "shots": episode.get("shots", []),
        "assets_root": str((project_dir / "assets").resolve()),
        "catalog_path": str((project_dir / "assets" / "characters" / "cast_60" / "catalog.json").resolve()),
        "output_root": str((project_dir / "renders" / "blender").resolve()),
    }
    target = project_dir / "production" / "blender_scene_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _resolve_binary(binary: str) -> str:
    resolved = str(Path(binary).resolve()) if Path(binary).is_file() else shutil.which(binary)
    if not resolved:
        raise RuntimeError("Blender executable not found. Install Blender 4.x and add it to PATH.")
    return resolved


def render_with_blender(project_dir: Path, *, blender: str = "blender",
                        script: Path | None = None) -> Path:
    """Render all episode frames with Blender, validate them, and encode an MP4."""
    binary = _resolve_binary(blender)
    script = script or Path(__file__).resolve().parent.parent / "tools" / "blender_scene.py"
    if not script.is_file():
        raise FileNotFoundError(f"Blender scene script missing: {script}")
    manifest_path = build_blender_manifest(project_dir)
    output_root = project_dir / "renders" / "blender"
    frames_dir = output_root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    command = [binary, "--background", "--python", str(script), "--",
               "--manifest", str(manifest_path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"Blender render failed ({completed.returncode}).\n"
            f"STDOUT:\n{completed.stdout[-3000:]}\nSTDERR:\n{completed.stderr[-5000:]}"
        )

    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    fmt = episode["format"]
    expected = int(round(float(fmt["duration_seconds"]) * int(fmt["fps"])))
    from PIL import Image
    errors: list[str] = []
    frame_paths = [frames_dir / f"frame_{index + 1:06d}.png" for index in range(expected)]
    for index, path in enumerate(frame_paths):
        if not path.is_file():
            errors.append(f"missing frame {index + 1}")
            continue
        try:
            with Image.open(path) as image:
                image.load()
                if image.size != (int(fmt["width"]), int(fmt["height"])):
                    errors.append(f"{path.name}: expected {(fmt['width'], fmt['height'])}, got {image.size}")
        except Exception as exc:
            errors.append(f"{path.name}: decode failed: {exc}")
    report: dict[str, Any] = {
        "backend": "blender",
        "expected_frames": expected,
        "valid_frames": expected - len(errors),
        "errors": errors,
        "status": "passed" if not errors else "failed",
    }
    report_path = output_root / "render_integrity.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("Blender frame integrity failed: " + "; ".join(errors[:12]))

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Install imageio-ffmpeg: pip install -r requirements.txt") from exc
    output_video = output_root / "episode-blender.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    encode = [
        ffmpeg, "-y", "-framerate", str(int(fmt["fps"])),
        "-start_number", "1", "-i", str(frames_dir / "frame_%06d.png"),
        "-frames:v", str(expected), "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_video),
    ]
    result = subprocess.run(encode, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Blender MP4 encoding failed:\n" + result.stderr[-5000:])
    if not output_video.is_file() or output_video.stat().st_size < 1024:
        raise RuntimeError("Blender MP4 output is missing or unexpectedly small.")
    report["video"] = str(output_video)
    report["video_bytes"] = output_video.stat().st_size
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_video
