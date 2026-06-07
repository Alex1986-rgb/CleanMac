#!/usr/bin/env python3
# Генерация иконки CleanMac: градиентный squircle + кольцевая шкала + блик.
from PIL import Image, ImageDraw
import math, os

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# --- squircle-фон с вертикальным градиентом ---
def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))
top, bot = (32, 201, 151), (15, 88, 120)        # бирюза → синий
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    gd.line([(0, y), (S, y)], fill=lerp(top, bot, y/S) + (255,))

# маска скруглённого квадрата (squircle через superellipse)
mask = Image.new("L", (S, S), 0)
md = ImageDraw.Draw(mask)
margin = 96
md.rounded_rectangle([margin, margin, S-margin, S-margin], radius=210, fill=255)
img.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(img)

cx = cy = S // 2

# --- мягкая внутренняя подсветка сверху ---
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
gdr = ImageDraw.Draw(glow)
gdr.ellipse([margin+40, margin-120, S-margin-40, cy], fill=(255, 255, 255, 38))
glow.putalpha(Image.composite(glow.getchannel("A"), Image.new("L", (S, S), 0), mask))
img = Image.alpha_composite(img, glow)
d = ImageDraw.Draw(img)

# --- кольцевая шкала (трек + дуга ~76%) ---
r = 300
w = 78
box = [cx-r, cy-r, cx+r, cy+r]
d.arc(box, 0, 360, fill=(255, 255, 255, 60), width=w)          # трек
d.arc(box, -90, -90 + int(360*0.76), fill=(255, 255, 255, 235), width=w)  # заполнение
# скруглённые концы дуги
for ang in (-90, -90 + int(360*0.76)):
    px = cx + r*math.cos(math.radians(ang))
    py = cy + r*math.sin(math.radians(ang))
    d.ellipse([px-w/2, py-w/2, px+w/2, py+w/2], fill=(255, 255, 255, 235))

# --- центральная «галочка» (оптимизировано) ---
d.line([(cx-95, cy+10), (cx-25, cy+80), (cx+110, cy-75)],
       fill=(255, 255, 255, 255), width=64, joint="curve")

# --- блик-искра ---
def star(dr, x, y, rr):
    pts = []
    for i in range(8):
        ang = math.pi/4 * i
        rad = rr if i % 2 == 0 else rr*0.4
        pts.append((x + rad*math.cos(ang), y + rad*math.sin(ang)))
    dr.polygon(pts, fill=(255, 255, 255, 230))
star(d, cx+205, cy-205, 46)
star(d, cx+255, cy-120, 24)

out_png = os.path.expanduser("~/mac-optimizer/cleaner/icon_1024.png")
img.save(out_png)
print("✓ PNG:", out_png)
