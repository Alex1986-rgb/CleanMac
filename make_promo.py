#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Генерация промо-графики KRYLAN: hero-баннер и OG-карточка.
from PIL import Image, ImageDraw, ImageFont
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "icon_1024.png")
SFNS = "/System/Library/Fonts/SFNS.ttf"

def font(sz):
    try: return ImageFont.truetype(SFNS, sz)
    except Exception: return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", sz)

def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def gradient(w, h, top, bot):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(top, bot, y/h))
    return img

def rounded_icon(size):
    ic = Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS)
    return ic

def banner(w, h, out, title_sz, slogan_sz, with_features=True):
    img = gradient(w, h, (24, 32, 48), (12, 17, 26)).convert("RGBA")
    d = ImageDraw.Draw(img)
    # подсветка
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([w*0.2, -h*0.4, w*0.8, h*0.5], fill=(55, 211, 154, 30))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    # иконка
    isz = int(h*0.42)
    ic = rounded_icon(isz)
    iy = int(h*0.18)
    img.paste(ic, (int(w*0.08), iy), ic)
    tx = int(w*0.08) + isz + int(w*0.04)
    # заголовок
    d.text((tx, iy + int(isz*0.04)), "KRYLAN", font=font(title_sz), fill=(238, 242, 248))
    d.text((tx, iy + int(isz*0.04) + int(title_sz*1.05)), "Дай устройству крылья",
           font=font(slogan_sz), fill=(55, 211, 154))
    d.text((tx, iy + int(isz*0.04) + int(title_sz*1.05) + int(slogan_sz*1.4)),
           "Оптимизатор для macOS · iPhone · Android", font=font(int(slogan_sz*0.66)), fill=(138, 148, 166))
    if with_features:
        feats = ["Дашборд", "Умная очистка", "Автопилот", "Приватность", "Защита"]
        fy = int(h*0.80); fx = int(w*0.08); fnt = font(int(h*0.045))
        chip = font(int(h*0.045))
        x = fx
        for fcap in feats:
            tw = d.textlength("•  " + fcap, font=chip)
            d.text((x, fy), "•  " + fcap, font=chip, fill=(206, 214, 228))
            x += tw + int(w*0.03)
    img.convert("RGB").save(out)
    print("✓", out)

banner(1280, 640, os.path.join(HERE, "docs/hero.png"), 120, 52)
banner(1200, 630, os.path.join(HERE, "docs/og.png"), 110, 48, with_features=False)
