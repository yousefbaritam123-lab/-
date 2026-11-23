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
                    shot: dict[str, Any], index: int) -> None:
    x = float(actor.get("x", 420 + index * 360))
    y = float(actor.get("y", 1450))
    scale = float(actor.get("scale", 1.0))
    action = str(actor.get("action", shot.get("action", "idle")))
    phase = time_s * (7.0 if action in ("run", "walk") else 2.2) + float(actor.get("phase", index * 1.7))
    moving = action in ("walk", "run")
    stride = math.sin(phase) if moving else 0.0
    bob = abs(math.sin(phase)) * (25 if action == "run" else 12) if moving else math.sin(phase) * 3
    talk = actor.get("talk", False) or any(
        line.get("speaker") == actor.get("id") for line in shot.get("dialogue", [])
    )
    wave = action == "wave" or actor.get("gesture") == "wave"
    jump = action == "jump"
    jump_y = abs(math.sin(min(time_s * 3.0, math.pi))) * 120 if jump else 0

    canvas.save()
    canvas.translate(x, y - bob - jump_y)
    canvas.scale(scale, scale)
    if actor.get("flip", False):
        canvas.scale(-1, 1)

    ink = _color(actor.get("outline", "#171923"))
    skin = _color(actor.get("skin", "#F4F0E8"))
    accent = _color(actor.get("accent", "#E34B4B"))
    shadow = _paint(skia.ColorSetARGB(48, 0, 0, 0), 1, skia.Paint.kFill_Style)
    canvas.drawOval(skia.Rect.MakeLTRB(-72, -5, 72, 17), shadow)

    hip = (0.0, -180.0)
    chest = (0.0, -355.0)
    neck = (0.0, -390.0)
    head = (0.0, -465.0)
    leg_swing = stride * (42 if action == "run" else 28)
    left_knee = _limb(hip, 105, 90 + leg_swing)
    right_knee = _limb(hip, 105, 90 - leg_swing)
    left_foot = _limb(left_knee, 100, 90 - leg_swing * 0.55)
    right_foot = _limb(right_knee, 100, 90 + leg_swing * 0.55)
    left_shoulder = (-48.0, -345.0)
    right_shoulder = (48.0, -345.0)
    arm_swing = -stride * 38 if moving else math.sin(phase) * 5
    left_elbow = _limb(left_shoulder, 92, 115 + arm_swing)
    right_elbow = _limb(right_shoulder, 92, 65 - arm_swing)
    left_hand = _limb(left_elbow, 78, 115 + arm_swing * 0.5)
    right_hand = _limb(right_elbow, 78, 65 - arm_swing * 0.5)
    if wave:
        right_elbow = (82.0, -455.0 + math.sin(time_s * 8) * 8)
        right_hand = (125.0, -510.0 + math.sin(time_s * 8) * 18)

    # Legs, shoes, torso and arms are layered to preserve a clean silhouette.
    limb_width = 22.0
    _line(canvas, hip, left_knee, ink, limb_width)
    _line(canvas, left_knee, left_foot, ink, limb_width * 0.82)
    _line(canvas, hip, right_knee, ink, limb_width)
    _line(canvas, right_knee, right_foot, ink, limb_width * 0.82)
    _line(canvas, (left_foot[0] - 8, left_foot[1]), (left_foot[0] + 38, left_foot[1]), accent, 19)
    _line(canvas, (right_foot[0] - 8, right_foot[1]), (right_foot[0] + 38, right_foot[1]), accent, 19)

    torso_paint = _paint(ink, 30)
    canvas.drawLine(hip[0], hip[1], chest[0], chest[1], torso_paint)
    canvas.drawLine(chest[0], chest[1], neck[0], neck[1], _paint(ink, 17))
    _line(canvas, left_shoulder, left_elbow, ink, 20)
    _line(canvas, left_elbow, left_hand, ink, 17)
    _line(canvas, right_shoulder, right_elbow, ink, 20)
    _line(canvas, right_elbow, right_hand, ink, 17)
    canvas.drawCircle(right_hand[0], right_hand[1], 12, _paint(skin, 1, skia.Paint.kFill_Style))
    canvas.drawCircle(left_hand[0], left_hand[1], 12, _paint(skin, 1, skia.Paint.kFill_Style))

    # Head, eyes and mouth are independent drawing layers.
    canvas.drawCircle(head[0], head[1], 72, _paint(ink, 7, skia.Paint.kStroke_Style))
    canvas.drawCircle(head[0], head[1], 68, _paint(skin, 1, skia.Paint.kFill_Style))
    eye_y = head[1] - 8
    canvas.drawCircle(-24, eye_y, 6, _paint(ink, 1, skia.Paint.kFill_Style))
    canvas.drawCircle(24, eye_y, 6, _paint(ink, 1, skia.Paint.kFill_Style))
    mouth = skia.Path()
    mouth.moveTo(-17, head[1] + 28)
    mouth.quadTo(0, head[1] + (48 if talk and int(time_s * 8) % 2 else 39), 17, head[1] + 28)
    canvas.drawPath(mouth, _paint(ink, 5))
    if actor.get("scarf", False):
        scarf = skia.Path()
        scarf.moveTo(-48, -365)
        scarf.quadTo(0, -325, 50, -365)
        scarf.lineTo(82, -280)
        scarf.lineTo(55, -292)
        scarf.lineTo(30, -340)
        scarf.close()
        canvas.drawPath(scarf, _paint(accent, 1, skia.Paint.kFill_Style))
    canvas.restore()


def _draw_background(canvas: "skia.Canvas", width: int, height: int,
                     time_s: float, location: dict[str, Any] | None) -> None:
    top = _color((location or {}).get("sky_top", "#87C9F2"))
    bottom = _color((location or {}).get("sky_bottom", "#F4D9B5"))
    shader = skia.GradientShader.MakeLinear(
        [(0, 0), (0, height)], [top, bottom], None, skia.TileMode.kClamp
    )
    canvas.drawRect(skia.Rect.MakeWH(width, height), _paint(skia.ColorWHITE, 1, skia.Paint.kFill_Style).setShader(shader))
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
        _draw_character(canvas, pose, local_time, shot, index)
    canvas.restore()

    # Simple editorial title/caption safe-area marker only when explicitly requested.
    title = shot.get("title")
    if title:
        font = skia.Font(skia.Typeface.MakeDefault(), 46)
        canvas.drawString(str(title), 64, 110, font, _paint(_color("#17202A"), 1, skia.Paint.kFill_Style))
    output.parent.mkdir(parents=True, exist_ok=True)
    image = surface.makeImageSnapshot()
    encoded = image.encodeToData(skia.kPNG)
    if encoded is None:
        raise RuntimeError(f"Skia failed to encode frame at {time_s:.3f}s")
    encoded.save(str(output))


def render_episode_frames(project_dir: Path, start_frame: int = 0,
                          max_frames: int | None = None) -> tuple[Path, int]:
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    fps = int(episode["format"]["fps"])
    total = int(round(float(episode["format"]["duration_seconds"]) * fps))
    start = max(0, start_frame)
    stop = min(total, start + max_frames) if max_frames is not None else total
    frame_dir = project_dir / "renders" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for frame_no in range(start, stop):
        render_frame(episode, frame_no / fps, frame_dir / f"frame_{frame_no:06d}.png")
    return frame_dir, stop - start
