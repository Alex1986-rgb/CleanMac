# KRYLAN — общие утилиты для всех Python-приложений экосистемы (CleanMac, KRYLAN Desktop).
# Единый источник истины, чтобы форматирование/логика не расходились между приложениями.

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
