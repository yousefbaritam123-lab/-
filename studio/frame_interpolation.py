"""Optional motion-compensated FPS conversion for rendered episode videos.

Uses FFmpeg's minterpolate filter. This is a post-process: it cannot repair bad
poses, anatomy, timing, or character consistency in the source animation.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def interpolate_video(
    project_dir: Path,
    target_fps: int,
    *,
    source: Path | None = None,
    output: Path | None = None,
    timeout_seconds: int = 1800,
) -> Path:
    """Create a motion-compensated higher-FPS copy and verify the complete decode."""
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Install project dependencies: pip install -r requirements.txt") from exc

    project_dir = Path(project_dir).resolve()
    episode_path = project_dir / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(f"Missing episode.json: {episode_path}")
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    source_fps = int(episode.get("format", {}).get("fps", 0))
    if source_fps < 1:
        raise ValueError("episode.json must define a positive format.fps")
    if isinstance(target_fps, bool) or int(target_fps) != target_fps:
        raise ValueError("target_fps must be an integer")
    target_fps = int(target_fps)
    if target_fps <= source_fps or target_fps > source_fps * 4 or target_fps % source_fps:
        raise ValueError(
            f"target_fps must be a multiple of source FPS between "
            f"{source_fps * 2} and {source_fps * 4}"
        )

    source_path = Path(source) if source else project_dir / "renders" / "episode.mp4"
    if not source_path.is_absolute():
        source_path = (project_dir / source_path).resolve()
    if not source_path.is_file() or source_path.stat().st_size < 1024:
        raise FileNotFoundError(f"Source video is missing or too small: {source_path}")

    output_path = Path(output) if output else (
        project_dir / "renders" / f"{source_path.stem}-{target_fps}fps.mp4"
    )
    if not output_path.is_absolute():
        output_path = (project_dir / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.resolve() == source_path.resolve():
        raise ValueError("Output must not overwrite the source video")
    temporary = output_path.with_name(output_path.stem + ".partial" + output_path.suffix)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    vf = (
        f"minterpolate=fps={target_fps}:mi_mode=mci:"
        "mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    )
    command = [
        ffmpeg, "-y", "-hide_banner", "-v", "error", "-xerror",
        "-i", str(source_path), "-map", "0:v:0", "-map", "0:a?",
        "-vf", vf, "-fps_mode", "cfr", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(temporary),
    ]
    try:
        if temporary.exists():
            temporary.unlink()
        result = subprocess.run(
            command, capture_output=True, text=True, check=False,
            timeout=timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "FFmpeg motion interpolation failed. The installed FFmpeg may "
                "not support minterpolate. Details: " + result.stderr[-2400:]
            )
        if not temporary.is_file() or temporary.stat().st_size < 1024:
            raise RuntimeError("Interpolated video is missing or unexpectedly small")
        verify = subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-i", str(temporary), "-f", "null", "-"],
            capture_output=True, text=True, check=False, timeout=timeout_seconds,
        )
        if verify.returncode != 0:
            raise RuntimeError("Interpolated video failed full decode: " + verify.stderr[-1800:])
        temporary.replace(output_path)
        return output_path
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"FPS interpolation exceeded {timeout_seconds} seconds; source video was preserved"
        ) from exc
    finally:
        if temporary.exists():
            temporary.unlink()
