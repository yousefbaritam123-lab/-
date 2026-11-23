"""Reusable motion catalogue and deterministic shot-track resolver."""
from __future__ import annotations

from typing import Any

BUILTIN_MOTIONS: dict[str, dict[str, Any]] = {
    "stand": {"base_action": "idle", "tags": ["neutral", "standing"]},
    "walk": {"base_action": "walk", "tags": ["locomotion", "travel"]},
    "run": {"base_action": "run", "tags": ["locomotion", "urgent"]},
    "greet": {"base_action": "wave", "tags": ["social", "friendly"]},
    "wave": {"base_action": "wave", "tags": ["social", "friendly"]},
    "talk": {"base_action": "talk", "tags": ["dialogue"]},
    "explain": {"base_action": "talk", "tags": ["dialogue", "gesture"], "pose": {"left_arm": -48, "left_elbow": 28, "right_arm": 54, "right_elbow": -24, "right_hand_spread": 0.8}},
    "listen": {"base_action": "idle", "tags": ["dialogue", "reaction"], "pose": {"head": 5, "gaze_x": -0.15, "right_arm": 12, "right_elbow": -28}},
    "think": {"base_action": "think", "tags": ["emotion", "thinking"]},
    "shrug": {"base_action": "surprised", "tags": ["gesture", "uncertain"], "pose": {"left_arm": -72, "right_arm": 72, "left_elbow": 25, "right_elbow": -25}},
    "point": {"base_action": "point", "tags": ["gesture", "direction"]},
    "agree": {"base_action": "wave", "tags": ["reaction", "positive"], "pose": {"head": 8, "right_arm": 30, "right_elbow": -15}},
    "disagree": {"base_action": "sad", "tags": ["reaction", "negative"], "pose": {"head": -18, "gaze_x": -0.3}},
    "laugh": {"base_action": "celebrate", "tags": ["emotion", "comedy"], "pose": {"head": 8, "mouth": 1, "emotion": 0.8}},
    "celebrate": {"base_action": "celebrate", "tags": ["emotion", "positive"]},
    "sad": {"base_action": "sad", "tags": ["emotion", "negative"]},
    "surprised": {"base_action": "surprised", "tags": ["emotion", "reaction"]},
    "jump": {"base_action": "jump", "tags": ["action", "physical"]},
    "dodge": {"base_action": "dodge", "tags": ["action", "physical"]},
    "hit_react": {"base_action": "impact_react", "tags": ["action", "reaction"]},
    "kick": {"base_action": "kick", "tags": ["action", "physical"]},
    "apologize": {"base_action": "sad", "tags": ["social", "emotion"], "pose": {"head": -15, "left_arm": -8, "right_arm": 8}},
    "wait": {"base_action": "idle", "tags": ["neutral", "standing"], "pose": {"gaze_x": 0.25}},
    "sneak": {"base_action": "walk", "tags": ["locomotion", "stealth"], "pose": {"torso": 12, "head": -8, "left_arm": -12, "right_arm": 12}},
    "celebrate_small": {"base_action": "wave", "tags": ["emotion", "positive"], "pose": {"right_arm": 80, "right_elbow": -35, "mouth": 1}},
}


def motion_definition(name: str, library: dict[str, Any] | None = None) -> dict[str, Any]:
    custom = (library or {}).get("motions", {})
    return dict(custom.get(name) or BUILTIN_MOTIONS.get(name) or {"base_action": name, "tags": []})


def resolve_motion(name: str, library: dict[str, Any] | None = None) -> tuple[str, dict[str, float]]:
    definition = motion_definition(name, library)
    return str(definition.get("base_action", name)), {
        str(key): float(value) for key, value in definition.get("pose", {}).items()
    }


def active_track_segment(track: list[dict[str, Any]], time_s: float) -> tuple[dict[str, Any] | None, float]:
    """Return the active segment and its local clock; tracks are random-access safe."""
    if not track:
        return None, time_s
    ordered = sorted(track, key=lambda item: float(item["start"]))
    for segment in ordered:
        start, end = float(segment["start"]), float(segment["end"])
        if start <= time_s < end:
            return segment, time_s - start
    if time_s < float(ordered[0]["start"]):
        return None, time_s
    last = ordered[-1]
    return last, max(0.0, float(last["end"]) - float(last["start"]))


def validate_motion_track(track: list[dict[str, Any]], shot_duration: float) -> list[str]:
    errors: list[str] = []
    previous_end = 0.0
    for index, segment in enumerate(sorted(track, key=lambda item: float(item.get("start", 0)))):
        try:
            start, end = float(segment["start"]), float(segment["end"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"motion track segment {index} needs numeric start and end")
            continue
        if start < 0 or end <= start or end > shot_duration + 1e-6:
            errors.append(f"motion track segment {index} has invalid time range")
        if start < previous_end - 1e-6:
            errors.append(f"motion track segment {index} overlaps the previous segment")
        if not segment.get("action"):
            errors.append(f"motion track segment {index} needs an action")
        previous_end = max(previous_end, end)
    return errors
