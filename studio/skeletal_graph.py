"""Named-joint skeleton graph and pose utilities.

The data model is a Python runtime adapter informed by Skele2D's MIT-licensed
Structure/BoneStructure/Pose model. The upstream CoffeeScript reference is kept
under vendor/skele2d-reference with its original license. This module is a
separate implementation, not a translated or copied source file.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class Pose:
    points: dict[str, dict[str, float]]

    def __post_init__(self) -> None:
        clean: dict[str, dict[str, float]] = {}
        for name, point in self.points.items():
            x, y = float(point["x"]), float(point["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"Pose point {name!r} must contain finite coordinates")
            clean[str(name)] = {"x": x, "y": y}
        object.__setattr__(self, "points", clean)

    @staticmethod
    def lerp(a: "Pose", b: "Pose", amount: float) -> "Pose":
        if set(a.points) != set(b.points):
            raise ValueError("Cannot interpolate poses with different joint names")
        t = min(1.0, max(0.0, float(amount)))
        return Pose({
            name: {
                "x": p["x"] + (b.points[name]["x"] - p["x"]) * t,
                "y": p["y"] + (b.points[name]["y"] - p["y"]) * t,
            }
            for name, p in a.points.items()
        })

    @staticmethod
    def loop(frames: list["Pose"], soft_index: float) -> "Pose":
        if not frames:
            raise ValueError("At least one pose frame is required")
        if len(frames) == 1:
            return frames[0]
        wrapped = float(soft_index) % len(frames)
        left = int(math.floor(wrapped))
        right = (left + 1) % len(frames)
        return Pose.lerp(frames[left], frames[right], wrapped - left)

    def flipped(self, *, horizontal: bool = False, vertical: bool = False,
                center_x: float = 0.0, center_y: float = 0.0) -> "Pose":
        return Pose({
            name: {
                "x": 2.0 * center_x - point["x"] if horizontal else point["x"],
                "y": 2.0 * center_y - point["y"] if vertical else point["y"],
            }
            for name, point in self.points.items()
        })


class SkeletonGraph:
    """Serializable named joints and directed bone segments."""

    def __init__(self, points: dict[str, dict[str, float]],
                 segments: dict[str, dict[str, Any]]) -> None:
        self.points = Pose(points).points
        self.segments: dict[str, dict[str, Any]] = {}
        for name, segment in segments.items():
            start, end = str(segment["from"]), str(segment["to"])
            if start not in self.points or end not in self.points:
                raise ValueError(f"Segment {name!r} references a missing joint")
            if start == end:
                raise ValueError(f"Segment {name!r} cannot connect a joint to itself")
            self.segments[str(name)] = {
                **{k: v for k, v in segment.items() if k not in {"from", "to"}},
                "from": start, "to": end,
            }

    @classmethod
    def from_rig(cls, joints: dict[str, list[float]],
                 bones: list[dict[str, str]]) -> "SkeletonGraph":
        points = {
            name: {"x": float(value[0]), "y": float(value[1])}
            for name, value in joints.items()
        }
        segments = {
            bone["name"]: {"from": bone["parent"], "to": bone["child"]}
            for bone in bones
        }
        return cls(points, segments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": {name: dict(point) for name, point in self.points.items()},
            "segments": {name: dict(segment) for name, segment in self.segments.items()},
        }

    def pose(self) -> Pose:
        return Pose(self.points)

    def set_pose(self, pose: Pose) -> None:
        if set(pose.points) != set(self.points):
            raise ValueError("Pose joint names do not match this skeleton")
        self.points = Pose(pose.points).points
