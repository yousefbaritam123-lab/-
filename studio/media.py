"""Video encoding helpers. Requires imageio-ffmpeg (bundled FFmpeg executable)."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
from PIL import Image


def encode_video(project_dir: Path, fps: int = 30, output_name: str = "episode.mp4") -> Path:
    """Validate the full PNG sequence, encode to a temporary MP4, then atomically publish."""
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Install project dependencies: pip install -r requirements.txt") from exc

    project_dir = Path(project_dir)
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    expected = int(round(float(episode["format"]["duration_seconds"]) * fps))
    width = int(episode["format"]["width"])
    height = int(episode["format"]["height"])
    frames = project_dir / "renders" / "frames"
    defects: list[str] = []
    for number in range(expected):
        frame = frames / f"frame_{number:06d}.png"
        if not frame.is_file() or frame.stat().st_size < 256:
            defects.append(f"{number}: missing or too small")
            continue
        try:
            with Image.open(frame) as image:
                image.verify()
            with Image.open(frame) as image:
                if image.size != (width, height):
                    defects.append(f"{number}: dimensions {image.size}, expected {(width, height)}")
        except Exception as exc:
            defects.append(f"{number}: corrupt PNG ({exc})")
    if defects:
        raise RuntimeError(
            f"Cannot encode: {len(defects)} defective frame(s). "
            "Run production-run to repair them. First defects: " + "; ".join(defects[:8])
        )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output = project_dir / "renders" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.stem + ".partial" + output.suffix)
    audio_mix = project_dir / "audio" / "final_mix.wav"
    base_command = [
        ffmpeg, "-y", "-hide_banner", "-v", "error", "-xerror",
        "-framerate", str(fps), "-start_number", "0",
        "-i", str(frames / "frame_%06d.png"),
        "-frames:v", str(expected), "-c:v", "libx264",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if audio_mix.is_file():
        base_command.extend([
            "-i", str(audio_mix), "-map", "0:v:0", "-map", "1:a:0",
            "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-t",
            f"{expected / fps:.3f}",
        ])

    failures: list[str] = []
    for attempt, preset in enumerate(("medium", "fast"), start=1):
        command = list(base_command)
        insert_at = command.index("-crf")
        command[insert_at:insert_at] = ["-preset", preset]
        command.append(str(temporary))
        try:
            if temporary.exists():
                temporary.unlink()
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, timeout=1800
            )
            if result.returncode != 0:
                failures.append(f"attempt {attempt} ({preset}): {result.stderr[-1800:]}")
                continue
            if not temporary.is_file() or temporary.stat().st_size < 1024:
                failures.append(f"attempt {attempt} ({preset}): output missing or too small")
                continue
            # Decode the entire resulting file before replacing the last good output.
            probe = subprocess.run(
                [ffmpeg, "-v", "error", "-i", str(temporary), "-f", "null", "-"],
                capture_output=True, text=True, check=False, timeout=1800
            )
            if probe.returncode != 0:
                failures.append(f"attempt {attempt} ({preset}): decode verification failed: {probe.stderr[-1800:]}")
                continue
            temporary.replace(output)
            return output
        except subprocess.TimeoutExpired:
            failures.append(f"attempt {attempt} ({preset}): encoding timed out after 30 minutes")
        finally:
            if temporary.exists():
                temporary.unlink()

    raise RuntimeError("FFmpeg encoding failed after automatic retry. " + " | ".join(failures))
