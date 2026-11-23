"""Small, dependency-free project model and validation helpers."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from .motion_library import validate_motion_track


REQUIRED_EPISODE_KEYS = {"id", "title", "language", "format", "characters", "locations", "shots"}
REQUIRED_FORMAT = {"fps": 30}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def validate_episode(project_dir: Path) -> list[str]:
    errors: list[str] = []
    episode_path = project_dir / "episode.json"
    try:
        doc = read_json(episode_path)
    except ValueError as exc:
        return [str(exc)]

    missing = sorted(REQUIRED_EPISODE_KEYS - set(doc))
    if missing:
        errors.append("Missing episode keys: " + ", ".join(missing))

    fmt = doc.get("format", {})
    if not isinstance(fmt, dict):
        errors.append("format must be an object")
    else:
        for key, expected in REQUIRED_FORMAT.items():
            if fmt.get(key) != expected:
                errors.append(f"format.{key} must be {expected}")
        width, height = fmt.get("width"), fmt.get("height")
        if not isinstance(width, int) or width < 240:
            errors.append("format.width must be an integer >= 240")
        if not isinstance(height, int) or height < 426:
            errors.append("format.height must be an integer >= 426")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            if abs((width / height) - (9 / 16)) > 0.002:
                errors.append("format must use a 9:16 portrait aspect ratio")
        duration = fmt.get("duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            errors.append("format.duration_seconds must be a positive number")

    chars = doc.get("characters", [])
    if not isinstance(chars, list):
        errors.append("characters must be an array")
        chars = []
    char_ids = [c.get("id") for c in chars if isinstance(c, dict)]
    if len(char_ids) != len(set(char_ids)):
        errors.append("Character IDs must be unique")
    known_chars = set(char_ids)
    for index, char in enumerate(chars):
        if not isinstance(char, dict) or not char.get("id") or not char.get("name"):
            errors.append(f"characters[{index}] needs id and name")

    locations = doc.get("locations", [])
    if not isinstance(locations, list):
        errors.append("locations must be an array")
        locations = []
    location_ids = [x.get("id") for x in locations if isinstance(x, dict)]
    if len(location_ids) != len(set(location_ids)):
        errors.append("Location IDs must be unique")

    shots = doc.get("shots", [])
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a non-empty array")
        shots = []
    total = 0.0
    shot_ids: set[str] = set()
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}] must be an object")
            continue
        sid = shot.get("id")
        if not sid:
            errors.append(f"shots[{index}] needs an id")
        elif sid in shot_ids:
            errors.append(f"Duplicate shot id: {sid}")
        shot_ids.add(sid)
        duration = shot.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(f"shots[{index}].duration_seconds must be positive")
        else:
            total += duration
        for actor in shot.get("actors", []):
            if actor not in known_chars:
                errors.append(f"shots[{index}] references unknown character '{actor}'")
        motion_tracks = shot.get("motion_tracks", {})
        if not isinstance(motion_tracks, dict):
            errors.append(f"shots[{index}].motion_tracks must be an object keyed by character id")
        else:
            for actor_id, track in motion_tracks.items():
                if actor_id not in known_chars:
                    errors.append(f"shots[{index}].motion_tracks references unknown character '{actor_id}'")
                if actor_id not in shot.get("actors", []):
                    errors.append(f"shots[{index}].motion_tracks actor '{actor_id}' is not in shot.actors")
                if not isinstance(track, list):
                    errors.append(f"shots[{index}].motion_tracks.{actor_id} must be an array")
                else:
                    errors.extend(
                        f"shots[{index}].motion_tracks.{actor_id}: {message}"
                        for message in validate_motion_track(track, float(duration) if isinstance(duration, (int, float)) else 0.0)
                    )
        dialogue = shot.get("dialogue", [])
        for line_no, line in enumerate(dialogue):
            if not isinstance(line, dict) or line.get("speaker") not in known_chars:
                errors.append(f"shots[{index}].dialogue[{line_no}] has an unknown speaker")

    expected_duration = fmt.get("duration_seconds", 100) if isinstance(fmt, dict) else 100
    if shots and abs(total - expected_duration) > 0.01:
        errors.append(f"Shot durations total {total:g}s; expected {expected_duration}s")
    return errors
