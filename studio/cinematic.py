"""Deterministic 2D cinematic overlay effects for shot-level direction."""
from __future__ import annotations
import math
from typing import Any
import skia


def _paint(color: int, width: float = 1.0, fill: bool = False) -> skia.Paint:
    p=skia.Paint(AntiAlias=True,Color=color,StrokeWidth=width)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    if fill: p.setStyle(skia.Paint.kFill_Style)
    return p


def draw_cinematic_effects(canvas: skia.Canvas, width: int, height: int,
                           shot: dict[str, Any], local_time: float) -> None:
    for effect in shot.get("effects", []):
        kind=str(effect.get("type","")).lower()
        start=float(effect.get("start",0.0))
        duration=max(.001,float(effect.get("duration",.35)))
        t=local_time-start
        if t<0 or t>duration: continue
        strength=max(0.0,1.0-t/duration)
        if kind=="impact_flash":
            alpha=int(max(0,min(150, float(effect.get("intensity",.45))*255*strength)))
            canvas.drawRect(skia.Rect.MakeWH(width,height),
                            _paint(skia.ColorSetARGB(alpha,255,248,220),fill=True))
        elif kind=="speed_lines":
            alpha=int(150*strength)
            p=_paint(skia.ColorSetARGB(alpha,255,255,255),max(1,float(effect.get("line_width",3))))
            cx=float(effect.get("x",width*.5)); cy=float(effect.get("y",height*.5))
            count=max(4,min(36,int(effect.get("count",18))))
            for i in range(count):
                angle=(i/count)*math.tau
                inner=float(effect.get("inner_radius",70))
                outer=float(effect.get("outer_radius",230))
                canvas.drawLine(cx+math.cos(angle)*inner,cy+math.sin(angle)*inner,
                                cx+math.cos(angle)*outer,cy+math.sin(angle)*outer,p)
        elif kind=="dust":
            alpha=int(130*strength)
            p=_paint(skia.ColorSetARGB(alpha,220,194,150),fill=True)
            seed=int(effect.get("seed",7))
            for i in range(max(3,min(40,int(effect.get("count",16))))):
                x=(seed*53+i*89+local_time*38)%width
                y=float(effect.get("y",height*.78))-(i*17%75)-local_time*8
                r=2+(i%4)*1.4
                canvas.drawCircle(x,y,r,p)
        elif kind=="vignette":
            alpha=int(115*strength)
            shader=skia.GradientShader.MakeRadial(
                (width*.5,height*.48),max(width,height)*.72,
                [skia.ColorSetARGB(0,0,0,0),skia.ColorSetARGB(alpha,0,0,0)],
                None,skia.TileMode.kClamp)
            p=_paint(skia.ColorBLACK,fill=True); p.setShader(shader)
            canvas.drawRect(skia.Rect.MakeWH(width,height),p)
        elif kind=="screen_shake":
            # A visible directional shake accent; camera transform remains deterministic.
            alpha=int(70*strength)
            p=_paint(skia.ColorSetARGB(alpha,255,255,255),max(2,float(effect.get("line_width",5))))
            offset=math.sin(t*65)*float(effect.get("amplitude",18))
            canvas.drawLine(0,height*.12+offset,width,height*.12-offset,p)
