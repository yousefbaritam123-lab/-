"""Optional local Piper TTS adapter for episode dialogue."""
from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any


def _inside_project(project: Path, relative: str) -> Path:
    path = (project / relative).resolve()
    if project.resolve() not in path.parents:
        raise ValueError(f"Voice model/audio path must stay inside project: {relative}")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        if wav.getnframes() <= 0 or wav.getframerate() <= 0:
            raise ValueError(f"Generated voice file is empty or invalid: {path}")
        return wav.getnframes() / wav.getframerate()


def generate_dialogue_audio(project_dir: Path, *, config_path: Path | None = None,
                            executable: str = "piper") -> Path:
    """Generate one WAV per dialogue line and a timed audio-mix plan.

    Requires the Piper executable and Arabic voice model files supplied by the user.
    """
    project = Path(project_dir).resolve()
    episode_path = project / "episode.json"
    if not episode_path.is_file():
        raise FileNotFoundError(episode_path)
    episode = json.loads(episode_path.read_text(encoding="utf-8"))
    config_path = config_path or project / "production" / "voice_cast.json"
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Voice cast config missing: {config_path}. Create production/voice_cast.json."
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    binary = str(Path(executable).resolve()) if Path(executable).is_file() else shutil.which(executable)
    if not binary:
        raise RuntimeError("Piper executable not found. Install Piper and add 'piper' to PATH.")

    voices = config.get("voices", {})
    default_voice = config.get("default_voice")
    output_dir = project / "audio" / "dialogue"
    output_dir.mkdir(parents=True, exist_ok=True)
    clips: list[dict[str, Any]] = []
    errors: list[str] = []
    shot_start = 0.0
    line_count = 0
    for shot in episode.get("shots", []):
        for line_index, line in enumerate(shot.get("dialogue", []), start=1):
            text = str(line.get("text", "")).strip()
            if not text:
                continue
            speaker = str(line.get("speaker", ""))
            voice = voices.get(speaker, voices.get(default_voice))
            if not isinstance(voice, dict) or not voice.get("model"):
                errors.append(f"{shot.get('id')} line {line_index}: no Piper voice model configured for {speaker}")
                continue
            model = _inside_project(project, str(voice["model"]))
            voice_config = None
            if voice.get("config"):
                voice_config = _inside_project(project, str(voice["config"]))
            shot_duration = float(shot["duration_seconds"])
            line_start = float(line.get("start_seconds", 0.0))
            line_end = float(line.get("end_seconds", shot_duration))
            if line_start < 0 or line_end <= line_start or line_end > shot_duration + 0.001:
                errors.append(f"{shot.get('id')} line {line_index}: invalid dialogue timing")
                continue
            safe_speaker = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in speaker)
            filename = f"{shot.get('id', 'shot')}_{safe_speaker}_{line_index:02d}.wav"
            output = output_dir / filename
            command = [str(binary), "--model", str(model), "--output_file", str(output)]
            if voice_config:
                command.extend(["--config", str(voice_config)])
            result = subprocess.run(command, input=text, capture_output=True, text=True, check=False)
            if result.returncode:
                errors.append(f"{shot.get('id')} line {line_index}: Piper failed: {result.stderr[-1000:]}")
                continue
            try:
                duration = _wav_duration(output)
            except Exception as exc:
                errors.append(f"{shot.get('id')} line {line_index}: invalid Piper WAV: {exc}")
                continue
            slot = line_end - line_start
            if duration > slot + 0.08:
                errors.append(
                    f"{shot.get('id')} line {line_index}: generated speech is {duration:.2f}s "
                    f"but dialogue slot is only {slot:.2f}s; extend the line timing or use a faster voice rate"
                )
                continue
            clips.append({
                "file": str(output.relative_to(project)).replace("\\", "/"),
                "start_seconds": round(shot_start + line_start, 4),
                "end_seconds": round(shot_start + line_start + duration, 4),
                "speaker": speaker,
            })
            line_count += 1
        shot_start += float(shot["duration_seconds"])

    report = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "generated_lines": line_count,
        "clips": clips,
        "errors": errors,
        "status": "failed" if errors else "passed",
        "note": "Piper is local TTS; speech quality and Algerian dialect accuracy depend on the supplied voice model.",
    }
    report_path = project / "production" / "voice_generation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("Dialogue voice generation blocked: " + "; ".join(errors))
    mix_plan = {
        "tracks": [{"name": "dialogue", "gain_db": 0, "clips": [
            {key: value for key, value in clip.items() if key != "speaker"} for clip in clips
        ]}]
    }
    mix_path = project / "production" / "audio_mix.generated.json"
    mix_path.write_text(json.dumps(mix_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mix_path
