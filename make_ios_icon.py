#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Иконка приложения для iOS/Android: полноразмерный квадрат 1024 без прозрачности.
from PIL import Image, ImageDraw
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
S = 1024
img = Image.new("RGBA", (S, S))
d = ImageDraw.Draw(img)

def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))
top, bot = (32, 201, 151), (15, 88, 120)
for y in range(S):
    d.line([(0, y), (S, y)], fill=lerp(top, bot, y/S) + (255,))

# мягкая подсветка сверху
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([120, -260, S-120, S//2], fill=(255, 255, 255, 34))
img = Image.alpha_composite(img, glow)
d = ImageDraw.Draw(img)

cx = cy = S // 2
r, w = 300, 78
box = [cx-r, cy-r, cx+r, cy+r]
d.arc(box, 0, 360, fill=(255, 255, 255, 60), width=w)
d.arc(box, -90, -90 + int(360*0.76), fill=(255, 255, 255, 235), width=w)
for ang in (-90, -90 + int(360*0.76)):
    px = cx + r*math.cos(math.radians(ang)); py = cy + r*math.sin(math.radians(ang))
    d.ellipse([px-w/2, py-w/2, px+w/2, py+w/2], fill=(255, 255, 255, 235))
d.line([(cx-95, cy+10), (cx-25, cy+80), (cx+110, cy-75)], fill=(255, 255, 255, 255), width=64, joint="curve")

def star(x, y, rr):
    pts = []
    for i in range(8):
        a = math.pi/4 * i; rad = rr if i % 2 == 0 else rr*0.4
        pts.append((x + rad*math.cos(a), y + rad*math.sin(a)))
    d.polygon(pts, fill=(255, 255, 255, 230))
star(cx+205, cy-205, 46); star(cx+255, cy-120, 24)

out = os.path.join(HERE, "krylan-swift/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
img.convert("RGB").save(out)            # без альфы — требование iOS
print("✓", out)
