"""Deterministic 2D stickman scene renderer using Skia.

The renderer is intentionally data-driven: the same episode JSON and frame time
always produce the same frame. It renders one frame at a time to keep RAM usage low.
"""
from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, features

try:
    import skia
except ImportError as exc:  # pragma: no cover - depends on local optional runtime
    raise RuntimeError("Skia is required. Install dependencies with: pip install -r requirements.txt") from exc

from .rig import blend_motion, build_skeleton, facial_pose, foot_plant_targets, sample_motion
from .cinematic import draw_cinematic_effects
from .motion_library import active_track_segment, resolve_motion


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
    motion_time = float(actor.get("_motion_time", time_s))
    rig = actor.get("_rig", {})
    # Character-instance overrides let the 60-profile catalog share one rig topology.
    appearance = {**rig.get("appearance", {}), **actor.get("appearance", {})}
    proportions = {**rig.get("proportions", {}), **actor.get("proportions", {})}
    transition = actor.get("transition")
    if transition and transition.get("from_action"):
        transition_start = float(transition.get("start_seconds", 0.0))
        transition_time = max(0.0, time_s - transition_start)
        pose = blend_motion(
            str(transition["from_action"]), action, transition_time,
            float(transition.get("duration_seconds", 0.25)), motion_library,
        )
    else:
        pose = sample_motion(action, motion_time, motion_library)
    plant = actor.get("_foot_plant")
    if plant and action in ("walk", "run"):
        pose.update(foot_plant_targets(
            action, time_s, proportions,
            root_dx_since_stance=float(plant.get("root_dx_since_stance", 0.0)),
            root_y=float(pose.get("root_y", 0.0)),
        ))
    for key, value in actor.get("_motion_pose", {}).items():
        if key in pose:
            pose[key] = float(value)
    for key, value in actor.get("pose", {}).items():
        if key in pose:
            pose[key] = float(value)
    # Optional timed viseme cues are relative to each dialogue line's start.
    viseme_codes = {"REST": 0, "A": 1, "E": 2, "I": 3, "O": 4, "U": 5,
                    "CLOSED": 6, "SMILE": 7, "FROWN": 8}
    for line in shot.get("dialogue", []):
        if line.get("speaker") != actor.get("id") or "visemes" not in line:
            continue
        line_start = float(line.get("start_seconds", 0.0))
        elapsed = time_s - line_start
        cues = sorted(line.get("visemes", []), key=lambda cue: float(cue.get("at", 0.0)))
        selected = None
        for cue in cues:
            if float(cue.get("at", 0.0)) <= elapsed:
                selected = cue
            else:
                break
        if selected is not None:
            shape_name = str(selected.get("shape", "REST")).upper()
            pose["mouth_shape"] = float(viseme_codes.get(shape_name, 0))
            pose["mouth"] = 1.0 if shape_name in ("A", "O", "U") else 0.0
        break
    joints = build_skeleton(pose, proportions)
    face = facial_pose(pose, time_s)

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
    canvas.translate(x, y + float(pose.get("root_y", 0.0)))
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
    for side, (fx, fy) in (("left", left_foot), ("right", right_foot)):
        tx, ty = point(f"{side}_toe")
        shoe_path = skia.Path()
        shoe_path.moveTo(fx - 13, fy - 9)
        shoe_path.quadTo(fx + 8, fy - 17, tx + 13, ty - 5)
        shoe_path.quadTo(tx + 26, ty + 8, tx - 2, ty + 10)
        shoe_path.lineTo(fx - 15, fy + 7)
        shoe_path.close()
        canvas.drawPath(shoe_path, _paint(ink, 1, skia.Paint.kFill_Style))
        inner = skia.Path()
        inner.moveTo(fx - 8, fy - 5)
        inner.quadTo(fx + 8, fy - 11, tx + 9, ty - 2)
        inner.quadTo(tx + 18, ty + 5, tx - 2, ty + 5)
        inner.close()
        canvas.drawPath(inner, _paint(shoes, 1, skia.Paint.kFill_Style))

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
    canvas.drawPath(torso, _paint(shirt, 1, skia.Paint.kFill_Style))
    canvas.drawPath(torso, _paint(ink, outline_width, skia.Paint.kStroke_Style))
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
    for side, (hx, hy) in (("left", left_hand), ("right", right_hand)):
        wx, wy = point(f"{side}_wrist")
        # Palm is a small oriented capsule; each digit receives an outline,
        # a tapered-looking inner stroke and a subtle fingertip highlight.
        dx, dy = hx - wx, hy - wy
        hand_angle = math.atan2(dy, dx)
        palm_cx = hx + math.cos(hand_angle) * 7
        palm_cy = hy + math.sin(hand_angle) * 7
        canvas.save()
        canvas.translate(palm_cx, palm_cy)
        canvas.rotate(math.degrees(hand_angle))
        canvas.drawRoundRect(skia.Rect.MakeLTRB(-9, -11, 20, 11), 9, 9,
                             _paint(ink, 1, skia.Paint.kFill_Style))
        canvas.drawRoundRect(skia.Rect.MakeLTRB(-6, -8, 17, 8), 7, 7,
                             _paint(skin, 1, skia.Paint.kFill_Style))
        canvas.restore()
        finger_points = joints[f"{side}_fingers"]
        for finger_index, (fx, fy) in enumerate(finger_points):
            fy -= 180.0
            # Slightly different widths make the thumb and little finger read
            # separately instead of five identical spokes.
            width = 4.2 if finger_index in (0, 4) else 3.5
            mid = (hx + (fx - hx) * .56, hy + (fy - hy) * .56)
            _line(canvas, (hx, hy), mid, ink, width + 1.8)
            _line(canvas, mid, (fx, fy), ink, width + 1.8)
            _line(canvas, (hx, hy), mid, skin, width)
            _line(canvas, mid, (fx, fy), skin, width)
            canvas.drawCircle(fx, fy, width * .52, _paint(skin, 1, skia.Paint.kFill_Style))

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
    gaze_x, gaze_y = face["gaze_x"] * 5.0, face["gaze_y"] * 4.0
    brow_raise = face["brow"] * 4
    for eye_x, tilt in ((head_x - eye_spacing, -1), (head_x + eye_spacing, 1)):
        brow_start = (eye_x - 8, eye_y - 15 - brow_raise + tilt * face["emotion"] * 3)
        brow_end = (eye_x + 7, eye_y - 17 - brow_raise - tilt * face["emotion"] * 3)
        _line(canvas, brow_start, brow_end, ink, 4)
        if face["blink"] > 0.72:
            _line(canvas, (eye_x - 7, eye_y), (eye_x + 7, eye_y), ink, 4)
        else:
            eye_h = max(1.5, 5.0 * (1.0 - face["blink"]))
            canvas.drawOval(skia.Rect.MakeLTRB(eye_x - 5 + gaze_x, eye_y - eye_h + gaze_y,
                                               eye_x + 5 + gaze_x, eye_y + eye_h + gaze_y),
                            _paint(ink, 1, skia.Paint.kFill_Style))
    shape = int(round(face.get("mouth_shape", 0.0)))
    if shape in (1, 2, 3, 4, 5) or face["mouth"] > .35:
        widths = {1: 13, 2: 15, 3: 7, 4: 16, 5: 12}
        heights = {1: 20, 2: 9, 3: 12, 4: 15, 5: 10}
        mw, mh = widths.get(shape, 10), heights.get(shape, 20)
        canvas.drawOval(skia.Rect.MakeLTRB(head_x - mw, head_y + 27,
                                           head_x + mw, head_y + 27 + mh),
                        _paint(ink, 2, skia.Paint.kFill_Style))
    elif shape == 6:
        _line(canvas, (head_x - 11, head_y + 34), (head_x + 11, head_y + 34), ink, 4)
    else:
        mouth = skia.Path()
        smile = face["emotion"] * 8.0
        if shape == 8:
            smile = -abs(smile) - 5
        if shape == 7:
            smile = abs(smile) + 8
        mouth.moveTo(head_x - 15, head_y + 30)
        mouth.quadTo(head_x, head_y + 39 + smile, head_x + 15, head_y + 30)
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
    # Algerian-neighborhood skyline: apartment blocks, balconies and shopfronts.
    facade_colors = ("#E8D7B8", "#D9C7A5", "#CBB99B", "#E6D4B5")
    for i, (left, block_w, top) in enumerate(((0.02, .19, .37), (.23, .17, .43), (.69, .18, .35), (.88, .15, .42))):
        x0, x1, y0 = width * left, width * (left + block_w), height * top
        canvas.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, height * .80),
                        _paint(_color(facade_colors[i]), 1, skia.Paint.kFill_Style))
        canvas.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, height * .80),
                        _paint(_color("#796B5A"), 3, skia.Paint.kStroke_Style))
        for row in range(3):
            for col in range(2):
                wx = x0 + width * (.035 + col * .075)
                wy = y0 + height * (.055 + row * .105)
                canvas.drawRect(skia.Rect.MakeLTRB(wx, wy, wx + width * .038, wy + height * .052),
                                _paint(_color("#6B9AA8"), 1, skia.Paint.kFill_Style))
                canvas.drawRect(skia.Rect.MakeLTRB(wx, wy, wx + width * .038, wy + height * .052),
                                _paint(_color("#F4EBDD"), 3, skia.Paint.kStroke_Style))
                canvas.drawLine(wx - 3, wy + height * .054, wx + width * .041, wy + height * .054,
                                _paint(_color("#6E6256"), 4))
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

    # Environment-specific set dressing; all geometry is deterministic and reusable.
    environment = str((location or {}).get("environment", "street")).lower()
    detail = _paint(_color((location or {}).get("detail", "#D8C4A2")), 1, skia.Paint.kFill_Style)
    if environment in ("room", "classroom"):
        wall = _paint(_color((location or {}).get("wall", "#E9E0D0")), 1, skia.Paint.kFill_Style)
        canvas.drawRect(skia.Rect.MakeLTRB(0, height*.60, width, height*.79), wall)
        canvas.drawRect(skia.Rect.MakeLTRB(width*.12, height*.30, width*.43, height*.52),
                        _paint(_color("#75AFC8"), 1, skia.Paint.kFill_Style))
        canvas.drawRect(skia.Rect.MakeLTRB(width*.10, height*.285, width*.45, height*.305),
                        _paint(_color("#765D48"), 1, skia.Paint.kFill_Style))
        if environment == "classroom":
            canvas.drawRect(skia.Rect.MakeLTRB(width*.12, height*.57, width*.88, height*.61),
                            _paint(_color("#79583D"), 1, skia.Paint.kFill_Style))
            for i in range(3):
                xx=width*(.20+i*.25)
                canvas.drawRect(skia.Rect.MakeLTRB(xx,height*.61,xx+width*.12,height*.66),
                                _paint(_color("#B98554"),1,skia.Paint.kFill_Style))
    elif environment == "beach":
        canvas.drawRect(skia.Rect.MakeLTRB(0,height*.68,width,height*.79),
                        _paint(_color("#E8C77C"),1,skia.Paint.kFill_Style))
        canvas.drawCircle(width*.78,height*.20,height*.07,
                          _paint(_color("#FFD76A"),1,skia.Paint.kFill_Style))
        for i in range(4):
            yy=height*(.70+i*.022)
            canvas.drawLine(0,yy,width,yy,_paint(skia.ColorSetARGB(95,255,255,255),3))
    elif environment == "rooftop":
        canvas.drawRect(skia.Rect.MakeLTRB(0,height*.72,width,height*.79),
                        _paint(_color("#B8A38A"),1,skia.Paint.kFill_Style))
        for xx in (0.08,.34,.68,.91):
            canvas.drawRect(skia.Rect.MakeLTRB(width*xx,height*.54,width*(xx+.08),height*.72),
                            _paint(_color("#D6C7AF"),1,skia.Paint.kFill_Style))
    elif environment == "park":
        for xx, yy, rr in ((.12,.64,.055),(.82,.62,.07),(.93,.68,.045)):
            canvas.drawRect(skia.Rect.MakeLTRB(width*xx-width*.009,height*yy,width*xx+width*.009,height*.80),
                            _paint(_color("#795B3B"),1,skia.Paint.kFill_Style))
            canvas.drawCircle(width*xx,height*yy-height*.045,height*rr,
                              _paint(_color("#477D4E"),1,skia.Paint.kFill_Style))
    weather = str((location or {}).get("weather", "clear")).lower()
    if weather == "rain":
        rain = _paint(skia.ColorSetARGB(95, 225, 240, 255), 2)
        for i in range(42):
            rx = (i*97 + time_s*170) % (width+40) - 20
            ry = (i*137 + time_s*520) % height
            canvas.drawLine(rx, ry, rx-12, ry+30, rain)
    elif weather == "fog":
        fog = _paint(skia.ColorSetARGB(45, 245, 246, 242), 1, skia.Paint.kFill_Style)
        canvas.drawRect(skia.Rect.MakeWH(width,height), fog)



def _draw_dialogue_caption(output: Path, text: str, width: int, height: int) -> None:
    """Draw timed dialogue captions; use RAQM for correct Arabic shaping when available."""
    if not text:
        return
    try:
        image = Image.open(output).convert("RGBA")
        draw = ImageDraw.Draw(image, "RGBA")
        candidates = [
            Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoSansArabic-Regular.ttf",
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        font_path = next((p for p in candidates if p.is_file()), None)
        raqm = bool(features.check_feature("raqm"))
        layout = ImageFont.Layout.RAQM if raqm else ImageFont.Layout.BASIC
        font = ImageFont.truetype(str(font_path), max(18, int(width * .047)), layout_engine=layout) if font_path else ImageFont.load_default()
        pad = max(14, int(width * .045))
        box_top = int(height * .84)
        draw.rounded_rectangle((pad, box_top, width - pad, height - pad), radius=18,
                               fill=(12, 18, 28, 218), outline=(255, 255, 255, 190), width=2)
        kwargs = {"anchor": "mm", "font": font, "fill": (255, 255, 255, 255)}
        if raqm:
            kwargs.update({"direction": "rtl", "language": "ar"})
        caption = textwrap.fill(text, width=30)
        draw.multiline_text((width // 2, (box_top + height - pad) // 2), caption, align="center", spacing=5, **kwargs)
        image.convert("RGB").save(output, format="PNG", optimize=True)
    except Exception as exc:
        raise RuntimeError(f"Could not render dialogue caption: {exc}") from exc


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
    progress = clamp(local_time / max(float(shot.get("duration_seconds", 1)), 0.001), 0.0, 1.0)
    camera_move = camera.get("move", {})
    start_camera = camera_move.get("from", {})
    end_camera = camera_move.get("to", {})
    eased = smoothstep(progress)
    zoom = float(camera.get("zoom", 1.0))
    pan_x = float(camera.get("x", 0.0))
    pan_y = float(camera.get("y", 0.0))
    if camera_move:
        zoom = float(start_camera.get("zoom", zoom)) + (float(end_camera.get("zoom", zoom)) - float(start_camera.get("zoom", zoom))) * eased
        pan_x = float(start_camera.get("x", pan_x)) + (float(end_camera.get("x", pan_x)) - float(start_camera.get("x", pan_x))) * eased
        pan_y = float(start_camera.get("y", pan_y)) + (float(end_camera.get("y", pan_y)) - float(start_camera.get("y", pan_y))) * eased
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
        # A shot can contain a time-coded sequence of reusable actions for each actor.
        # Each segment has its own clock, so scrubbing/resume renders remain deterministic.
        motion_track = shot.get("motion_tracks", {}).get(actor_id, pose.get("motion_track", []))
        segment, segment_time = active_track_segment(motion_track, local_time) if motion_track else (None, local_time)
        if segment is not None:
            requested_action = str(segment.get("action", "idle"))
            resolved_action, overlay = resolve_motion(requested_action, episode.get("_motion_library"))
            pose["action"] = resolved_action
            pose["_motion_time"] = segment_time
            pose["_motion_pose"] = {**overlay, **segment.get("pose", {})}
            transition_seconds = float(segment.get("transition_seconds", 0.0))
            ordered_track = sorted(motion_track, key=lambda item: float(item["start"]))
            previous = next((item for item in reversed(ordered_track)
                             if float(item["end"]) <= float(segment["start"])), None)
            if previous and transition_seconds > 0:
                previous_action, _ = resolve_motion(str(previous["action"]), episode.get("_motion_library"))
                pose["transition"] = {
                    "from_action": previous_action,
                    "start_seconds": float(segment["start"]),
                    "duration_seconds": transition_seconds,
                }
            else:
                pose.pop("transition", None)
        movement = shot.get("movement", {}).get(actor_id)
        if movement:
            shot_duration = max(float(shot.get("duration_seconds", 1)), 0.001)
            move_t = smoothstep(clamp(local_time / shot_duration, 0.0, 1.0))
            default_x = float(pose.get("x", 420 + index * 360))
            from_x = float(movement.get("from_x", default_x))
            to_x = float(movement.get("to_x", default_x))
            pose["x"] = from_x + (to_x - from_x) * move_t
            action_name = str(pose.get("action", shot.get("action", "idle")))
            if action_name in ("walk", "run"):
                cycle_duration = 0.8 if action_name == "walk" else 0.48
                phase_time = local_time % cycle_duration
                stance_offset = 0.0 if phase_time < cycle_duration * 0.5 else cycle_duration * 0.5
                stance_start = local_time - phase_time + stance_offset
                stance_progress = smoothstep(clamp(stance_start / shot_duration, 0.0, 1.0))
                current_root = (to_x - from_x) * move_t
                stance_root = (to_x - from_x) * stance_progress
                actor_scale = max(abs(float(pose.get("scale", 1.0))), 1e-6)
                pose["_foot_plant"] = {
                    "root_dx_since_stance": (current_root - stance_root) / actor_scale
                }
        if not movement:
            action_name = str(pose.get("action", shot.get("action", "idle")))
            if action_name in ("walk", "run"):
                pose["_foot_plant"] = {"root_dx_since_stance": 0.0}
        active_lines = [
            line for line in shot.get("dialogue", [])
            if float(line.get("start_seconds", 0.0)) <= local_time < float(line.get("end_seconds", shot.get("duration_seconds", 0)))
        ]
        active_shot = dict(shot)
        active_shot["dialogue"] = active_lines
        _draw_character(canvas, pose, local_time, active_shot, index, episode.get("_motion_library"))
    canvas.restore()
    draw_cinematic_effects(canvas, width, height, shot, local_time)

    active_lines = [
        line for line in shot.get("dialogue", [])
        if float(line.get("start_seconds", 0.0)) <= local_time < float(line.get("end_seconds", shot.get("duration_seconds", 0)))
    ]

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
    if active_lines:
        _draw_dialogue_caption(output, active_lines[-1].get("text", ""), width, height)


def render_episode_frames(project_dir: Path, start_frame: int = 0,
                          max_frames: int | None = None,
                          resume: bool = False) -> tuple[Path, int]:
    episode = json.loads((project_dir / "episode.json").read_text(encoding="utf-8"))
    # Resolve optional cast catalog IDs into per-instance visual/proportion overrides.
    catalog_path = project_dir / "assets" / "characters" / "cast_60" / "catalog.json"
    cast_catalog = None
    if catalog_path.is_file():
        cast_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    cast_by_id = {
        item.get("id"): item for item in (cast_catalog or {}).get("characters", [])
    }
    # Resolve canonical character rigs once per render; shot overrides remain local.
    for character in episode.get("characters", []):
        cast_id = character.get("cast_id")
        if cast_id:
            profile = cast_by_id.get(cast_id)
            if profile is None:
                raise ValueError(f"Unknown cast_id '{cast_id}' for character {character.get('id')}")
            character.setdefault("appearance", dict(profile.get("appearance", {})))
            character.setdefault("proportions", dict(profile.get("proportions", {})))
            character.setdefault("rig", profile.get("rig", (cast_catalog or {}).get("shared_rig")))
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
    rendered = 0
    for frame_no in range(start, stop):
        frame_path = frame_dir / f"frame_{frame_no:06d}.png"
        if resume and frame_path.is_file() and frame_path.stat().st_size > 0:
            continue
        render_frame(episode, frame_no / fps, frame_path)
        rendered += 1
    return frame_dir, rendered
