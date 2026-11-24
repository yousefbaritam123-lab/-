"""Optional MoviePy editorial compositor for assembling rendered shots.

The core renderer remains Skia/Blender + FFmpeg. This adapter adds a
licensed, optional timeline-based finishing stage without replacing that path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_timeline(project_dir: Path, timeline_path: Path) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    timeline_path = Path(timeline_path)
    if not timeline_path.is_absolute():
        timeline_path = project_dir / timeline_path
    timeline_path = timeline_path.resolve()
    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("MoviePy timeline requires a non-empty 'clips' array.")
    normalized = []
    for index, item in enumerate(clips):
        if not isinstance(item, dict) or not isinstance(item.get("source"), str):
            raise ValueError(f"Timeline clip {index} requires a source path.")
        source = (project_dir / item["source"]).resolve()
        if source != project_dir and project_dir not in source.parents:
            raise ValueError(f"Timeline clip {index} source must stay inside the project.")
        if not source.is_file():
            raise FileNotFoundError(source)
        start = float(item.get("start_seconds", 0.0))
        end = item.get("end_seconds")
        end = None if end is None else float(end)
        if start < 0 or (end is not None and end <= start):
            raise ValueError(f"Timeline clip {index} has invalid trim points.")
        transition = float(item.get("transition_in_seconds", 0.0))
        if transition < 0 or (end is not None and transition >= end - start):
            raise ValueError(f"Timeline clip {index} has invalid transition duration.")
        normalized.append({
            "source": source, "start_seconds": start,
            "end_seconds": end, "transition_in_seconds": transition,
        })
    audio = data.get("audio")
    audio_path = None
    if audio:
        audio_path = (project_dir / str(audio)).resolve()
        if project_dir not in audio_path.parents or not audio_path.is_file():
            raise ValueError("Timeline audio must be an existing file inside the project.")
    output = str(data.get("output", "renders/moviepy-final.mp4"))
    output_path = (project_dir / output).resolve()
    if output_path == project_dir or project_dir not in output_path.parents:
        raise ValueError("MoviePy output must be a file inside the project.")
    return {"clips": normalized, "audio": audio_path, "output": output_path,
            "fps": int(data.get("fps", 30)), "codec": str(data.get("codec", "libx264"))}


def compose_moviepy_timeline(project_dir: Path, timeline_path: Path) -> Path:
    """Compose trimmed rendered shots with optional crossfades and replacement mix."""
    spec = load_timeline(project_dir, timeline_path)
    try:
        from moviepy import AudioFileClip, VideoFileClip, CompositeVideoClip, vfx
    except ImportError:
        try:
            from moviepy.editor import AudioFileClip, VideoFileClip, CompositeVideoClip, vfx
        except ImportError as exc:
            raise RuntimeError(
                "MoviePy is optional. Install it with: pip install -r requirements-editorial.txt"
            ) from exc

    opened = []
    final = None
    audio_clip = None
    try:
        clips = []
        cursor = 0.0
        canvas_size = None
        for index, item in enumerate(spec["clips"]):
            source_clip = VideoFileClip(str(item["source"]))
            opened.append(source_clip)
            start = item["start_seconds"]
            end = item["end_seconds"] if item["end_seconds"] is not None else source_clip.duration
            if end > source_clip.duration:
                raise ValueError(f"Timeline clip {index} ends after its source duration.")
            clip = source_clip.subclipped(start, end)
            if canvas_size is None:
                canvas_size = clip.size
            elif clip.size != canvas_size:
                raise ValueError(
                    f"Timeline clip {index} resolution {clip.size} differs from {canvas_size}."
                )
            transition = item["transition_in_seconds"] if index else 0.0
            if transition > clip.duration:
                raise ValueError(f"Timeline clip {index} transition exceeds its trimmed duration.")
            if index:
                previous_duration = clips[-1].duration
                if transition > previous_duration:
                    raise ValueError(f"Timeline clip {index} transition exceeds the previous clip.")
                cursor -= transition
                if transition:
                    clip = clip.with_effects([vfx.CrossFadeIn(transition)])
            clip = clip.with_start(cursor)
            clips.append(clip)
            cursor += clip.duration
        final = CompositeVideoClip(clips, size=canvas_size).with_duration(cursor)
        if spec["audio"]:
            audio_clip = AudioFileClip(str(spec["audio"]))
            final = final.with_audio(audio_clip)
        spec["output"].parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(spec["output"]), fps=spec["fps"], codec=spec["codec"],
            audio_codec="aac", preset="medium", logger=None,
        )
        if not spec["output"].is_file() or spec["output"].stat().st_size < 1024:
            raise RuntimeError("MoviePy did not produce a valid output file.")
        return spec["output"]
    finally:
        if final is not None:
            final.close()
        if audio_clip is not None:
            audio_clip.close()
        for clip in opened:
            clip.close()
