#!/usr/bin/env python3
"""Render a 72-second vertical 2D stickman short."""
import math, os, subprocess, wave
from PIL import Image, ImageDraw, ImageFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display

W,H,FPS,DURATION=720,1280,12,72
OUT="output"
os.makedirs(OUT,exist_ok=True)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font=ImageFont.truetype(FONT,34)
small=ImageFont.truetype(FONT,25)
def ar(s): return get_display(reshape(s))
def smooth(t): return t*t*(3-2*t)
def mix(a,b,t): return int(a+(b-a)*t)
def gradient(top,bottom):
    im=Image.new("RGB",(W,H))
    p=im.load()
    for y in range(H):
        q=y/(H-1); c=tuple(mix(top[i],bottom[i],q) for i in range(3))
        for x in range(W): p[x,y]=c
    return im
def stick(d,x,y,scale=1,color=(20,22,30),pose="stand",arm=0):
    r=28*scale; lw=max(5,int(10*scale))
    d.ellipse((x-r,y-190*scale-r,x+r,y-190*scale+r),outline=color,width=lw)
    d.line((x,y-160*scale,x,y-70*scale),fill=color,width=lw)
    if pose=="give":
        d.line((x,y-145*scale,x+65*scale,y-112*scale),fill=color,width=lw)
        d.line((x+65*scale,y-112*scale,x+100*scale,y-105*scale),fill=color,width=lw)
        d.line((x,y-145*scale,x-42*scale,y-105*scale),fill=color,width=lw)
    elif pose=="sad":
        d.line((x,y-145*scale,x-48*scale,y-105*scale),fill=color,width=lw)
        d.line((x,y-145*scale,x+40*scale,y-105*scale),fill=color,width=lw)
    else:
        d.line((x,y-145*scale,x-48*scale,y-100*scale),fill=color,width=lw)
        d.line((x,y-145*scale,x+48*scale,y-100*scale),fill=color,width=lw)
    d.line((x,y-70*scale,x-40*scale,y),fill=color,width=lw)
    d.line((x,y-70*scale,x+42*scale,y),fill=color,width=lw)
def centered(d,text,y,ft,fill,stroke=0):
    txt=ar(text); box=d.textbbox((0,0),txt,font=ft, direction="rtl")
    x=(W-(box[2]-box[0]))//2
    d.text((x,y),txt,font=ft,fill=fill, direction="rtl",stroke_width=stroke,stroke_fill=(0,0,0))
def frame(t):
    scene=0 if t<8 else 1 if t<18 else 2 if t<30 else 3 if t<43 else 4 if t<58 else 5
    palettes=[((12,20,39),(40,48,70)),((31,34,48),(82,61,54)),((21,31,49),(63,75,83)),((35,30,38),(83,60,54)),((20,37,48),(47,87,79)),((10,24,42),(27,51,70))]
    im=gradient(*palettes[scene]); d=ImageDraw.Draw(im)
    # ground and cinematic lights
    d.rectangle((0,1010,W,H),fill=(18,23,31))
    for k in range(5):
        x=(k*181+int(t*13))%W
        d.ellipse((x,180+(k%3)*90,x+5,185+(k%3)*90),fill=(190,199,214))
    if scene==0:
        x=120+int(t*18); stick(d,x,1010,1.25,pose="sad")
        centered(d,"في ليلة باردة، كان شاب فقير يمشي وحيداً.",1060,small,(245,239,226))
    elif scene==1:
        stick(d,300,1010,1.25)
        d.rounded_rectangle((390,935,510,975),radius=10,fill=(205,157,91))
        centered(d,"وفجأة وجد قطعة خبز صغيرة على الأرض.",1060,small,(255,240,218))
    elif scene==2:
        stick(d,250,1010,1.15)
        stick(d,520,1010,1.05,(205,210,220),"sad")
        centered(d,"رأى رجلاً جائعاً، بالكاد يستطيع الوقوف.",1060,small,(245,239,226))
    elif scene==3:
        stick(d,250,1010,1.15,pose="give")
        stick(d,520,1010,1.05,(205,210,220),"sad")
        d.rounded_rectangle((365,855,425,880),radius=8,fill=(205,157,91))
        centered(d,"تردد لحظة... ثم قسم الخبز وأعطاه نصفه.",1060,small,(255,240,218))
    elif scene==4:
        stick(d,250,1010,1.15)
        stick(d,520,1010,1.05,(205,210,220))
        d.ellipse((475,780,565,870),outline=(245,205,110),width=7)
        centered(d,"ابتسم الغريب وقال: كنت أملك طعاماً،",1050,small,(255,244,214))
        centered(d,"لكنني أردت أن أرى من يشارك رغم حاجته.",1090,small,(255,244,214))
    else:
        stick(d,360,1010,1.3)
        centered(d,"الخير لا يُقاس بما تملك، بل بما تعطي.",1035,font,(255,230,170),2)
        centered(d,"حتى القليل قد يصنع فرقاً كبيراً.",1090,small,(245,239,226))
    # title and subtle frame
    centered(d,"آخر قطعة خبز",70,font,(255,224,160),2)
    d.rectangle((18,18,W-18,H-18),outline=(78,84,98),width=2)
    return im
# Render frames directly into ffmpeg to avoid thousands of temporary images.
cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-crf","22","-pix_fmt","yuv420p","output/silent.mp4"]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(FPS*DURATION):
    p.stdin.write(frame(i/FPS).tobytes())
p.stdin.close()
if p.wait()!=0: raise RuntimeError("FFmpeg video encoding failed")
narration="""في ليلة باردة، كان شاب فقير يمشي وحيداً.
لم يكن يملك مالاً، ولا حتى عشاءً.
وفجأة، وجد قطعة خبز صغيرة على الأرض.
فرح بها، فهي كل ما سيأكله تلك الليلة.
لكن قبل أن يأكل، رأى رجلاً جائعاً بالكاد يستطيع الوقوف.
تردد الشاب... فهو جائع أيضاً.
ثم نظر إلى الخبز، وقسمه نصفين، وأعطى الرجل نصفه.
ابتسم الغريب وقال: كنت أملك طعاماً، ولم أكن جائعاً.
كنت أختبر إن كان هناك من يشارك غيره رغم حاجته.
ثم أخرج طعاماً كافياً، وتقاسمه مع الشاب.
في تلك الليلة تعلّم الشاب درساً لن ينساه:
الخير لا يُقاس بما تملك، بل بما تعطي.
فحتى القليل، إذا خرج من قلب صادق، قد يصنع فرقاً كبيراً."""
open("output/narration.txt","w",encoding="utf-8").write(narration)
subprocess.run(["espeak-ng","-v","ar","-s","132","-p","42","-f","output/narration.txt","-w","output/voice.wav"],check=True)
# Fit narration into 72 seconds; add a gentle original synthesized musical bed.
with wave.open("output/voice.wav","rb") as wf:
    params=wf.getparams(); audio=wf.readframes(wf.getnframes())
voice_duration=params.nframes/params.framerate
# Use ffmpeg to pad voice and mix a soft low-volume tonal bed.
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","output/silent.mp4","-i","output/voice.wav",
 "-filter_complex", "sine=frequency=196:duration=72,volume=0.035[m];[1:a]apad,atrim=0:72,volume=1.35[v];[v][m]amix=inputs=2:duration=longest:normalize=0[a]",
 "-map","0:v","-map","[a]","-t","72","-c:v","copy","-c:a","aac","-b:a","128k","-shortest",
 "output/last_piece_of_bread.mp4"],check=True)
print(f"Created output/last_piece_of_bread.mp4 (voice {voice_duration:.1f}s, total 72s)")
