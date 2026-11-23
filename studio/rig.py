"""Keyframed 2D character rig runtime.

Angles are degrees. The pose is evaluated deterministically from clip time;
the renderer consumes joint transforms rather than hard-coded limb endpoints.
"""
from __future__ import annotations

import math
from typing import Any

POSE_KEYS = (
    "root_y", "torso", "head", "left_arm", "left_elbow",
    "right_arm", "right_elbow", "left_leg", "left_knee",
    "right_leg", "right_knee", "mouth", "brow",
)

DEFAULT_CLIPS: dict[str, dict[str, Any]] = {
    "idle": {"duration": 2.0, "loop": True, "keyframes": [
        {"at": 0.0, "pose": {"root_y": 0, "torso": 0, "head": 0, "left_arm": -22, "left_elbow": 8, "right_arm": 22, "right_elbow": -8, "left_leg": -5, "left_knee": 2, "right_leg": 5, "right_knee": -2, "mouth": 0, "brow": 0}},
        {"at": 0.5, "pose": {"root_y": -5, "torso": -1, "head": 1, "left_arm": -20, "left_elbow": 10, "right_arm": 20, "right_elbow": -10, "left_leg": -5, "left_knee": 2, "right_leg": 5, "right_knee": -2, "mouth": 0, "brow": 0}},
        {"at": 1.0, "pose": {"root_y": 0, "torso": 0, "head": 0, "left_arm": -22, "left_elbow": 8, "right_arm": 22, "right_elbow": -8, "left_leg": -5, "left_knee": 2, "right_leg": 5, "right_knee": -2, "mouth": 0, "brow": 0}},
    ]},
    "walk": {"duration": 0.8, "loop": True, "keyframes": [
        {"at": 0.0, "pose": {"root_y": 0, "torso": -5, "head": 2, "left_arm": -42, "left_elbow": 8, "right_arm": 42, "right_elbow": -8, "left_leg": -28, "left_knee": 8, "right_leg": 28, "right_knee": -8, "mouth": 0, "brow": 0}},
        {"at": 0.25, "pose": {"root_y": -12, "torso": -4, "head": 1, "left_arm": -5, "left_elbow": 12, "right_arm": 5, "right_elbow": -12, "left_leg": 8, "left_knee": 22, "right_leg": -8, "right_knee": -3, "mouth": 0, "brow": 0}},
        {"at": 0.5, "pose": {"root_y": 0, "torso": -5, "head": 2, "left_arm": 42, "left_elbow": -8, "right_arm": -42, "right_elbow": 8, "left_leg": 28, "left_knee": -8, "right_leg": -28, "right_knee": 8, "mouth": 0, "brow": 0}},
        {"at": 0.75, "pose": {"root_y": -12, "torso": -4, "head": 1, "left_arm": 5, "left_elbow": -12, "right_arm": -5, "right_elbow": 12, "left_leg": -8, "left_knee": -3, "right_leg": 8, "right_knee": 22, "mouth": 0, "brow": 0}},
        {"at": 1.0, "pose": {"root_y": 0, "torso": -5, "head": 2, "left_arm": -42, "left_elbow": 8, "right_arm": 42, "right_elbow": -8, "left_leg": -28, "left_knee": 8, "right_leg": 28, "right_knee": -8, "mouth": 0, "brow": 0}},
    ]},
    "run": {"duration": 0.48, "loop": True, "keyframes": [
        {"at": 0.0, "pose": {"root_y": 0, "torso": -18, "head": 8, "left_arm": -65, "left_elbow": 24, "right_arm": 62, "right_elbow": -22, "left_leg": -48, "left_knee": 28, "right_leg": 42, "right_knee": -18, "mouth": 1, "brow": 1}},
        {"at": 0.25, "pose": {"root_y": -38, "torso": -18, "head": 7, "left_arm": -12, "left_elbow": 38, "right_arm": 12, "right_elbow": -38, "left_leg": 15, "left_knee": 42, "right_leg": -18, "right_knee": 25, "mouth": 1, "brow": 1}},
        {"at": 0.5, "pose": {"root_y": 0, "torso": -18, "head": 8, "left_arm": 62, "left_elbow": -22, "right_arm": -65, "right_elbow": 24, "left_leg": 42, "left_knee": -18, "right_leg": -48, "right_knee": 28, "mouth": 1, "brow": 1}},
        {"at": 0.75, "pose": {"root_y": -38, "torso": -18, "head": 7, "left_arm": 12, "left_elbow": -38, "right_arm": -12, "right_elbow": 38, "left_leg": -18, "left_knee": 25, "right_leg": 15, "right_knee": 42, "mouth": 1, "brow": 1}},
        {"at": 1.0, "pose": {"root_y": 0, "torso": -18, "head": 8, "left_arm": -65, "left_elbow": 24, "right_arm": 62, "right_elbow": -22, "left_leg": -48, "left_knee": 28, "right_leg": 42, "right_knee": -18, "mouth": 1, "brow": 1}},
    ]},
    "wave": {"duration": 1.2, "loop": False, "keyframes": [
        {"at": 0, "pose": {"right_arm": 22, "right_elbow": -8}},
        {"at": .25, "pose": {"right_arm": 145, "right_elbow": -75, "head": -3}},
        {"at": .5, "pose": {"right_arm": 145, "right_elbow": -92, "head": 2}},
        {"at": .75, "pose": {"right_arm": 145, "right_elbow": -75, "head": -2}},
        {"at": 1, "pose": {"right_arm": 22, "right_elbow": -8, "head": 0}},
    ]},
    "talk": {"duration": 1.0, "loop": True, "keyframes": [
        {"at": 0, "pose": {"mouth": 0, "head": 0, "right_arm": 24, "right_elbow": -10}},
        {"at": .25, "pose": {"mouth": 1, "head": 2, "right_arm": 38, "right_elbow": -20}},
        {"at": .5, "pose": {"mouth": 0, "head": 0, "right_arm": 18, "right_elbow": -4}},
        {"at": .75, "pose": {"mouth": 1, "head": -2, "right_arm": 48, "right_elbow": -28}},
        {"at": 1, "pose": {"mouth": 0, "head": 0, "right_arm": 24, "right_elbow": -10}},
    ]},
    "jump": {"duration": .9, "loop": False, "keyframes": [
        {"at": 0, "pose": {"root_y": 0, "left_leg": -5, "right_leg": 5}},
        {"at": .2, "pose": {"root_y": 22, "torso": 4, "left_leg": -24, "right_leg": 24, "left_knee": 35, "right_knee": -35}},
        {"at": .55, "pose": {"root_y": -145, "torso": -4, "left_arm": -95, "right_arm": 95, "left_leg": -28, "right_leg": 28, "left_knee": 24, "right_knee": -24}},
        {"at": .78, "pose": {"root_y": 18, "torso": 3, "left_leg": -8, "right_leg": 8, "left_knee": 18, "right_knee": -18}},
        {"at": 1, "pose": {"root_y": 0, "torso": 0, "left_arm": -22, "right_arm": 22, "left_leg": -5, "right_leg": 5, "left_knee": 0, "right_knee": 0}},
    ]},
    "dodge": {"duration": .72, "loop": False, "keyframes": [
        {"at": 0, "pose": {"torso": 0, "head": 0}},
        {"at": .3, "pose": {"torso": 42, "head": -12, "root_y": -18, "left_arm": -85, "right_arm": 80}},
        {"at": .62, "pose": {"torso": 18, "head": -5, "root_y": -8}},
        {"at": 1, "pose": {"torso": 0, "head": 0, "root_y": 0}},
    ]},
    "impact_react": {"duration": .62, "loop": False, "keyframes": [
        {"at": 0, "pose": {"torso": 0, "head": 0}},
        {"at": .18, "pose": {"torso": -28, "head": 22, "root_y": 12, "left_arm": -105, "right_arm": 105}},
        {"at": .48, "pose": {"torso": 12, "head": -8, "root_y": -8}},
        {"at": 1, "pose": {"torso": 0, "head": 0, "root_y": 0, "left_arm": -22, "right_arm": 22}},
    ]},
}


def _mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _ease(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def sample_motion(action: str, time_s: float, library: dict[str, Any] | None = None) -> dict[str, float]:
    clips = (library or {}).get("clips", {})
    clip = clips.get(action) or DEFAULT_CLIPS.get(action) or DEFAULT_CLIPS["idle"]
    duration = max(float(clip.get("duration", 1.0)), 0.001)
    loop = bool(clip.get("loop", False))
    phase = (time_s % duration) / duration if loop else min(max(time_s / duration, 0.0), 1.0)
    frames = clip.get("keyframes") or DEFAULT_CLIPS.get(action, DEFAULT_CLIPS["idle"])["keyframes"]
    frames = sorted(frames, key=lambda item: float(item["at"]))
    if phase <= float(frames[0]["at"]):
        left = right = frames[0]
        local = 0.0
    elif phase >= float(frames[-1]["at"]):
        left = right = frames[-1]
        local = 0.0
    else:
        left, right = frames[0], frames[-1]
        for a, b in zip(frames, frames[1:]):
            if float(a["at"]) <= phase <= float(b["at"]):
                left, right = a, b
                break
        span = max(float(right["at"]) - float(left["at"]), 1e-9)
        local = _ease((phase - float(left["at"])) / span)
    lp, rp = left.get("pose", {}), right.get("pose", {})
    result = {key: 0.0 for key in POSE_KEYS}
    for key in POSE_KEYS:
        result[key] = _mix(float(lp.get(key, 0.0)), float(rp.get(key, 0.0)), local)
    return result


def _point(origin: tuple[float, float], length: float, angle: float, upward: bool = False) -> tuple[float, float]:
    radians = math.radians(angle)
    direction = -1.0 if upward else 1.0
    return origin[0] + math.sin(radians) * length, origin[1] + direction * math.cos(radians) * length


def build_skeleton(pose: dict[str, float], proportions: dict[str, float] | None = None) -> dict[str, tuple[float, float]]:
    p = proportions or {}
    length = lambda key, base: base * float(p.get(key, 1.0))
    hip = (0.0, 0.0)
    torso_angle = float(pose.get("torso", 0.0))
    chest = _point(hip, length("torso", 175), torso_angle, upward=True)
    neck = _point(chest, 34, torso_angle, upward=True)
    head = _point(neck, 75 * float(p.get("head", 1.0)), float(pose.get("head", 0.0)) + torso_angle, upward=True)
    shoulders = {
        "left_shoulder": (chest[0] - 48, chest[1] + 10),
        "right_shoulder": (chest[0] + 48, chest[1] + 10),
    }
    joints = {"hip": hip, "chest": chest, "neck": neck, "head": head, **shoulders}
    for side in ("left", "right"):
        sign = -1 if side == "left" else 1
        shoulder = joints[f"{side}_shoulder"]
        arm = float(pose.get(f"{side}_arm", sign * 22)) + torso_angle
        elbow_angle = arm + float(pose.get(f"{side}_elbow", sign * 8))
        elbow = _point(shoulder, length("upper_arm", 92), arm)
        hand = _point(elbow, length("forearm", 78), elbow_angle)
        leg = float(pose.get(f"{side}_leg", sign * 5))
        knee_angle = leg + float(pose.get(f"{side}_knee", 0.0))
        knee = _point(hip, length("thigh", 105), leg)
        foot = _point(knee, length("shin", 100), knee_angle)
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_hand"] = hand
        joints[f"{side}_knee"] = knee
        joints[f"{side}_foot"] = foot
    return joints
