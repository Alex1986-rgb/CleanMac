# KRYLAN — общие утилиты для всех Python-приложений экосистемы (CleanMac, KRYLAN Desktop).
# Единый источник истины, чтобы форматирование/логика не расходились между приложениями.
import re


def human(n):
    """Человекочитаемый размер: 1536 → '1.5 КБ', 0 → '0 Б'."""
    n = float(n)
    for u in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024 or u == "ТБ":
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024


def load_color(p, green, yellow, red):
    """Цвет по нагрузке (семафор DESIGN.md): <60 green · 60–85 yellow · >85 red.
    Цвета передаются вызывающим (у приложений своя палитра/темы)."""
    return green if p < 60 else (yellow if p < 85 else red)


def ver_tuple(s):
    """Версия '2.29.0' → (2,29,0) для корректного числового сравнения.
    Строковое сравнение ошибается ('2.9' > '2.29'); числовое — нет."""
    try:
        return tuple(int(x) for x in str(s).strip().split("."))
    except Exception:
        return (0,)


def disk_advice(disk_pct, ram_pct, batt_pct=None):
    """Краткие безопасные рекомендации по метрикам. Возвращает [(иконка, текст)].
    Чистая функция — без побочных эффектов, удобно тестировать."""
    advice = []
    if disk_pct >= 90:
        advice.append(("🔴", f"Диск заполнен на {int(disk_pct)}% — запустите Умную очистку и проверьте «Крупные файлы»."))
    elif disk_pct >= 80:
        advice.append(("🟡", f"Диск на {int(disk_pct)}% — стоит очистить кэши и старые загрузки."))
    if ram_pct >= 85:
        advice.append(("🔴", f"Память загружена на {int(ram_pct)}% — закройте лишние приложения или разгрузите автопилотом."))
    elif ram_pct >= 70:
        advice.append(("🟡", f"Память на {int(ram_pct)}% — близко к пределу."))
    if batt_pct is not None and 0 < batt_pct <= 20:
        advice.append(("🟡", f"Низкий заряд ({int(batt_pct)}%) — подключите зарядку."))
    if not advice:
        advice.append(("🟢", "Система в порядке — критичных проблем нет."))
    return advice


def parse_brew_outdated(text, kind):
    """Парсит вывод `brew outdated --verbose`: 'name (cur) < new' / 'name (cur) != new'.
    Возвращает [(name, cur, new, kind)]. Чистая функция — тестируемая."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line: continue
        m = re.match(r"^(\S+)\s+\((.+?)\)\s*(?:<|!=|->|≠)\s*(.+)$", line)
        if m:
            out.append((m.group(1), m.group(2).strip(), m.group(3).strip(), kind))
        else:
            out.append((line.split()[0], "?", "новее", kind))
    return out


def squarify(sizes, x, y, dx, dy):
    """Squarified treemap: возвращает прямоугольники (rx,ry,rw,rh) в порядке sizes.
    sizes — по убыванию; нормируются под площадь dx*dy. Чистый алгоритм."""
    sizes=[s for s in sizes if s>0]
    if not sizes or dx<=0 or dy<=0: return []
    total=sum(sizes); scaled=[s/total*(dx*dy) for s in sizes]
    rects=[]
    def worst(row, w):
        s=sum(row); mx=max(row); mn=min(row)
        if s<=0 or w<=0 or mn<=0: return float("inf")
        return max(w*w*mx/(s*s), s*s/(w*w*mn))
    def layout(row, x, y, dx, dy):
        covered=sum(row)
        if dx>=dy:
            width=covered/dy if dy else 0; yy=y
            for r in row:
                h=r/width if width else 0; rects.append((x,yy,width,h)); yy+=h
            return x+width,y,dx-width,dy
        else:
            height=covered/dx if dx else 0; xx=x
            for r in row:
                wv=r/height if height else 0; rects.append((xx,y,wv,height)); xx+=wv
            return x,y+height,dx,dy-height
    row=[]; i=0
    while i<len(scaled):
        r=scaled[i]; w=min(dx,dy)
        if not row or worst(row+[r], w) <= worst(row, w):
            row.append(r); i+=1
        else:
            x,y,dx,dy=layout(row,x,y,dx,dy); row=[]
    if row: layout(row,x,y,dx,dy)
    return rects
