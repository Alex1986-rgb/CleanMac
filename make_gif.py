#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Анимированное demo-GIF KRYLAN для лендинга (без записи экрана).
from PIL import Image, ImageDraw, ImageFont
import os, math

HERE = os.path.dirname(os.path.abspath(__file__))
SFNS = "/System/Library/Fonts/SFNS.ttf"
W, H = 720, 380
BG0, GLASS, TRACK, TEXT, MUTED = (17,21,29), (34,43,58), (51,61,78), (238,242,248), (138,148,166)
GREEN, BLUE, YELLOW = (55,211,154), (75,140,249), (246,187,69)

def font(sz):
    try: return ImageFont.truetype(SFNS, sz)
    except Exception: return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", sz)

def ring(d, cx, cy, r, frac, color, w=16):
    d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=TRACK, width=w)
    if frac > 0.01:
        d.arc([cx-r,cy-r,cx+r,cy+r], -90, -90+frac*360, fill=color, width=w)

def ease(t): return 1-(1-t)*(1-t)

_ICON = Image.open(os.path.join(HERE, "icon_1024.png")).convert("RGBA").resize((48, 48), Image.LANCZOS)

def frame(i, n):
    img = Image.new("RGB", (W, H), BG0); d = ImageDraw.Draw(img)
    # шапка: иконка + бренд
    img.paste(_ICON, (34, 26), _ICON)
    d.text((92, 30), "KRYLAN", font=font(34), fill=TEXT)
    d.text((94, 74), "Дай устройству крылья", font=font(18), fill=GREEN)
    # карточка
    d.rounded_rectangle([34, 116, W-34, H-30], radius=18, fill=GLASS)
    half = n//2
    if i < half:                       # фаза 1: анализ, кольца заполняются
        p = ease(i/half)
        cpu, ram, disk = 34*p, 58*p, 71*p
        caption, cap_col = f"Анализ системы… {int(p*100)}%", MUTED
    else:                              # фаза 2: очистка, освобождено
        cpu, ram, disk = 22, 41, 64    # после очистки нагрузка ниже
        caption, cap_col = "✨ Освобождено 2.4 ГБ · память разгружена", GREEN
    rings = [("CPU", cpu, BLUE), ("ОЗУ", ram, YELLOW), ("ДИСК", disk, GREEN)]
    for k,(lbl,val,col) in enumerate(rings):
        cx = 150 + k*210; cy = 210
        ring(d, cx, cy, 52, val/100, col)
        d.text((cx, cy-12), f"{int(val)}%", font=font(26), fill=TEXT, anchor="mm")
        d.text((cx, cy+66), lbl, font=font(14), fill=MUTED, anchor="mm")
    d.text((W//2, H-52), caption, font=font(18), fill=cap_col, anchor="mm")
    return img

N = 30
frames = [frame(i, N) for i in range(N)]
# подержим финальный кадр подольше
frames += [frames[-1]]*8
out = os.path.join(HERE, "docs/demo.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
print("✓", out, f"({os.path.getsize(out)//1024} КБ)")
