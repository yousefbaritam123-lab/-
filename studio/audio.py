"""Project audio post-production: timed dialogue, ambience, music and effects mix."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any


def _safe_project_file(project: Path, relative: str) -> Path:
    candidate = (project / relative).resolve()
    root = project.resolve()
    if root not in candidate.parents:
        raise ValueError(f"Audio path must stay inside the episode project: {relative}")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def mix_episode_audio(project_dir: Path, *, config_path: Path | None = None,
                      output_path: Path | None = None) -> Path:
    """Mix timed audio clips into a broadcast-safe stereo WAV using bundled FFmpeg.

    Config file: production/audio_mix.json
    {
      "tracks": [{"name":"dialogue","gain_db":0,"clips":[
        {"file":"audio/dialogue/youssef.wav","start_seconds":1.2,
         "end_seconds":4.8,"gain_db":-1}
      ]}]
    }
    """
    project = Path(project_dir).resolve()
    episode_path = project / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(episode_path)
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    duration = float(episode["format"]["duration_seconds"])
    config_path = config_path or project / "production" / "audio_mix.json"
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Audio mix plan not found: {config_path}. Create production/audio_mix.json."
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    clips: list[dict[str, Any]] = []
    for track in config.get("tracks", []):
        track_gain = float(track.get("gain_db", 0.0))
        for clip in track.get("clips", []):
            start = float(clip.get("start_seconds", 0.0))
            end = float(clip.get("end_seconds", duration))
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or start >= duration:
                raise ValueError(f"Invalid audio clip timing: {clip}")
            end = min(end, duration)
            source = _safe_project_file(project, str(clip["file"]))
            gain = track_gain + float(clip.get("gain_db", 0.0))
            if not math.isfinite(gain) or not -60 <= gain <= 24:
                raise ValueError(f"Audio gain outside safe range (-60 to +24 dB): {gain}")
            clips.append({"path": source, "start": start, "end": end, "gain": gain})
    if not clips:
        raise ValueError("Audio mix plan contains no usable clips.")

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Install imageio-ffmpeg: pip install -r requirements.txt") from exc
    output = output_path or project / "audio" / "final_mix.wav"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y"]
    filters = []
    labels = []
    for index, clip in enumerate(clips):
        command.extend(["-i", str(clip["path"])])
        start_ms = round(clip["start"] * 1000)
        delay = f"{start_ms}|{start_ms}"
        clip_duration = clip["end"] - clip["start"]
        label = f"a{index}"
        filters.append(
            f"[{index}:a]atrim=duration={clip_duration:.4f},asetpts=PTS-STARTPTS,"
            f"adelay={delay},volume={clip['gain']:.3f}dB,"
            f"aformat=sample_rates=48000:channel_layouts=stereo[{label}]"
        )
        labels.append(f"[{label}]")
    mix_inputs = "".join(labels)
    filters.append(
        f"{mix_inputs}amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95,"
        f"apad,atrim=duration={duration:.4f}[mixout]"
    )
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[mixout]",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
        "-t", f"{duration:.4f}", str(output),
    ])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Audio mix failed:\n" + result.stderr[-5000:])
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("Audio mix output is missing or unexpectedly small.")
    report = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "duration_seconds": duration,
        "sample_rate": 48000,
        "channels": 2,
        "format": "PCM 24-bit WAV",
        "clip_count": len(clips),
        "loudness_target": {"integrated_lufs": -16, "true_peak_dbtp": -1.5},
        "output": str(output),
        "output_bytes": output.stat().st_size,
        "status": "mixed",
    }
    report_path = project / "production" / "audio_mix_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
