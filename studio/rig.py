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
    "right_leg", "right_knee", "left_wrist", "right_wrist",
    "left_hand_spread", "right_hand_spread", "left_foot_angle", "right_foot_angle",
    "left_thumb_curl", "left_index_curl", "left_middle_curl", "left_ring_curl", "left_little_curl",
    "right_thumb_curl", "right_index_curl", "right_middle_curl", "right_ring_curl", "right_little_curl",
    "gaze_x", "gaze_y", "blink", "mouth", "brow", "emotion",
    "left_hand_target_x", "left_hand_target_y", "right_hand_target_x", "right_hand_target_y",
    "left_ankle_target_x", "left_ankle_target_y", "right_ankle_target_x", "right_ankle_target_y",
    "left_ik_bend", "right_ik_bend", "mouth_shape",
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
    "kick": {"duration": 0.9, "loop": False, "keyframes": [
        {"at": 0.0, "pose": {"root_y": 0, "torso": -3, "head": 1, "left_leg": -5, "left_knee": 2, "right_leg": 5, "right_knee": 0, "left_arm": -22, "right_arm": 22}},
        {"at": 0.22, "pose": {"root_y": -7, "torso": -10, "head": 3, "left_leg": -8, "left_knee": 8, "right_leg": 34, "right_knee": 58, "left_arm": -48, "right_arm": 62, "left_elbow": 22, "right_elbow": -28}},
        {"at": 0.52, "pose": {"root_y": -18, "torso": -15, "head": 5, "left_leg": -12, "left_knee": 12, "right_leg": 72, "right_knee": -12, "left_arm": -68, "right_arm": 88, "left_elbow": 28, "right_elbow": -18}},
        {"at": 0.72, "pose": {"root_y": -8, "torso": 5, "head": -2, "left_leg": -8, "left_knee": 8, "right_leg": 38, "right_knee": 42, "left_arm": -42, "right_arm": 48}},
        {"at": 1.0, "pose": {"root_y": 0, "torso": 0, "head": 0, "left_leg": -5, "left_knee": 2, "right_leg": 5, "right_knee": 0, "left_arm": -22, "right_arm": 22, "left_elbow": 8, "right_elbow": -8}}
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
    "point": {"duration": 0.9, "loop": False, "keyframes": [
        {"at": 0, "pose": {"right_arm": 22, "right_elbow": -8}},
        {"at": 0.35, "pose": {"right_arm": 82, "right_elbow": -12, "right_wrist": 8, "right_hand_spread": 1}},
        {"at": 0.7, "pose": {"right_arm": 82, "right_elbow": -12, "right_wrist": 8, "right_hand_spread": 1, "head": 4, "brow": 0.5}},
        {"at": 1, "pose": {"right_arm": 22, "right_elbow": -8}},
    ]},
    "think": {"duration": 2.0, "loop": True, "keyframes": [
        {"at": 0, "pose": {"right_arm": 35, "right_elbow": -65, "right_wrist": 18, "head": -5, "gaze_x": -0.3, "brow": 0.4, "mouth": 0}},
        {"at": 0.5, "pose": {"right_arm": 40, "right_elbow": -72, "right_wrist": 12, "head": -2, "gaze_x": 0.2, "brow": 0.7, "mouth": 0}},
        {"at": 1, "pose": {"right_arm": 35, "right_elbow": -65, "right_wrist": 18, "head": -5, "gaze_x": -0.3, "brow": 0.4, "mouth": 0}},
    ]},
    "celebrate": {"duration": 1.1, "loop": False, "keyframes": [
        {"at": 0, "pose": {"root_y": 0, "left_arm": -22, "right_arm": 22, "emotion": 0.2}},
        {"at": 0.25, "pose": {"root_y": -35, "left_arm": -145, "right_arm": 145, "left_elbow": 18, "right_elbow": -18, "emotion": 0.9, "mouth": 1}},
        {"at": 0.65, "pose": {"root_y": -22, "left_arm": -138, "right_arm": 138, "emotion": 1, "mouth": 1}},
        {"at": 1, "pose": {"root_y": 0, "left_arm": -22, "right_arm": 22, "emotion": 0.2, "mouth": 0}},
    ]},
    "sad": {"duration": 1.6, "loop": True, "keyframes": [
        {"at": 0, "pose": {"head": -12, "left_arm": -8, "right_arm": 8, "brow": -0.8, "emotion": -0.8, "mouth": 0}},
        {"at": 0.5, "pose": {"head": -10, "left_arm": -5, "right_arm": 5, "brow": -0.6, "emotion": -0.7, "mouth": 0}},
        {"at": 1, "pose": {"head": -12, "left_arm": -8, "right_arm": 8, "brow": -0.8, "emotion": -0.8, "mouth": 0}},
    ]},
    "surprised": {"duration": 0.8, "loop": False, "keyframes": [
        {"at": 0, "pose": {"head": 0, "brow": 0, "mouth": 0}},
        {"at": 0.25, "pose": {"head": -8, "brow": 1.5, "mouth": 1, "emotion": 0.2, "left_arm": -65, "right_arm": 65}},
        {"at": 0.7, "pose": {"head": -5, "brow": 1.2, "mouth": 1, "left_arm": -55, "right_arm": 55}},
        {"at": 1, "pose": {"head": 0, "brow": 0, "mouth": 0}},
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
    neutral = {"left_arm": -22.0, "right_arm": 22.0, "left_leg": -5.0, "right_leg": 5.0}
    result = {key: neutral.get(key, 0.0) for key in POSE_KEYS}
    for key in POSE_KEYS:
        base = neutral.get(key, 0.0)
        result[key] = _mix(float(lp.get(key, base)), float(rp.get(key, base)), local)
    return result


def foot_plant_targets(
    action: str,
    time_s: float,
    proportions: dict[str, float] | None = None,
    *,
    root_dx_since_stance: float = 0.0,
    root_y: float = 0.0,
) -> dict[str, float]:
    """Return IK ankle targets for the support foot of a looping walk/run cycle.

    root_dx_since_stance is actor-root travel since the current stance began,
    expressed in the character's local rig units. The support ankle is held at
    its stance-start world position while the root advances.
    """
    if action not in ("walk", "run"):
        return {}
    clip = DEFAULT_CLIPS[action]
    duration = max(float(clip.get("duration", 1.0)), 1e-6)
    phase = (time_s % duration) / duration
    side = "left" if phase < 0.5 else "right"
    stance_phase = 0.0 if side == "left" else 0.5
    stance_pose = sample_motion(action, stance_phase * duration)
    anchor = build_skeleton(stance_pose, proportions)[f"{side}_foot"]
    target_x = anchor[0] - root_dx_since_stance
    target_y = anchor[1] - root_y
    p = proportions or {}
    max_reach = 105.0 * float(p.get("thigh", 1.0)) + 100.0 * float(p.get("shin", 1.0)) - 0.05
    distance = math.hypot(target_x, target_y)
    adjusted_root_y = root_y
    if distance > max_reach and abs(target_x) < max_reach:
        # Keep the foot planted by limiting body bob before the leg overextends.
        reachable_y = math.sqrt(max_reach * max_reach - target_x * target_x)
        target_y = math.copysign(reachable_y, target_y)
        adjusted_root_y = anchor[1] - target_y
    return {
        f"{side}_ankle_target_x": target_x,
        f"{side}_ankle_target_y": target_y,
        f"{side}_ik_bend": -1.0 if side == "left" else 1.0,
        "root_y": adjusted_root_y,
    }


def blend_motion(
    from_action: str,
    to_action: str,
    time_s: float,
    transition_seconds: float,
    library: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Crossfade two clips over a finite transition window using eased weights."""
    duration = max(float(transition_seconds), 1e-6)
    weight = _ease(_clamp(time_s / duration, 0.0, 1.0))
    source = sample_motion(from_action, time_s, library)
    target = sample_motion(to_action, time_s, library)
    return {key: _mix(source[key], target[key], weight) for key in POSE_KEYS}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def solve_two_bone(
    origin: tuple[float, float],
    target: tuple[float, float],
    upper_length: float,
    lower_length: float,
    bend: float = 1.0,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Solve a planar two-bone limb (shoulder/hip -> elbow/knee -> target)."""
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    distance = math.hypot(dx, dy)
    minimum = abs(upper_length - lower_length) + 1e-6
    maximum = max(minimum, upper_length + lower_length - 1e-6)
    distance = _clamp(distance, minimum, maximum)
    if math.hypot(dx, dy) < 1e-9:
        dx, dy = distance, 0.0
    base_angle = math.atan2(dy, dx)
    # Preserve direction while clamping the end effector to the reachable annulus.
    dx, dy = math.cos(base_angle) * distance, math.sin(base_angle) * distance
    cosine = _clamp((upper_length**2 + distance**2 - lower_length**2) /
                    (2.0 * upper_length * distance), -1.0, 1.0)
    offset = math.acos(cosine) * (1.0 if bend >= 0 else -1.0)
    elbow_angle = base_angle + offset
    elbow = (origin[0] + math.cos(elbow_angle) * upper_length,
             origin[1] + math.sin(elbow_angle) * upper_length)
    end = (origin[0] + dx, origin[1] + dy)
    return elbow, end


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
    limits = (p.get("joint_limits") or {})
    for side in ("left", "right"):
        sign = -1 if side == "left" else 1
        shoulder = joints[f"{side}_shoulder"]
        arm_limit = limits.get("shoulder", [-165, 165])
        elbow_limit = limits.get("elbow", [-145, 145])
        knee_limit = limits.get("knee", [-150, 150])
        arm = _clamp(float(pose.get(f"{side}_arm", sign * 22)) + torso_angle,
                     float(arm_limit[0]), float(arm_limit[1]))
        elbow_delta = _clamp(float(pose.get(f"{side}_elbow", sign * 8)),
                             float(elbow_limit[0]), float(elbow_limit[1]))
        elbow_angle = arm + elbow_delta
        elbow = _point(shoulder, length("upper_arm", 92), arm)
        wrist_delta = _clamp(float(pose.get(f"{side}_wrist", 0.0)), -90.0, 90.0)
        wrist = _point(elbow, length("forearm", 78), elbow_angle)
        target_x = pose.get(f"{side}_hand_target_x")
        target_y = pose.get(f"{side}_hand_target_y")
        if target_x is not None and target_y is not None:
            elbow, wrist = solve_two_bone(
                shoulder, (float(target_x), float(target_y)),
                length("upper_arm", 92), length("forearm", 78),
                bend=float(pose.get(f"{side}_ik_bend", sign)),
            )
            elbow_angle = math.degrees(math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0]))
        hand = _point(wrist, length("hand", 22), elbow_angle + wrist_delta)
        leg = _clamp(float(pose.get(f"{side}_leg", sign * 5)),
                     float(limits.get("hip", [-100, 100])[0]),
                     float(limits.get("hip", [-100, 100])[1]))
        knee_delta = _clamp(float(pose.get(f"{side}_knee", 0.0)),
                            float(knee_limit[0]), float(knee_limit[1]))
        knee_angle = leg + knee_delta
        knee = _point(hip, length("thigh", 105), leg)
        ankle_angle = _clamp(float(pose.get(f"{side}_foot_angle", 0.0)), -65.0, 65.0)
        foot = _point(knee, length("shin", 100), knee_angle)
        ankle_x = pose.get(f"{side}_ankle_target_x")
        ankle_y = pose.get(f"{side}_ankle_target_y")
        if ankle_x is not None and ankle_y is not None:
            knee, foot = solve_two_bone(
                hip, (float(ankle_x), float(ankle_y)),
                length("thigh", 105), length("shin", 100),
                bend=float(pose.get(f"{side}_ik_bend", sign)),
            )
            knee_angle = math.degrees(math.atan2(foot[1] - knee[1], foot[0] - knee[0]))
        toe = _point(foot, length("foot", 38), knee_angle + ankle_angle, upward=False)
        hand_spread = _clamp(float(pose.get(f"{side}_hand_spread", 0.5)), 0.0, 1.0)
        fingers = []
        # Five stylized digits: four-finger fan plus an opposing thumb.
        finger_names = ("index", "middle", "ring", "little")
        for finger_index, finger_name in enumerate(finger_names):
            fan = (finger_index - 1.5) * (6.0 + 9.0 * hand_spread)
            curl = _clamp(float(pose.get(f"{side}_{finger_name}_curl", 0.0)), 0.0, 1.0)
            finger_length = length("finger", 17) * (1.0 - .34 * curl)
            finger_angle = elbow_angle + wrist_delta + fan + curl * 28.0 * sign
            fingers.append(_point(hand, finger_length, finger_angle))
        thumb_curl = _clamp(float(pose.get(f"{side}_thumb_curl", 0.0)), 0.0, 1.0)
        thumb_length = length("finger", 15) * (1.0 - .30 * thumb_curl)
        thumb_angle = elbow_angle + wrist_delta + sign * (48.0 - 25.0 * thumb_curl)
        fingers.append(_point(hand, thumb_length, thumb_angle))
        joints[f"{side}_wrist"] = wrist
        joints[f"{side}_toe"] = toe
        joints[f"{side}_fingers"] = tuple(fingers)
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_hand"] = hand
        joints[f"{side}_knee"] = knee
        joints[f"{side}_foot"] = foot
    return joints



def facial_pose(pose: dict[str, float], time_s: float) -> dict[str, float]:
    """Return deterministic face controls with periodic blinks and gaze defaults."""
    blink = _clamp(float(pose.get("blink", 0.0)), 0.0, 1.0)
    # Short natural blink every ~3.7 seconds; explicit blink keyframes override it.
    phase = (time_s % 3.7)
    if 0.08 <= phase <= 0.22:
        blink = max(blink, math.sin(math.pi * (phase - 0.08) / 0.14))
    emotion = _clamp(float(pose.get("emotion", 0.0)), -1.0, 1.0)
    return {
        "blink": blink,
        "gaze_x": _clamp(float(pose.get("gaze_x", 0.0)), -1.0, 1.0),
        "gaze_y": _clamp(float(pose.get("gaze_y", 0.0)), -1.0, 1.0),
        "brow": _clamp(float(pose.get("brow", 0.0)) + emotion * 0.35, -2.0, 2.0),
        "mouth": _clamp(float(pose.get("mouth", 0.0)), 0.0, 1.0),
        "mouth_shape": _clamp(float(pose.get("mouth_shape", 0.0)), 0.0, 8.0),
        "emotion": emotion,
    }
