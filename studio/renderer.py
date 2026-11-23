"""Deterministic 2D stickman scene renderer using Skia.

The renderer is intentionally data-driven: the same episode JSON and frame time
always produce the same frame. It renders one frame at a time to keep RAM usage low.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    import skia
except ImportError as exc:  # pragma: no cover - depends on local optional runtime
    raise RuntimeError("Skia is required. Install dependencies with: pip install -r requirements.txt") from exc

from .rig import build_skeleton, sample_motion


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smoothstep(value: float) -> float:
    x = clamp(value, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def shot_at(shots: list[dict[str, Any]], time_s: float) -> tuple[dict[str, Any], float]:
    cursor = 0.0
    for shot in shots:
        end = cursor + float(shot["duration_seconds"])
        if time_s < end:
            return shot, time_s - cursor
        cursor = end
    last = shots[-1]
    return last, float(last["duration_seconds"])


def _paint(color: int, width: float = 1.0, style: int | None = None) -> "skia.Paint":
    p = skia.Paint(AntiAlias=True, Color=color, StrokeWidth=width)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if style is not None:
        p.setStyle(style)
    return p


def _color(hex_value: str) -> int:
    value = hex_value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return skia.ColorSetARGB(255, int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _line(canvas: "skia.Canvas", a: tuple[float, float], b: tuple[float, float],
          color: int, width: float) -> None:
    canvas.drawLine(a[0], a[1], b[0], b[1], _paint(color, width))


def _limb(a: tuple[float, float], length: float, angle: float) -> tuple[float, float]:
    rad = math.radians(angle)
    return a[0] + math.cos(rad) * length, a[1] + math.sin(rad) * length


def _draw_character(canvas: "skia.Canvas", actor: dict[str, Any], time_s: float,
                    shot: dict[str, Any], index: int,
                    motion_library: dict[str, Any] | None = None) -> None:
    """Render a layered character from its canonical rig and sampled keyframe pose."""
    x = float(actor.get("x", 420 + index * 360))
    y = float(actor.get("y", 1450))
    scale = float(actor.get("scale", 1.0))
    dialogue_active = any(line.get("speaker") == actor.get("id") for line in shot.get("dialogue", []))
    action = str(actor.get("action", "talk" if dialogue_active else shot.get("action", "idle")))
    rig = actor.get("_rig", {})
    appearance = rig.get("appearance", {})
    proportions = rig.get("proportions", {})
    pose = sample_motion(action, time_s, motion_library)
    for key, value in actor.get("pose", {}).items():
        if key in pose:
            pose[key] = float(value)
    joints = build_skeleton(pose, proportions)

    def point(name: str) -> tuple[float, float]:
        px, py = joints[name]
        return px, py - 180.0

    ink = _color(appearance.get("outline", actor.get("outline", "#171923")))
    skin = _color(appearance.get("skin", actor.get("skin", "#F3D2B2")))
    shirt = _color(appearance.get("shirt", actor.get("shirt", "#E9E6DF")))
    trousers = _color(appearance.get("trousers", actor.get("trousers", "#26364A")))
    shoes = _color(appearance.get("shoes", actor.get("shoes", appearance.get("accent", "#C62828"))))
    accent = _color(appearance.get("accent", actor.get("accent", "#C62828")))
    hair = _color(appearance.get("hair", "#24212A"))
    outline_width = float(rig.get("design_lock", {}).get("outline_width", 7))

    canvas.save()
    canvas.translate(x, y - float(pose.get("root_y", 0.0)))
    canvas.scale(scale, scale)
    if actor.get("flip", False):
        canvas.scale(-1, 1)

    shadow = _paint(skia.ColorSetARGB(52, 0, 0, 0), 1, skia.Paint.kFill_Style)
    canvas.drawOval(skia.Rect.MakeLTRB(-76, -5, 76, 18), shadow)
    hip = point("hip")
    left_knee, left_foot = point("left_knee"), point("left_foot")
    right_knee, right_foot = point("right_knee"), point("right_foot")
    left_shoulder, right_shoulder = point("left_shoulder"), point("right_shoulder")
    left_elbow, left_hand = point("left_elbow"), point("left_hand")
    right_elbow, right_hand = point("right_elbow"), point("right_hand")

    def limb(a: tuple[float, float], b: tuple[float, float], color: int, width: float) -> None:
        _line(canvas, a, b, ink, width + outline_width * 0.55)
        _line(canvas, a, b, color, width)

    limb(hip, left_knee, trousers, 17)
    limb(left_knee, left_foot, trousers, 15)
    limb(hip, right_knee, trousers, 17)
    limb(right_knee, right_foot, trousers, 15)
    for fx, fy in (left_foot, right_foot):
        canvas.drawRoundRect(skia.Rect.MakeLTRB(fx - 12, fy - 10, fx + 43, fy + 12),
                             9, 9, _paint(ink, 1, skia.Paint.kFill_Style))
        canvas.drawRoundRect(skia.Rect.MakeLTRB(fx - 8, fy - 7, fx + 39, fy + 8),
                             7, 7, _paint(shoes, 1, skia.Paint.kFill_Style))

    limb(left_shoulder, left_elbow, shirt, 16)
    limb(left_elbow, left_hand, skin, 12)
    chest = point("chest")
    neck = point("neck")
    torso = skia.Path()
    torso.moveTo(left_shoulder[0] - 8, left_shoulder[1] - 3)
    torso.quadTo(-28, chest[1] - 12, hip[0] - 30, hip[1] - 2)
    torso.lineTo(hip[0] + 30, hip[1] - 2)
    torso.quadTo(28, chest[1] - 12, right_shoulder[0] + 8, right_shoulder[1] - 3)
    torso.close()
    canvas.drawPath(torso, _paint(ink, outline_width, skia.Paint.kStroke_Style))
    canvas.drawPath(torso, _paint(shirt, 1, skia.Paint.kFill_Style))
    _line(canvas, neck, (neck[0], neck[1] + 30), skin, 20)

    if appearance.get("scarf", actor.get("scarf", False)):
        flutter = math.sin(time_s * 7.0) * (8 if action in ("walk", "run") else 3)
        scarf = skia.Path()
        scarf.moveTo(-43, -365)
        scarf.quadTo(-3, -337, 42, -365)
        scarf.lineTo(68 + flutter, -285 + flutter * .25)
        scarf.lineTo(48 + flutter, -296 + flutter * .25)
        scarf.lineTo(22, -342)
        scarf.close()
        canvas.drawPath(scarf, _paint(ink, 3, skia.Paint.kStroke_Style))
        canvas.drawPath(scarf, _paint(accent, 1, skia.Paint.kFill_Style))

    limb(right_shoulder, right_elbow, shirt, 16)
    limb(right_elbow, right_hand, skin, 12)
    for hx, hy in (left_hand, right_hand):
        canvas.drawCircle(hx, hy, 10, _paint(ink, 2, skia.Paint.kStroke_Style))
        canvas.drawCircle(hx, hy, 8, _paint(skin, 1, skia.Paint.kFill_Style))

    head_x, head_y = point("head")
    radius = float(appearance.get("head_radius", 72))
    canvas.drawOval(skia.Rect.MakeLTRB(head_x - radius, head_y - radius,
                                       head_x + radius, head_y + radius),
                    _paint(ink, outline_width, skia.Paint.kStroke_Style))
    canvas.drawOval(skia.Rect.MakeLTRB(head_x - radius + 4, head_y - radius + 4,
                                       head_x + radius - 4, head_y + radius - 4),
                    _paint(skin, 1, skia.Paint.kFill_Style))
    hair_path = skia.Path()
    hair_path.moveTo(head_x - radius + 5, head_y - 15)
    hair_path.quadTo(head_x - radius * .72, head_y - radius - 15,
                     head_x + 2, head_y - radius + 1)
    hair_path.quadTo(head_x + radius * .72, head_y - radius - 8,
                     head_x + radius - 4, head_y - 15)
    hair_path.quadTo(head_x + radius * .48, head_y - 32,
                     head_x + 12, head_y - 39)
    hair_path.quadTo(head_x - radius * .48, head_y - 28,
                     head_x - radius + 5, head_y - 15)
    hair_path.close()
    canvas.drawPath(hair_path, _paint(hair, 1, skia.Paint.kFill_Style))
    eye_spacing = float(appearance.get("eye_spacing", 48)) / 2
    eye_y = head_y - 5
    brow_raise = float(pose.get("brow", 0.0)) * 4
    _line(canvas, (head_x - eye_spacing - 8, eye_y - 15 - brow_raise),
          (head_x - eye_spacing + 7, eye_y - 17 - brow_raise), ink, 4)
    _line(canvas, (head_x + eye_spacing - 7, eye_y - 17 - brow_raise),
          (head_x + eye_spacing + 8, eye_y - 15 - brow_raise), ink, 4)
    canvas.drawCircle(head_x - eye_spacing, eye_y, 5, _paint(ink, 1, skia.Paint.kFill_Style))
    canvas.drawCircle(head_x + eye_spacing, eye_y, 5, _paint(ink, 1, skia.Paint.kFill_Style))
    if float(pose.get("mouth", 0.0)) > .35:
        canvas.drawOval(skia.Rect.MakeLTRB(head_x - 10, head_y + 22,
                                           head_x + 10, head_y + 43),
                        _paint(ink, 2, skia.Paint.kFill_Style))
    else:
        mouth = skia.Path()
        mouth.moveTo(head_x - 15, head_y + 30)
        mouth.quadTo(head_x, head_y + 39, head_x + 15, head_y + 30)
        canvas.drawPath(mouth, _paint(ink, 4))
    canvas.restore()

def _draw_background(canvas: "skia.Canvas", width: int, height: int,
                     time_s: float, location: dict[str, Any] | None) -> None:
    top = _color((location or {}).get("sky_top", "#87C9F2"))
    bottom = _color((location or {}).get("sky_bottom", "#F4D9B5"))
    shader = skia.GradientShader.MakeLinear(
        [(0, 0), (0, height)], [top, bottom], None, skia.TileMode.kClamp
    )
    sky_paint = _paint(skia.ColorWHITE, 1, skia.Paint.kFill_Style)
    sky_paint.setShader(shader)
    canvas.drawRect(skia.Rect.MakeWH(width, height), sky_paint)
    # Distant hills and a few parallax clouds create depth without external assets.
    hill = _paint(_color((location or {}).get("hill", "#6DAD79")), 1, skia.Paint.kFill_Style)
    path = skia.Path()
    path.moveTo(0, height * 0.66)
    path.cubicTo(width * 0.22, height * 0.52, width * 0.38, height * 0.72, width * 0.58, height * 0.62)
    path.cubicTo(width * 0.78, height * 0.52, width * 0.9, height * 0.69, width, height * 0.59)
    path.lineTo(width, height)
    path.lineTo(0, height)
    path.close()
    canvas.drawPath(path, hill)
    cloud_paint = _paint(skia.ColorSetARGB(190, 255, 255, 255), 1, skia.Paint.kFill_Style)
    for i, base_x in enumerate((0.18, 0.53, 0.82)):
        cx = (base_x * width + time_s * (8 + i * 3)) % (width + 220) - 110
        cy = height * (0.17 + i * 0.075)
        canvas.drawOval(skia.Rect.MakeLTRB(cx - 65, cy - 15, cx + 65, cy + 15), cloud_paint)
        canvas.drawCircle(cx - 25, cy - 12, 22, cloud_paint)
        canvas.drawCircle(cx + 15, cy - 18, 28, cloud_paint)
    # Ground plane.
    ground = _paint(_color((location or {}).get("ground", "#4F865B")), 1, skia.Paint.kFill_Style)
    canvas.drawRect(skia.Rect.MakeLTRB(0, height * 0.79, width, height), ground)
    horizon = _paint(skia.ColorSetARGB(70, 255, 255, 255), 3)
    canvas.drawLine(0, height * 0.79, width, height * 0.79, horizon)


def render_frame(episode: dict[str, Any], time_s: float, output: Path) -> None:
    fmt = episode["format"]
    width, height = int(fmt["width"]), int(fmt["height"])
    shots = episode["shots"]
    shot, local_time = shot_at(shots, time_s)
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    location_map = {item["id"]: item for item in episode.get("locations", [])}
    location = location_map.get(shot.get("location"))
    _draw_background(canvas, width, height, time_s, location)

    camera = shot.get("camera", {})
    zoom = float(camera.get("zoom", 1.0))
    pan_x = float(camera.get("x", 0.0))
    pan_y = float(camera.get("y", 0.0))
    canvas.save()
    canvas.translate(width * 0.5, height * 0.5)
    canvas.scale(zoom, zoom)
    canvas.translate(-width * 0.5 + pan_x, -height * 0.5 + pan_y)

    actors = shot.get("actors", [])
    for index, actor_id in enumerate(actors):
        actor = next((c for c in episode.get("characters", []) if c["id"] == actor_id), None)
        if actor is None:
            continue
        pose = dict(actor)
        pose.update(shot.get("actor_overrides", {}).get(actor_id, {}))
        pose["id"] = actor_id
        # Shot-relative positions may override the episode's canonical character record.
        if "positions" in shot and actor_id in shot["positions"]:
            pose.update(shot["positions"][actor_id])
        _draw_character(canvas, pose, local_time, shot, index, episode.get("_motion_library"))
    canvas.restore()

    # Simple editorial title/caption safe-area marker only when explicitly requested.
    title = shot.get("title")
    if title:
        font = skia.Font(skia.Typeface.MakeDefault(), 46)
        canvas.drawString(str(title), 64, 110, font, _paint(_color("#17202A"), 1, skia.Paint.kFill_Style))
    output.parent.mkdir(parents=True, exist_ok=True)
    image = surface.makeImageSnapshot()
    image.save(str(output), skia.kPNG, 100)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Skia failed to encode frame at {time_s:.3f}s")


def render_episode_frames(project_dir: Path, start_frame: int = 0,
                          max_frames: int | None = None) -> tuple[Path, int]:
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    # Resolve canonical character rigs once per render; shot overrides remain local.
    for character in episode.get("characters", []):
        rig_rel = character.get("rig")
        if rig_rel:
            rig_path = (project_dir / rig_rel).resolve()
            if project_dir.resolve() not in rig_path.parents:
                raise ValueError(f"Character rig path escapes project: {rig_rel}")
            if not rig_path.is_file():
                raise FileNotFoundError(f"Missing character rig: {rig_path}")
            character["_rig"] = json.loads(rig_path.read_text(encoding="utf-8"))
    motion_path = project_dir / "assets" / "motions" / "motion_library.json"
    if motion_path.is_file():
        episode["_motion_library"] = json.loads(motion_path.read_text(encoding="utf-8"))
    fps = int(episode["format"]["fps"])
    total = int(round(float(episode["format"]["duration_seconds"]) * fps))
    start = max(0, start_frame)
    stop = min(total, start + max_frames) if max_frames is not None else total
    frame_dir = project_dir / "renders" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for frame_no in range(start, stop):
        render_frame(episode, frame_no / fps, frame_dir / f"frame_{frame_no:06d}.png")
    return frame_dir, stop - start
