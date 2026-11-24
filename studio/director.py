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
    "cold_open": {"shot_size": "close_up", "zoom": 1.16, "focus": "protagonist"},
    "setup": {"shot_size": "wide", "move": {"from": {"x": 0, "y": 0, "zoom": 0.96}, "to": {"x": 0, "y": 0, "zoom": 1.0}}},
    "inciting_incident": {"shot_size": "close_up", "zoom": 1.18, "focus": "protagonist"},
    "reaction": {"shot_size": "medium", "zoom": 1.08, "focus": "supporting_character"},
    "escalation": {"shot_size": "dynamic", "move": {"from": {"x": -18, "y": 0, "zoom": 1.0}, "to": {"x": 24, "y": -10, "zoom": 1.12}}},
    "turning_point": {"shot_size": "close_up", "zoom": 1.17, "focus": "protagonist"},
    "payoff": {"shot_size": "medium_wide", "zoom": 1.02, "focus": "group"},
    "cliffhanger": {"shot_size": "close_up", "zoom": 1.2, "focus": "protagonist"},
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
    fmt = episode.get("format", {})
    frame_width = int(fmt.get("width", 1080))
    frame_height = int(fmt.get("height", 1920))
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
        camera = dict(CAMERAS.get(beat_type, {"shot_size": "medium", "zoom": 1.0}))
        focus_role = camera.get("focus")
        focus_actor = actor_ids[0] if focus_role == "protagonist" else (
            actor_ids[1] if focus_role == "supporting_character" and len(actor_ids) > 1 else None
        )
        if focus_actor:
            focus_index = actor_ids.index(focus_actor)
            focus_x = frame_width * (0.32 if len(actor_ids) > 1 and focus_index == 0 else
                                     0.68 if len(actor_ids) > 1 else 0.5)
            camera["x"] = frame_width * 0.5 - focus_x
        positions = {
            actor_id: {
                "x": frame_width * (0.32 if len(actor_ids) > 1 and actor_index == 0 else
                                     0.68 if len(actor_ids) > 1 else 0.5),
                "y": frame_height * 0.78,
            }
            for actor_index, actor_id in enumerate(actor_ids)
        }
        shots.append({
            "id": f"{outline.get('episode_id', 'episode')}-shot-{index:02d}",
            "beat_id": beat.get("id"),
            "beat_type": beat_type,
            "duration_seconds": duration,
            "start_seconds": round(elapsed, 3),
            "location": default_location,
            "actors": actor_ids,
            "action": main_first,
            "camera": camera,
            "shot_size": camera.get("shot_size", "medium"),
            "focus_actor": focus_actor or actor_ids[0],
            "cut_reason": beat.get("writer_instruction", ""),
            "transition_out": "cut",
            "positions": positions,
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
