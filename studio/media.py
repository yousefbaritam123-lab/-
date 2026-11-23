"""Video encoding helpers. Requires imageio-ffmpeg (bundled FFmpeg executable)."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess


def encode_video(project_dir: Path, fps: int = 30, output_name: str = "episode.mp4") -> Path:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Install project dependencies: pip install -r requirements.txt") from exc

    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    expected = int(round(float(episode["format"]["duration_seconds"]) * fps))
    frames = project_dir / "renders" / "frames"
    missing = [n for n in range(expected) if not (frames / f"frame_{n:06d}.png").is_file()]
    if missing:
        sample = ", ".join(str(n) for n in missing[:12])
        raise RuntimeError(
            f"Cannot encode an incomplete render: {len(missing)} of {expected} frames are missing. "
            f"First missing frame numbers: {sample}. Render the missing ranges first."
        )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output = project_dir / "renders" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-y", "-framerate", str(fps),
        "-start_number", "0", "-i", str(frames / "frame_%06d.png"),
        "-frames:v", str(expected), "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg encoding failed:\n" + result.stderr[-5000:])
    return output
