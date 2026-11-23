"""Deterministic director pass: turns approved story beats into editable shot plans."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BEAT_PERFORMANCES = {
    "cold_open": ("surprised", "think", "listen", "listen"),
    "setup": ("walk", "talk", "wait", "listen"),
    "inciting_incident": ("surprised", "point", "disagree", "listen"),
    "reaction": ("think", "explain", "listen", "agree"),
    "escalation": ("run", "dodge", "surprised", "surprised"),
    "turning_point": ("think", "explain", "listen", "agree"),
    "payoff": ("celebrate_small", "agree", "laugh", "celebrate"),
    "cliffhanger": ("think", "surprised", "wait", "listen"),
}

CAMERAS = {
    "cold_open": {"zoom": 1.08},
    "setup": {"move": {"from": {"x": 0, "y": 0, "zoom": 1.0}, "to": {"x": -12, "y": 0, "zoom": 1.025}}},
    "inciting_incident": {"zoom": 1.12},
    "reaction": {"zoom": 1.06},
    "escalation": {"move": {"from": {"x": 0, "y": 0, "zoom": 1.0}, "to": {"x": 16, "y": -8, "zoom": 1.08}}},
    "turning_point": {"zoom": 1.1},
    "payoff": {"zoom": 1.04},
    "cliffhanger": {"zoom": 1.14},
}

def _segments(duration: float, first: str, second: str) -> list[dict[str, Any]]:
    split = round(duration * 0.42, 3)
    if split <= 0 or split >= duration:
        return [{"start": 0.0, "end": duration, "action": first}]
    return [
        {"start": 0.0, "end": split, "action": first},
        {"start": split, "end": duration, "action": second, "transition_seconds": min(0.25, duration * 0.08)},
    ]

def build_storyboard(project_dir: Path, outline_path: Path | None = None) -> Path:
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    if outline_path is None:
        candidates = sorted((project_dir / "production" / "story").glob("episode-*-outline.json"))
        if not candidates:
            raise FileNotFoundError("No story outline found. Run 'story-next' first.")
        outline_path = candidates[-1]
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    beats = outline.get("beats")
    if not isinstance(beats, list) or not beats:
        raise ValueError("Story outline has no beats")
    characters = [item for item in episode.get("characters", []) if isinstance(item, dict) and item.get("id")]
    if not characters:
        raise ValueError("Episode has no characters")
    actor_ids = [item["id"] for item in characters]
    locations = [item.get("id") for item in episode.get("locations", []) if isinstance(item, dict) and item.get("id")]
    default_location = locations[0] if locations else None
    shots = []
    elapsed = 0.0
    for index, beat in enumerate(beats, start=1):
        beat_type = str(beat.get("type", "setup"))
        duration = float(beat.get("duration_seconds", 0))
        if duration <= 0:
            raise ValueError(f"Beat {beat.get('id', index)} has invalid duration")
        performance = BEAT_PERFORMANCES.get(beat_type, ("talk", "think", "listen", "agree"))
        main_first, main_second, support_first, support_second = performance
        tracks: dict[str, list[dict[str, Any]]] = {
            actor_ids[0]: _segments(duration, main_first, main_second)
        }
        if len(actor_ids) > 1:
            tracks[actor_ids[1]] = _segments(duration, support_first, support_second)
        # Remaining cast members are staged as listeners; the screenwriter can reassign them.
        for actor_id in actor_ids[2:]:
            tracks[actor_id] = [{"start": 0.0, "end": duration, "action": "listen"}]
        shots.append({
            "id": f"{outline.get('episode_id', 'episode')}-shot-{index:02d}",
            "beat_id": beat.get("id"),
            "beat_type": beat_type,
            "duration_seconds": duration,
            "start_seconds": round(elapsed, 3),
            "location": default_location,
            "actors": actor_ids,
            "action": main_first,
            "camera": CAMERAS.get(beat_type, {"zoom": 1.0}),
            "motion_tracks": tracks,
            "dialogue": [],
            "editorial_notes": beat.get("writer_instruction", ""),
            "dialogue_status": "needs_algerian_arabic_script_and_voice_recording",
            "review_required": ["dialogue", "staging", "character_intent", "camera", "continuity"],
        })
        elapsed += duration
    expected = float(episode.get("format", {}).get("duration_seconds", 100))
    if abs(elapsed - expected) > 0.01:
        raise ValueError(f"Outline totals {elapsed:g}s, but episode format requires {expected:g}s")
    result = {
        "schema_version": 1,
        "episode_id": episode.get("id"),
        "outline_file": str(outline_path),
        "target_duration_seconds": expected,
        "total_duration_seconds": round(elapsed, 3),
        "shot_count": len(shots),
        "status": "director_blocking_pass_needs_screenwriter_and_director_review",
        "automation_note": "This is a first-pass editable storyboard, not a finished screenplay or approved animation.",
        "shots": shots,
    }
    out_dir = project_dir / "production" / "story"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{outline.get('episode_id', 'episode')}-storyboard.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
