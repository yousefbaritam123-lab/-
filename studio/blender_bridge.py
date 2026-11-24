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
        "prepared_cast_path": str((project_dir / "assets" / "characters" / "prepared_cast_60").resolve()),
        "cast_source_svg": str((project_dir / "assets" / "characters" / "cast_60" / "contact_sheet.svg").resolve()),
        "output_root": str((project_dir / "renders" / "blender").resolve()),
    }
    target = project_dir / "production" / "blender_scene_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target



def _rasterize_character_svg(svg_path: Path) -> Path:
    """Rasterize the original vector art with alpha so no SVG strokes are lost."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("Install CairoSVG for original-art Blender rendering: pip install CairoSVG") from exc
    svg_path = Path(svg_path)
    root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(svg_path).getroot()
    view_box = [float(value) for value in root.get("viewBox", "0 0 200 220").replace(",", " ").split()]
    if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
        raise ValueError(f"Invalid SVG viewBox in {svg_path}")
    png_path = svg_path.with_suffix(".png")
    cairosvg.svg2png(
        url=str(svg_path), write_to=str(png_path),
        output_width=int(round(view_box[2] * 3)),
        output_height=int(round(view_box[3] * 3)),
    )
    if not png_path.is_file() or png_path.stat().st_size < 256:
        raise RuntimeError(f"Original SVG rasterization produced no usable PNG: {svg_path}")
    return png_path


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
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    cast_ids = {
        str(actor.get("cast_id", actor.get("id", "")))
        for actor in episode.get("characters", [])
        if str(actor.get("cast_id", actor.get("id", ""))).startswith("extra_")
    }
    source_svg = project_dir / "assets" / "characters" / "cast_60" / "contact_sheet.svg"
    prepared = project_dir / "assets" / "characters" / "prepared_cast_60"
    if cast_ids:
        if not (prepared / "cast_manifest.json").is_file():
            from .svg_character_assets import prepare_svg_cast
            prepare_svg_cast(source_svg, prepared)
        missing = [cast_id for cast_id in sorted(cast_ids) if not (prepared / f"{cast_id}.svg").is_file()]
        if missing:
            raise RuntimeError("Prepared original SVG cast assets are missing: " + ", ".join(missing))
    named_ids = {
        str(actor.get("id", ""))
        for actor in episode.get("characters", [])
        if str(actor.get("id", "")) in {"youssef", "adam"}
    }
    if named_ids:
        from .svg_character_assets import prepare_named_character_svg
        for character_id in sorted(named_ids):
            source = project_dir / "assets" / "characters" / character_id / "design_sheet.svg"
            target = prepared / f"{character_id}.svg"
            if not target.is_file():
                if not source.is_file():
                    raise RuntimeError(f"Original {character_id} model-sheet SVG is missing: {source}")
                prepare_named_character_svg(source, target, character_id)
    raster_ids = set(cast_ids) | set(named_ids)
    for character_id in sorted(raster_ids):
        _rasterize_character_svg(prepared / f"{character_id}.svg")
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
        "-frames:v", str(expected),
    ]
    audio_mix = project_dir / "audio" / "final_mix.wav"
    if audio_mix.is_file():
        encode.extend([
            "-i", str(audio_mix), "-map", "0:v:0", "-map", "1:a:0",
            "-c:a", "aac", "-b:a", "192k", "-af", "apad",
            "-t", f"{float(fmt['duration_seconds']):.3f}",
        ])
    encode.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_video),
    ])
    result = subprocess.run(encode, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Blender MP4 encoding failed:\n" + result.stderr[-5000:])
    if not output_video.is_file() or output_video.stat().st_size < 1024:
        raise RuntimeError("Blender MP4 output is missing or unexpectedly small.")
    report["video"] = str(output_video)
    report["video_bytes"] = output_video.stat().st_size
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_video
