"""Project audio post-production: timed clips, dialogue ducking and loudness control."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any


def _safe_project_file(project: Path, relative: str) -> Path:
    candidate = (project / relative).resolve()
    if project.resolve() not in candidate.parents:
        raise ValueError(f"Audio path must stay inside the episode project: {relative}")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _bus_name(track: dict[str, Any]) -> str:
    name = str(track.get("kind", track.get("name", "other"))).lower()
    if name in {"dialogue", "voice", "voices", "speech"}:
        return "dialogue"
    if name in {"music", "score", "soundtrack"}:
        return "music"
    if name in {"ambience", "ambient", "background"}:
        return "ambience"
    if name in {"fx", "sfx", "effects", "sound_effects"}:
        return "effects"
    return "other"


def mix_episode_audio(project_dir: Path, *, config_path: Path | None = None,
                      output_path: Path | None = None) -> Path:
    """Create final_mix.wav from production/audio_mix.json using FFmpeg.

    Dialogue automatically ducks the music bus. Example:
    {"tracks":[{"name":"dialogue","clips":[{"file":"audio/dialogue/a.wav",
    "start_seconds":1.2,"end_seconds":4.8}]},
    {"name":"music","gain_db":-12,"clips":[{"file":"audio/music/theme.wav"}]}]}
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
        bus = _bus_name(track)
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
            clips.append({"path": source, "start": start, "end": end, "gain": gain, "bus": bus})
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
    filters: list[str] = []
    buses: dict[str, list[str]] = {}
    for index, clip in enumerate(clips):
        command.extend(["-i", str(clip["path"])])
        delay = round(clip["start"] * 1000)
        label = f"clip{index}"
        filters.append(
            f"[{index}:a]atrim=duration={clip['end'] - clip['start']:.4f},"
            f"asetpts=PTS-STARTPTS,adelay={delay}|{delay},"
            f"volume={clip['gain']:.3f}dB,"
            f"aformat=sample_rates=48000:channel_layouts=stereo[{label}]"
        )
        buses.setdefault(clip["bus"], []).append(f"[{label}]")

    bus_labels: dict[str, str] = {}
    for bus, labels in buses.items():
        label = f"bus_{bus}"
        if len(labels) == 1:
            filters.append(f"{labels[0]}anull[{label}]")
        else:
            filters.append(
                f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:"
                f"dropout_transition=0:normalize=0[{label}]"
            )
        bus_labels[bus] = label

    mix_labels = []
    if "music" in bus_labels and "dialogue" in bus_labels:
        filters.append(
            f"[{bus_labels['music']}][{bus_labels['dialogue']}]"
            "sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[ducked_music]"
        )
        mix_labels.append("[ducked_music]")
        mix_labels.extend(f"[{label}]" for bus, label in bus_labels.items()
                          if bus not in {"music", "dialogue"})
        mix_labels.append(f"[{bus_labels['dialogue']}]")
    else:
        mix_labels = [f"[{label}]" for label in bus_labels.values()]
    if len(mix_labels) == 1:
        final_input = mix_labels[0]
    else:
        filters.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=longest:"
            f"dropout_transition=0:normalize=0[all_buses]"
        )
        final_input = "[all_buses]"
    filters.append(
        f"{final_input}loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"alimiter=limit=0.95,apad,atrim=duration={duration:.4f}[mixout]"
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
        "buses": sorted(buses),
        "music_ducking": "dialogue_sidechain" if "music" in buses and "dialogue" in buses else "not_applicable",
        "loudness_target": {"integrated_lufs": -16, "true_peak_dbtp": -1.5},
        "output": str(output),
        "output_bytes": output.stat().st_size,
        "status": "mixed",
    }
    report_path = project / "production" / "audio_mix_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
