"""Optional Rhubarb Lip Sync adapter.

Rhubarb is an external executable (not a pip package). This module converts its
mouth-cue JSON into the renderer's normalized viseme timeline. It never invents
cues when the executable or audio is unavailable.
"""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
from typing import Any

RHUBARB_TO_STUDIO = {"X":"REST","A":"A","B":"CLOSED","C":"E","D":"E","E":"A","F":"O","G":"U","H":"SMILE"}

def convert_rhubarb_data(data: dict[str, Any], *, offset: float = 0.0) -> list[dict[str, Any]]:
    cues = data.get("mouthCues")
    if not isinstance(cues, list):
        raise ValueError("Rhubarb JSON must contain a mouthCues array")
    result = []
    for cue in cues:
        if not isinstance(cue, dict) or "start" not in cue or "value" not in cue:
            raise ValueError("Invalid Rhubarb mouth cue")
        shape = RHUBARB_TO_STUDIO.get(str(cue["value"]).upper())
        if shape is None:
            raise ValueError(f"Unsupported Rhubarb mouth shape: {cue['value']}")
        result.append({"at": round(max(0.0, float(cue["start"]) + offset), 4), "shape": shape})
    return sorted(result, key=lambda item: item["at"])

def generate_visemes(audio_path: Path, output_path: Path, *, speaker: str,
                     line_start: float = 0.0, executable: str = "rhubarb",
                     dialog_file: Path | None = None) -> list[dict[str, Any]]:
    binary = shutil.which(executable) if not Path(executable).is_file() else executable
    if not binary:
        raise RuntimeError("Rhubarb Lip Sync was not found. Install it and add 'rhubarb' to PATH.")
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(binary), "-f", "json", "-o", str(output_path), str(audio_path)]
    if dialog_file:
        if not dialog_file.is_file():
            raise FileNotFoundError(dialog_file)
        command.extend(["-d", str(dialog_file)])
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(f"Rhubarb failed ({completed.returncode}): {completed.stderr.strip()}")
    return convert_rhubarb_data(json.loads(output_path.read_text(encoding="utf-8")), offset=line_start)

def attach_visemes(episode: dict[str, Any], *, shot_id: str, speaker: str,
                   cues: list[dict[str, Any]]) -> None:
    for shot in episode.get("shots", []):
        if shot.get("id") == shot_id:
            for line in shot.get("dialogue", []):
                if line.get("speaker") == speaker:
                    line["visemes"] = cues
                    return
            raise ValueError(f"Speaker {speaker!r} has no dialogue line in shot {shot_id!r}")
    raise ValueError(f"Unknown shot: {shot_id}")
