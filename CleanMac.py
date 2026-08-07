#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN · CleanMac — оптимизатор для macOS со «стеклянным» интерфейсом.
Слоган: «Дай устройству крылья».
Создатель: Кырлан Александр Сергеевич.
Дашборд с диаграммами, автопилот, очистка в Корзину, инструменты,
проверка обновлений (GitHub) и Pro-каркас. Запуск: framework-python 3.12.
"""
import os, time, shutil, hashlib, threading, queue, subprocess, collections, math, re, json, random, fcntl
import sys
import urllib.request
try:
    import psutil
except Exception:
    psutil = None

# ---------- сеть (интернет): скорость вниз/вверх ----------
_net_prev = {"t": None, "down": 0, "up": 0}

def _net_counters_netstat():
    """Суммарные байты recv/sent по всем физическим интерфейсам через netstat -ib.
    Резерв, когда psutil недоступен (например, не попал в .app-бандл)."""
    try:
        out = subprocess.run(["/usr/sbin/netstat", "-ib"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    recv = sent = 0; seen = set()
    for line in out.splitlines()[1:]:
        f = line.split()
        # строка-агрегат интерфейса помечена <Link#..> в колонке Network
        if len(f) < 10 or f[0] == "lo0" or not f[2].startswith("<Link"):
            continue
        if f[0] in seen:
            continue
        seen.add(f[0])
        try:
            recv += int(f[6]); sent += int(f[9])
        except (ValueError, IndexError):
            continue
    return (recv, sent) if seen else None

def _net_raw_counters():
    """(bytes_recv, bytes_sent) от psutil, иначе от netstat. None — если никак."""
    if psutil is not None:
        try:
            io = psutil.net_io_counters()
            return (io.bytes_recv, io.bytes_sent)
        except Exception:
            pass
    return _net_counters_netstat()

def stat_net():
    """Текущая скорость сети (байт/с) как (down, up)."""
    c = _net_raw_counters()
    if c is None:
        return (0.0, 0.0)
    recv, sent = c; now = time.time()
    if _net_prev["t"] is None:
        _net_prev.update({"t": now, "down": recv, "up": sent})
        return (0.0, 0.0)
    dt = max(0.5, now - _net_prev["t"])
    down = max(0, (recv - _net_prev["down"]) / dt)
    up = max(0, (sent - _net_prev["up"]) / dt)
    _net_prev.update({"t": now, "down": recv, "up": sent})
    return (down, up)
import tkinter as tk
from tkinter import messagebox, filedialog

# Общий модуль экосистемы (рядом с этим файлом; в т.ч. внутри .app-бандла).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from krylan_core import human, ver_tuple, disk_advice, parse_brew_outdated, squarify  # noqa: E402

VERSION = "2.56.0"
BRAND   = "KRYLAN"
SLOGAN  = "Дай устройству крылья"
AUTHOR  = "Кырлан Александр Сергеевич"
REPO    = "Alex1986-rgb/CleanMac"          # для проверки обновлений
BUY_URL = "https://alex1986-rgb.gumroad.com/l/cleanmac"   # ссылка на Pro (заглушка)
HOME  = os.path.expanduser("~")
TRASH = os.path.join(HOME, ".Trash")
OPT   = os.path.join(HOME, "mac-optimizer")
# Исходники стража (ставятся в OPT установщиком autopilot/install.sh).
AP_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autopilot")
CFG   = os.path.join(HOME, ".config", "cleanmac")
LIC   = os.path.join(CFG, "license")
LANG_FILE = os.path.join(CFG, "lang")

# ---------- глубокая корзина ----------
# Главное: ~/.Trash часто пустая, а место душит СИСТЕМНАЯ корзина тома
# (/System/Volumes/Data/.Trashes/UID) — туда уходят удаления из /Applications
# и т.п., и там копятся десятки гигабайт незаметно.
def trash_locations():
    """Все корзины пользователя: ~/.Trash + системная корзина тома + тома в /Volumes."""
    uid = os.getuid()
    cands = [TRASH, f"/System/Volumes/Data/.Trashes/{uid}", f"/.Trashes/{uid}"]
    vols = "/Volumes"
    if os.path.isdir(vols):
        try:
            for v in os.listdir(vols):
                cands.append(os.path.join(vols, v, ".Trashes", str(uid)))
        except OSError:
            pass
    seen, out = set(), []
    for p in cands:
        rp = os.path.realpath(p)
        if rp in seen or not os.path.isdir(p):
            continue
        seen.add(rp); out.append(p)
    return out

def deep_trash_size():
    """Суммарный размер всех корзин в байтах (du, пути свои — без sudo)."""
    total = 0
    for p in trash_locations():
        try:
            r = subprocess.run(["/usr/bin/du", "-sk", p], capture_output=True, text=True, timeout=60)
            kb = (r.stdout.split("\t")[0].strip() if r.stdout else "")
            if kb.isdigit():
                total += int(kb) * 1024
        except Exception:
            pass
    return total

def trash_count():
    """Сколько объектов в Корзине по версии Finder (агрегирует все тома)."""
    try:
        r = subprocess.run(["osascript", "-e", 'tell application "Finder" to count items of trash'],
                           capture_output=True, text=True, timeout=30)
        n = r.stdout.strip()
        return int(n) if n.isdigit() else None
    except Exception:
        return None

# ---------- локализация (RU/EN) ----------
def _load_lang():
    try:
        v=open(LANG_FILE).read().strip()
        if v in ("ru","en"): return v
    except Exception: pass
    try:
        import locale; loc=(locale.getlocale()[0] or "")
        return "ru" if loc.lower().startswith("ru") else "en"
    except Exception: return "ru"
LANG = _load_lang()
TR = {
    "Дашборд":"Dashboard","Умная очистка":"Smart Scan","Приватность":"Privacy","Защита":"Protection",
    "Автопилот":"Autopilot","Очистка":"Cleanup","Инструменты":"Tools","Pro / О программе":"Pro / About",
    "Состояние системы в реальном времени":"Real-time system status",
    "☀️ Яркость 100%":"☀️ Brightness 100%","✨ Умная очистка":"✨ Smart Scan","🚀 Автопилот":"🚀 Autopilot",
    "Анализ":"Analyze","Очистить":"Clean","Готово к анализу":"Ready to analyze",
    "Расширения браузеров":"Browser extensions",
    "Установленные расширения Chrome / Edge / Brave. Только просмотр — не удаляем.":
        "Installed Chrome / Edge / Brave extensions. View only — nothing is removed.",
    "🔎 Сканирую…":"🔎 Scanning…",
    "💡 Чтобы отключить или удалить расширение — сделайте это в самом браузере "
    "(меню → Расширения). Safari-расширения управляются в Настройках Safari.":
        "💡 To disable or remove an extension, do it in the browser itself "
        "(menu → Extensions). Safari extensions are managed in Safari Settings.",
    "Расширения не найдены (браузеры Chromium не установлены или нет профилей).":
        "No extensions found (Chromium browsers are not installed or have no profiles).",
    "Всего расширений: ":"Total extensions: ",
    "Вложения Почты":"Mail Attachments",
    "Найдено":"Found",
    "  Крупных вложений не найдено.":"  No large attachments found.",
    "Крупные вложения Apple Mail (> 5 МБ). Сами письма не удаляются; "
    "на IMAP вложение можно скачать заново.":
        "Large Apple Mail attachments (> 5 MB). The emails themselves are not "
        "deleted; on IMAP an attachment can be downloaded again.",
    "Крупные вложения Apple Mail (> 5 МБ). Отметьте лишние → в Корзину. "
    "Сами письма не удаляются; на IMAP вложение можно скачать заново.":
        "Large Apple Mail attachments (> 5 MB). Check unneeded ones → Trash. "
        "The emails themselves are not deleted; on IMAP an attachment can be "
        "downloaded again.",
    # --- 🗜 Сжать базы браузеров (VACUUM) ---
    "🗜 Сжать базы браузеров":"🗜 Compact browser databases",
    "Сжатие баз браузеров":"Compacting browser databases",
    "Перепаковка баз SQLite (VACUUM) без потери данных. Только для закрытых "
    "браузеров — запущенные пропускаются.":
        "Repacking SQLite databases (VACUUM) without data loss. Closed browsers "
        "only — running ones are skipped.",
    "Найдено баз: ":"Databases found: ",
    "  Баз для сжатия не найдено.":"  No databases to compact found.",
    "⚠️ Сначала закройте: ":"⚠️ Close these first: ",
    " — их базы заняты и будут пропущены.":
        " — their databases are locked and will be skipped.",
    "🗜 Сжать закрытые браузеры":"🗜 Compact closed browsers",
    "Сжать базы закрытых браузеров?\nДанные не удаляются — только перепаковка "
    "(VACUUM).":
        "Compact databases of closed browsers?\nNo data is deleted — repack only "
        "(VACUUM).",
    "Сжато баз: ":"Databases compacted: ",
    " · сэкономлено ":" · saved ",
    " · пропущено (браузер запущен): ":" · skipped (browser running): ",
    "Все найденные браузеры запущены — закройте их и повторите.":
        "All found browsers are running — close them and try again.",
    # --- 📦🕒 Большие и старые ---
    "📦🕒 Большие и старые":"📦🕒 Big & old",
    "Большие и старые файлы":"Big & old files",
    "Крупные файлы, которые давно не открывали и не меняли (размер × возраст). "
    "Отметьте лишние → в Корзину.":
        "Large files untouched and unchanged for a long time (size × age). Check "
        "unneeded ones → Trash.",
    "  Больших старых файлов не найдено.":"  No big old files found.",
    "Размер ≥":"Size ≥","Возраст ≥":"Age ≥",
    "МБ":"MB","дн":"days",

    # --- Семейства инструментов ---
    "🔍 Найти и освободить":"🔍 Find & free up","🧩 Приложения":"🧩 Applications",
    "🌐 Браузеры":"🌐 Browsers","🩺 Система":"🩺 System",
    "📦 Крупные файлы":"📦 Large files","🕒 Старые загрузки":"🕒 Old downloads",
    "👯 Дубликаты":"👯 Duplicates","📸 Скриншоты":"📸 Screenshots",
    "📧 Вложения Почты":"📧 Mail attachments","🧰 Dev-мусор":"🧰 Dev junk",
    "🗺 Карта диска":"🗺 Disk map","♻️ Корзина":"♻️ Trash",
    "🧩 Деинсталлятор":"🧩 Uninstaller","🧹 Остатки":"🧹 Leftovers",
    "⚙️ Автозагрузка":"⚙️ Login items","📦 Апдейтер":"📦 Updater",
    "🌐 Следы браузеров":"🌐 Browser traces","🧩 Расширения":"🧩 Extensions",
    "🗜 Сжать базы":"🗜 Compact databases","🩺 Обслуживание":"🩺 Maintenance",
    "🔥 Шредер":"🔥 Shredder","📜 История":"📜 History",

    # --- Дашборд ---
    "В РЕАЛЬНОМ ВРЕМЕНИ":"REAL TIME","♥ ПУЛЬС СИСТЕМЫ":"♥ SYSTEM PULSE",
    "СИСТЕМА · РЕАЛЬНОЕ ВРЕМЯ":"SYSTEM · REAL TIME","🌐 ИНТЕРНЕТ":"🌐 INTERNET",
    "✨ Оптимизировать  ":"✨ Optimize  ","  ✨ Оптимизировать  ":"  ✨ Optimize  ",
    "✨ Оптимизирую…  ":"✨ Optimizing…  ","✓ Оптимизировано  ":"✓ Optimized  ",
    "✨ Готово — Mac оптимизирован":"✨ Done — Mac optimized",
    "Выполнено на этом Mac:":"Done on this Mac:",
    "Пропущено (неприменимо на этом Mac):":"Skipped (not applicable on this Mac):",
    "Чисто! Нечего освобождать.":"Clean! Nothing to free up.",
    "можно освободить безопасно":"can be freed safely",
    "оцениваю объём…":"estimating size…",

    # --- Общие состояния ---
    "Анализирую…":"Analyzing…","Очищаю…":"Cleaning…","Сканирую…":"Scanning…",
    "🔎 Считаю размеры…":"🔎 Calculating sizes…","⏳ Тестирую…":"⏳ Testing…",
    "Сканирую обновления…":"Scanning for updates…",
    "🔎 Ищу артефакты сборки…":"🔎 Looking for build artifacts…",
    "🔎 Сканирую точки автозапуска…":"🔎 Scanning startup items…",
    "Ничего не найдено.":"Nothing found.","Файлы не выбраны.":"No files selected.",
    "Дубликатов не найдено.":"No duplicates found.",
    "Скриншотов не найдено.":"No screenshots found.",
    "Старых загрузок не найдено.":"No old downloads found.",
    "Артефактов сборки не найдено.":"No build artifacts found.",
    "✅ Все приложения обновлены.":"✅ All apps are up to date.",
    "✅ Осиротевших данных не найдено.":"✅ No orphaned data found.",
    "✅ Подозрительных объектов не обнаружено":"✅ No suspicious items detected",
    "✅ Готово: ":"✅ Done: ","Открыть →":"Open →","Удалить…":"Delete…",
    "↑ вверх":"↑ up","Старше:":"Older than:",
    "Отметьте, что очистить":"Check what to clean",

    # --- Автопилот ---
    "Фоновый страж следит за памятью и при пике сам чистит и разгружает.":
        "A background guard watches memory and cleans up on a peak by itself.",
    "Журнал автопилота:":"Autopilot log:",
    "⚪️ НЕ УСТАНОВЛЕН":"⚪️ NOT INSTALLED","🟢 РАБОТАЕТ":"🟢 RUNNING",
    "🔴 ОСТАНОВЛЕН":"🔴 STOPPED","Включить":"Enable","Выключить":"Disable",
    "  Разрешить автопилоту закрывать фоновые браузеры при пике памяти":
        "  Allow the autopilot to close background browsers on a memory peak",
    "⚡️ Оптимизировать сейчас":"⚡️ Optimize now",
    "🧊 Освободить место на диске":"🧊 Free up disk space",

    # --- Очистка ---
    "Один проход по всем безопасным категориям. Всё уходит в Корзину.":
        "One pass over all safe categories. Everything goes to the Trash.",
    "Пока пусто. После первой очистки здесь появится журнал.":
        "Empty for now. The log appears after the first cleanup.",
    "Пользовательские данные в порядке — дублей и крупных файлов не найдено.":
        "User data is fine — no duplicates or large files found.",
    "По всем параметрам — найдено для вашего ревью (не удалено):":
        "Across all checks — found for your review (nothing deleted):",
    "Очистка следов работы → в Корзину (обратимо). Браузеры должны быть закрыты.":
        "Clearing activity traces → Trash (reversible). Browsers must be closed.",

    # --- Инструменты ---
    "🏁 Бенчмарк диска":"🏁 Disk benchmark",
    "⏳ Идёт бенчмарк: пишу и читаю ~128 МБ во временный файл… пара секунд.":
        "⏳ Benchmark running: writing and reading ~128 MB to a temp file… a couple of seconds.",
    "Homebrew не найден. Установите с brew.sh, чтобы обновлять приложения отсюда.":
        "Homebrew not found. Install it from brew.sh to update apps from here.",
    "🔓 Не открывается?":"🔓 Won't open?","🔄 Обновления":"🔄 Updates",
    # --- состав памяти (пончик на дашборде) ---
    "занято":"used","Активная":"Active","Связанная":"Wired","Сжатая":"Compressed",
    "Неактивная":"Inactive","Свободная":"Free",
    # ведущие/хвостовые пробелы значимы — ключ должен совпадать байт в байт
    "  Артефактов сборки не найдено.":"  No build artifacts found.",
    "  Дубликатов не найдено.":"  No duplicates found.",
    "  Ничего не найдено.":"  Nothing found.",
    "  Старых загрузок не найдено.":"  No old downloads found.",
    "  ✓ Оптимизировано  ":"  ✓ Optimized  ",
    "  ✨ Оптимизирую…  ":"  ✨ Optimizing…  ",
    "«Анализ» посчитает объём, «Очистить» переместит в Корзину.":
        "“Analyze” measures the size, “Clean” moves items to the Trash.",
    "Эвристический поиск известного рекламного/нежелательного ПО в точках автозапуска. Не заменяет антивирус.":
        "Heuristic search for known adware/unwanted software in startup items. "
        "Not a replacement for an antivirus.",
}
def L(s):
    return TR.get(s, s) if LANG=="en" else s

# ---------- акценты: неоновые (HUD), близко к iOS-системным ----------
GREEN, BLUE, YELLOW, RED, PURPLE, CYAN = "#2fe5a0", "#2f8fff", "#ffd60a", "#ff5a52", "#a98bff", "#36d6ff"

# ---------- темы оформления (сгруппированные фоны как в iOS) ----------
THEMES = {
    # HUD navy: глубокий навигационный синий, панели-карточки, неоновые акценты
    "dark":  {"BG0":"#091327","BG1":"#15315a","SIDEBAR":"#0a1426","GLASS":"#102444",
              "GLASS_HI":"#1c3a66","TRACK":"#22436f","TEXT":"#e4eefb","MUTED":"#7088b2"},
    # iOS light: systemGroupedBackground + белые карточки
    "light": {"BG0":"#f2f2f7","BG1":"#ffffff","SIDEBAR":"#f2f2f7","GLASS":"#ffffff",
              "GLASS_HI":"#e5e5ea","TRACK":"#d1d1d6","TEXT":"#000000","MUTED":"#8e8e93"},
}
THEME_FILE = os.path.join(CFG, "theme")
def _load_theme():
    try:
        v=open(THEME_FILE).read().strip()
        if v in THEMES: return v
    except Exception: pass
    return "dark"

BG0=BG1=SIDEBAR=GLASS=GLASS_HI=TRACK=TEXT=MUTED=""
def apply_theme(name):
    global BG0,BG1,SIDEBAR,GLASS,GLASS_HI,TRACK,TEXT,MUTED,THEME
    THEME=name; p=THEMES.get(name, THEMES["dark"])
    BG0,BG1,SIDEBAR,GLASS,GLASS_HI,TRACK,TEXT,MUTED = (
        p["BG0"],p["BG1"],p["SIDEBAR"],p["GLASS"],p["GLASS_HI"],p["TRACK"],p["TEXT"],p["MUTED"])
THEME="dark"
apply_theme(_load_theme())

def col_for(p, inv=False):
    v = p if inv else 100 - p
    return GREEN if v >= 50 else YELLOW if v >= 25 else RED

# ---------- helpers ----------
def run(cmd, t=8):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout
    except Exception:
        return ""

def _lighten(hexc, amt=0.16):
    r,g,b = int(hexc[1:3],16), int(hexc[3:5],16), int(hexc[5:7],16)
    f = lambda c: min(255, int(c+(255-c)*amt))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"

def _blend(hexc, other, t):
    """Смешать цвет hexc с other на долю t (0..1). Для градиентов и свечения."""
    a = (int(hexc[1:3],16), int(hexc[3:5],16), int(hexc[5:7],16))
    b = (int(other[1:3],16), int(other[3:5],16), int(other[5:7],16))
    m = lambda i: max(0, min(255, int(a[i] + (b[i]-a[i])*t)))
    return f"#{m(0):02x}{m(1):02x}{m(2):02x}"

class RoundedButton(tk.Canvas):
    """Скруглённая кнопка (Apple/iOS-пилюля) на Canvas. Поддерживает configure(text=)/cget."""
    def __init__(self, parent, text, color, cmd, fg="white", radius=13,
                 padx=17, pady=9, font=("SF Pro Text", 13, "bold")):
        import tkinter.font as tkfont
        self._text=text; self._color=color; self._hov=_lighten(color)
        self._cmd=cmd; self._fg=fg; self._font=font; self._r=radius
        self._padx=padx; self._pady=pady; self._fnt=tkfont.Font(font=font)
        try: pbg=parent.cget("bg")
        except Exception: pbg=BG0
        super().__init__(parent, bg=pbg, highlightthickness=0, cursor="pointinghand")
        self._render(self._color)
        self.bind("<Enter>", lambda e: self._render(self._hov))
        self.bind("<Leave>", lambda e: self._render(self._color))
        self.bind("<Button-1>", lambda e: self._cmd())

    def _poly(self, x0,y0,x1,y1, r, **kw):
        pts=[x0+r,y0, x1-r,y0, x1,y0, x1,y0+r, x1,y1-r, x1,y1, x1-r,y1, x0+r,y1, x0,y1, x0,y1-r, x0,y0+r, x0,y0]
        return self.create_polygon(pts, smooth=True, **kw)

    def _render(self, col):
        tw=self._fnt.measure(self._text); th=self._fnt.metrics("linespace")
        gp=4
        pw=tw+self._padx*2; ph=th+self._pady*2
        w=pw+gp*2; h=ph+gp*2; r=min(self._r, ph//2)
        super().configure(width=w, height=h)
        self.delete("all")
        # HUD-свечение (halo) под кнопкой
        self._poly(1,1,w-1,h-1, r+gp, fill=_blend(col,BG0,0.55), outline="")
        # пилюля
        self._poly(gp,gp,w-gp,h-gp, r, fill=col, outline="")
        self.create_text(w/2, h/2, text=self._text, fill=self._fg, font=self._font)

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self._text=kw.pop("text"); self._render(self._color)
        if "bg" in kw: kw.pop("bg")
        if kw: super().configure(**kw)
    config = configure

    def cget(self, key):
        if key=="text": return self._text
        return super().cget(key)

# ---------- яркость экрана (приватный DisplayServices, без Accessibility) ----------
_DS=None; _DID=None
def _ds_init():
    global _DS,_DID
    if _DS is None:
        import ctypes
        cg=ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        cg.CGMainDisplayID.restype=ctypes.c_uint32; _DID=cg.CGMainDisplayID()
        ds=ctypes.CDLL("/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices")
        ds.DisplayServicesSetBrightness.argtypes=[ctypes.c_uint32, ctypes.c_float]
        ds.DisplayServicesGetBrightness.argtypes=[ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
        _DS=ds
    return _DS,_DID

def set_brightness(val):
    try:
        ds,did=_ds_init(); ds.DisplayServicesSetBrightness(did, float(val)); return True
    except Exception: return False

def get_brightness():
    try:
        import ctypes
        ds,did=_ds_init(); cur=ctypes.c_float(0)
        ds.DisplayServicesGetBrightness(did, ctypes.byref(cur)); return cur.value
    except Exception: return None

def path_size(p):
    if not os.path.exists(p): return 0
    # -P: не следовать по симлинкам. Иначе, если p — симлинк на каталог, du считал
    # размер ЧУЖОГО дерева (цели), завышая «освобождено» и вводя в заблуждение.
    try: return int(run(["/usr/bin/du", "-sk", "-P", p], 60).split("\t")[0]) * 1024
    except Exception: return 0

def _scan_size(path):
    """Размер каталога/файла в байтах через os.walk (без перехода по симлинкам).
    Чистая функция (без subprocess) — быстрая и тестируемая на temp-деревьях."""
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        try: return os.path.getsize(path)
        except OSError: return 0
    total = 0
    for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
        # не уходим в симлинки-каталоги
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
            except OSError:
                pass
    return total

def scan_old_downloads(base, min_days=90, top=200, now=None):
    """Старые файлы в папке загрузок: топ по размеру среди файлов старше ``min_days``.

    Возвращает отсортированный по убыванию размера список кортежей
    ``(size, path, age_days)``. Чистая ФС-функция (без subprocess/GUI) —
    тестируется на temp-дереве.

    Безопасность:
      * НЕ переходит по симлинкам-каталогам и НЕ считает симлинки-файлы
        (их размер/возраст обманчив, а удалять чужую цель нельзя);
      * пропускает защищённые/системные пути (``is_protected``);
      * «возраст» — по дате изменения (mtime) в днях, как в UI.
    Каталоги не возвращаются — только обычные файлы, чтобы удаление в Корзину
    било точечно по реальным загрузкам, а не по вложенным папкам.
    """
    if now is None:
        now = time.time()
    if not base or not os.path.isdir(base):
        return []
    cutoff = float(min_days) * 86400
    out = []
    for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
        # не уходим в симлинки-каталоги
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.islink(fp):           # симлинк-файл не трогаем
                    continue
                st = os.lstat(fp)
                age_sec = now - st.st_mtime
                if age_sec < cutoff:
                    continue
                if is_protected(fp):             # страховка от системных путей
                    continue
                out.append((st.st_size, fp, int(age_sec / 86400)))
            except OSError:
                pass
    out.sort(reverse=True)
    return out[:top] if top else out


def scan_mail_attachments(bases, min_mb=5, top=200):
    """Крупные файлы-вложения Apple Mail в указанных базовых каталогах.

    ``bases`` — список путей (обычно «Mail Downloads» и ~/Library/Mail).
    Возвращает отсортированный по убыванию размера список кортежей
    ``(size, path)`` для обычных файлов крупнее ``min_mb`` МБ.

    Чистая ФС-функция (без subprocess/GUI) — тестируется на temp-дереве.

    Безопасность (важно: сами письма не удаляются, на IMAP вложение можно
    скачать заново):
      * НЕ переходит по симлинкам-каталогам и НЕ считает симлинки-файлы
        (их размер обманчив, а удалять чужую цель нельзя);
      * пропускает защищённые/системные пути (``is_protected``);
      * каталоги не возвращаются — только обычные файлы, чтобы удаление в
        Корзину било точечно по конкретным вложениям.
    """
    cutoff = float(min_mb) * 1024 * 1024
    out, seen = [], set()
    for base in (bases or []):
        if not base or not os.path.isdir(base) or os.path.islink(base):
            continue
        for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
            # не уходим в симлинки-каталоги
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if os.path.islink(fp):           # симлинк-файл не трогаем
                        continue
                    st = os.lstat(fp)
                    if st.st_size < cutoff:
                        continue
                    if is_protected(fp):             # страховка от системных путей
                        continue
                    if fp in seen:                   # базы могут перекрываться
                        continue
                    seen.add(fp)
                    out.append((st.st_size, fp))
                except OSError:
                    pass
    out.sort(reverse=True)
    return out[:top] if top else out


# ---------- 🗜 Сжатие баз браузеров (VACUUM SQLite) ----------
# Семейство Chromium: User Data браузера внутри ~/Library/Application Support.
# Маппинг «процесс браузера → его UserData» для пропуска занятых файлов и поиска
# баз SQLite. Процесс — то, что видит app_running (через `ps -axo comm`).
SQLITE_CHROMIUM = [
    # (метка, имя процесса для app_running, относительный путь к User Data)
    ("Chrome", "Google Chrome",  "Google/Chrome"),
    ("Brave",  "Brave Browser",  "BraveSoftware/Brave-Browser"),
    ("Edge",   "Microsoft Edge", "Microsoft Edge"),
]
# Базы SQLite Chromium лежат БЕЗ расширения .sqlite (это файлы такого формата).
_CHROMIUM_DB_FILES = ("History", "Cookies", "Favicons", "Web Data", "Top Sites")


def vacuum_sqlite(path):
    """Сжать одну базу SQLite на месте через VACUUM. Возвращает (before, after)
    в байтах. Только sqlite3 из стандартной библиотеки; данные НЕ удаляются
    (VACUUM лишь перепаковывает файл). Любая ошибка/не-БД → (size, size)
    (изменений нет). Вызывать ТОЛЬКО при закрытом браузере — иначе файл занят
    и VACUUM либо упадёт, либо повредит данные. Чистая и тестируемая."""
    import sqlite3
    try:
        before = os.path.getsize(path)
    except OSError:
        return (0, 0)
    try:
        con = sqlite3.connect(path)
        try:
            con.execute("VACUUM")
            con.commit()
        finally:
            con.close()
    except Exception:
        return (before, before)
    try:
        after = os.path.getsize(path)
    except OSError:
        after = before
    return (before, after)


def browser_sqlite_dbs():
    """Файлы баз SQLite браузеров (history/cookies/favicons/web data), пригодные
    для VACUUM. Возвращает [(браузер, путь)] — только существующие обычные файлы.

    macOS:
      • Chromium (Chrome/Brave/Edge):
        ~/Library/Application Support/<UserData>/<Profile>/{History,Cookies,…}
        Профили: Default, Profile 1, … (БЕЗ расширения .sqlite);
      • Firefox: ~/Library/Application Support/Firefox/Profiles/*/*.sqlite.
    Чистая ФС-функция (без subprocess/GUI) — тестируется на temp-дереве."""
    import glob
    appsup = os.path.join(HOME, "Library/Application Support")
    out = []
    for browser, _proc, rel in SQLITE_CHROMIUM:
        base = os.path.join(appsup, rel)
        if not os.path.isdir(base):
            continue
        for prof in glob.glob(os.path.join(base, "*")):
            if not os.path.isdir(prof):
                continue
            for fn in _CHROMIUM_DB_FILES:
                fp = os.path.join(prof, fn)
                if os.path.isfile(fp) and not os.path.islink(fp):
                    out.append((browser, fp))
    ff = os.path.join(appsup, "Firefox/Profiles")
    for fp in glob.glob(os.path.join(ff, "*", "*.sqlite")):
        if os.path.isfile(fp) and not os.path.islink(fp):
            out.append(("Firefox", fp))
    return out


def scan_big_old(base, min_mb=200, min_days=180, top=100, now=None):
    """Файлы размером ≥ ``min_mb`` МБ И не открывавшиеся/менявшиеся ≥ ``min_days``
    дней. Возвращает отсортированный по размеру (убыв.) список
    ``(size, path, age_days)``.

    Это НЕ дубль «Старых загрузок» (только ~/Downloads, без порога размера) и
    не «Крупных файлов» (только размер, без возраста) — здесь фильтр размер ×
    возраст одновременно. Чистая ФС-функция (без subprocess/GUI) — тестируется
    на temp-дереве.

    Безопасно:
      • симлинки пропускаем (os.path.islink) — не идём по чужим целям;
      • is_protected() исключает защищённые/системные пути;
      • возраст = по max(mtime, atime) — «последнее касание» (открыли ИЛИ
        изменили);
      • ``now`` передаётся в тестах для детерминизма (по умолчанию time.time()).
    """
    if now is None:
        now = time.time()
    min_bytes = int(min_mb) * 1024 * 1024
    cutoff_age = int(min_days) * 86400
    out = []
    if not base or not os.path.isdir(base):
        return out
    for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
        # не уходим в симлинки-каталоги
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                if os.path.islink(fp):
                    continue
                st = os.lstat(fp)
                if st.st_size < min_bytes:
                    continue
                last_touch = max(st.st_mtime, st.st_atime)
                age = now - last_touch
                if age < cutoff_age:
                    continue
                if is_protected(fp):
                    continue
                out.append((st.st_size, fp, int(age // 86400)))
            except OSError:
                pass
    out.sort(reverse=True)
    return out[:top] if top else out


# Проектные артефакты сборки — безопасно удаляются и пересоздаются менеджером
# пакетов (npm install / cargo build / pod install / …). Часто занимают гигабайты.
DEV_JUNK_ALWAYS = {
    "node_modules": "npm/yarn", "__pycache__": "Python", ".pytest_cache": "pytest",
    ".mypy_cache": "mypy", ".ruff_cache": "ruff", ".terraform": "Terraform",
    ".turbo": "Turborepo", ".parcel-cache": "Parcel", ".next": "Next.js",
    ".nuxt": "Nuxt", ".svelte-kit": "SvelteKit",
}
# Неоднозначные имена — берём ТОЛЬКО при наличии манифеста-маркера рядом (иначе
# рискуем удалить не сборочную папку). Для venv маркер — pyvenv.cfg внутри самой папки.
DEV_JUNK_GATED = {
    "target": ("Cargo.toml", "pom.xml"),
    "build": ("build.gradle", "build.gradle.kts", "CMakeLists.txt"),
    "Pods": ("Podfile",),
    ".venv": ("pyvenv.cfg",),
    "venv": ("pyvenv.cfg",),
}

def scan_dev_junk(base, top=200):
    """Найти проектные артефакты сборки (node_modules, target, __pycache__, Pods,
    .venv, .next …) — крупные и безопасно пересоздаваемые. Возвращает
    отсортированный по размеру список ``(size, path, kind)``.

    Безопасно: симлинки не следуются; внутрь найденной папки не спускаемся (нет
    двойного счёта); неоднозначные имена берём только при манифесте рядом; ветки
    Library/.Trash пропускаем. Чистая ФС-функция — тестируется на temp-дереве."""
    out = []
    if not base or not os.path.isdir(base):
        return out
    for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))
                   and d not in ("Library", ".Trash")]
        pruned = []
        for d in list(dirs):
            full = os.path.join(root, d)
            kind = None
            if d in DEV_JUNK_ALWAYS:
                kind = DEV_JUNK_ALWAYS[d]
            elif d in DEV_JUNK_GATED:
                if d in (".venv", "venv"):
                    if os.path.exists(os.path.join(full, "pyvenv.cfg")): kind = "venv"
                elif any(os.path.exists(os.path.join(root, m)) for m in DEV_JUNK_GATED[d]):
                    kind = {"target": "Rust/Maven", "build": "Gradle/CMake", "Pods": "CocoaPods"}[d]
            if kind and not is_protected(full):
                sz = _scan_size(full)
                if sz > 0:
                    out.append((sz, full, kind))
                pruned.append(d)          # не спускаться внутрь артефакта
        for d in pruned:
            dirs.remove(d)
    out.sort(reverse=True)
    return out[:top] if top else out


# ---------- Расширения браузеров (read-only) ----------
# Семейство Chromium: каталоги профилей внутри Application Support.
CHROMIUM_BROWSERS = [
    ("Chrome", "Google/Chrome"),
    ("Edge",   "Microsoft Edge"),
    ("Brave",  "BraveSoftware/Brave-Browser"),
]


def parse_chromium_extension(manifest_dict, messages_dict=None):
    """Имя расширения Chromium из его ``manifest.json`` (как dict).

    Чистая функция (без ФС/subprocess/GUI) — легко тестируется.

      * ``manifest_dict`` — разобранный ``manifest.json`` расширения;
      * ``messages_dict`` — разобранный ``_locales/<locale>/messages.json``
        (нужен только для раскрытия плейсхолдеров вида ``__MSG_appName__``).

    Логика:
      * имя берётся из ключа ``name``;
      * если значение — плейсхолдер локализации ``__MSG_<key>__``, оно
        раскрывается через ``messages_dict[<key>]["message"]``
        (ключ нечувствителен к регистру, как в спецификации i18n);
      * если name отсутствует/пустой или раскрыть не удалось — возвращается
        пустая строка (вызывающий код подставит id).
    """
    if not isinstance(manifest_dict, dict):
        return ""
    name = manifest_dict.get("name") or ""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    m = re.fullmatch(r"__MSG_(.+?)__", name)
    if not m:
        return name
    key = m.group(1)
    if not isinstance(messages_dict, dict):
        return ""
    # ключи messages.json регистронезависимы
    entry = messages_dict.get(key)
    if entry is None:
        low = key.lower()
        for k, v in messages_dict.items():
            if isinstance(k, str) and k.lower() == low:
                entry = v
                break
    if isinstance(entry, dict):
        msg = entry.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
    return ""


def _chromium_ext_name(ext_dir):
    """Имя одного расширения по пути ``.../<id>/<version>`` (read-only ФС).

    Читает ``manifest.json`` и, при необходимости, ``messages.json`` из
    дефолтной локали (или ``en``). Любая ошибка → пустая строка.
    """
    mf = os.path.join(ext_dir, "manifest.json")
    try:
        with open(mf, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return ""
    name = parse_chromium_extension(manifest)
    if name:
        return name
    # нужен перевод плейсхолдера — ищем messages.json
    default_loc = manifest.get("default_locale") if isinstance(manifest, dict) else None
    candidates = []
    if isinstance(default_loc, str) and default_loc:
        candidates.append(default_loc)
    candidates.append("en")
    for loc in candidates:
        mp = os.path.join(ext_dir, "_locales", loc, "messages.json")
        try:
            with open(mp, "r", encoding="utf-8") as f:
                messages = json.load(f)
        except Exception:
            continue
        name = parse_chromium_extension(manifest, messages)
        if name:
            return name
    return ""


def list_browser_extensions(base=None):
    """Список установленных расширений Chromium-браузеров (read-only).

    Возвращает отсортированный список кортежей ``(браузер, имя, id)``.
    НИЧЕГО не удаляет и не изменяет. Graceful при отсутствии путей: если
    каталоги браузеров/профилей нет — вернётся ``[]``.

    ``base`` — корень ``Application Support`` (по умолчанию домашний); параметр
    нужен для тестов на временном дереве.
    """
    if base is None:
        base = os.path.join(HOME, "Library/Application Support")
    out = []
    seen = set()
    for label, rel in CHROMIUM_BROWSERS:
        broot = os.path.join(base, rel)
        if not os.path.isdir(broot):
            continue
        # профили: Default, Profile 1, ... — у каждого свой каталог Extensions
        try:
            profiles = sorted(os.listdir(broot))
        except OSError:
            continue
        for prof in profiles:
            exts_root = os.path.join(broot, prof, "Extensions")
            if not os.path.isdir(exts_root):
                continue
            try:
                ids = sorted(os.listdir(exts_root))
            except OSError:
                continue
            for ext_id in ids:
                id_dir = os.path.join(exts_root, ext_id)
                if ext_id.startswith(".") or not os.path.isdir(id_dir):
                    continue
                # самая свежая версия (последняя по сортировке)
                try:
                    vers = sorted(d for d in os.listdir(id_dir)
                                  if os.path.isdir(os.path.join(id_dir, d)))
                except OSError:
                    continue
                if not vers:
                    continue
                name = ""
                for ver in reversed(vers):
                    name = _chromium_ext_name(os.path.join(id_dir, ver))
                    if name:
                        break
                key = (label, ext_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append((label, name or ext_id, ext_id))
    out.sort(key=lambda r: (r[0], r[1].lower()))
    return out


def dir_tree(path, depth=2, min_frac=0.01, total=None, top_n=12):
    """Рекурсивно собирает дерево размеров подкаталогов до глубины ``depth``.

    Возвращает dict ``{name, path, size, children:[...]}``. Чистая функция
    (только файловая система), пригодна для тестов и для фонового воркера.

    - Недоступное пропускается (try/except).
    - Симлинки не раскрываются (os.path.islink) — защита от циклов.
    - Дети меньше ``min_frac`` от ``total`` сворачиваются в узел «Прочее».
    - Оставляется не более ``top_n`` крупнейших детей (+ «Прочее»),
      чтобы sunburst не порождал тысячи дуг.

    ``total`` — база для отсечки min_frac; если None, берётся размер корня.
    """
    path = os.path.abspath(path)
    name = os.path.basename(path.rstrip("/")) or path

    # Лист (достигли предела глубины или это файл/симлинк) — без детей.
    if depth <= 0 or os.path.islink(path) or not os.path.isdir(path):
        return {"name": name, "path": path, "size": _scan_size(path), "children": []}

    # Размеры прямых потомков.
    entries = []
    try:
        names = os.listdir(path)
    except OSError:
        names = []
    for child in names:
        cp = os.path.join(path, child)
        try:
            if os.path.islink(cp):
                continue  # симлинки не учитываем и не раскрываем
            sz = _scan_size(cp)
        except OSError:
            continue
        if sz > 0:
            entries.append((sz, cp, child))

    node_size = sum(sz for sz, _, _ in entries)
    base = total if total is not None else node_size
    cutoff = base * min_frac if base else 0

    entries.sort(reverse=True)  # по размеру, убыв.

    kept, rest_size = [], 0
    for sz, cp, child in entries:
        if sz < cutoff or len(kept) >= top_n:
            rest_size += sz
        else:
            kept.append((sz, cp, child))

    children = []
    for sz, cp, child in kept:
        if os.path.isdir(cp) and depth - 1 > 0:
            children.append(dir_tree(cp, depth - 1, min_frac, base, top_n))
        else:
            children.append({"name": child, "path": cp, "size": sz, "children": []})

    if rest_size > 0:
        children.append({"name": "Прочее", "path": path, "size": rest_size,
                         "children": [], "is_rest": True})

    return {"name": name, "path": path, "size": node_size, "children": children}


def app_running(name):
    return name.lower() in run(["/bin/ps", "-axo", "comm"]).lower()

# Пути, которые НИКОГДА нельзя перемещать в Корзину (защита от ошибки).
PROTECTED = {os.path.realpath(p) for p in (
    "/", HOME, "/System", "/Library", "/Applications", "/usr", "/bin", "/etc", "/var", "/private",
    os.path.join(HOME, "Library"), os.path.join(HOME, "Documents"), os.path.join(HOME, "Desktop"),
    os.path.join(HOME, "Downloads"), os.path.join(HOME, "Pictures"), os.path.join(HOME, "Movies"),
    os.path.join(HOME, "Music"), os.path.join(HOME, "Library/Keychains"),
    os.path.join(HOME, "Library/Caches"), os.path.join(HOME, "Library/Application Support"),
)}

def is_protected(path):
    """True, если путь — защищённый корень (его удалять нельзя; подпапки внутри — можно).

    Дополнительно (защита от ошибки): считаем «защищённым» любой пустой/относительный
    путь. Пустая строка или "." раскрываются через realpath в текущий рабочий каталог,
    а относительный путь — в произвольное место под ним; такие пути НИКОГДА не должны
    попадать под удаление. Удалять можно только явные абсолютные пути вне корней."""
    if not path or not os.path.isabs(path):
        return True
    rp = os.path.realpath(path)
    return rp in PROTECTED or rp == os.path.realpath(HOME) or len(rp.strip("/").split("/")) < 2

def to_trash(path):
    # lexists, а не exists: битый симлинк (цель отсутствует) тоже нужно уметь убрать
    # в Корзину — иначе шаг «битые файлы» молча ничего не делает. shutil.move
    # переносит сам симлинк, не следуя за ним.
    if not os.path.lexists(path): return False
    if is_protected(path): return False          # страховка: не трогаем системные/корневые папки
    base = os.path.basename(path.rstrip("/")) or "item"
    dest = os.path.join(TRASH, base)
    # Уникализация счётчиком, а не time.time(): два файла с одинаковым basename,
    # перемещённые в одну миллисекунду (частый случай в цикле очистки), раньше
    # давали одинаковый dest и второй shutil.move затирал первый → потеря данных.
    n = 0
    while os.path.lexists(dest):
        n += 1
        dest = os.path.join(TRASH, f"{base}-{int(time.time()*1000)}-{n}")
    try: shutil.move(path, dest); return True
    except Exception: return False

def leftover_match(entry, name, bid):
    """True, если элемент папки ~/Library/* — это «хвост» удаляемого приложения.

    Совпадение ТОЧНОЕ, а не по подстроке: иначе приложение с коротким/общим именем
    (напр. «Mail») увело бы в Корзину чужие данные — com.apple.mail, MailChimp,
    любые *mail*. Матчим по bundle-id (точно или его под-компоненты вида
    `<bid>.helper`) и, только если bid нет, по точной основе имени приложения.

    Чистая функция — тестируется без ФС/GUI."""
    low = (entry or "").lower()
    stem = low
    for suf in (".plist", ".savedstate", ".binarycookies"):
        if stem.endswith(suf):
            stem = stem[:-len(suf)]
            break
    if bid:
        b = bid.lower()
        if stem == b or stem.startswith(b + "."):
            return True
        return False            # есть bundle-id → имя-подстроку не используем (слишком широко)
    if name and len(name) >= 3:
        return stem == name.lower()   # точная основа, НЕ подстрока
    return False

def as_escape(s):
    """Экранирование строки для вставки в литерал AppleScript (osascript -e).
    Сначала обратный слэш, потом двойная кавычка — иначе `\\` перед `"` ломает
    экранирование. Защита от инъекции AppleScript через динамические имена/тексты."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')

def brew_path():
    for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew", shutil.which("brew")):
        if p and os.path.exists(p): return p
    return None

def brew_outdated():
    """Список устаревших пакетов Homebrew (formulae + casks). None — brew не установлен."""
    brew = brew_path()
    if not brew: return None
    items = parse_brew_outdated(run([brew, "outdated", "--verbose"], 90), "формула")
    items += parse_brew_outdated(run([brew, "outdated", "--cask", "--greedy", "--verbose"], 90), "приложение")
    return items

def installed_bundle_ids():
    """Множество bundle id и имён всех установленных .app (нижний регистр)."""
    import plistlib
    ids = set()
    for base in ("/Applications", os.path.join(HOME, "Applications"), "/System/Applications"):
        if not os.path.isdir(base): continue
        for name in os.listdir(base):
            if not name.endswith(".app"): continue
            ids.add(name[:-4].lower())
            try:
                with open(os.path.join(base, name, "Contents", "Info.plist"), "rb") as f:
                    bid = plistlib.load(f).get("CFBundleIdentifier")
                if bid: ids.add(bid.lower())
            except Exception: pass
    return ids

_RDNS_TLDS = {"com","org","net","io","co","app","dev","me","ru","cloud","xyz","us","de","fr","uk","ai","tv"}
def _is_orphan_name(name, ids):
    """True, если имя — настоящий reverse-DNS bundle id (com.vendor.app, ≥3 сегмента,
    известный TLD-префикс) без установленного .app. Apple/системное и обычные файлы не трогаем."""
    low = name.lower()
    if low.startswith(("com.apple.", "apple.", "group.com.apple")): return False
    parts = low.split(".")
    if len(parts) < 3: return False          # нужен com.vendor.app, а не default.store
    if parts[0] not in _RDNS_TLDS: return False
    if low in ids: return False
    for i in ids:
        if i == low or i.startswith(low + ".") or low.startswith(i + "."): return False
    return True

def orphaned_leftovers():
    """Осиротевшие данные удалённых программ в ~/Library. [(path, size)] по убыванию."""
    ids = installed_bundle_ids()
    out = []
    bases = [os.path.join(HOME, "Library", d) for d in
             ("Application Support", "Caches", "Preferences", "Containers", "Logs", "Saved Application State")]
    for base in bases:
        if not os.path.isdir(base): continue
        for name in os.listdir(base):
            stem = name
            for suf in (".plist", ".savedState"):
                if stem.endswith(suf): stem = stem[:-len(suf)]
            if _is_orphan_name(stem, ids):
                p = os.path.join(base, name)
                try: sz = path_size(p) if os.path.isdir(p) else os.path.getsize(p)
                except Exception: sz = 0
                out.append((p, sz))
    out.sort(key=lambda x: -x[1])
    return out

# ---------- безопасные находки для «волшебной кнопки» ----------
def find_empty_dirs(bases=None, max_per_base=4000):
    """Пустые (рекурсивно) подкаталоги внутри пользовательских кэшей/логов.

    Безопасно для авто-очистки: возвращает только каталоги, не содержащие
    НИ ОДНОГО файла на всю глубину (остаются лишь пустые вложенные папки).
    Никогда не отдаёт защищённые корни и сами базовые каталоги. Чистая
    ФС-функция — тестируется на temp-дереве.
    """
    if bases is None:
        bases = [os.path.join(HOME, "Library/Caches"), os.path.join(HOME, "Library/Logs")]
    found = []
    for base in bases:
        if not os.path.isdir(base):
            continue
        cnt = 0
        # снизу вверх: глубокие пустые папки попадают раньше родительских
        for root, dirs, files in os.walk(base, topdown=False, followlinks=False):
            if os.path.realpath(root) == os.path.realpath(base):
                continue                      # сам базовый каталог не трогаем
            if is_protected(root) or os.path.islink(root):
                continue
            try:
                # пусто, если нет файлов и все подкаталоги уже признаны пустыми
                has_file = bool(files)
                live_sub = any(os.path.join(root, d) not in found and not os.path.islink(os.path.join(root, d))
                               for d in dirs)
                if not has_file and not live_sub:
                    found.append(root); cnt += 1
            except OSError:
                continue
            if cnt >= max_per_base:
                break
    return found

def find_broken_files(bases=None, max_per_base=4000):
    """Нулевые (0 байт) обычные файлы и битые симлинки в кэшах/логах.

    Это «мусорные» артефакты прерванных загрузок/записей — удалять безопасно.
    Не трогает каталоги и непустые файлы. Возвращает список путей.
    """
    if bases is None:
        bases = [os.path.join(HOME, "Library/Caches"), os.path.join(HOME, "Library/Logs")]
    found = []
    for base in bases:
        if not os.path.isdir(base):
            continue
        cnt = 0
        for root, dirs, files in os.walk(base, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    if os.path.islink(fp):
                        if not os.path.exists(fp):     # битый симлинк
                            found.append(fp); cnt += 1
                    elif os.path.isfile(fp) and os.path.getsize(fp) == 0:
                        found.append(fp); cnt += 1
                except OSError:
                    continue
                if cnt >= max_per_base:
                    break
            if cnt >= max_per_base:
                break
    return found

# Декларативный план «волшебной кнопки»: список безопасных шагов по порядку.
# Каждый элемент — (ключ, человекочитаемая подпись). Чистые данные → тестируется,
# а воркер просто исполняет их по очереди и шлёт прогресс в UI-поток.
OPTIMIZE_STEPS = [
    ("caches",      "🧽 Кэши и логи приложений → Корзина"),
    ("syscache",    "👁 Системные кэши · Quick Look · кэш шрифтов"),
    ("snapshots",   "🧊 Локальные снимки APFS (очищаемое место)"),
    ("memory",      "⚡️ Разгрузка памяти (purge)"),
    ("emptydirs",   "📂 Пустые папки → Корзина"),
    ("broken",      "🧩 Битые и нулевые файлы → Корзина"),
    ("orphans",     "🧹 Остатки удалённых приложений → Корзина"),
    ("brewcleanup", "🍺 Homebrew: чистка старых версий формул"),
    ("launchsvc",   "🗂 Перестройка БД Launch Services («Открыть с помощью»)"),
    ("dockicons",   "🚀 Сброс кэша иконок · перезапуск Dock"),
    ("dns",         "🌐 Сброс кэша DNS"),
    ("trim",        "💽 SSD/TRIM: обслуживается системой автоматически"),
]

def optimize_plan():
    """Возвращает копию плана авто-оптимизации (порядок шагов и подписи).
    Чистая функция-оркестратор — удобно проверить состав/порядок тестом."""
    return list(OPTIMIZE_STEPS)

def _history_path():
    return os.path.join(OPT, "cleanup_history.json")

def record_cleanup(freed_bytes, kind="clean"):
    """Записывает факт очистки в историю: {ts, freed, kind}. Игнорирует нулевые."""
    if not freed_bytes or freed_bytes <= 0: return
    hist = cleanup_history()
    hist.append({"ts": int(time.time()), "freed": int(freed_bytes), "kind": kind})
    hist = hist[-200:]   # держим последние 200 записей
    # Атомарная запись: пишем во временный файл и os.replace. Иначе прерывание
    # json.dump (сбой/второй экземпляр) оставляло усечённый JSON, и cleanup_history
    # молча возвращал [] — терялся весь журнал. os.replace атомарен в пределах тома.
    try:
        os.makedirs(OPT, exist_ok=True)
        dst = _history_path()
        tmp = f"{dst}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hist, f)
        os.replace(tmp, dst)
    except Exception:
        try: os.remove(tmp)
        except Exception: pass

def cleanup_history():
    """Список записей истории очисток (старые→новые)."""
    try:
        with open(_history_path(), encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def total_freed():
    """Суммарно освобождено за всё время (байт)."""
    return sum(int(e.get("freed", 0)) for e in cleanup_history())

def shred_file(path):
    """Безвозвратное удаление файла: перезапись случайными данными → усечение → удаление.
    Защищает системные/корневые пути; работает только с обычными файлами."""
    if not os.path.isfile(path) or os.path.islink(path): return False
    if is_protected(path): return False
    try:
        size = os.path.getsize(path)
        with open(path, "r+b", buffering=0) as f:
            written, chunk = 0, 1024 * 1024
            while written < size:
                n = min(chunk, size - written)
                f.write(os.urandom(n)); written += n
            f.flush(); os.fsync(f.fileno())
            f.seek(0); f.truncate(0)
        os.remove(path)
        return True
    except Exception:
        return False

# ---------- метрики ----------
# ---------- разбор вывода системных команд ----------
# Парсеры отделены от вызова команд намеренно. Дважды подряд ошибка пряталась
# именно здесь и оставалась незамеченной, потому что при сбое разбора функция
# возвращала правдоподобный ноль: «swap 0» при раздутом свопе, «пика нет» при
# захлёбывающемся маке. Ноль в метрике выглядит как здоровая система, поэтому
# такие сбои не видны глазом — их ловят только тесты на реальных строках вывода.

def parse_top_cpu(out):
    """Загрузка CPU в процентах (user + sys) из `top -l 1 -n 0`."""
    for ln in (out or "").splitlines():
        if ln.startswith("CPU usage"):
            p = ln.replace("CPU usage:", "").split(",")
            try: return min(100, float(p[0].split("%")[0]) + float(p[1].split("%")[0].strip()))
            except Exception: return 0
    return 0

def parse_memory_pressure(out):
    """Занятая память в процентах из `memory_pressure`.

    Возвращает 0, если строку не нашли. Помним: этот показатель считает сжатое
    и вытесняемое доступным, поэтому под свопом почти не падает — как
    единственный сигнал нехватки памяти он не годится (см. autopilot/optimize.sh).
    """
    for ln in (out or "").splitlines():
        if "free percentage" in ln:
            try: return 100 - float(ln.split(":")[1].strip().rstrip("%"))
            except Exception: return 0
    return 0

# Ключи состава памяти: стабильные идентификаторы, подписи берутся из VM_LABELS
# при отрисовке. Раньше ключами были русские подписи, и диаграмму памяти было
# невозможно перевести на английский, не сломав обращения к словарю.
VM_KEYS = ("active", "wired", "compressed", "inactive", "free")
VM_LABELS = {"active": "Активная", "wired": "Связанная", "compressed": "Сжатая",
             "inactive": "Неактивная", "free": "Свободная"}
_VM_FIELDS = {"active": ("Pages active",), "wired": ("Pages wired down",),
              "compressed": ("Pages occupied by compressor",),
              "inactive": ("Pages inactive",),
              "free": ("Pages free", "Pages speculative")}

def parse_vm_stat(out):
    """Состав памяти в байтах из `vm_stat`.

    Размер страницы берём из самого вывода: на Apple Silicon он 16 КБ, на Intel
    4 КБ — зашитая константа врала бы вчетверо на половине маков.
    """
    out = out or ""
    m = re.search(r"page size of (\d+)", out)
    ps = int(m.group(1)) if m else 16384
    def pages(name):
        mm = re.search(re.escape(name) + r":\s+(\d+)", out)
        return int(mm.group(1)) if mm else 0
    return {k: sum(pages(f) for f in fields) * ps for k, fields in _VM_FIELDS.items()}

def stat_cpu():
    return parse_top_cpu(run(["/usr/bin/top", "-l", "1", "-n", "0"], 5))

def stat_mem():
    return parse_memory_pressure(run(["memory_pressure"], 5))

def stat_vm():
    """Состав памяти (байты): active/wired/compressed/inactive/free."""
    return parse_vm_stat(run(["vm_stat"]))

_SWAP_UNIT = {"K": 1/1024, "M": 1.0, "G": 1024.0, "T": 1024.0*1024}

def parse_swapusage(out):
    """(используется, всего) в МБ из строки vm.swapusage.

    Разбор по именам полей, а не по позициям. Прежний вариант брал f[5]/f[2]
    и делал rstrip("M"): при любом сдвиге формата или единице, отличной от M,
    float() падал и функция возвращала (0, 0) — дашборд рисовал «swap 0»
    ровно в тот момент, когда swap раздут и это важнее всего видеть.
    """
    def field(name):
        m = re.search(name + r"\s*=\s*([\d.]+)\s*([KMGT])?", out or "", re.I)
        if not m: return None
        return float(m.group(1)) * _SWAP_UNIT.get((m.group(2) or "M").upper(), 1.0)
    used, total = field("used"), field("total")
    if used is None or total is None: return 0, 0
    return used, total

def stat_swap():
    return parse_swapusage(run(["sysctl", "-n", "vm.swapusage"]))

def stat_disk():
    try: st = os.statvfs("/System/Volumes/Data")
    except Exception: st = os.statvfs("/")
    total = st.f_blocks*st.f_frsize; free = st.f_bavail*st.f_frsize
    return ((total-free)/total*100 if total else 0), free, total


def disk_benchmark(path=None, size_mb=128):
    """Безопасный бенчмарк скорости диска (read/write).

    Пишет временный файл size_mb МБ блоками по 4 МБ, измеряет время записи,
    затем заново открывает файл и читает целиком — измеряет время чтения.
    Временный файл всегда удаляется (finally). Возвращает dict:
        {"write_mbps": float, "read_mbps": float, "size_mb": int}
    либо {"error": "..."} при нехватке места/прав/иной ошибке.
    """
    import tempfile
    size_mb = max(1, int(size_mb))
    block = 4 * 1024 * 1024            # 4 МБ
    total = size_mb * 1024 * 1024
    chunk = b"\0" * block
    # каталог: рядом с HOME, если доступен на запись; иначе системный temp
    if path:
        tmpdir = path
    else:
        tmpdir = HOME if os.path.isdir(HOME) and os.access(HOME, os.W_OK) else tempfile.gettempdir()
    fd, fpath = None, None
    try:
        fd, fpath = tempfile.mkstemp(prefix=".cleanmac_bench_", dir=tmpdir)
        os.close(fd); fd = None
        # --- запись ---
        written = 0
        t0 = time.perf_counter()
        with open(fpath, "wb", buffering=0) as f:
            while written < total:
                n = min(block, total - written)
                f.write(chunk if n == block else chunk[:n])
                written += n
            f.flush(); os.fsync(f.fileno())
        wt = time.perf_counter() - t0
        # --- сброс кэша чтения: F_NOCACHE на свежем дескрипторе ---
        read_bytes = 0
        t1 = time.perf_counter()
        with open(fpath, "rb", buffering=0) as f:
            try: fcntl.fcntl(f.fileno(), getattr(fcntl, "F_NOCACHE", 48), 1)
            except Exception: pass
            while True:
                d = f.read(block)
                if not d: break
                read_bytes += len(d)
        rt = time.perf_counter() - t1
        mb = total / (1024 * 1024)
        return {
            "write_mbps": round(mb / wt, 1) if wt > 0 else 0.0,
            "read_mbps":  round(mb / rt, 1) if rt > 0 else 0.0,
            "size_mb":    size_mb,
        }
    except OSError as e:
        return {"error": f"{e.__class__.__name__}: {e}"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            if fd is not None: os.close(fd)
        except Exception: pass
        try:
            if fpath and os.path.exists(fpath): os.remove(fpath)
        except Exception: pass

_bc = {"health": 0, "cycles": 0, "cond": "—", "t": 0}
def parse_pmset_batt(out):
    """Заряд, состояние зарядки и остаток времени из `pmset -g batt`.

    Формат строки:
      ` -InternalBattery-0 (id=…)\t87%; discharging; 3:41 remaining present: true`
    На маке без батареи (десктоп) строки с процентом нет — возвращаем нули,
    а не падаем.
    """
    pct, charging, tleft = 0, False, ""
    for ln in (out or "").splitlines():
        if "%" not in ln: continue
        seg = ln.split(";")
        m = re.search(r"(\d+)%", seg[0])
        if m: pct = int(m.group(1))
        charging = "discharging" not in ln
        for s in seg:
            if "remaining" in s: tleft = s.strip().split(" ")[0]
        break
    return {"pct": pct, "charging": charging, "tleft": tleft}

def parse_ps_procs(out, n=5):
    """Топ процессов из `ps -axo %cpu,rss,comm -r` → [(cpu%, байты, имя)]."""
    rows = []
    for ln in (out or "").splitlines()[1:]:
        p = ln.split(None, 2)
        if len(p) < 3: continue
        try: rows.append((float(p[0]), int(p[1])*1024, p[2].split("/")[-1][:22]))
        except Exception: pass
    return rows[:n]

def parse_autopilot_log(text, hours=24, now=None):
    """Сводка работы автопилота за последние `hours` часов.

    Журнал — это простыня из четырёх типов строк на каждое срабатывание.
    Читать её, чтобы понять «а он вообще работает?», невозможно. Собираем
    цифры: сколько раз вмешался, сколько кэша убрал, трогал ли браузеры,
    сколько раз промолчал из-за того, что человек за компьютером.
    """
    import datetime
    now = now or datetime.datetime.now()
    since = now - datetime.timedelta(hours=hours)
    peaks = cleaned_mb = closed = declined = held = 0
    swap_before = swap_after = None
    last = None
    for ln in (text or "").splitlines():
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+(.*)", ln)
        if not m: continue
        try: ts = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError: continue
        if ts < since: continue
        body = m.group(2)
        last = ts
        if "ПИК:" in body: peaks += 1
        elif body.startswith("🧹"):
            c = re.search(r"~(\d+)M", body)
            if c: cleaned_mb += int(c.group(1))
        elif body.startswith("🔻"): closed += 1
        elif body.startswith("🚫"): declined += 1
        elif body.startswith("⏸"): held += 1
        elif "Итог:" in body:
            s = re.search(r"swap (\d+)M → (\d+)M", body)
            if s:
                if swap_before is None: swap_before = int(s.group(1))
                swap_after = int(s.group(2))
    return {"hours": hours, "peaks": peaks, "cleaned_mb": cleaned_mb,
            "closed": closed, "declined": declined, "held": held,
            "swap_before": swap_before, "swap_after": swap_after, "last": last}

def format_autopilot_summary(s):
    """Человеческая строка из сводки parse_autopilot_log."""
    if not s["peaks"]:
        return f"За {s['hours']} ч автопилот не вмешивался — нехватки памяти не было."
    parts = [f"За {s['hours']} ч: вмешался {s['peaks']} раз"]
    if s["cleaned_mb"]: parts.append(f"кэша убрано ~{human(s['cleaned_mb']*1024*1024)}")
    if s["closed"]:     parts.append(f"браузеры закрывались {s['closed']} раз")
    if s["declined"]:   parts.append(f"вы отменили {s['declined']}")
    if s["held"]:       parts.append(f"{s['held']} раз не трогал — вы были за маком")
    if s["swap_before"] is not None and s["swap_after"] is not None:
        parts.append(f"swap {s['swap_before']}М → {s['swap_after']}М")
    return " · ".join(parts)

def stat_batt():
    b = parse_pmset_batt(run(["pmset", "-g", "batt"]))
    pct, charging, tleft = b["pct"], b["charging"], b["tleft"]
    if time.time() - _bc["t"] > 25:
        sp = run(["system_profiler", "SPPowerDataType"])
        m = re.search(r"Maximum Capacity:\s*(\d+)", sp); _bc["health"] = int(m.group(1)) if m else _bc["health"]
        m = re.search(r"Cycle Count:\s*(\d+)", sp);      _bc["cycles"] = int(m.group(1)) if m else _bc["cycles"]
        m = re.search(r"Condition:\s*(\w+)", sp);        _bc["cond"]   = m.group(1) if m else _bc["cond"]
        if not _bc["health"]:
            io = run(["ioreg", "-rn", "AppleSmartBattery"])
            rm = re.search(r'"AppleRawMaxCapacity" = (\d+)', io); dz = re.search(r'"DesignCapacity" = (\d+)', io)
            if rm and dz: _bc["health"] = round(int(rm.group(1))/int(dz.group(1))*100)
        _bc["t"] = time.time()
    return {"pct": pct, "charging": charging, "tleft": tleft, **_bc}

def stat_procs(n=5):
    return parse_ps_procs(run(["/bin/ps", "-axo", "%cpu,rss,comm", "-r"]), n)

# ---------- категории очистки ----------
def chromium_caches(*app_support_rel):
    """Кэши Chromium-браузера, лежащие ВНЕ ~/Library/Caches.

    Chromium держит в ~/Library/Caches только сетевой кэш. Ещё несколько кэшей
    того же рода живут в профиле, внутри Application Support, и раньше не
    попадали в очистку вообще:

      Service Worker/CacheStorage — кэш офлайн-данных сайтов; на реальной машине
        разрастался до 430 МБ (Edge) при 1,6 ГБ обычного кэша;
      Service Worker/ScriptCache, Code Cache, GPUCache — компилированный JS
        и шейдеры, пересобираются сами.

    Всё перечисленное — производные данные: браузер восстановит их при первом
    же заходе на сайт. Историю, куки, пароли и расширения не трогаем.
    Профили перебираем все (Default, Profile 1, …), а не только Default.
    Существование самих кэшей не проверяем: их может не быть в момент запуска
    приложения, но браузер создаст их через минуту работы — очистка сама
    пропустит то, чего нет, а вот выкинуть путь из списка навсегда нельзя.
    """
    out = []
    for rel in app_support_rel:
        root = os.path.join(HOME, "Library/Application Support", rel)
        if not os.path.isdir(root): continue
        for prof in sorted(os.listdir(root)):
            if prof != "Default" and not prof.startswith("Profile "): continue
            p = os.path.join(root, prof)
            if not os.path.isdir(p): continue
            out += [os.path.join(p, "Service Worker", "CacheStorage"),
                    os.path.join(p, "Service Worker", "ScriptCache"),
                    os.path.join(p, "Code Cache"),
                    os.path.join(p, "GPUCache")]
    return out

CATEGORIES = [
    ("user_caches", "Кэш приложений (пользовательский)", [os.path.join(HOME,"Library/Caches")], None, "subitems"),
    ("safari", "Кэш Safari", [os.path.join(HOME,"Library/Caches/com.apple.Safari"),
        os.path.join(HOME,"Library/Containers/com.apple.Safari/Data/Library/Caches")], "Safari", "whole"),
    ("chrome", "Кэш Google Chrome", [os.path.join(HOME,"Library/Caches/Google")]
        + chromium_caches("Google/Chrome"), "Chrome", "whole"),
    ("edge", "Кэш Microsoft Edge", [os.path.join(HOME,"Library/Caches/Microsoft Edge")]
        + chromium_caches("Microsoft Edge"), "Edge", "whole"),
    ("yandex", "Кэш Yandex", [os.path.join(HOME,"Library/Caches/Yandex")]
        + chromium_caches("Yandex/YandexBrowser"), "Yandex", "whole"),
    ("updaters", "Кэши автообновлений (Google/Microsoft)",
        [os.path.join(HOME,"Library/Application Support/Google/GoogleUpdater/crx_cache"),
         os.path.join(HOME,"Library/Caches/com.microsoft.EdgeUpdater"),
         os.path.join(HOME,"Library/Caches/com.google.Keystone"),
         os.path.join(HOME,"Library/Caches/com.google.GoogleUpdater")], None, "whole"),
    ("logs", "Системные логи пользователя", [os.path.join(HOME,"Library/Logs")], None, "subitems"),
    ("crash", "Отчёты о сбоях (Diagnostics)", [os.path.join(HOME,"Library/Logs/DiagnosticReports")], None, "subitems"),
    ("ql", "Кэш миниатюр Quick Look", [os.path.join(HOME,"Library/Caches/com.apple.QuickLook.thumbnailcache")], None, "subitems"),
    ("xcode", "Xcode: DerivedData / DeviceSupport / Archives",
        [os.path.join(HOME,"Library/Developer/Xcode/DerivedData"),
         os.path.join(HOME,"Library/Developer/Xcode/iOS DeviceSupport"),
         os.path.join(HOME,"Library/Developer/Xcode/Archives"),
         os.path.join(HOME,"Library/Developer/CoreSimulator/Caches")], None, "whole"),
    ("devcache", "Кэши пакетных менеджеров (npm/pip/yarn/brew)",
        [os.path.join(HOME,".npm/_cacache"), os.path.join(HOME,"Library/Caches/pip"),
         os.path.join(HOME,"Library/Caches/Yarn"), os.path.join(HOME,"Library/Caches/Homebrew")], None, "whole"),
    ("iosbackup", "Резервные копии iPhone/iPad (MobileSync)",
        [os.path.join(HOME,"Library/Application Support/MobileSync/Backup")], None, "subitems"),
    ("maildl", "Вложения Почты (Mail Downloads)",
        [os.path.join(HOME,"Library/Containers/com.apple.mail/Data/Library/Mail Downloads")], None, "subitems"),
    ("claudevm", "Образ VM-песочницы Claude (vm_bundles)",
        [os.path.join(HOME,"Library/Application Support/Claude/vm_bundles")], None, "whole"),
]

# ---------- приватность ----------
PRIVACY_ITEMS = [
    ("recent", "Списки недавних файлов", [os.path.join(HOME,"Library/Application Support/com.apple.sharedfilelist")], None),
    ("savedstate", "Сохранённые состояния окон", [os.path.join(HOME,"Library/Saved Application State")], None),
    ("safari", "История Safari", [os.path.join(HOME,"Library/Safari/History.db"),
        os.path.join(HOME,"Library/Safari/History.db-wal"), os.path.join(HOME,"Library/Safari/History.db-shm")], "Safari"),
    ("chrome", "История и cookies Chrome", [
        os.path.join(HOME,"Library/Application Support/Google/Chrome/Default/History"),
        os.path.join(HOME,"Library/Application Support/Google/Chrome/Default/Cookies"),
        os.path.join(HOME,"Library/Application Support/Google/Chrome/Default/Visited Links")], "Chrome"),
    ("edge", "История и cookies Edge", [
        os.path.join(HOME,"Library/Application Support/Microsoft Edge/Default/History"),
        os.path.join(HOME,"Library/Application Support/Microsoft Edge/Default/Cookies")], "Edge"),
]

# ---------- сигнатуры известного рекламного/нежелательного ПО (эвристика) ----------
# Подстроки имён/путей типичных рекламных и «mac-cleaner»-агентов. НЕ полноценный
# антивирус — только безопасный обзор точек автозапуска для ручного разбора.
ADWARE = ["genieo","installmac","vsearch","conduit","mackeeper","pirrit","bundlore","adload",
          "spigot","crossrider","trovi","mughthesec","shlayer","searchquick","search-quick",
          "advancedmaccleaner","advancedmac","macsweeper","weknow","aerodynamic","chumsearch",
          "maxxmediasearch","pcvark","mac-cleanup","maccleanup","cleanmymac-helper","geneio",
          "imckeeper","macreviver","mediadownloader","searchmine","searchpie","spaces.app",
          "wirelurker","silver","keranger","macdownloader","macupdater-helper"]

# Каталоги автозапуска, которые мы сканируем (только чтение).
LAUNCH_DIRS = (
    os.path.join(HOME, "Library/LaunchAgents"),
    "/Library/LaunchAgents",
    "/Library/LaunchDaemons",
)

def _parse_launch_plist(path):
    """Прочитать .plist автозапуска → dict с Label/Program/ProgramArguments/RunAtLoad.
    Безопасно (только чтение); при ошибке возвращает пустой dict."""
    import plistlib
    try:
        with open(path, "rb") as f:
            d = plistlib.load(f)
    except Exception:
        return {}
    args = d.get("ProgramArguments")
    if isinstance(args, str):
        args = [args]
    elif not isinstance(args, (list, tuple)):
        args = []
    return {
        "label": str(d.get("Label", "") or ""),
        "program": str(d.get("Program", "") or ""),
        "args": [str(a) for a in args],
        "run_at_load": bool(d.get("RunAtLoad", False)),
    }

def adware_suspect(label, path, args):
    """Чистая классификация записи автозапуска: подозрительна ли она (эвристика).

    Возвращает (suspect: bool, reason: str). reason пуст, если запись чистая.
    Системное Apple (``com.apple.*``) и защищённые пути НИКОГДА не помечаются.
    ``args`` — список строк (ProgramArguments + Program), ``path`` — путь к plist."""
    label = (label or "").strip()
    path = (path or "").strip()
    low_label = label.lower()
    low_path = path.lower()
    if isinstance(args, str):
        args = [args]
    blob = " ".join([low_label] + [str(a).lower() for a in (args or [])] + [low_path])

    # 1) Apple-системное и безопасное — никогда не подозрительно.
    if low_label.startswith(("com.apple.", "apple.", "group.com.apple")):
        return (False, "")
    if path and is_protected(path):
        return (False, "")

    # 2) Прямое совпадение с сигнатурой известного adware.
    for tok in ADWARE:
        if tok in blob:
            return (True, f"известная сигнатура «{tok}»")

    # 3) Запуск исполняемого из временных/подозрительных каталогов.
    for arg in ([low_label] + [str(a).lower() for a in (args or [])]):
        a = arg.strip().strip('"')
        if a.startswith(("/tmp/", "/private/tmp/", "/var/tmp/", "/private/var/tmp/")):
            return (True, "запуск из временного каталога (/tmp)")
        if "/.hidden" in a or a.startswith(os.path.join(HOME, ".").lower()) or "/users/shared/." in a:
            return (True, "запуск из скрытого каталога")

    # 4) Случайное (бессмысленное) имя лейбла: длинная «каша» из букв/цифр без точек.
    stem = label.split(".")[-1] if label else ""
    if stem and len(stem) >= 12 and "." not in label:
        digits = sum(c.isdigit() for c in stem)
        if digits >= 4 and stem.isalnum():
            return (True, "случайное имя агента")

    return (False, "")

def scan_launch_agents(dirs=None):
    """Сканировать каталоги автозапуска. Возвращает (suspicious, clean) — два списка
    dict {label, path, reason, run_at_load}. Только чтение, никаких изменений."""
    if dirs is None:
        dirs = LAUNCH_DIRS
    suspicious, clean = [], []
    for loc in dirs:
        if not os.path.isdir(loc):
            continue
        try:
            names = sorted(os.listdir(loc))
        except OSError:
            continue
        for fn in names:
            if not fn.endswith(".plist"):
                continue
            p = os.path.join(loc, fn)
            meta = _parse_launch_plist(p)
            label = meta.get("label") or fn[:-6]
            args = list(meta.get("args", []))
            if meta.get("program"):
                args = [meta["program"]] + args
            suspect, reason = adware_suspect(label, p, args)
            rec = {"label": label, "path": p, "reason": reason,
                   "run_at_load": meta.get("run_at_load", False)}
            (suspicious if suspect else clean).append(rec)
    return suspicious, clean


class CleanMac(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CleanMac")
        self.minsize(960, 680)
        _w,_h=1000,720
        _x=max(0,(self.winfo_screenwidth()-_w)//2); _y=max(0,(self.winfo_screenheight()-_h)//3)
        self.geometry(f"{_w}x{_h}+{_x}+{_y}")
        self.configure(bg=BG0)
        try: self.attributes("-alpha", 0.985)          # лёгкая «стеклянная» прозрачность
        except Exception: pass
        self.q = queue.Queue()
        self.page = None
        self.disp = {"cpu":0,"ram":0,"swap":0,"disk":0,"health":0,"batt":0}
        self.tgt = dict(self.disp)
        self.swap_mb = 0; self.disk_free = 0; self.disk_total = 1
        self.vm = {}; self.batt = {"pct":0,"charging":False,"tleft":"","health":0,"cycles":0,"cond":"—"}
        self.procs = []
        self.cpu_hist = collections.deque([0]*70, maxlen=70)
        self.ram_hist = collections.deque([0]*70, maxlen=70)
        self.net_down_hist = collections.deque([0]*70, maxlen=70)
        self.net_up_hist = collections.deque([0]*70, maxlen=70)
        self.net_down = 0.0; self.net_up = 0.0
        self.health_hist = collections.deque([0]*70, maxlen=70)
        self.disk_hist = collections.deque([0]*70, maxlen=70)
        self.cat_vars={}; self.cat_size_lbl={}; self.found={}; self._alert_t={}
        self.is_pro = os.path.exists(LIC)
        self.update_note = ""
        self._group_active = {}   # запоминаем активную под-вкладку каждой группы
        self._visible = True      # окно на экране и в фокусе → анимируем; иначе пауза
        self._alive = True        # снимается при закрытии — сигнал потокам/циклам остановиться
        self._build()
        self.nav("dash")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # пауза анимации, когда окно не активно/свёрнуто — чтобы не жечь CPU
        self.bind("<FocusIn>",  lambda e: setattr(self, "_visible", True))
        self.bind("<FocusOut>", lambda e: setattr(self, "_visible", False))
        self.bind("<Unmap>",    lambda e: setattr(self, "_visible", False))
        self.bind("<Map>",      lambda e: setattr(self, "_visible", True))
        self._spawn(self._sampler)
        self._spawn(self._net_sampler)
        self._spawn(self._check_update)
        self.after(80, self._poll); self.after(66, self._animate)

    # ---------- каркас ----------
    def _build(self):
        self.side = tk.Frame(self, bg=SIDEBAR, width=204); self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        tk.Label(self.side, text="  🪽 KRYLAN", bg=SIDEBAR, fg=TEXT,
                 font=("SF Pro Display", 19, "bold")).pack(anchor="w", pady=(22,0), padx=12)
        tk.Label(self.side, text=f"  {SLOGAN}", bg=SIDEBAR, fg=GREEN,
                 font=("SF Pro Text", 9, "bold")).pack(anchor="w", padx=12, pady=(2,0))
        tk.Label(self.side, text=f"  CleanMac · v{VERSION}", bg=SIDEBAR, fg=MUTED,
                 font=("SF Pro Text", 10)).pack(anchor="w", padx=12, pady=(0,16))
        self.nav_btns = {}
        for key,glyph,name in [("dash","dash","Дашборд"),("clean","clean","Очистка"),
                               ("guard","guard","Защита"),("pro","pro","Pro / О программе")]:
            row = tk.Frame(self.side, bg=SIDEBAR, cursor="pointinghand"); row.pack(fill="x", pady=1)
            cv = tk.Canvas(row, width=26, height=44, bg=SIDEBAR, highlightthickness=0)
            cv.pack(side="left", padx=(12,2))
            lbl = tk.Label(row, text=f" {L(name)}", bg=SIDEBAR, fg=MUTED, font=("SF Pro Text", 13),
                           anchor="w"); lbl.pack(side="left", fill="x", expand=True)
            for wdg in (row, cv, lbl):
                wdg.bind("<Button-1>", lambda e,k=key: self.nav(k))
                wdg.bind("<Enter>", lambda e,k=key: self._nav_hover(k, True))
                wdg.bind("<Leave>", lambda e,k=key: self._nav_hover(k, False))
            self.nav_btns[key] = {"row":row, "cv":cv, "lbl":lbl, "glyph":glyph}
            self._glyph(cv, glyph, MUTED)
        self.badge = tk.Label(self.side, text="", bg=SIDEBAR, fg=YELLOW, font=("SF Pro Text", 11, "bold"),
                              wraplength=184, justify="left"); self.badge.pack(side="bottom", fill="x", padx=12, pady=(0,6))
        self.statusbar = tk.Label(self.side, text="", bg=SIDEBAR, fg=MUTED, font=("SF Pro Text", 10),
                                  wraplength=184, justify="left"); self.statusbar.pack(side="bottom", fill="x", padx=12, pady=4)
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    # Консолидация: 4 раздела сайдбара, под-вкладки внутри групп.
    GROUPS = {"clean": [("smart","Умная очистка"), ("cleaner","Категории"), ("privacy","Приватность")],
              "guard": [("threats","Угрозы"), ("autopilot","Автопилот"), ("tools","Инструменты")]}

    def _parent_of(self, page):
        for g, leaves in self.GROUPS.items():
            if page in [lk for lk,_ in leaves]: return g
        return page   # dash / pro — сами себе раздел

    def _nav_hover(self, key, on):
        d = self.nav_btns.get(key)
        if not d or self._parent_of(self.page) == key: return
        bg = GLASS_HI if on else SIDEBAR
        d["row"].configure(bg=bg); d["cv"].configure(bg=bg); d["lbl"].configure(bg=bg)

    def nav(self, key):
        if key in self.GROUPS:                       # клик по группе → её активная под-вкладка
            key = self._group_active.get(key) or self.GROUPS[key][0][0]
        self.page = key
        parent = self._parent_of(key)
        if parent in self.GROUPS: self._group_active[parent] = key
        for k, d in self.nav_btns.items():
            on = (k == parent); bg = GLASS_HI if on else SIDEBAR
            d["row"].configure(bg=bg); d["cv"].configure(bg=bg)
            d["lbl"].configure(bg=bg, fg=GREEN if on else MUTED,
                               font=("SF Pro Text", 13, "bold" if on else "normal"))
            self._glyph(d["cv"], d["glyph"], GREEN if on else MUTED)
        for w in self.main.winfo_children(): w.destroy()
        if parent in self.GROUPS:
            self._render_subnav(parent, key)
        {"dash":self.show_dash,"smart":self.show_smart,"privacy":self.show_privacy,"threats":self.show_threats,
         "autopilot":self.show_autopilot,"cleaner":self.show_cleaner,
         "tools":self.show_tools,"pro":self.show_pro}[key]()

    def _render_subnav(self, parent, active):
        """iOS-стиль сегментированного переключателя под-вкладок группы."""
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=(16,0))
        for lk, label in self.GROUPS[parent]:
            on = (lk == active)
            seg = tk.Label(bar, text=f"  {L(label)}  ", bg=GREEN if on else GLASS,
                           fg="#0b1410" if on else MUTED,
                           font=("SF Pro Text", 12, "bold" if on else "normal"),
                           padx=10, pady=7, cursor="pointinghand")
            seg.pack(side="left", padx=(0,8))
            seg.bind("<Button-1>", lambda e,k=lk: self.nav(k))

    def _glyph(self, cv, name, color):
        """Минималистичные векторные иконки сайдбара (в духе SF Symbols), центр ~ (13,22)."""
        cv.delete("all"); w = 2
        if name == "dash":                       # сетка 2×2
            for gx,gy in [(6,15),(15,15),(6,24),(15,24)]:
                cv.create_rectangle(gx,gy,gx+5,gy+5, outline=color, width=w)
        elif name == "clean":                    # искра (4-конечная звезда)
            cv.create_polygon(13,13, 16,19, 22,22, 16,25, 13,31, 10,25, 4,22, 10,19,
                              outline=color, width=w, fill="", joinstyle="round")
        elif name == "guard":                    # щит
            cv.create_polygon(13,13, 21,16, 21,22, 13,31, 5,22, 5,16,
                              outline=color, width=w, fill="", joinstyle="round")
        elif name == "pro":                      # звезда (5 лучей)
            cv.create_polygon(13,13, 15,19, 22,19, 16,24, 18,31, 13,26, 8,31, 10,24, 4,19, 11,19,
                              outline=color, width=w, fill="", joinstyle="round")

    def status(self,t): self.statusbar.configure(text=t)

    def set_lang(self, lang):
        global LANG
        LANG = lang
        try:
            os.makedirs(CFG, exist_ok=True)
            with open(LANG_FILE, "w") as f: f.write(lang)
        except Exception: pass
        cur = self.page or "dash"
        for w in self.winfo_children(): w.destroy()
        self.nav_btns = {}; self._build(); self.nav(cur)

    def _render_advice(self):
        """Строка рекомендаций под шапкой дашборда. Молчит, когда всё в порядке."""
        lbl = getattr(self, "advice_lbl", None)
        if not lbl or not lbl.winfo_exists(): return
        rows = disk_advice(self.tgt.get("disk", 0), self.tgt.get("ram", 0), self.tgt.get("batt"))
        hot = [(i, t) for i, t in rows if i in ("🔴", "🟡")]
        if not hot:
            lbl.configure(text="", fg=MUTED); return
        lbl.configure(text="   ".join(f"{i} {t}" for i, t in hot[:2]),
                      fg=(RED if any(i == "🔴" for i, _ in hot) else YELLOW))

    def _maybe_alert(self, disk, batt_health):
        now = time.time()
        def fire(key, cooldown, title, msg):
            if now - self._alert_t.get(key, 0) > cooldown:
                self._alert_t[key] = now
                run(["osascript", "-e", f'display notification "{as_escape(msg)}" with title "{as_escape(title)}"'])
        if disk >= 90:
            fire("disk", 6*3600, "🪽 KRYLAN", "Диск почти заполнен — запустите Умную очистку.")
        if batt_health and batt_health < 80:
            fire("batt", 24*3600, "🪽 KRYLAN", f"Батарея деградирует: ёмкость {int(batt_health)}%.")

    def set_theme(self, name):
        apply_theme(name)
        try:
            os.makedirs(CFG, exist_ok=True)
            with open(THEME_FILE, "w") as f: f.write(name)
        except Exception: pass
        self.configure(bg=BG0)
        cur = self.page or "dash"
        for w in self.winfo_children(): w.destroy()
        self.nav_btns = {}; self._build(); self.nav(cur)

    # ---------- рисовалки ----------
    @staticmethod
    def _round(c, x0,y0,x1,y1, r, **kw):
        pts=[x0+r,y0,x1-r,y0,x1,y0,x1,y0+r,x1,y1-r,x1,y1,x1-r,y1,x0+r,y1,x0,y1,x0,y1-r,x0,y0+r,x0,y0]
        return c.create_polygon(pts, smooth=True, **kw)

    def _grad(self, c, w, h):
        # Радиальное свечение HUD: ярче к центру-верху, темнее к краям (как на референсе).
        base="#060d1e"; glow="#173d72"
        c.create_rectangle(0,0,w,h, fill=base, outline=base)
        cxp, cyp = w*0.5, h*0.30
        rings=11; maxr=max(w,h)*1.0
        for i in range(rings,0,-1):
            t=i/rings; rr=maxr*t
            col=_blend(glow, base, t)        # внешние кольца тёмные, центр — свечение
            c.create_oval(cxp-rr, cyp-rr*0.85, cxp+rr, cyp+rr*0.85, fill=col, outline=col)
        self._starfield(c, w, h)

    def _starfield(self, c, w, h):
        """Натуральное звёздное небо: звёзды разного размера, мерцание, блики у ярких."""
        if not hasattr(self, "_stars"):
            rnd = random.Random(42); self._stars=[]
            for _ in range(90):
                self._stars.append((rnd.random(), rnd.random(),
                                    rnd.uniform(0.4,2.2),        # размер
                                    rnd.uniform(0,6.28),         # фаза мерцания
                                    rnd.uniform(0.25,1.0),       # базовая яркость
                                    rnd.uniform(0.02,0.09),      # скорость мерцания
                                    rnd.random()<0.08))          # яркая (с бликом-крестом)
        fr = getattr(self, "_frame", 0)
        for fx, fy, sz, ph, bb, spd, bright in self._stars:
            x, y = fx*w, fy*h
            tw = bb*(0.5 + 0.5*math.sin(fr*spd + ph))
            r = sz*(0.55+0.55*tw)
            v = min(255, int(190*tw)+18)
            col = "#%02x%02x%02x"%(v, v, min(255, v+22))   # чуть голубоватый белый
            c.create_oval(x-r,y-r,x+r,y+r, fill=col, outline=col)
            if bright and tw>0.62:                          # тонкий блик-крест у ярких
                g=r*2.8; gc=_blend("#cfe0ff", BG0, 1-(tw-0.62)/0.38*0.55)
                c.create_line(x-g,y, x+g,y, fill=gc, width=1)
                c.create_line(x,y-g, x,y+g, fill=gc, width=1)

    def _ring(self, c, cx,cy,r,frac,color,w,big,small,val):
        glow=_blend(color,BG0,0.5)
        # внешний круг-след
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        # HUD-насечки по периметру: горят неоном до текущего значения; каждая 6-я — длинная
        N=28
        for i in range(N):
            a=math.radians(90 - (i/N)*360); lit=(i/N)<=frac; major=(i%6==0)
            rr1=r+4; rr2=r+(13 if major else (10 if lit else 7))
            c.create_line(cx+rr1*math.cos(a), cy-rr1*math.sin(a),
                          cx+rr2*math.cos(a), cy-rr2*math.sin(a),
                          fill=(color if lit else _blend(color,BG0,0.68)),
                          width=(2 if (lit or major) else 1))
        # дуга прогресса со свечением
        if frac>0.001:
            ext=-frac*359.9
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=90, extent=ext, style="arc", outline=glow, width=w+7)
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=90, extent=ext, style="arc", outline=color, width=w)
            ea=math.radians(90+ext); px=cx+r*math.cos(ea); py=cy-r*math.sin(ea)
            c.create_oval(px-w/2-1,py-w/2-1,px+w/2+1,py+w/2+1, fill="#ffffff", outline=color)
        # внутреннее декоративное кольцо (HUD-глубина)
        ri=r-w-6
        if ri>6: c.create_oval(cx-ri,cy-ri,cx+ri,cy+ri, outline=_blend(color,BG0,0.8), width=1)
        c.create_text(cx,cy-2, text=val, fill=TEXT, font=("SF Pro Display", big, "bold"))
        c.create_text(cx,cy+r+15, text=small, fill=MUTED, font=("SF Pro Text", 10))

    def _donut(self, c, cx,cy,r,w, segs, center_top="", center_bot=""):
        start=90
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        for frac,color in segs:
            if frac<=0: continue
            ext=-frac*359.9
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=start, extent=ext, style="arc",
                         outline=_blend(color,BG0,0.5), width=w+5)
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=start, extent=ext, style="arc", outline=color, width=w)
            start+=ext
        if center_top: c.create_text(cx,cy-7, text=center_top, fill=TEXT, font=("SF Pro Display", 17, "bold"))
        if center_bot: c.create_text(cx,cy+12, text=center_bot, fill=MUTED, font=("SF Pro Text", 10))

    def _spark(self, c, x,y,w,h, series):
        # Тренды 0..100% в стиле Binance: лёгкое свечение + чёткая линия.
        c.create_line(x,y+h,x+w,y+h, fill=TRACK)
        for deq,color in series:
            n=len(deq)
            if n<2: continue
            sw=w/(n-1); pts=[]
            for i,v in enumerate(deq): pts += [x+i*sw, y+h-(min(100,v)/100)*h]
            c.create_line(*pts, fill=_blend(color,BG0,0.45), width=5, smooth=True, capstyle="round")
            c.create_line(*pts, fill=color, width=2, smooth=True, capstyle="round")

    def _spark_auto(self, c, x,y,w,h, series, peak):
        """Авто-масштаб по пику (сеть): градиентная заливка + светящаяся линия (Binance-style)."""
        c.create_line(x,y+h,x+w,y+h, fill=TRACK)
        peak=max(1,peak)
        for deq,color in series:
            n=len(deq)
            if n<2: continue
            sw=w/(n-1)
            pts=[(x+i*sw, y+h-min(1.0,v/peak)*h) for i,v in enumerate(deq)]
            flat=[co for p in pts for co in p]
            # градиентная заливка: 4 полосы, ярче ближе к линии
            BANDS=4
            for k in range(BANDS):
                floor=y+h - (h*k/BANDS)
                t=0.88 - 0.13*k
                band=[(px, min(py, floor)) for (px,py) in pts]
                poly=[x,floor]+[co for p in band for co in p]+[x+w,floor]
                c.create_polygon(*poly, fill=_blend(color,BG0,t), outline="", smooth=True)
            # светящаяся линия поверх
            c.create_line(*flat, fill=_blend(color,BG0,0.35), width=6, smooth=True, capstyle="round")
            c.create_line(*flat, fill=color, width=2, smooth=True, capstyle="round")

    def _globe(self, c, cx, cy, r, fr):
        """Вращающаяся каркасная «планета-устройство» (HUD, неон-циан), с пульсом-сердцебиением."""
        # пульс-сердцебиение: два быстрых удара за цикл
        ph=(fr*0.03)%1.0
        puls=math.exp(-((ph-0.16)**2)/0.004)+0.6*math.exp(-((ph-0.34)**2)/0.004)
        puls=min(1.0,puls)
        # ореол-свечение (пульсирует)
        for k in range(4,0,-1):
            rr=r+k*4 + puls*7
            c.create_oval(cx-rr,cy-rr,cx+rr,cy+rr, outline=_blend(CYAN,BG0,0.88-0.10*puls*(6-k)/6), width=1)
        # кольцо-импульс, расходящееся при ударе
        if puls>0.15:
            pr=r+8+puls*16
            c.create_oval(cx-pr,cy-pr,cx+pr,cy+pr, outline=_blend(CYAN,BG0,0.45-puls*0.25), width=2)
        # тёмная сфера + лимб (ярче на ударе)
        c.create_oval(cx-r,cy-r,cx+r,cy+r, fill=_blend(BG0,CYAN,0.10+0.06*puls), outline=_blend(CYAN,"#ffffff",puls*0.35), width=2)
        # параллели (широты)
        for lat in (-0.66,-0.33,0.0,0.33,0.66):
            rx=r*math.sqrt(max(0.0,1-lat*lat)); yy=cy-r*lat
            c.create_oval(cx-rx, yy-rx*0.18, cx+rx, yy+rx*0.18, outline=_blend(CYAN,BG0,0.62), width=1)
        # меридианы (долготы) — вращаются: ширина = |r·cos(phase)|
        phase=fr*0.04; M=6
        for k in range(M):
            ang=phase + k*math.pi/M
            rx=abs(r*math.cos(ang))
            col=_blend(CYAN, BG0, 0.40 + 0.32*(1-abs(math.cos(ang))))
            if rx>1: c.create_oval(cx-rx, cy-r, cx+rx, cy+r, outline=col, width=1)
        # светящиеся узлы («города»), вращаются с планетой
        rnd=random.Random(7)
        for n in range(7):
            la=rnd.uniform(-0.7,0.7); na=phase*1.0 + n*0.9
            rx=r*math.sqrt(max(0.0,1-la*la))
            nx=cx+rx*math.cos(na); ny=cy-r*la
            if math.sin(na)>-0.1:                 # только передняя полусфера
                c.create_oval(nx-2,ny-2,nx+2,ny+2, fill="#ff66d4", outline="#ff66d4")

    def _hints(self, c, cx, cy, r, fr):
        """Парящие подсказки-чипы вокруг планеты — как в фантастических HUD."""
        tips=[f"ОЗУ {int(self.disp['ram'])}%", f"CPU {int(self.disp['cpu'])}%",
              f"Диск {int(self.disp['disk'])}%", f"↓ {human(self.net_down)}/с",
              f"Здоровье {int(self.disp['health'])}", f"Батарея {self.batt.get('pct',0)}%"]
        n=len(tips)
        for i,t in enumerate(tips):
            a=fr*0.012 + i*(2*math.pi/n)
            rad=r+34+8*math.sin(fr*0.03+i)
            hx=cx+rad*math.cos(a)*1.55; hy=cy+rad*math.sin(a)*0.78
            ex=cx+r*math.cos(a); ey=cy+r*math.sin(a)*0.78
            tw=0.55+0.45*math.sin(fr*0.05+i)
            c.create_line(ex,ey,hx,hy, fill=_blend(CYAN,BG0,0.80), width=1)
            c.create_oval(hx-3,hy-3,hx+3,hy+3, outline=CYAN, fill=_blend(CYAN,BG0,0.45))
            right=math.cos(a)>=0
            c.create_text(hx+(14 if right else -14), hy, anchor=("w" if right else "e"),
                          fill=_blend(TEXT,BG0,1-tw*0.7), font=("SF Pro Text",10,"bold"), text=t)

    # ================= ДАШБОРД =================
    def show_dash(self):
        # Шапка в один ряд: «Дашборд» + LIVE-индикатор слева, кнопки справа
        head=tk.Frame(self.main, bg=BG0); head.pack(fill="x", padx=22, pady=(16,12))
        left=tk.Frame(head, bg=BG0); left.pack(side="left")
        tk.Label(left, text=L("Дашборд"), bg=BG0, fg=TEXT, font=("SF Pro Display", 26, "bold")).pack(side="left")
        self.live_dot=tk.Label(left, text="●", bg=BG0, fg=GREEN, font=("SF Pro Text", 13))
        self.live_dot.pack(side="left", padx=(14,4), pady=(8,0))
        tk.Label(left, text=L("В РЕАЛЬНОМ ВРЕМЕНИ"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text", 10, "bold")).pack(side="left", pady=(9,0))
        # яркость: компактная кнопка-цикл 25 → 50 → 75 → 100 %
        cur=get_brightness()
        self._bri_lvl=int(round((cur if cur is not None else 0.75)*100/25)*25) or 25
        self.bri_btn=self._btn(head, f"☀ {self._bri_lvl}%", YELLOW, self._brightness_cycle)
        self.bri_btn.pack(side="right", padx=(8,2))
        # ✨ ГЛАВНАЯ кнопка-герой: один клик делает ВСЁ безопасное, без диалогов
        self.magic_btn=RoundedButton(head, "  ✨ Оптимизировать  ", GREEN, self._optimize_all,
                                     fg="#0b1410", radius=16, padx=20, pady=12,
                                     font=("SF Pro Display", 15, "bold"))
        self.magic_btn.pack(side="right", padx=(0,10))
        # Единственная главная кнопка — «✨ Оптимизировать». Вторичную «Ускорить» убрали.
        # строка живого прогресса оптимизации (под шапкой)
        self.magic_prog=tk.Label(self.main, text="", bg=BG0, fg=GREEN,
                                 font=("SF Pro Text", 12, "bold"), anchor="w")
        self.magic_prog.pack(fill="x", padx=24, pady=(0,2))
        # Живые рекомендации по метрикам (общая с Desktop-версией функция
        # krylan_core.disk_advice). Раньше она была импортирована, покрыта
        # тестами — и нигде на маке не показывалась.
        self.advice_lbl=tk.Label(self.main, text="", bg=BG0, fg=MUTED,
                                 font=("SF Pro Text", 11), anchor="w", justify="left")
        self.advice_lbl.pack(fill="x", padx=24, pady=(0,2))
        self._render_advice()
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=14, pady=(0,12))
        # прокрутка дашборда колёсиком (чтобы дотянуться до нижних карточек и планеты)
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", self._dash_wheel))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    def _dash_wheel(self, e):
        try: self.cv.yview_scroll(int(-e.delta/3), "units")
        except Exception: pass

    def _brightness_cycle(self):
        presets=[25,50,75,100]
        cur=getattr(self,"_bri_lvl",75)
        nxt=next((p for p in presets if p>cur), presets[0])   # следующий пресет, по кругу
        self._bri_lvl=nxt
        set_brightness(nxt/100)
        try: self.bri_btn.configure(text=f"☀ {nxt}%")
        except Exception: pass

    def _card(self, c, x,y,w,h, title=None, accent=None, icon=None):
        # iOS-стиль: мягкое скругление, без жёсткой обводки (как сгруппированные ячейки)
        self._round(c, x,y,x+w,y+h, 18, fill=GLASS, outline="")
        if title:
            tx = x+18
            if accent:
                c.create_oval(x+16, y+13, x+23, y+20, fill=accent, outline="")   # точка-акцент
                tx = x+31
            label = (icon+"  " if icon else "") + title.upper()
            c.create_text(tx, y+16, text=label, anchor="w", fill=MUTED, font=("SF Pro Text", 10, "bold"))

    def _ekg(self, c, x, y, w, h, fr, color):
        """Бегущая кардиограмма «пульс системы» (ЭКГ-волна со свечением)."""
        def beat(t):
            if 0.12<t<0.17:  return 0.18*math.sin((t-0.12)/0.05*math.pi)   # P
            if 0.18<t<0.205: return -0.12                                   # Q
            if 0.205<t<0.235:return 1.0                                     # R
            if 0.235<t<0.27: return -0.42                                   # S
            if 0.32<t<0.45:  return 0.24*math.sin((t-0.32)/0.13*math.pi)    # T
            return 0.0
        baseline=y+h*0.55; amp=h*0.42; cyc=118.0; off=(fr*1.7)%cyc
        pts=[]
        for px in range(0,int(w)+1,3):
            t=((px+off)%cyc)/cyc
            pts += [x+px, baseline-beat(t)*amp]
        if len(pts)>=4:
            c.create_line(*pts, fill=_blend(color,BG0,0.40), width=4, capstyle="round")
            c.create_line(*pts, fill=color, width=2, capstyle="round")
        # бегущая точка-«сердце» на гребне последнего удара
        hx=x+((cyc-off+0.22*cyc)%cyc);
        c.create_oval(hx-3,baseline-amp-3,hx+3,baseline-amp+3, fill=color, outline=color)

    def _device_info(self):
        if hasattr(self, "_devinfo"): return self._devinfo
        import platform as _pl, socket as _sk
        def sc(k):
            try: return subprocess.run(["sysctl","-n",k],capture_output=True,text=True,timeout=3).stdout.strip()
            except Exception: return ""
        chip=sc("machdep.cpu.brand_string") or _pl.processor() or "Apple Silicon"
        model=sc("hw.model") or "Mac"
        try: mem=int(sc("hw.memsize") or 0)
        except Exception: mem=0
        try: name=_sk.gethostname().replace(".local","")
        except Exception: name="Mac"
        try: osv=_pl.mac_ver()[0]
        except Exception: osv=""
        self._devinfo={"name":name,"chip":chip,"model":model,"ram":human(mem),"os":osv}
        return self._devinfo

    def _draw_dash(self):
        if not (self.page=="dash" and self.cv.winfo_exists()): return
        c=self.cv; c.delete("all")
        W=c.winfo_width() or 760; H=c.winfo_height() or 620
        self._grad(c, W, H)
        fr=getattr(self,"_frame",0)
        # ===== радиальная «рубка»: планета в центре, метрики вокруг =====
        cx=W/2; cy=H*0.47
        gr=max(58, min(W*0.115, H*0.165, 116))
        gauge_r=max(27, min(40, min(W,H)*0.05))
        orbit=min(gr+90, cy-gauge_r-24, (H-cy)-gauge_r-44, W/2-gauge_r-16)
        orbit=max(orbit, gr+gauge_r+20)
        # часы — верх-центр (HUD)
        c.create_text(cx, 20, fill=CYAN, font=("SF Mono",22,"bold"), text=time.strftime("%H:%M"))
        c.create_text(cx, 40, fill=MUTED, font=("SF Pro Text",9,"bold"), text=L("СИСТЕМА · РЕАЛЬНОЕ ВРЕМЯ"))
        # интернет — верх-право
        c.create_text(W-22, 18, anchor="e", fill=MUTED, font=("SF Pro Text",10,"bold"), text=L("🌐 ИНТЕРНЕТ"))
        c.create_text(W-22, 40, anchor="e", fill=GREEN, font=("SF Pro Display",14,"bold"), text=f"↓ {human(self.net_down)}/с")
        c.create_text(W-22, 60, anchor="e", fill=BLUE, font=("SF Pro Display",14,"bold"), text=f"↑ {human(self.net_up)}/с")
        # кардиограмма «пульс системы» — верх-лево (ЭКГ, цвет по здоровью)
        c.create_text(22, 13, anchor="w", fill=MUTED, font=("SF Pro Text",9,"bold"), text=L("♥ ПУЛЬС СИСТЕМЫ"))
        self._ekg(c, 22, 22, max(140, cx-150), 42, fr, RED)
        # ===== метрики-гейджи вокруг планеты =====
        sval=human(self.swap_mb*1024*1024).replace(" ","")
        gauges=[("ЗДОРОВЬЕ", str(int(self.disp["health"])), self.disp["health"]/100, col_for(self.disp["health"],inv=True)),
                ("CPU", f'{int(self.disp["cpu"])}%', self.disp["cpu"]/100, col_for(self.disp["cpu"],inv=True)),
                ("ОЗУ", f'{int(self.disp["ram"])}%', self.disp["ram"]/100, col_for(self.disp["ram"],inv=True)),
                ("ДИСК", f'{int(self.disp["disk"])}%', self.disp["disk"]/100, col_for(self.disp["disk"],inv=True)),
                ("SWAP", sval, min(1,self.swap_mb/8192.0), CYAN),
                ("БАТАРЕЯ", f'{self.batt["pct"]}%', self.disp["batt"]/100, col_for(self.disp["batt"],inv=True))]
        angles=[-120,-60,0,60,120,180]   # верх-центр и низ-центр свободны (часы / характеристики)
        for (label,val,frac,color),deg in zip(gauges,angles):
            a=math.radians(deg)
            gxp=cx+orbit*math.cos(a); gyp=cy+orbit*math.sin(a)
            ex=cx+gr*math.cos(a); ey=cy+gr*math.sin(a)
            lx=gxp-gauge_r*math.cos(a); ly=gyp-gauge_r*math.sin(a)
            c.create_line(ex,ey,lx,ly, fill=_blend(CYAN,BG0,0.42), width=1)   # светящийся коннектор
            c.create_oval(ex-2,ey-2,ex+2,ey+2, fill=CYAN, outline=CYAN)        # узел у планеты
            c.create_oval(lx-2,ly-2,lx+2,ly+2, fill=_blend(color,BG0,0.2), outline=color)  # узел у гейджа
            self._ring(c, gxp,gyp,gauge_r, min(1,frac), color, 8, 15, label, val)
        # ===== состав памяти — пончик в левом нижнем углу =====
        # README обещал «пончики памяти и диска», но _donut ни разу не вызывался,
        # а self.vm присваивался и не читался: и рисовалка, и данные лежали
        # мёртвым грузом. Пончик без подписей — украшение, поэтому рядом легенда.
        self._mem_donut(c, 74, H-96, 42, 13)
        # ===== ЦЕНТР: вращающаяся планета-устройство =====
        self._globe(c, cx, cy, gr, fr)
        # характеристики устройства — под планетой (на «земле»)
        di=self._device_info()
        c.create_text(cx, cy+gr+18, fill=TEXT, font=("SF Pro Display",15,"bold"), text=di["name"])
        c.create_text(cx, cy+gr+38, fill=CYAN, font=("SF Pro Text",11,"bold"),
                      text=f'{di["chip"]} · {di["ram"]}' if di["chip"] else di["ram"])
        c.create_text(cx, H-16, fill=MUTED, font=("SF Pro Text",9),
                      text=f'{di["model"]} · macOS {di["os"]}')
        c.configure(scrollregion=(0,0,W,H))

    # Цвета сегментов состава памяти. Порядок фиксирован VM_KEYS, чтобы
    # сегменты не прыгали местами между перерисовками.
    VM_COLORS = {"active": BLUE, "wired": PURPLE, "compressed": YELLOW,
                 "inactive": CYAN, "free": GREEN}

    def _mem_donut(self, c, cx, cy, r, w):
        """Пончик состава памяти + легенда справа. Молчит, пока нет данных."""
        vm = getattr(self, "vm", None) or {}
        total = sum(vm.get(k, 0) for k in VM_KEYS)
        if total <= 0:
            return
        segs = [(vm.get(k, 0) / total, self.VM_COLORS[k]) for k in VM_KEYS]
        used = total - vm.get("free", 0)
        self._donut(c, cx, cy, r, w, segs,
                    center_top=f"{used * 100 // total}%", center_bot=L("занято"))
        lx = cx + r + 16
        ly = cy - r + 2
        for k in VM_KEYS:
            v = vm.get(k, 0)
            if v <= 0: continue
            c.create_oval(lx, ly + 3, lx + 7, ly + 10, fill=self.VM_COLORS[k], outline="")
            c.create_text(lx + 13, ly + 6, anchor="w", fill=MUTED, font=("SF Pro Text", 9),
                          text=f"{L(VM_LABELS[k])} {human(v)}")
            ly += 15

    def _battery(self, c, x,y,w,h,frac,charging):
        col = GREEN if charging or frac>.4 else (YELLOW if frac>.2 else RED)
        self._round(c, x,y,x+w,y+h, 7, fill="", outline=MUTED, width=3)
        c.create_rectangle(x+w,y+h*0.32,x+w+6,y+h*0.68, fill=MUTED, outline=MUTED)
        p=4; self._round(c, x+p,y+p,x+p+(w-2*p)*frac,y+h-p, 4, fill=col, outline=col)
        if charging:
            cx0,cy0=x+w/2,y+h/2
            c.create_polygon(cx0+4,cy0-11,cx0-6,cy0+2,cx0+1,cy0+2,cx0-4,cy0+11,cx0+7,cy0-2,cx0,cy0-2,
                             fill="white", outline="white")

    # ================= УМНАЯ ОЧИСТКА =================
    def show_smart(self):
        tk.Label(self.main, text=L("Умная очистка"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text=L("Один проход по всем безопасным категориям. Всё уходит в Корзину."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,10))
        top=tk.Frame(self.main, bg=GLASS); top.pack(fill="x", padx=24, pady=6)
        self.smart_big=tk.Label(top, text=L("Сканирую…"), bg=GLASS, fg=GREEN, font=("SF Pro Display",30,"bold"))
        self.smart_big.pack(side="left", padx=20, pady=16)
        self.smart_sub=tk.Label(top, text=L("оцениваю объём…"), bg=GLASS, fg=MUTED, font=("SF Pro Text",12))
        self.smart_sub.pack(side="left", pady=16)
        self.smart_btn=self._btn(top, "🧹 Очистить всё", GREEN, self._smart_clean)
        self.smart_btn.pack(side="right", padx=18, pady=14)
        self.smart_list=tk.Frame(self.main, bg=GLASS); self.smart_list.pack(fill="both", expand=True, padx=24, pady=(8,16))
        self.smart_found={}
        self._spawn(self._smart_w)

    def _smart_w(self):
        found={}; total=0
        for cid,title,paths,skip,mode in CATEGORIES:
            if skip and app_running(skip): continue
            items,ct=[],0
            for p in paths:
                if not os.path.exists(p): continue
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm)
                        if os.path.islink(fp): continue   # не трогаем симлинки пользователя
                        s=path_size(fp); ct+=s; items.append((fp,s))
                else: s=path_size(p); ct+=s; items.append((p,s))
            if ct>0: found[cid]=(title,items,ct); total+=ct
        self.q.put(("smart",(found,total),None))

    def _render_smart(self, found, total):
        self.smart_found={c:v[1] for c,v in found.items()}
        self.smart_big.configure(text=human(total)); self.smart_sub.configure(text=L("можно освободить безопасно"))
        for w in self.smart_list.winfo_children(): w.destroy()
        for cid,(title,items,ct) in sorted(found.items(), key=lambda x:-x[1][2]):
            r=tk.Frame(self.smart_list, bg=GLASS); r.pack(fill="x", padx=14, pady=5)
            tk.Label(r, text="🧩  "+title, bg=GLASS, fg=TEXT, font=("SF Pro Text",12), anchor="w").pack(side="left")
            tk.Label(r, text=human(ct), bg=GLASS, fg=GREEN, font=("SF Pro Text",12,"bold")).pack(side="right")
        if not found:
            tk.Label(self.smart_list, text=L("Чисто! Нечего освобождать."), bg=GLASS, fg=MUTED,
                     font=("SF Pro Text",13)).pack(anchor="w", padx=14, pady=14)

    def _smart_clean(self):
        if not self.smart_found: return
        tot=sum(s for items in self.smart_found.values() for _,s in items)
        if not messagebox.askyesno("Умная очистка", f"Переместить в Корзину ~{human(tot)}?"): return
        self.smart_big.configure(text=L("Очищаю…")); self._spawn(self._smart_clean_w)

    def _smart_clean_w(self):
        freed=0
        for items in list(self.smart_found.values()):
            for fp,s in items:
                if to_trash(fp): freed+=s
        self.q.put(("smartdone", freed, None))

    # ================= АВТОПИЛОТ =================
    def show_autopilot(self):
        tk.Label(self.main, text=L("Автопилот"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text=L("Фоновый страж следит за памятью и при пике сам чистит и разгружает."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,14))
        card=tk.Frame(self.main, bg=GLASS); card.pack(fill="x", padx=24, pady=6)
        self.ap_state=tk.Label(card, text="…", bg=GLASS, fg=TEXT, font=("SF Pro Display",16,"bold"))
        self.ap_state.pack(side="left", padx=18, pady=18)
        self._btn(card, "Включить", GREEN, lambda: self._ap("start")).pack(side="right", padx=(8,18), pady=14)
        self._btn(card, "Выключить", RED, lambda: self._ap("stop")).pack(side="right", pady=14)
        row=tk.Frame(self.main, bg=BG0); row.pack(fill="x", padx=24, pady=8)
        self._btn(row, "⚡️ Оптимизировать сейчас", BLUE, self._optimize_now).pack(side="left")
        self._btn(row, "🧊 Освободить место на диске", GREEN, self._free_purgeable).pack(side="left", padx=8)

        # Переключатель закрытия браузеров (по умолчанию ВЫКЛ)
        opt=tk.Frame(self.main, bg=BG0); opt.pack(fill="x", padx=24, pady=(2,4))
        self.ap_close_var=tk.BooleanVar(value=os.path.exists(os.path.join(OPT,"close_browsers.on")))
        tk.Checkbutton(opt, text=L("  Разрешить автопилоту закрывать фоновые браузеры при пике памяти"),
                       variable=self.ap_close_var, command=self._toggle_close_browsers,
                       bg=BG0, fg=TEXT, selectcolor=GLASS, activebackground=BG0, activeforeground=TEXT,
                       font=("SF Pro Text",11), anchor="w").pack(side="left")
        tk.Label(self.main, text="По умолчанию выключено: автопилот чистит кэши и разгружает память, "
                 "не трогая ваши вкладки. Дефрагментация SSD не нужна и вредна — поэтому её нет.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",10), wraplength=600, justify="left"
                 ).pack(anchor="w", padx=24, pady=(0,6))

        # Сводка за сутки — ответ на вопрос «он вообще работает?» без чтения
        # четырёх строк журнала на каждое срабатывание.
        self.ap_summary=tk.Label(self.main, text="", bg=GLASS, fg=TEXT,
                                 font=("SF Pro Text",12,"bold"), anchor="w", justify="left",
                                 padx=14, pady=11, wraplength=620)
        self.ap_summary.pack(fill="x", padx=24, pady=(10,0))
        tk.Label(self.main, text=L("Журнал автопилота:"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)
                 ).pack(anchor="w", padx=24, pady=(10,2))
        self.ap_log=tk.Text(self.main, bg=GLASS, fg=TEXT, font=("SF Mono",11), relief="flat",
                            padx=12, pady=10); self.ap_log.pack(fill="both", expand=True, padx=24, pady=(0,16))
        self._ap_refresh()

    def _ap_install(self):
        """Разложить страж в ~/mac-optimizer и поставить LaunchAgent.

        Скрипты автопилота живут в репозитории (autopilot/), а работает страж
        из ~/mac-optimizer. Если этот каталог почистили или приложение
        переехало, ctl.sh пропадал и автопилот молча становился «недоступен» —
        поэтому ставим его сами, а не только сообщаем о поломке.
        """
        inst=os.path.join(AP_SRC,"install.sh")
        if not os.path.exists(inst): return False
        run(["/bin/bash",inst], t=60)
        return os.path.exists(os.path.join(OPT,"ctl.sh"))

    def _ap(self, action):
        ctl=os.path.join(OPT,"ctl.sh")
        if not os.path.exists(ctl) and action=="start":
            if not self._ap_install():
                messagebox.showerror("Автопилот",
                    "Не удалось установить страж.\nОжидался установщик: "
                    + os.path.join(AP_SRC, "install.sh")
                    + "\nПапка autopilot/ должна лежать рядом с CleanMac.py.")
                return
            self._ap_refresh(); return
        if os.path.exists(ctl): run(["/bin/bash",ctl,action]); time.sleep(1)
        self._ap_refresh()

    def _ap_refresh(self):
        ctl=os.path.join(OPT,"ctl.sh")
        if not os.path.exists(ctl):
            st="⚪️ НЕ УСТАНОВЛЕН" if os.path.exists(os.path.join(AP_SRC,"install.sh")) \
               else "🔴 НЕДОСТУПЕН (нет папки autopilot/)"
        else:
            out=run(["/bin/bash",ctl,"status"]); st="🟢 РАБОТАЕТ" if "🟢" in out or "Работает" in out else "🔴 ОСТАНОВЛЕН"
        self.ap_state.configure(text="Автопилот: "+st, fg=(GREEN if "🟢" in st else RED))
        log=os.path.join(OPT,"optimize.log")
        # сводка за сутки — читаем весь журнал, а не хвост: срабатывание
        # растянуто на несколько строк и хвост мог бы обрезать его посередине
        if getattr(self, "ap_summary", None) and self.ap_summary.winfo_exists():
            try:
                with open(log, encoding="utf-8", errors="replace") as f:
                    s = parse_autopilot_log(f.read())
                self.ap_summary.configure(text=format_autopilot_summary(s),
                                          fg=(YELLOW if s["peaks"] else MUTED))
            except Exception:
                self.ap_summary.configure(text="Журнала пока нет — автопилот ещё не срабатывал.", fg=MUTED)
        self.ap_log.configure(state="normal"); self.ap_log.delete("1.0","end")
        if os.path.exists(log):
            body=open(log).read()[-2500:]
        elif "НЕ УСТАНОВЛЕН" in st:
            body="Страж ещё не установлен. Нажмите «Включить» — файлы\nразложатся в ~/mac-optimizer и агент запустится."
        else:
            body="(журнал пуст — пиков не было)"
        self.ap_log.insert("end", body)
        self.ap_log.configure(state="disabled")

    def _optimize_now(self):
        self._spawn(self._optimize_worker)

    def _optimize_worker(self):
        freed=0
        for cid,_,paths,skip,mode in CATEGORIES:
            if cid=="user_caches": continue
            if skip and app_running(skip): continue
            for p in paths:
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm)
                        if os.path.islink(fp): continue   # не трогаем симлинки пользователя
                        s=path_size(fp)
                        if to_trash(fp): freed+=s
                elif os.path.exists(p):
                    s=path_size(p)
                    if to_trash(p): freed+=s
        # Браузеры закрываем ТОЛЬКО если пользователь явно включил это в настройках.
        # По умолчанию — НЕ трогаем (чтобы не терять открытые вкладки).
        if os.path.exists(os.path.join(OPT, "close_browsers.on")):
            front=run(["osascript","-e",'tell application "System Events" to name of first process whose frontmost is true']).strip()
            for app in ("Microsoft Edge","Google Chrome","Safari","Yandex"):
                if app_running(app) and app!=front: run(["osascript","-e",f'quit app "{as_escape(app)}"'])
        self.q.put(("optimized", freed, None))

    # ===== 1 КЛИК «УСКОРИТЬ» — всё безопасное разом (лучше BoostSpeed: без дефрага/реестра) =====
    def _boost_now(self):
        if getattr(self, "_boosting", False): return
        self._boosting = True
        self._spawn(self._boost_worker)

    def _boost_worker(self):
        steps = []
        # 1) Безопасные кэши и логи → Корзина (обратимо)
        freed = 0
        for cid,_,paths,skip,mode in CATEGORIES:
            if skip and app_running(skip): continue       # не трогаем кэш открытого браузера
            for p in paths:
                if not os.path.exists(p): continue
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm)
                        if os.path.islink(fp): continue   # не трогаем симлинки пользователя
                        s=path_size(fp)
                        if to_trash(fp): freed+=s
                else:
                    s=path_size(p)
                    if to_trash(p): freed+=s
        steps.append(f"🧽 Кэши и логи → Корзина: {human(freed)}")

        # 2) Освободить «очищаемое» место (локальные снимки APFS) — безопасно
        purged = 0
        try:
            before = shutil.disk_usage(HOME).free
            run(["tmutil","thinlocalsnapshots","/","999999999999","4"], 120)
            purged = max(0, shutil.disk_usage(HOME).free - before)
        except Exception: pass
        if purged: steps.append(f"🧊 Освобождено места: {human(purged)}")

        # 3) Сбросить кэш миниатюр Quick Look (без пароля)
        run(["qlmanage","-r","cache"], 30)
        steps.append("👁 Кэш Quick Look сброшен")

        # 4) Разгрузить неактивную память (purge — без админа на свежих macOS; иначе тихо пропустим)
        run(["/usr/sbin/purge"], 30)
        steps.append("⚡️ Память разгружена")

        record_cleanup(freed + purged, "boost")
        self._boosting = False
        self.q.put(("boosted", freed + purged, steps))

    # ===== ✨ ВОЛШЕБНАЯ КНОПКА: одним кликом — ВСЁ безопасное, без диалогов =====
    def _optimize_all(self):
        """Запуск авто-оптимизации в фоне. Без messagebox-подтверждений —
        идея «установил → нажал → оптимизировано». Повторный клик игнорируется."""
        if getattr(self, "_optimizing", False):
            return
        self._optimizing = True
        try: self.magic_btn.configure(text=L("  ✨ Оптимизирую…  "))
        except Exception: pass
        self._spawn(self._optimize_all_w)

    def _opt_progress(self, idx, total, label, detail=""):
        """Живой прогресс шага в UI-поток (не блокируя его)."""
        self.q.put(("optprog", (idx, total, label, detail), None))

    def _optimize_all_w(self):
        steps = optimize_plan(); n = len(steps); done = []; skipped = []; freed = 0
        for i, (key, label) in enumerate(steps, 1):
            self._opt_progress(i, n, label)
            try:
                if key == "caches":
                    got = 0
                    # кэши и логи приложений → Корзина; кэш браузера — только если закрыт
                    for cid,_,paths,skip,mode in CATEGORIES:
                        if skip and app_running(skip): continue
                        for p in paths:
                            if not os.path.exists(p): continue
                            if mode == "subitems" and os.path.isdir(p):
                                for nm in os.listdir(p):
                                    fp = os.path.join(p, nm)
                                    if os.path.islink(fp): continue   # не трогаем симлинки пользователя
                                    s = path_size(fp)
                                    if to_trash(fp): got += s
                            else:
                                s = path_size(p)
                                if to_trash(p): got += s
                    freed += got
                    done.append(f"{label}: {human(got)}")

                elif key == "syscache":
                    # системные кэши без пароля: Quick Look + кэш шрифтов пользователя
                    run(["qlmanage", "-r", "cache"], 30)
                    run(["atsutil", "databases", "-removeUser"], 30)
                    done.append(label)

                elif key == "snapshots":
                    got = 0
                    try:
                        before = shutil.disk_usage(HOME).free
                        run(["tmutil", "thinlocalsnapshots", "/", "999999999999", "4"], 120)
                        got = max(0, shutil.disk_usage(HOME).free - before)
                    except Exception: pass
                    freed += got
                    done.append(f"{label}: {human(got)}" if got else label)

                elif key == "memory":
                    run(["/usr/sbin/purge"], 30)
                    done.append(label)

                elif key == "emptydirs":
                    cnt = 0
                    for d in find_empty_dirs():
                        if to_trash(d): cnt += 1
                    done.append(f"{label}: {cnt}")

                elif key == "broken":
                    cnt = 0
                    for fp in find_broken_files():
                        if to_trash(fp): cnt += 1
                    done.append(f"{label}: {cnt}")

                elif key == "orphans":
                    got = 0
                    for p, s in orphaned_leftovers():
                        if to_trash(p): got += s
                    freed += got
                    done.append(f"{label}: {human(got)}")

                elif key == "brewcleanup":
                    # Чистит старые версии формул и кэш загрузок Homebrew → реально освобождает место.
                    brew = brew_path()
                    if not brew:
                        skipped.append(f"{label}: Homebrew не установлен")
                    else:
                        before = 0
                        try: before = shutil.disk_usage(HOME).free
                        except Exception: pass
                        run([brew, "cleanup", "-s", "--prune=all"], 180)
                        got = 0
                        try: got = max(0, shutil.disk_usage(HOME).free - before)
                        except Exception: pass
                        freed += got
                        done.append(f"{label}: {human(got)}" if got else label)

                elif key == "launchsvc":
                    # Перестраивает БД Launch Services: убирает дубли в «Открыть с помощью». Без sudo.
                    lsreg = ("/System/Library/Frameworks/CoreServices.framework/"
                             "Versions/A/Frameworks/LaunchServices.framework/"
                             "Versions/A/Support/lsregister")
                    if os.path.exists(lsreg):
                        run([lsreg, "-kill", "-r", "-domain", "local",
                             "-domain", "system", "-domain", "user"], 120)
                        done.append(label)
                    else:
                        skipped.append(f"{label}: lsregister недоступен в этой системе")

                elif key == "dockicons":
                    # Перезапуск Dock сбрасывает кэш иконок Dock. Безопасно, Dock сам поднимется.
                    run(["killall", "Dock"], 15)
                    done.append(label)

                elif key == "dns":
                    run(["/bin/bash", "-c", "dscacheutil -flushcache; killall -HUP mDNSResponder"], 30)
                    done.append(label)

                elif key == "trim":
                    # Информационный шаг: на macOS TRIM для SSD включён системой автоматически.
                    # Дефрагментация APFS/SSD НЕ нужна и вредна — ничего не делаем.
                    done.append("💽 SSD обслуживается системой (TRIM авто) — действий не требуется")
            except Exception:
                pass  # один сбойный шаг не должен валить всю оптимизацию

        # ----- скан (БЕЗ удаления): дубли / крупные файлы / старые загрузки -----
        self._opt_progress(n, n, "🔎 Сканирую дубли, крупные файлы, старые загрузки…")
        review = self._optimize_scan_review()

        record_cleanup(freed, "magic")
        self._optimizing = False
        self.q.put(("optimized_all", {"freed": freed, "steps": done,
                                       "skipped": skipped, "review": review}, None))

    def _optimize_scan_review(self):
        """Безопасный обзор пользовательских данных для ревью (НЕ удаляет).
        Возвращает [(tool_key, текст)] — что нашли и куда вести пользователя."""
        review = []
        # дубликаты в Downloads/Desktop/Documents (> 1 МБ)
        try:
            by_size = {}
            for base in (os.path.join(HOME, d) for d in ("Downloads", "Desktop", "Documents")):
                if not os.path.isdir(base): continue
                for root, _, files in os.walk(base):
                    for fn in files:
                        fp = os.path.join(root, fn)
                        try:
                            s = os.path.getsize(fp)
                            if s > 1024*1024: by_size.setdefault(s, []).append(fp)
                        except Exception: pass
            dup_n, dup_waste = 0, 0
            for s, paths in by_size.items():
                if len(paths) < 2: continue
                bh = {}
                for fp in paths:
                    h = self._hash(fp)
                    if h: bh.setdefault(h, []).append(fp)
                for same in bh.values():
                    if len(same) > 1:
                        dup_n += len(same) - 1; dup_waste += s * (len(same) - 1)
            if dup_n:
                review.append(("dupes", f"👯 Дубликаты: {dup_n} лишних копий на ~{human(dup_waste)}"))
        except Exception: pass
        # крупные файлы (> 100 МБ) вне Library/.Trash
        try:
            big_n, big_sz, skip = 0, 0, {".Trash", "Library"}
            for root, dirs, files in os.walk(HOME):
                parts = root.replace(HOME, "").strip("/").split("/")
                if parts and parts[0] in skip: dirs[:] = []; continue
                for fn in files:
                    try:
                        s = os.path.getsize(os.path.join(root, fn))
                        if s > 100*1024*1024: big_n += 1; big_sz += s
                    except Exception: pass
            if big_n:
                review.append(("large", f"📦 Крупные файлы: {big_n} шт на ~{human(big_sz)}"))
        except Exception: pass
        # старые загрузки (> 90 дней) в ~/Downloads
        try:
            now = time.time(); old_n, old_sz = 0, 0
            dl = os.path.join(HOME, "Downloads")
            if os.path.isdir(dl):
                for fn in os.listdir(dl):
                    fp = os.path.join(dl, fn)
                    try:
                        if os.path.isfile(fp) and (now - os.path.getmtime(fp)) > 90*86400:
                            old_n += 1; old_sz += os.path.getsize(fp)
                    except Exception: pass
            if old_n:
                review.append(("large", f"🕒 Старые загрузки (>90 дн): {old_n} шт на ~{human(old_sz)}"))
        except Exception: pass
        return review

    def _render_optimize_summary(self, res):
        """Финальная сводка волшебной кнопки: освобождено X, шагов N,
        + найденные категории для ревью со ссылками на инструменты."""
        freed = res.get("freed", 0); steps = res.get("steps", [])
        skipped = res.get("skipped", []); review = res.get("review", [])
        try: self.magic_btn.configure(text=L("  ✓ Оптимизировано  "))
        except Exception: pass
        self.after(2400, lambda: self.magic_btn.configure(text=L("  ✨ Оптимизировать  "))
                   if getattr(self, "magic_btn", None) and self.magic_btn.winfo_exists() else None)
        if getattr(self, "magic_prog", None) and self.magic_prog.winfo_exists():
            self.magic_prog.configure(text=f"✓ Готово · освобождено ~{human(freed)} · шагов {len(steps)}")
        self.status(f"Оптимизация завершена · ~{human(freed)}")
        # Модальное окно-сводка (без подтверждений на безопасных шагах — они уже сделаны).
        win = tk.Toplevel(self); win.title("Оптимизация завершена"); win.configure(bg=BG0)
        win.transient(self); win.resizable(False, False)
        tk.Label(win, text=L("✨ Готово — Mac оптимизирован"), bg=BG0, fg=GREEN,
                 font=("SF Pro Display", 18, "bold")).pack(anchor="w", padx=22, pady=(18,2))
        tk.Label(win, text=f"Освобождено ~{human(freed)} · выполнено шагов: {len(steps)}",
                 bg=BG0, fg=TEXT, font=("SF Pro Text", 12)).pack(anchor="w", padx=22, pady=(0,10))
        tk.Label(win, text=L("Выполнено на этом Mac:"), bg=BG0, fg=TEXT,
                 font=("SF Pro Text", 11, "bold")).pack(anchor="w", padx=22, pady=(2,4))
        card=tk.Frame(win, bg=GLASS); card.pack(fill="x", padx=18, pady=4)
        for s in steps:
            tk.Label(card, text="• "+s, bg=GLASS, fg=TEXT, font=("SF Pro Text", 11),
                     anchor="w", justify="left", wraplength=460).pack(anchor="w", padx=14, pady=2)
        # Прозрачность: что неприменимо к этому устройству и почему.
        if skipped:
            tk.Label(win, text=L("Пропущено (неприменимо на этом Mac):"), bg=BG0, fg=MUTED,
                     font=("SF Pro Text", 11, "bold")).pack(anchor="w", padx=22, pady=(12,4))
            sc=tk.Frame(win, bg=GLASS); sc.pack(fill="x", padx=18, pady=4)
            for s in skipped:
                tk.Label(sc, text="– "+s, bg=GLASS, fg=MUTED, font=("SF Pro Text", 11),
                         anchor="w", justify="left", wraplength=460).pack(anchor="w", padx=14, pady=2)
        if review:
            tk.Label(win, text=L("По всем параметрам — найдено для вашего ревью (не удалено):"),
                     bg=BG0, fg=MUTED, font=("SF Pro Text", 11, "bold")).pack(anchor="w", padx=22, pady=(12,4))
            rc=tk.Frame(win, bg=GLASS); rc.pack(fill="x", padx=18, pady=4)
            for tool_key, text in review:
                row=tk.Frame(rc, bg=GLASS); row.pack(fill="x", padx=12, pady=4)
                tk.Label(row, text=text, bg=GLASS, fg=TEXT, font=("SF Pro Text", 11),
                         anchor="w").pack(side="left", fill="x", expand=True)
                op=tk.Label(row, text=L("Открыть →"), bg=BLUE, fg="white",
                            font=("SF Pro Text", 10, "bold"), padx=10, pady=3, cursor="pointinghand")
                op.pack(side="right")
                op.bind("<Button-1>", lambda e, k=tool_key, w=win: (w.destroy(), self._open_tool(k)))
        else:
            tk.Label(win, text=L("Пользовательские данные в порядке — дублей и крупных файлов не найдено."),
                     bg=BG0, fg=MUTED, font=("SF Pro Text", 11)).pack(anchor="w", padx=22, pady=(12,4))
        tk.Label(win, text="Очищенное обратимо — лежит в Корзине. Дубли, крупные и старые файлы "
                 "не удалялись автоматически: решение за вами.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text", 10), wraplength=480, justify="left"
                 ).pack(anchor="w", padx=22, pady=(10,6))
        self._btn(win, "Готово", GREEN, win.destroy).pack(anchor="e", padx=18, pady=(4,16))
        try:
            win.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width()-win.winfo_width())//2
            y = self.winfo_rooty() + 80
            win.geometry(f"+{max(0,x)}+{max(0,y)}")
        except Exception: pass

    def _open_tool(self, key):
        """Перейти в раздел Инструменты и открыть нужный инструмент (для ревью)."""
        self.nav("tools")
        try: self._tool(key)
        except Exception: pass

    def _toggle_close_browsers(self):
        flag=os.path.join(OPT,"close_browsers.on")
        try:
            if self.ap_close_var.get():
                os.makedirs(OPT, exist_ok=True); open(flag,"w").write("on")
            elif os.path.exists(flag):
                os.remove(flag)
        except Exception as e:
            messagebox.showwarning("CleanMac", f"Не удалось сохранить настройку: {e}")

    def _free_purgeable(self):
        """Безопасное освобождение места: удаление локальных снимков Time Machine (APFS).
        Это реальный аналог 'очистки' без вреда — в отличие от дефрагментации SSD."""
        if not messagebox.askyesno("Освободить место",
            "Удалить локальные снимки Time Machine (APFS) и освободить «очищаемое» место?\n\n"
            "Это безопасно: облачные/внешние резервные копии не затрагиваются. "
            "Дефрагментация SSD не выполняется — она бесполезна и вредна для SSD."):
            return
        self.status("🧊 Освобождаю место…")
        self._spawn(self._free_purgeable_w)

    def _free_purgeable_w(self):
        before=0
        try: before=shutil.disk_usage(HOME).free
        except Exception: pass
        # thinlocalsnapshots просит до ~999 ГБ освободить, срочность 4 (максимум)
        run(["tmutil","thinlocalsnapshots","/","999999999999","4"], 120)
        after=before
        try: after=shutil.disk_usage(HOME).free
        except Exception: pass
        freed=max(0, after-before)
        self.q.put(("purged", freed, None))

    # ================= ОЧИСТКА =================
    def show_cleaner(self):
        tk.Label(self.main, text=L("Очистка"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text=L("«Анализ» посчитает объём, «Очистить» переместит в Корзину."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,12))
        wrap=tk.Frame(self.main, bg=GLASS); wrap.pack(fill="both", expand=True, padx=24, pady=(0,10))
        self.cat_vars={}; self.cat_size_lbl={}
        for cid,title,paths,skip,mode in CATEGORIES:
            r=tk.Frame(wrap, bg=GLASS); r.pack(fill="x", padx=14, pady=6)
            var=tk.BooleanVar(value=(cid!="user_caches")); self.cat_vars[cid]=var
            tk.Checkbutton(r, text="  "+title, variable=var, bg=GLASS, fg=TEXT, selectcolor=BG0,
                           activebackground=GLASS, activeforeground=TEXT, font=("SF Pro Text",12), anchor="w").pack(side="left")
            if skip: tk.Label(r, text=f"(если {skip} закрыт)", bg=GLASS, fg=MUTED, font=("SF Pro Text",9)).pack(side="left", padx=6)
            sl=tk.Label(r, text="—", bg=GLASS, fg=GREEN, font=("SF Pro Text",11,"bold")); sl.pack(side="right"); self.cat_size_lbl[cid]=sl
        bar=tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=(4,16))
        self.total_lbl=tk.Label(bar, text=L("Готово к анализу"), bg=BG0, fg=TEXT, font=("SF Pro Text",13,"bold")); self.total_lbl.pack(side="left")
        self._btn(bar,L("Очистить"),GREEN,self.run_clean).pack(side="right", padx=(8,0))
        self._btn(bar,L("Анализ"),BLUE,self.run_analyze).pack(side="right")

    def _btn(self, parent, text, color, cmd):
        return RoundedButton(parent, text, color, cmd)

    def run_analyze(self):
        self.total_lbl.configure(text=L("Анализирую…"))
        for cid in self.cat_vars: self.cat_size_lbl[cid].configure(text="…")
        # Снимаем значения Tk-переменных в ГЛАВНОМ потоке: чтение BooleanVar.get()
        # из рабочего потока обращается к интерпретатору Tcl не из main loop и
        # может уронить приложение. Передаём готовый набор выбранных id воркеру.
        sel={cid for cid in self.cat_vars if self.cat_vars[cid].get()}
        self._spawn(self._analyze_worker, sel)

    def _analyze_worker(self, sel):
        self.found={}; total=0
        for cid,title,paths,skip,mode in CATEGORIES:
            if cid not in sel: self.q.put(("catsize",cid,None)); continue
            if skip and app_running(skip): self.q.put(("catsize",cid,"skip")); continue
            items,ct=[],0
            for p in paths:
                if not os.path.exists(p): continue
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm)
                        if os.path.islink(fp): continue   # не трогаем симлинки пользователя
                        s=path_size(fp); ct+=s; items.append((fp,s))
                else: s=path_size(p); ct+=s; items.append((p,s))
            self.found[cid]=items; total+=ct; self.q.put(("catsize",cid,ct))
        self.q.put(("total",total,None))

    def run_clean(self):
        sel=[c for c in self.cat_vars if self.cat_vars[c].get()]
        if not sel: messagebox.showinfo("CleanMac","Не выбрана категория."); return
        if not self.found: messagebox.showinfo("CleanMac","Сначала «Анализ»."); return
        if not messagebox.askyesno("Подтверждение","Переместить найденное в Корзину?"): return
        self.total_lbl.configure(text=L("Очищаю…")); self._spawn(self._clean_worker, sel)

    def _clean_worker(self, sel):
        freed,moved=0,0
        for cid in sel:
            for fp,s in self.found.get(cid,[]):
                if to_trash(fp): freed+=s; moved+=1
        self.q.put(("cleaned",freed,moved))

    # ================= ИНСТРУМЕНТЫ (интерактивные) =================
    def show_tools(self):
        tk.Label(self.main, text=L("Инструменты"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,8))
        # Было 19 плоских чипов в три ряда вперемешку — поиск файлов, обслуживание
        # системы, браузеры и деинсталляция в одной куче. Теперь два уровня:
        # 4 семейства сверху, внутри — только чипы выбранного семейства.
        # На экране одновременно 4 + 3..7 кнопок вместо девятнадцати.
        self.tool_chips={}
        gwrap=tk.Frame(self.main, bg=BG0); gwrap.pack(fill="x", padx=22, pady=(0,2))
        self.tool_gbtns={}
        for gkey,glabel,_ in self.TOOL_GROUPS:
            gb=tk.Label(gwrap, text=L(glabel), bg=GLASS, fg=TEXT, font=("SF Pro Text",12,"bold"),
                        padx=14, pady=9, cursor="pointinghand")
            gb.pack(side="left", padx=(0,6))
            gb.bind("<Button-1>", lambda e,k=gkey: self._tool_group(k))
            self.tool_gbtns[gkey]=gb
        self.chip_row=tk.Frame(self.main, bg=BG0); self.chip_row.pack(fill="x", padx=22, pady=(4,0))
        self.tpanel=tk.Frame(self.main, bg=BG0); self.tpanel.pack(fill="both", expand=True, padx=22, pady=(10,14))
        self._lv=[]
        self._tool_group(getattr(self, "_tool_group_cur", None) or self.TOOL_GROUPS[0][0])

    # Семейства инструментов: ключ, подпись, состав.
    TOOL_GROUPS = [
        ("space", "🔍 Найти и освободить", [
            ("large","📦 Крупные файлы"), ("bigold","📦🕒 Большие и старые"),
            ("olddl","🕒 Старые загрузки"), ("dupes","👯 Дубликаты"),
            ("shots","📸 Скриншоты"), ("mailatt","📧 Вложения Почты"),
            ("devjunk","🧰 Dev-мусор"), ("disk","🗺 Карта диска"), ("trash","♻️ Корзина")]),
        ("apps", "🧩 Приложения", [
            ("uninstall","🧩 Деинсталлятор"), ("leftovers","🧹 Остатки"),
            ("startup","⚙️ Автозагрузка"), ("updater","📦 Апдейтер")]),
        ("web", "🌐 Браузеры", [
            ("browsers","🌐 Следы браузеров"), ("extensions","🧩 Расширения"),
            ("vacuum","🗜 Сжать базы")]),
        ("system", "🩺 Система", [
            ("maintain","🩺 Обслуживание"), ("shred","🔥 Шредер"), ("history","📜 История")]),
    ]

    def _tool_group(self, gkey):
        """Показать чипы одного семейства; остальные скрыты, а не свалены рядом."""
        self._tool_group_cur = gkey
        for k,b in self.tool_gbtns.items():
            b.configure(bg=(BLUE if k==gkey else GLASS), fg=("white" if k==gkey else TEXT))
        for w in self.chip_row.winfo_children(): w.destroy()
        self.tool_chips={}
        chips = next(c for k,_,c in self.TOOL_GROUPS if k==gkey)
        for key,lbl in chips:
            b=tk.Label(self.chip_row, text=L(lbl), bg=GLASS, fg=TEXT, font=("SF Pro Text",12),
                       padx=11, pady=8, cursor="pointinghand")
            b.pack(side="left", padx=(0,6))
            b.bind("<Button-1>", lambda e,k=key:self._tool(k))
            b.bind("<Enter>", lambda e,bb=b: bb.configure(bg=GLASS_HI) if bb.cget("bg")!=BLUE else None)
            b.bind("<Leave>", lambda e,bb=b: bb.configure(bg=GLASS) if bb.cget("bg")==GLASS_HI else None)
            self.tool_chips[key]=b
        # запомненный чип этого семейства, иначе первый
        want = getattr(self, "_tool_last", {}).get(gkey) or chips[0][0]
        self._tool(want)

    def _tool(self, key):
        if not hasattr(self, "_tool_last"): self._tool_last={}
        self._tool_last[getattr(self, "_tool_group_cur", "space")] = key
        for k,b in self.tool_chips.items(): b.configure(bg=(BLUE if k==key else GLASS), fg=("white" if k==key else TEXT))
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        {"startup":self._t_startup,"large":self._t_large,"devjunk":self._t_devjunk,"bigold":self._t_bigold,
         "olddl":self._t_olddl,"mailatt":self._t_mailatt,"dupes":self._t_dupes,
         "uninstall":self._t_uninstall,"disk":self._t_disk,"maintain":self._t_maintain,
         "shots":self._t_shots,"shred":self._t_shred,"vacuum":self._t_vacuum,
         "updater":self._t_updater,
         "leftovers":self._t_leftovers,"history":self._t_history,
         "browsers":self._t_browsers,"extensions":self._t_extensions,
         "trash":self._t_trash}[key]()

    def _ptitle(self, text, sub=""):
        tk.Label(self.tpanel, text=text, bg=BG0, fg=TEXT, font=("SF Pro Display",15,"bold")).pack(anchor="w")
        if sub: tk.Label(self.tpanel, text=sub, bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", pady=(0,6))

    def _scrollarea(self):
        wrap=tk.Frame(self.tpanel, bg=GLASS); wrap.pack(fill="both", expand=True, pady=(4,8))
        cv=tk.Canvas(wrap, bg=GLASS, highlightthickness=0)
        sb=tk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        inner=tk.Frame(cv, bg=GLASS)
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win=cv.create_window((0,0), window=inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        def _wheel(e):
            try: cv.yview_scroll(int(-e.delta/3), "units")
            except Exception: pass
        cv.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", _wheel))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        return inner

    def _checkrow(self, inner, path, label, size, preselect=False):
        r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
        v=tk.BooleanVar(value=preselect)
        tk.Checkbutton(r, variable=v, bg=GLASS, selectcolor=BG0, activebackground=GLASS,
                       highlightthickness=0, bd=0).pack(side="left")
        tk.Label(r, text=human(size), bg=GLASS, fg=MUTED, font=("SF Pro Text",10), width=9, anchor="e").pack(side="right", padx=(6,4))
        tk.Label(r, text=label, bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
        self._lv.append((v,path,size))

    def _actionbar(self, total_text, on_trash, trash_label="🗑 В Корзину выбранное"):
        bar=tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x")
        tk.Label(bar, text=total_text, bg=BG0, fg=TEXT, font=("SF Pro Text",12,"bold")).pack(side="left")
        if on_trash: self._btn(bar, trash_label, GREEN, on_trash).pack(side="right", padx=(8,0))
        self._btn(bar, "Показать в Finder", GLASS_HI, self._reveal_sel).pack(side="right")

    def _reveal_sel(self):
        for v,path,_ in getattr(self,"_lv",[]):
            if v.get(): run(["/usr/bin/open","-R",path]); return
        messagebox.showinfo("CleanMac","Отметьте хотя бы один элемент.")

    def _trash_sel(self, rebuild):
        sel=[(p,s) for v,p,s in getattr(self,"_lv",[]) if v.get()]
        if not sel: messagebox.showinfo("CleanMac","Ничего не выбрано."); return
        tot=sum(s for _,s in sel)
        if not messagebox.askyesno("Подтверждение", f"Переместить в Корзину {len(sel)} элем. (~{human(tot)})?"): return
        freed=sum(s for p,s in sel if to_trash(p))
        messagebox.showinfo("CleanMac", f"В Корзину: {human(freed)}."); rebuild()

    # --- Автозагрузка ---
    def _t_startup(self):
        self._ptitle("Автозагрузка", "Фоновые агенты при входе — можно включать/выключать.")
        li=run(["osascript","-e",'tell application "System Events" to get the name of every login item']).strip()
        tk.Label(self.tpanel, text="Элементы входа: "+(li or "пусто"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text",11)).pack(anchor="w", pady=(0,4))
        inner=self._scrollarea(); la=os.path.join(HOME,"Library/LaunchAgents")
        if os.path.isdir(la):
            for f in sorted(os.listdir(la)):
                if not (f.endswith(".plist") or f.endswith(".disabled")): continue
                on=f.endswith(".plist")
                r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=2)
                tk.Label(r, text=("🟢" if on else "⚪️"), bg=GLASS, fg=TEXT, font=("SF Pro Text",11)).pack(side="left")
                tk.Label(r, text="  "+f, bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
                btn=tk.Label(r, text=("Выключить" if on else "Включить"), bg=(RED if on else GREEN), fg="white",
                             font=("SF Pro Text",10,"bold"), padx=10, pady=3, cursor="pointinghand")
                btn.pack(side="right"); btn.bind("<Button-1>", lambda e,fn=f,o=on: self._toggle_agent(fn,o))

    def _toggle_agent(self, fname, on):
        la=os.path.join(HOME,"Library/LaunchAgents"); src=os.path.join(la,fname); uid=str(os.getuid())
        try:
            if on:
                run(["launchctl","bootout",f"gui/{uid}/{fname[:-6]}"]); os.rename(src, src+".disabled")
            else:
                dst=src[:-9]; os.rename(src, dst); run(["launchctl","bootstrap",f"gui/{uid}", dst])
        except Exception: pass
        self._tool("startup")

    # --- Крупные файлы ---
    def _t_large(self):
        self._ptitle("Крупные файлы", "Файлы крупнее 100 МБ. Отметьте лишние → в Корзину.")
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._large_w)

    def _large_w(self):
        big,skip=[],{".Trash","Library"}
        now=time.time()
        for root,dirs,files in os.walk(HOME):
            parts=root.replace(HOME,"").strip("/").split("/")
            if parts and parts[0] in skip: dirs[:]=[]; continue
            for fn in files:
                fp=os.path.join(root,fn)
                try:
                    s=os.path.getsize(fp)
                    if s>100*1024*1024:
                        age=int((now-os.path.getmtime(fp))/86400)
                        big.append((s,fp,age))
                except Exception: pass
        big.sort(reverse=True); self.q.put(("tool",("large",big[:60]),None))

    def _render_large(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        # нормализуем к (size, path, age) — совместимость со старым форматом
        rows=[(r if len(r)==3 else (r[0],r[1],0)) for r in rows]
        if not hasattr(self,"_large_oldonly"): self._large_oldonly=False
        shown=[r for r in rows if (r[2]>=180)] if self._large_oldonly else rows
        self._ptitle("Крупные и старые файлы", "Файлы крупнее 100 МБ. Возраст — по дате изменения. Отметьте лишние → в Корзину.")
        bar=tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x")
        lbl="☑ Только старые (>6 мес)" if self._large_oldonly else "☐ Только старые (>6 мес)"
        tg=tk.Label(bar, text=lbl, bg=GLASS_HI, fg=TEXT, font=("SF Pro Text",11,"bold"), padx=10, pady=5, cursor="pointinghand")
        tg.pack(side="left"); tg.bind("<Button-1>", lambda e: (setattr(self,"_large_oldonly",not self._large_oldonly), self._render_large(rows)))
        inner=self._scrollarea()
        for s,fp,age in shown:
            agetxt = f"{age//365} г" if age>=365 else (f"{age} дн" if age>0 else "сегодня")
            self._checkrow(inner, fp, f"{fp.replace(HOME,'~')}   ·   {agetxt}", s, preselect=(age>=180))
        if not shown: tk.Label(inner, text=L("  Ничего не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"Показано: {len(shown)} (~{human(sum(s for s,_,_ in shown))}) · старые отмечены",
                        lambda: self._trash_sel(lambda: self._tool('large')))

    # --- Dev-мусор (проектные артефакты сборки) ---
    def _t_devjunk(self):
        self._ptitle("🧰 Dev-мусор", "Проектные node_modules, target, __pycache__, Pods, .venv и т.п. "
                     "Безопасно — пересоздаются менеджером пакетов (npm install / cargo build / …).")
        tk.Label(self.tpanel, text=L("🔎 Ищу артефакты сборки…"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._devjunk_w)

    def _devjunk_w(self):
        rows=scan_dev_junk(HOME, top=200)
        self.q.put(("tool",("devjunk",rows),None))

    def _render_devjunk(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        self._ptitle("🧰 Dev-мусор", "Артефакты сборки — крупные и безопасно пересоздаваемые. "
                     "Отметьте лишние → в Корзину (обратимо). Восстанавливаются командой сборки/установки.")
        inner=self._scrollarea()
        for s,fp,kind in rows:
            self._checkrow(inner, fp, f"{fp.replace(HOME,'~')}   ·   {kind}", s, preselect=False)
        if not rows:
            tk.Label(inner, text=L("  Артефактов сборки не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"Найдено: {len(rows)} (~{human(sum(s for s,_,_ in rows))})",
                        lambda: self._trash_sel(lambda: self._tool('devjunk')))

    # --- Старые загрузки ---
    def _t_olddl(self):
        self._ptitle("Старые загрузки", "Файлы в ~/Downloads старше выбранного срока. Отметьте лишние → в Корзину.")
        if not hasattr(self, "_olddl_days"): self._olddl_days = 90
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        days = self._olddl_days
        threading.Thread(target=lambda: self._olddl_w(days), daemon=True).start()

    def _olddl_w(self, days):
        rows = scan_old_downloads(os.path.join(HOME, "Downloads"), min_days=days, top=200)
        self.q.put(("tool", ("olddl", rows), None))

    def _render_olddl(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv = []
        days = getattr(self, "_olddl_days", 90)
        self._ptitle("Старые загрузки",
                     f"Файлы в ~/Downloads старше {days} дн. Возраст — по дате изменения. Отметьте лишние → в Корзину.")
        bar = tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x", pady=(0,4))
        tk.Label(bar, text=L("Старше:"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(side="left", padx=(0,6))
        for d in (30, 90, 180, 365):
            lbl = {30:"30 дн", 90:"90 дн", 180:"6 мес", 365:"1 год"}[d]
            sel = (d == days)
            ch = tk.Label(bar, text=lbl, bg=(BLUE if sel else GLASS_HI), fg=("white" if sel else TEXT),
                          font=("SF Pro Text",11,"bold"), padx=10, pady=5, cursor="pointinghand")
            ch.pack(side="left", padx=3)
            ch.bind("<Button-1>", lambda e, dd=d: (setattr(self, "_olddl_days", dd), self._t_olddl()))
        inner = self._scrollarea()
        for s, fp, age in rows:
            agetxt = f"{age//365} г" if age >= 365 else (f"{age} дн" if age > 0 else "сегодня")
            self._checkrow(inner, fp, f"{fp.replace(HOME,'~')}   ·   {agetxt}", s)
        if not rows:
            tk.Label(inner, text=L("  Старых загрузок не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"Найдено: {len(rows)} (~{human(sum(s for s,_,_ in rows))})",
                        lambda: self._trash_sel(lambda: self._tool('olddl')))

    # --- 📦🕒 Большие и старые (размер × возраст) ---
    def _t_bigold(self):
        if not hasattr(self, "_bigold_mb"):   self._bigold_mb = 200
        if not hasattr(self, "_bigold_days"): self._bigold_days = 180
        self._ptitle(L("Большие и старые файлы"),
                     L("Крупные файлы, которые давно не открывали и не меняли (размер × возраст). "
                       "Отметьте лишние → в Корзину."))
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text",11)).pack(anchor="w")
        mb, days = self._bigold_mb, self._bigold_days
        threading.Thread(target=lambda: self._bigold_w(mb, days), daemon=True).start()

    def _bigold_w(self, mb, days):
        rows = scan_big_old(HOME, min_mb=mb, min_days=days, top=200)
        self.q.put(("tool", ("bigold", rows), None))

    def _render_bigold(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv = []
        mb, days = getattr(self,"_bigold_mb",200), getattr(self,"_bigold_days",180)
        self._ptitle(L("Большие и старые файлы"),
                     L("Крупные файлы, которые давно не открывали и не меняли (размер × возраст). "
                       "Отметьте лишние → в Корзину."))
        bar = tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x", pady=(0,4))
        tk.Label(bar, text=L("Размер ≥"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(side="left", padx=(0,4))
        for v in (100, 200, 500, 1024):
            lbl = ("1 ГБ" if v==1024 else f"{v} {L('МБ')}")
            sel = (v == mb)
            ch = tk.Label(bar, text=lbl, bg=(BLUE if sel else GLASS_HI), fg=("white" if sel else TEXT),
                          font=("SF Pro Text",11,"bold"), padx=9, pady=4, cursor="pointinghand")
            ch.pack(side="left", padx=2)
            ch.bind("<Button-1>", lambda e, vv=v: (setattr(self,"_bigold_mb",vv), self._t_bigold()))
        tk.Label(bar, text="   "+L("Возраст ≥"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(side="left", padx=(0,4))
        for d in (90, 180, 365):
            lbl = {90:"3 мес", 180:"6 мес", 365:"1 год"}[d]
            sel = (d == days)
            ch = tk.Label(bar, text=lbl, bg=(BLUE if sel else GLASS_HI), fg=("white" if sel else TEXT),
                          font=("SF Pro Text",11,"bold"), padx=9, pady=4, cursor="pointinghand")
            ch.pack(side="left", padx=2)
            ch.bind("<Button-1>", lambda e, dd=d: (setattr(self,"_bigold_days",dd), self._t_bigold()))
        inner = self._scrollarea()
        for s, fp, age in rows:
            agetxt = f"{age//365} г" if age >= 365 else f"{age} дн"
            self._checkrow(inner, fp, f"{fp.replace(HOME,'~')}   ·   {agetxt}", s)
        if not rows:
            tk.Label(inner, text=L("  Больших старых файлов не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"{L('Найдено')}: {len(rows)} (~{human(sum(s for s,_,_ in rows))})",
                        lambda: self._trash_sel(lambda: self._tool('bigold')))

    # --- Вложения Почты ---
    @staticmethod
    def _mail_bases():
        """Каталоги Apple Mail с файлами-вложениями (загрузки + хранилища V*)."""
        return [
            os.path.join(HOME, "Library/Containers/com.apple.mail/Data/Library/Mail Downloads"),
            os.path.join(HOME, "Library/Mail"),
        ]

    def _t_mailatt(self):
        self._ptitle(L("Вложения Почты"),
                     L("Крупные вложения Apple Mail (> 5 МБ). Сами письма не удаляются; "
                       "на IMAP вложение можно скачать заново."))
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._mailatt_w)

    def _mailatt_w(self):
        rows = scan_mail_attachments(self._mail_bases(), min_mb=5, top=200)
        self.q.put(("tool", ("mailatt", rows), None))

    def _render_mailatt(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv = []
        self._ptitle(L("Вложения Почты"),
                     L("Крупные вложения Apple Mail (> 5 МБ). Отметьте лишние → в Корзину. "
                       "Сами письма не удаляются; на IMAP вложение можно скачать заново."))
        inner = self._scrollarea()
        for s, fp in rows:
            self._checkrow(inner, fp, fp.replace(HOME, "~"), s)
        if not rows:
            tk.Label(inner, text=L("  Крупных вложений не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"{L('Найдено')}: {len(rows)} (~{human(sum(s for s,_ in rows))})",
                        lambda: self._trash_sel(lambda: self._tool('mailatt')))

    # --- Дубликаты ---
    def _t_dupes(self):
        self._ptitle("Дубликаты", "Одинаковые файлы в Downloads/Desktop/Documents.")
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._dupes_w)

    def _dupes_w(self):
        by_size={}
        for base in (os.path.join(HOME,d) for d in ("Downloads","Desktop","Documents")):
            if not os.path.isdir(base): continue
            for root,_,files in os.walk(base):
                for fn in files:
                    fp=os.path.join(root,fn)
                    try:
                        s=os.path.getsize(fp)
                        if s>1024*1024: by_size.setdefault(s,[]).append(fp)
                    except Exception: pass
        groups=[]
        for s,paths in by_size.items():
            if len(paths)<2: continue
            bh={}
            for fp in paths:
                h=self._hash(fp)
                if h: bh.setdefault(h,[]).append(fp)
            for same in bh.values():
                if len(same)>1: groups.append((s,sorted(same)))
        groups.sort(reverse=True); self.q.put(("tool",("dupes",groups[:50]),None))

    def _render_dupes(self, groups):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        wasted=sum(s*(len(g)-1) for s,g in groups)
        self._ptitle("Дубликаты", "Первая копия оставлена, остальные отмечены к удалению.")
        inner=self._scrollarea()
        for s,same in groups:
            tk.Label(inner, text=f"  {human(s)} ×{len(same)}", bg=GLASS, fg=CYAN,
                     font=("SF Pro Text",10,"bold")).pack(anchor="w", padx=8, pady=(6,0))
            for i,fp in enumerate(same):
                self._checkrow(inner, fp, "    "+fp.replace(HOME,"~"), s, preselect=(i>0))
        if not groups: tk.Label(inner, text=L("  Дубликатов не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"Групп: {len(groups)} · освободить ~{human(wasted)}",
                        lambda: self._trash_sel(lambda: self._tool('dupes')))

    @staticmethod
    def _hash(fp):
        try:
            h=hashlib.md5()
            with open(fp,"rb") as f:
                for b in iter(lambda:f.read(1<<20), b""): h.update(b)
            return h.hexdigest()
        except Exception: return None

    # --- Деинсталлятор ---
    def _t_uninstall(self):
        self._ptitle("Деинсталлятор", "Удаление приложения вместе с его кэшами и настройками.")
        inner=self._scrollarea()
        for base in ("/Applications", os.path.join(HOME,"Applications")):
            if not os.path.isdir(base): continue
            for f in sorted(os.listdir(base)):
                if not f.endswith(".app"): continue
                ap=os.path.join(base,f)
                r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
                tk.Label(r, text=f[:-4], bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
                btn=tk.Label(r, text=L("Удалить…"), bg=RED, fg="white", font=("SF Pro Text",10,"bold"),
                             padx=10, pady=3, cursor="pointinghand")
                btn.pack(side="right"); btn.bind("<Button-1>", lambda e,p=ap: self._uninstall(p))

    def _uninstall(self, app_path):
        import plistlib
        name=os.path.basename(app_path)[:-4]; bid=""
        try:
            with open(os.path.join(app_path,"Contents","Info.plist"),"rb") as f:
                bid=plistlib.load(f).get("CFBundleIdentifier","")
        except Exception: pass
        targets=[app_path]
        for sub in ("Library/Caches","Library/Application Support","Library/Preferences","Library/Logs",
                    "Library/Containers","Library/Saved Application State","Library/HTTPStorages","Library/WebKit"):
            d=os.path.join(HOME,sub)
            if not os.path.isdir(d): continue
            for f in os.listdir(d):
                if leftover_match(f, name, bid):
                    targets.append(os.path.join(d,f))
        sizes=[(t,path_size(t)) for t in targets]; tot=sum(s for _,s in sizes)
        lines="\n".join(f"  {human(s):>8}  {t.replace(HOME,'~')}" for t,s in sizes)
        if not messagebox.askyesno("Удалить "+name, f"В Корзину уйдут (~{human(tot)}):\n\n{lines}\n\nПродолжить?"): return
        freed=sum(s for t,s in sizes if to_trash(t))
        messagebox.showinfo("CleanMac", f"{name}: в Корзину {human(freed)}."); self._tool("uninstall")

    # --- Карта диска ---
    def _t_disk(self):
        self._ptitle("Карта диска", "Крупнейшие папки в домашней директории.")
        tk.Label(self.tpanel, text=L("🔎 Считаю размеры…"), bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._disk_w)

    def _disk_w(self):
        rows=[]
        for ln in run(["/usr/bin/du","-d","1","-k",HOME], 180).splitlines():
            try:
                kb,p=ln.split("\t",1)
                if p.rstrip("/")==HOME.rstrip("/"): continue
                rows.append((int(kb)*1024, p))
            except Exception: pass
        rows.sort(reverse=True); self.q.put(("disk", rows[:16], None))

    # Алгоритм вынесен в krylan_core.squarify (кросс-платформенный, тестируемый).
    # Псевдоним сохраняет вызовы self._squarify(...) и тест CleanMac._squarify.
    _squarify = staticmethod(squarify)

    def _render_disk(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._ptitle("Карта диска (Space Lens)", "Площадь блока = размер папки. Клик — открыть в Finder.")
        if not hasattr(self, "_disk_mode"): self._disk_mode="tree"
        bar=tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x")
        # переключение режима делает lambda ниже (k=key); отдельный setmode и m=key
        # были мёртвым кодом — ни то, ни другое никогда не вызывалось
        for key,label in [("tree","🟦 Treemap"),("bars","📊 Бары"),("sun","☀️ Sunburst")]:
            b=tk.Label(bar, text=label, bg=(BLUE if self._disk_mode==key else GLASS_HI), fg="white" if self._disk_mode==key else TEXT,
                       font=("SF Pro Text",11,"bold"), padx=10, pady=5, cursor="pointinghand")
            b.pack(side="left", padx=(0,6)); b.bind("<Button-1>", lambda e,k=key: (setattr(self,"_disk_mode",k), self._render_disk(rows)))
        self.bench_btn=tk.Label(bar, text=L("🏁 Бенчмарк диска"), bg=GREEN, fg="white",
                                font=("SF Pro Text",11,"bold"), padx=10, pady=5, cursor="pointinghand")
        self.bench_btn.pack(side="right"); self.bench_btn.bind("<Button-1>", lambda e: self._bench_start())
        self.bench_lbl=tk.Label(self.tpanel, text="🏁 Тест скорости SSD/HDD: запись и чтение ~128 МБ во временный файл "
                                "(удаляется сразу). Занимает пару секунд.",
                                bg=BG0, fg=MUTED, font=("SF Pro Text",11), wraplength=620, justify="left", anchor="w")
        self.bench_lbl.pack(anchor="w", pady=(6,0))
        if self._disk_mode=="sun":
            self._render_sunburst(rows); return
        cv=tk.Canvas(self.tpanel, bg=GLASS, highlightthickness=0); cv.pack(fill="both", expand=True, pady=(6,8))
        pal=[BLUE,GREEN,PURPLE,YELLOW,CYAN,RED]
        def draw(e=None):
            cv.delete("all"); W=cv.winfo_width() or 600; H=cv.winfo_height() or 360
            if self._disk_mode=="bars":
                mx=rows[0][0] if rows else 1; y=14
                for i,(sz,p) in enumerate(rows):
                    col=pal[i%len(pal)]; bw=max(6,(W-180)*sz/mx); tag=f"r{i}"
                    self._round(cv, 150,y,150+bw,y+22,6, fill=col, outline=col, tags=tag)
                    cv.create_text(12,y+11, anchor="w", fill=TEXT, font=("SF Pro Text",11),
                                   text=p.replace(HOME,"~")[:26], tags=tag)
                    cv.create_text(W-12,y+11, anchor="e", fill=MUTED, font=("SF Pro Text",11), text=human(sz), tags=tag)
                    cv.tag_bind(tag,"<Button-1>", lambda e,pp=p: run(["/usr/bin/open",pp]))
                    y+=30
                cv.configure(scrollregion=(0,0,W,y))
            else:
                rects=self._squarify([s for s,_ in rows], 4,4,W-8,H-8)
                for i,((rx,ry,rw,rh),(sz,p)) in enumerate(zip(rects,rows)):
                    col=pal[i%len(pal)]; tag=f"t{i}"
                    cv.create_rectangle(rx,ry,rx+rw,ry+rh, fill=col, outline=BG0, width=2, tags=tag)
                    if rw>54 and rh>22:
                        cv.create_text(rx+6,ry+12, anchor="w", fill="white", font=("SF Pro Text",10,"bold"),
                                       text=os.path.basename(p.rstrip("/"))[:18], tags=tag)
                        cv.create_text(rx+6,ry+26, anchor="w", fill="white", font=("SF Pro Text",9),
                                       text=human(sz), tags=tag)
                    cv.tag_bind(tag,"<Button-1>", lambda e,pp=p: run(["/usr/bin/open",pp]))
                cv.configure(scrollregion=(0,0,W,H))
        cv.bind("<Configure>", draw); draw()

    # --- Sunburst (кольцевая карта папок, фирменная фича а-ля DaisyDisk) ---
    def _render_sunburst(self, rows):
        """Контейнер режима Sunburst: кнопки + холст. Дерево строится в фоне."""
        # стартовая папка — HOME, если ещё не выбрана
        if not getattr(self, "_sun_path", None):
            self._sun_path = HOME
        info = tk.Label(self.tpanel,
                        text="☀️ Кольцевая карта: центр — папка, кольца — вложенные каталоги. "
                             "Клик по сектору — провалиться внутрь, клик в центр — на уровень вверх.",
                        bg=BG0, fg=MUTED, font=("SF Pro Text",11), wraplength=620, justify="left", anchor="w")
        info.pack(anchor="w", pady=(6,2))
        # «Хлебные крошки» текущего пути + кнопка «вверх» — обновляются при навигации.
        self._sun_crumbs=tk.Frame(self.tpanel, bg=BG0)
        self._sun_crumbs.pack(fill="x", pady=(0,2))
        cv=tk.Canvas(self.tpanel, bg=GLASS, highlightthickness=0)
        cv.pack(fill="both", expand=True, pady=(4,8))
        self._sun_cv=cv; self._sun_rows=rows; self._sun_tree=None
        cv.bind("<Configure>", lambda e: self._draw_sunburst())
        self._draw_crumbs()
        self._sun_status(cv, "Считаю размеры…")
        self._sun_seq = getattr(self, "_sun_seq", 0) + 1
        self._spawn(self._sun_w, self._sun_path, self._sun_seq)

    @staticmethod
    def _crumb_parts(path):
        """Путь → список (label, abs_path) для хлебных крошек, HOME свёрнут в «~»."""
        path=os.path.abspath(path).rstrip("/") or "/"
        parts=[]
        cur=path
        guard=0
        while True:
            guard+=1
            if guard>64: break
            name=os.path.basename(cur) or "/"
            if cur==HOME: name="~"
            parts.append((name, cur))
            parent=os.path.dirname(cur)
            if parent==cur: break
            if cur==HOME: break               # выше домашней папки крошки не строим
            cur=parent
        return list(reversed(parts))

    def _draw_crumbs(self):
        bar=getattr(self,"_sun_crumbs",None)
        if not bar or not bar.winfo_exists(): return
        for w in bar.winfo_children(): w.destroy()
        path=getattr(self,"_sun_path",HOME)
        up=os.path.dirname(path.rstrip("/"))
        upbtn=tk.Label(bar, text=L("↑ вверх"), bg=(GLASS_HI if (up and up!=path) else GLASS),
                       fg=(TEXT if (up and up!=path) else MUTED), font=("SF Pro Text",10,"bold"),
                       padx=8, pady=3, cursor=("pointinghand" if (up and up!=path) else "arrow"))
        upbtn.pack(side="left", padx=(0,8))
        if up and up!=path:
            upbtn.bind("<Button-1>", lambda e,p=up: self._sun_navigate(p))
        parts=self._crumb_parts(path)
        for i,(name,p) in enumerate(parts):
            last=(i==len(parts)-1)
            c=tk.Label(bar, text=name[:22], bg=BG0, fg=(CYAN if last else MUTED),
                       font=("SF Pro Text",10,"bold" if last else "normal"),
                       cursor=("arrow" if last else "pointinghand"))
            c.pack(side="left")
            if not last:
                c.bind("<Button-1>", lambda e,pp=p: self._sun_navigate(pp))
                tk.Label(bar, text=" › ", bg=BG0, fg=MUTED, font=("SF Pro Text",10)).pack(side="left")

    def _sun_status(self, cv, text):
        cv.delete("all")
        W=cv.winfo_width() or 600; H=cv.winfo_height() or 360
        cv.create_text(W/2, H/2, fill=MUTED, font=("SF Pro Text",13,"bold"), text="⏳ "+text)

    def _sun_w(self, path, seq):
        """Фоновый воркер: строит dir_tree (медленно — НЕ в UI-потоке).
        seq — токен запроса: приёмник отбросит результат устаревшего клика."""
        try:
            tree = dir_tree(path, depth=2, min_frac=0.012, top_n=12)
        except Exception:
            tree = {"name": os.path.basename(path) or path, "path": path, "size": 0, "children": []}
        self.q.put(("sunburst", (seq, tree), None))

    def _on_sun_tree(self, payload):
        """Колбэк из очереди (UI-поток): дерево готово — рисуем.
        Игнорируем результат устаревшего запроса (быстрые клики по секторам):
        рисуем только дерево последнего запрошенного каталога, а не последнего
        досчитавшегося."""
        seq, tree = payload
        if seq != getattr(self, "_sun_seq", 0): return
        if self.page!="tools" or getattr(self,"_disk_mode",None)!="sun": return
        self._sun_tree=tree
        if getattr(self,"_sun_cv",None) and self._sun_cv.winfo_exists():
            self._draw_sunburst()

    @staticmethod
    def _sun_layout(tree, max_depth=2):
        """Чистая раскладка дерева в дуги: список (depth, start, extent, node).

        Углы — в градусах CCW от 3 часов (как у tkinter create_arc).
        Дети распределяются по углу пропорционально размеру в пределах
        сектора родителя. Тестируемо без Canvas."""
        arcs=[]
        def walk(node, start, extent, depth):
            if depth>max_depth: return
            kids=[c for c in node.get("children",[]) if c.get("size",0)>0]
            ssum=sum(c["size"] for c in kids) or 1
            a=start
            for c in kids:
                ext=extent*c["size"]/ssum
                arcs.append((depth, a, ext, c))
                walk(c, a, ext, depth+1)
                a+=ext
        walk(tree, 0, 360, 1)
        return arcs

    def _draw_sunburst(self):
        cv=getattr(self,"_sun_cv",None); tree=getattr(self,"_sun_tree",None)
        if not cv or not cv.winfo_exists(): return
        if tree is None:
            self._sun_status(cv, "Считаю размеры…"); return
        cv.delete("all")
        W=cv.winfo_width() or 600; H=cv.winfo_height() or 360
        cx, cy = W/2, H/2
        R = max(60, min(W, H)/2 - 30)
        ring = R/3.0                      # центр + 2 кольца
        r0 = ring                         # радиус центрального круга
        pal=[BLUE,CYAN,GREEN,PURPLE,YELLOW]
        total = tree.get("size",0) or 1
        nm=os.path.basename(tree["path"].rstrip("/")) or tree["path"]
        up = os.path.dirname(tree["path"].rstrip("/"))

        arcs=self._sun_layout(tree, max_depth=2)
        # Рисуем от ВНЕШНЕГО кольца к внутреннему: pieslice depth=2 (до r0+2*ring)
        # перекрывается pieslice depth=1 (до r0+ring), затем центр-круг (r0).
        # Так образуются аккуратные кольца без отдельной «маски».
        for depth in (2, 1):
            radius = r0 + ring*depth
            for di,(d, a, ext, c) in enumerate(arcs):
                if d!=depth or ext<0.6: continue
                base = pal[0] if depth==1 else pal[2]
                col=_blend(base, BG0, 0.06 + 0.14*(di%4))
                tag=f"sun_{depth}_{di}"
                cv.create_arc(cx-radius, cy-radius, cx+radius, cy+radius,
                              start=a, extent=ext, style="pieslice",
                              fill=col, outline=GLASS, width=2, tags=(tag,))
                if ext>=16:   # подпись только для крупных секторов
                    mid=math.radians(a+ext/2)
                    lr=r0 + ring*(depth-0.5)
                    lx=cx+lr*math.cos(mid); ly=cy-lr*math.sin(mid)
                    label="прочее" if c.get("is_rest") else (os.path.basename(c["path"].rstrip("/")) or c["name"])
                    cv.create_text(lx, ly-6, fill="white", font=("SF Pro Text",9,"bold"),
                                   text=label[:14], tags=(tag,))
                    cv.create_text(lx, ly+6, fill="white", font=("SF Pro Text",8),
                                   text=human(c["size"]), tags=(tag,))
                if not c.get("is_rest") and os.path.isdir(c["path"]):
                    cv.tag_bind(tag,"<Button-1>", lambda e,p=c["path"]: self._sun_navigate(p))

        # центральный круг поверх колец (даёт «дырку» = кольцевая карта)
        cv.create_oval(cx-r0, cy-r0, cx+r0, cy+r0,
                       fill=_blend(BG0,CYAN,0.18), outline=_blend(CYAN,"#ffffff",0.2), width=2,
                       tags=("sun_center",))
        cv.create_text(cx, cy-7, fill=TEXT, font=("SF Pro Text",12,"bold"),
                       text=nm[:18], tags=("sun_center",))
        cv.create_text(cx, cy+10, fill=CYAN, font=("SF Pro Text",10),
                       text=human(total), tags=("sun_center",))
        if up and up != tree["path"]:
            cv.create_text(cx, cy+r0-12, fill=MUTED, font=("SF Pro Text",9), text=L("↑ вверх"),
                           tags=("sun_center",))
            cv.tag_bind("sun_center","<Button-1>", lambda e,p=up: self._sun_navigate(p))

    def _sun_navigate(self, path):
        """Провалиться/подняться: перестроить дерево от новой папки (в фоне)."""
        if not path or not os.path.isdir(path): return
        self._sun_path=path; self._sun_tree=None
        self._draw_crumbs()
        cv=getattr(self,"_sun_cv",None)
        if cv and cv.winfo_exists(): self._sun_status(cv, "Считаю размеры…")
        self._sun_seq = getattr(self, "_sun_seq", 0) + 1
        self._spawn(self._sun_w, path, self._sun_seq)

    def _bench_start(self):
        try:
            self.bench_btn.configure(text=L("⏳ Тестирую…"), bg=GLASS_HI)
            self.bench_lbl.configure(text=L("⏳ Идёт бенчмарк: пишу и читаю ~128 МБ во временный файл… пара секунд."), fg=TEXT)
        except Exception: pass
        self._spawn(self._bench_w)

    def _bench_w(self):
        res = disk_benchmark(size_mb=128)
        self.q.put(("bench", res, None))

    @staticmethod
    def _bench_verdict(mbps):
        if mbps >= 1500: return "🟢 отличный NVMe SSD"
        if mbps >= 500:  return "🟢 быстрый SSD"
        if mbps >= 100:  return "🟡 SSD начального уровня / внешний диск"
        return "🔴 медленный (HDD или перегруженный диск)"

    def _render_bench(self, res):
        if not hasattr(self, "bench_btn"): return
        try: self.bench_btn.configure(text=L("🏁 Бенчмарк диска"), bg=GREEN)
        except Exception: pass
        if not res or "error" in (res or {}):
            self.bench_lbl.configure(
                text="⚠️ Не удалось выполнить бенчмарк: " + (res.get("error","нет данных") if res else "нет данных") +
                     " (проверьте свободное место и права).", fg=RED)
            return
        w, r = res.get("write_mbps",0), res.get("read_mbps",0)
        self.bench_lbl.configure(
            text=(f"🏁 Бенчмарк диска ({res.get('size_mb',128)} МБ):\n"
                  f"   ✍️ Запись: {w} МБ/с  —  {self._bench_verdict(w)}\n"
                  f"   📖 Чтение: {r} МБ/с  —  {self._bench_verdict(r)}\n"
                  "Ориентир: >1500 МБ/с — отличный SSD, 100–500 — норма, <100 — медленный/HDD."),
            fg=GREEN if min(w, r) >= 500 else (YELLOW if min(w, r) >= 100 else RED))

    # --- Обслуживание ---
    def _t_maintain(self):
        self._ptitle("Обслуживание", "Сервисные операции macOS. Для пунктов ★ потребуется пароль администратора.")
        # 4-й элемент — предупреждение о ЦЕНЕ операции. Не всякое «обслуживание»
        # бесплатно: переиндексация Spotlight стирает индекс всего тома, после чего
        # mdworker часами грузит процессор и диск. На маке с 8 ГБ ОЗУ это ощущается
        # как «стало хуже» — ровно то, чего оптимизатор делать не должен. Такие
        # пункты помечены ⚠️, спрашивают подтверждение и честно называют цену.
        acts=[("⚡️ Освободить память (purge) ★", "purge", True, None),
              ("🌐 Сбросить кэш DNS ★", "dscacheutil -flushcache; killall -HUP mDNSResponder", True, None),
              ("🔍 Переиндексировать Spotlight ★", "mdutil -E /", True,
               "Индекс Spotlight будет стёрт и построен заново.\n\n"
               "Пока идёт переиндексация — от 30 минут до нескольких часов, смотря сколько данных:\n"
               "•  поиск Spotlight работать не будет;\n"
               "•  mdworker сильно нагрузит процессор и диск, компьютер станет МЕДЛЕННЕЕ.\n\n"
               "Это лечение сломанного поиска, а не ускорение. Продолжить?"),
              ("🔤 Очистить кэш шрифтов ★", "atsutil databases -remove", True,
               "Кэш шрифтов будет очищен.\n\n"
               "Чтобы изменения вступили в силу, нужно выйти из учётной записи и войти снова. "
               "До перезахода часть шрифтов может отображаться некорректно.\n\nПродолжить?"),
              ("👁 Сбросить кэш Quick Look", "qlmanage -r cache", False, None),
              ("🧱 Перестроить Launch Services", "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user", False, None)]
        for label,cmd,admin,warn in acts:
            b=tk.Label(self.tpanel, text=label+("   ⚠️" if warn else ""), bg=GLASS, fg=TEXT,
                       font=("SF Pro Text",12), padx=12, pady=9, cursor="pointinghand", anchor="w")
            b.pack(fill="x", pady=3)
            b.bind("<Button-1>", lambda e,c=cmd,a=admin,l=label,w=warn: self._maintain_run(l,c,a,w))
        tk.Label(self.tpanel, text="⚠️ — операция полезна не всегда и может временно замедлить мак. "
                 "Перед запуском покажем, чем именно платите.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",10), wraplength=620, justify="left"
                 ).pack(anchor="w", pady=(8,0))
        self._mrez=tk.Label(self.tpanel, text="", bg=BG0, fg=MUTED, font=("SF Pro Text",12)); self._mrez.pack(anchor="w", pady=8)

    def _maintain_run(self, label, cmd, admin, warn=None):
        if warn and not messagebox.askyesno(label.replace("★","").strip(), warn, default="no"):
            return
        self._mrez.configure(text="⏳ Выполняю: "+label.replace("★","").strip())
        self._spawn(self._maintain_w, label,cmd,admin)

    def _maintain_w(self, label, cmd, admin):
        try:
            if admin:
                run(["osascript","-e",f'do shell script "{as_escape(cmd)}" with administrator privileges'], 180)
            else:
                run(["/bin/bash","-c",cmd], 180)
        except Exception: pass
        self.q.put(("maintdone", label, None))

    # --- Скриншоты ---
    SHOT_PREFIXES = ("снимок экрана", "screenshot", "screen shot", "cleanshot", "снимок_экрана")

    def _t_shots(self):
        self._ptitle("Скриншоты", "Снимки экрана на Рабочем столе и в ~/Pictures — копятся незаметно.")
        inner=self._scrollarea()
        import time
        total=0; n=0; now=time.time()
        bases=[os.path.join(HOME,"Desktop"), os.path.join(HOME,"Pictures"),
               os.path.join(HOME,"Pictures/Screenshots")]
        seen=set()
        rows=[]
        for base in bases:
            if not os.path.isdir(base): continue
            for f in sorted(os.listdir(base)):
                fp=os.path.join(base,f)
                if fp in seen or not os.path.isfile(fp): continue
                if not f.lower().startswith(self.SHOT_PREFIXES): continue
                if not f.lower().endswith((".png",".jpg",".jpeg",".heic")): continue
                seen.add(fp)
                try:
                    sz=os.path.getsize(fp); age=(now-os.path.getmtime(fp))/86400
                except OSError: continue
                rows.append((sz, age, fp, f))
        rows.sort(reverse=True)
        for sz, age, fp, f in rows:
            label=f"{f}  ·  {int(age)} дн."
            self._checkrow(inner, fp, label, sz, preselect=(age>30))
            total+=sz; n+=1
        if not n:
            tk.Label(inner, text=L("Скриншотов не найдено."), bg=GLASS, fg=MUTED,
                     font=("SF Pro Text",12)).pack(anchor="w", padx=10, pady=10)
        self._actionbar(f"Скриншотов: {n} · ~{human(total)} (старше 30 дн. отмечены)",
                        lambda: self._trash_sel(lambda: self._tool("shots")))

    # --- Шредер (безопасное удаление по явному выбору) ---
    def _t_shred(self):
        self._ptitle("Шредер", "Безвозвратное удаление выбранных файлов с перезаписью. Не для системных папок.")
        self._shred_files = []
        self._btn(self.tpanel, "➕ Выбрать файлы…", BLUE, self._shred_pick).pack(anchor="w", pady=(2,6))
        self._shred_box = tk.Frame(self.tpanel, bg=GLASS); self._shred_box.pack(fill="both", expand=True, pady=(0,8))
        tk.Label(self._shred_box, text=L("Файлы не выбраны."), bg=GLASS, fg=MUTED,
                 font=("SF Pro Text",12)).pack(anchor="w", padx=10, pady=10)
        self._shred_action = tk.Frame(self.tpanel, bg=BG0); self._shred_action.pack(fill="x")
        tk.Label(self.tpanel,
                 text="⚠️ На SSD из-за wear-leveling и TRIM перезапись не гарантирует физическое стирание ячеек, "
                      "но логически файл невосстановим. Для надёжности используйте шифрование диска (FileVault).",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",10), wraplength=560, justify="left").pack(anchor="w", pady=(6,0))

    def _shred_pick(self):
        paths = filedialog.askopenfilenames(title="Выберите файлы для уничтожения")
        if not paths: return
        self._shred_files = [p for p in paths if os.path.isfile(p) and not is_protected(p)]
        for w in self._shred_box.winfo_children(): w.destroy()
        for w in self._shred_action.winfo_children(): w.destroy()
        if not self._shred_files:
            tk.Label(self._shred_box, text=L("Файлы не выбраны."), bg=GLASS, fg=MUTED,
                     font=("SF Pro Text",12)).pack(anchor="w", padx=10, pady=10); return
        total = 0
        for p in self._shred_files:
            try: sz = os.path.getsize(p)
            except OSError: sz = 0
            total += sz
            r = tk.Frame(self._shred_box, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=human(sz), bg=GLASS, fg=MUTED, font=("SF Pro Text",10),
                     width=9, anchor="e").pack(side="right", padx=(6,4))
            tk.Label(r, text=os.path.basename(p), bg=GLASS, fg=TEXT, font=("SF Pro Text",11),
                     anchor="w").pack(side="left", fill="x", expand=True)
        self._btn(self._shred_action, f"🔥 Уничтожить {len(self._shred_files)} ({human(total)})",
                  RED, self._shred_run).pack(side="left", pady=4)

    def _shred_run(self):
        n = len(self._shred_files)
        if not n: return
        if not messagebox.askyesno("Шредер",
            f"Безвозвратно уничтожить {n} файл(ов)?\nЭто действие НЕОБРАТИМО — файлы не попадут в Корзину."): return
        ok = 0
        for p in list(self._shred_files):
            if shred_file(p): ok += 1
        messagebox.showinfo("CleanMac", f"Уничтожено: {ok} из {n}.")
        self._shred_files = []
        self._tool("shred")

    # --- Апдейтер приложений (Homebrew) ---
    def _t_updater(self):
        self._ptitle("Апдейтер", "Устаревшие приложения и пакеты Homebrew. Обновление — безопасно, официальными источниками.")
        if brew_path() is None:
            tk.Label(self.tpanel, text=L("Homebrew не найден. Установите с brew.sh, чтобы обновлять приложения отсюда."),
                     bg=BG0, fg=MUTED, font=("SF Pro Text",12), wraplength=560, justify="left").pack(anchor="w", pady=10)
            return
        tk.Label(self.tpanel, text=L("Сканирую обновления…"), bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w")
        self._spawn(self._updater_w)

    def _updater_w(self):
        items = brew_outdated()
        self.q.put(("updater", items, None))

    def _render_updater(self, items):
        for w in self.tpanel.winfo_children()[2:]: w.destroy()   # убрать «Сканирую…»
        if not items:
            tk.Label(self.tpanel, text=L("✅ Все приложения обновлены."), bg=BG0, fg=GREEN,
                     font=("SF Pro Text",13,"bold")).pack(anchor="w", pady=8); return
        inner=self._scrollarea()
        for name,cur,new,kind in items:
            r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=f"{cur} → {new}", bg=GLASS, fg=GREEN, font=("SF Pro Text",10),
                     width=18, anchor="e").pack(side="right", padx=(6,4))
            tk.Label(r, text=kind, bg=GLASS, fg=MUTED, font=("SF Pro Text",9), width=11, anchor="e").pack(side="right")
            tk.Label(r, text=name, bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
        bar=tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x", pady=(6,0))
        tk.Label(bar, text=f"Обновлений: {len(items)}", bg=BG0, fg=TEXT, font=("SF Pro Text",12,"bold")).pack(side="left")
        self._btn(bar, "⬆️ Обновить всё", GREEN, self._brew_upgrade_all).pack(side="right")

    def _brew_upgrade_all(self):
        if not messagebox.askyesno("CleanMac", "Обновить все устаревшие пакеты и приложения Homebrew?\n"
                                   "Это может занять несколько минут."): return
        self.status("⬆️ Обновляю через Homebrew…")
        self._spawn(self._brew_upgrade_w)

    def _brew_upgrade_w(self):
        brew=brew_path()
        if brew:
            run([brew, "upgrade"], 1800)
            run([brew, "upgrade", "--cask", "--greedy"], 1800)
        self.q.put(("upgraded", None, None))

    # --- Остатки удалённых программ ---
    def _t_leftovers(self):
        self._ptitle("Остатки удалённых программ",
                     "Данные в ~/Library от приложений, которых уже нет. Только bundle-id-папки; Apple не трогается.")
        tk.Label(self.tpanel, text=L("Сканирую…"), bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w")
        threading.Thread(target=lambda: self.q.put(("leftovers", orphaned_leftovers(), None)), daemon=True).start()

    def _render_leftovers(self, items):
        for w in self.tpanel.winfo_children()[2:]: w.destroy()
        if not items:
            tk.Label(self.tpanel, text=L("✅ Осиротевших данных не найдено."), bg=BG0, fg=GREEN,
                     font=("SF Pro Text",13,"bold")).pack(anchor="w", pady=8); return
        total=sum(s for _,s in items)
        inner=self._scrollarea()
        for p,s in items:
            self._checkrow(inner, p, p.replace(HOME,"~"), s, preselect=False)
        self._actionbar(f"Остатков: {len(items)} · ~{human(total)} (проверьте перед удалением)",
                        lambda: self._trash_sel(lambda: self._tool("leftovers")))

    # --- История очисток ---
    def _t_history(self):
        hist = cleanup_history()
        total = total_freed()
        self._ptitle("История очисток", f"Освобождено за всё время: ~{human(total)} · записей: {len(hist)}")
        if not hist:
            tk.Label(self.tpanel, text=L("Пока пусто. После первой очистки здесь появится журнал."),
                     bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w", pady=8)
            return
        names={"clean":"Очистка","smart":"Умная очистка","autopilot":"Автопилот","purge":"Освобождение места"}
        inner=self._scrollarea()
        for e in reversed(hist):   # новые сверху
            try:
                ts=time.strftime("%d.%m.%Y %H:%M", time.localtime(int(e.get("ts",0))))
            except Exception:
                ts="—"
            kind=names.get(e.get("kind","clean"),"Очистка")
            r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=human(e.get("freed",0)), bg=GLASS, fg=GREEN, font=("SF Pro Text",11,"bold"),
                     width=10, anchor="e").pack(side="right", padx=(6,4))
            tk.Label(r, text=f"{ts}   ·   {kind}", bg=GLASS, fg=TEXT, font=("SF Pro Text",11),
                     anchor="w").pack(side="left", fill="x", expand=True)

    # --- Браузеры / Корзина ---
    def _t_browsers(self):
        self._ptitle("Браузеры", "Закрыть фоновые браузеры для разгрузки памяти (активное окно не трогается).")
        self._btn(self.tpanel, "🌐 Закрыть фоновые браузеры", BLUE, self._do_browsers).pack(anchor="w", pady=8)
        self._brez=tk.Label(self.tpanel, text="", bg=BG0, fg=MUTED, font=("SF Pro Text",12)); self._brez.pack(anchor="w")

    def _do_browsers(self):
        front=run(["osascript","-e",'tell application "System Events" to name of first process whose frontmost is true']).strip()
        closed=[]
        for app in ("Microsoft Edge","Google Chrome","Safari","Yandex"):
            if app_running(app) and app!=front: run(["osascript","-e",f'quit app "{as_escape(app)}"']); closed.append(app)
        self._brez.configure(text=("Закрыты: "+", ".join(closed)) if closed else "Фоновых браузеров нет.")

    # --- 🗜 Сжать базы браузеров (VACUUM SQLite) ---
    @staticmethod
    def _browser_proc(label):
        """Имя процесса браузера для app_running по его метке."""
        for lbl, proc, _rel in SQLITE_CHROMIUM:
            if lbl == label:
                return proc
        return "Firefox" if label == "Firefox" else label

    def _t_vacuum(self):
        self._ptitle(L("Сжатие баз браузеров"),
                     L("Перепаковка баз SQLite (VACUUM) без потери данных. Только для закрытых "
                       "браузеров — запущенные пропускаются."))
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._vacuum_w)

    def _vacuum_w(self):
        try:
            dbs = browser_sqlite_dbs()
        except Exception:
            dbs = []
        # запущенность браузера определяем один раз на метку
        running = {}
        rows = []
        for browser, fp in dbs:
            if browser not in running:
                try: running[browser] = app_running(self._browser_proc(browser))
                except Exception: running[browser] = False
            try: sz = os.path.getsize(fp)
            except OSError: sz = 0
            rows.append((browser, fp, sz, running[browser]))
        self.q.put(("tool", ("vacuum", rows), None))

    def _render_vacuum(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv = []
        self._ptitle(L("Сжатие баз браузеров"),
                     L("Перепаковка баз SQLite (VACUUM) без потери данных. Только для закрытых "
                       "браузеров — запущенные пропускаются."))
        busy = sorted({b for b,_,_,run_ in rows if run_})
        if busy:
            tk.Label(self.tpanel, text=L("⚠️ Сначала закройте: ")+", ".join(busy)+L(" — их базы заняты и будут пропущены."),
                     bg=BG0, fg=YELLOW, font=("SF Pro Text",11), wraplength=560, justify="left").pack(anchor="w", pady=(0,4))
        inner = self._scrollarea()
        for browser, fp, sz, run_ in rows:
            mark = "🔒 " if run_ else ""
            r = tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=human(sz), bg=GLASS, fg=MUTED, font=("SF Pro Text",10),
                     width=9, anchor="e").pack(side="right", padx=(6,4))
            tk.Label(r, text=f"{mark}{browser}  ·  {os.path.basename(fp)}", bg=GLASS,
                     fg=(MUTED if run_ else TEXT), font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
        if not rows:
            tk.Label(inner, text=L("  Баз для сжатия не найдено."), bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        closed = [(b,fp,sz) for b,fp,sz,run_ in rows if not run_]
        bar = tk.Frame(self.tpanel, bg=BG0); bar.pack(fill="x")
        tk.Label(bar, text=f"{L('Найдено баз: ')}{len(rows)} (~{human(sum(sz for _,_,sz,_ in rows))})",
                 bg=BG0, fg=TEXT, font=("SF Pro Text",12,"bold")).pack(side="left")
        if closed:
            self._btn(bar, L("🗜 Сжать закрытые браузеры"), GREEN,
                      lambda c=closed: self._vacuum_run(c)).pack(side="right")

    def _vacuum_run(self, closed):
        if not closed: return
        if not messagebox.askyesno("CleanMac",
            L("Сжать базы закрытых браузеров?\nДанные не удаляются — только перепаковка (VACUUM).")):
            return
        self.status(L("Сжатие баз браузеров"))
        threading.Thread(target=lambda c=closed: self._vacuum_do(c), daemon=True).start()

    def _vacuum_do(self, closed):
        done, saved, skipped = 0, 0, 0
        for browser, fp, _sz in closed:
            # повторно убеждаемся, что браузер всё ещё закрыт (мог стартовать)
            try:
                if app_running(self._browser_proc(browser)):
                    skipped += 1; continue
            except Exception:
                pass
            before, after = vacuum_sqlite(fp)
            if after < before:
                saved += (before - after)
            done += 1
        self.q.put(("vacuumed", (done, saved, skipped), None))

    # --- Расширения браузеров (read-only) ---
    def _t_extensions(self):
        self._ptitle(L("Расширения браузеров"),
                     L("Установленные расширения Chrome / Edge / Brave. Только просмотр — не удаляем."))
        tk.Label(self.tpanel, text=L("🔎 Сканирую…"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text",11)).pack(anchor="w")
        self._spawn(self._extensions_w)

    def _extensions_w(self):
        try:
            rows = list_browser_extensions()
        except Exception:
            rows = []
        self.q.put(("tool", ("extensions", rows), None))

    def _render_extensions(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        self._ptitle(L("Расширения браузеров"),
                     L("Установленные расширения Chrome / Edge / Brave. Только просмотр — не удаляем."))
        tk.Label(self.tpanel,
                 text=L("💡 Чтобы отключить или удалить расширение — сделайте это в самом браузере "
                        "(меню → Расширения). Safari-расширения управляются в Настройках Safari."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11), justify="left",
                 wraplength=720).pack(anchor="w", pady=(0,6))
        if not rows:
            tk.Label(self.tpanel,
                     text=L("Расширения не найдены (браузеры Chromium не установлены или нет профилей)."),
                     bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w", pady=8)
            return
        inner=self._scrollarea()
        cur=None
        for browser, name, ext_id in rows:
            if browser!=cur:
                cur=browser
                tk.Label(inner, text=browser, bg=GLASS, fg=BLUE,
                         font=("SF Pro Text",12,"bold")).pack(anchor="w", padx=8, pady=(8,2))
            r=tk.Frame(inner, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=ext_id, bg=GLASS, fg=MUTED, font=("SF Pro Text",9),
                     anchor="e").pack(side="right", padx=(6,4))
            tk.Label(r, text="🧩  "+name, bg=GLASS, fg=TEXT, font=("SF Pro Text",11),
                     anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(self.tpanel,
                 text=L("Всего расширений: ")+str(len(rows)),
                 bg=BG0, fg=TEXT, font=("SF Pro Text",12,"bold")).pack(anchor="w", pady=(6,0))

    def _t_trash(self):
        self._ptitle("Корзина", "Считаю размер всех корзин (включая системную корзину тома)…")
        self._btn(self.tpanel, "♻️ Очистить Корзину (безвозвратно)", RED, self._do_trash).pack(anchor="w", pady=8)
        self._spawn(self._trash_scan)

    def _trash_scan(self):
        sz = deep_trash_size()
        n = trash_count()
        locs = trash_locations()
        # подсветим скрытый источник: ~/.Trash пустая, а место есть
        hidden = sz - path_size(TRASH)
        self.q.put(("trash_info", {"sz": sz, "n": n, "locs": locs, "hidden": hidden}, None))

    def _render_trash_info(self, info):
        for w in self.tpanel.winfo_children(): w.destroy()
        sz, n, locs, hidden = info["sz"], info["n"], info["locs"], info["hidden"]
        cnt = f"{n} объектов" if n is not None else "размер ниже"
        txt = f"В Корзине ~{human(sz)} ({cnt})."
        if hidden > 50*1024*1024 and len(locs) > 1:
            txt += f"\n⚠️ Из них ~{human(hidden)} в системной корзине тома — её не видно в обычной Корзине Finder."
        self._ptitle("Корзина", txt)
        for p in locs:
            tk.Label(self.tpanel, text=f"• {p.replace(HOME,'~')} — {human(path_size(p))}",
                     bg=BG0, fg=MUTED, font=("SF Pro Text",10)).pack(anchor="w", padx=4)
        self._btn(self.tpanel, "♻️ Очистить Корзину (безвозвратно)", RED, self._do_trash).pack(anchor="w", pady=8)

    def _do_trash(self):
        sz = deep_trash_size()
        if not messagebox.askyesno("Очистить Корзину",
                f"Во всех корзинах ~{human(sz)} (включая системную корзину тома). Удалить безвозвратно?"): return
        run(["osascript","-e",'tell application "Finder" to empty the trash'])
        record_cleanup(sz, kind="trash")
        messagebox.showinfo("CleanMac", f"Запрошена очистка Корзины (~{human(sz)}). Может занять минуту.")

    # ================= ПРИВАТНОСТЬ =================
    def show_privacy(self):
        tk.Label(self.main, text=L("Приватность"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text=L("Очистка следов работы → в Корзину (обратимо). Браузеры должны быть закрыты."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,10))
        wrap=tk.Frame(self.main, bg=GLASS); wrap.pack(fill="x", padx=24, pady=(0,8))
        self.pv_vars={}; self.pv_lbl={}; self.pv_found={}
        for pid,title,paths,skip in PRIVACY_ITEMS:
            r=tk.Frame(wrap, bg=GLASS); r.pack(fill="x", padx=14, pady=6)
            v=tk.BooleanVar(value=False); self.pv_vars[pid]=v
            tk.Checkbutton(r, text="  "+title, variable=v, bg=GLASS, fg=TEXT, selectcolor=BG0,
                           activebackground=GLASS, activeforeground=TEXT, font=("SF Pro Text",12), anchor="w").pack(side="left")
            if skip: tk.Label(r, text=f"(если {skip} закрыт)", bg=GLASS, fg=MUTED, font=("SF Pro Text",9)).pack(side="left", padx=6)
            sl=tk.Label(r, text="…", bg=GLASS, fg=PURPLE, font=("SF Pro Text",11,"bold")); sl.pack(side="right"); self.pv_lbl[pid]=sl
        bar=tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=(2,14))
        tk.Label(bar, text=L("Отметьте, что очистить"), bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(side="left")
        self._btn(bar, "🗑 Очистить выбранное", PURPLE, self._pv_clean).pack(side="right")
        self._spawn(self._pv_scan)

    def _pv_scan(self):
        res={}
        for pid,title,paths,skip in PRIVACY_ITEMS:
            if skip and app_running(skip): res[pid]=("skip",[]); continue
            items=[(p,path_size(p)) for p in paths if os.path.exists(p)]
            res[pid]=(sum(s for _,s in items), items)
        self.q.put(("privacy", res, None))

    def _render_privacy(self, res):
        self.pv_found={pid:items for pid,(sz,items) in res.items() if sz!="skip"}
        for pid,(sz,items) in res.items():
            lbl=self.pv_lbl.get(pid)
            if lbl: lbl.configure(text=("пропуск" if sz=="skip" else human(sz)))

    def _pv_clean(self):
        sel=[pid for pid,v in self.pv_vars.items() if v.get()]
        if not sel: messagebox.showinfo("CleanMac","Ничего не выбрано."); return
        items=[it for pid in sel for it in self.pv_found.get(pid,[])]
        if not items: messagebox.showinfo("CleanMac","Нечего очищать (возможно, приложение запущено)."); return
        tot=sum(s for _,s in items)
        if not messagebox.askyesno("Приватность", f"Переместить в Корзину {len(items)} объектов (~{human(tot)})?"): return
        freed=sum(s for p,s in items if to_trash(p))
        messagebox.showinfo("CleanMac", f"В Корзину: {human(freed)}."); self.nav("privacy")

    # ================= ЗАЩИТА =================
    def show_threats(self):
        tk.Label(self.main, text=L("Защита"), bg=BG0, fg=TEXT, font=("SF Pro Display",28,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text=L("Эвристический поиск известного рекламного/нежелательного ПО в точках автозапуска. Не заменяет антивирус."),
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11), wraplength=640, justify="left").pack(anchor="w", padx=24, pady=(0,8))
        self.th_box=tk.Frame(self.main, bg=BG0); self.th_box.pack(fill="both", expand=True, padx=24, pady=(4,14))
        tk.Label(self.th_box, text=L("🔎 Сканирую точки автозапуска…"), bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w")
        self.th_found=[]
        self._spawn(self._threats_scan)

    def _threats_scan(self):
        suspicious, clean = scan_launch_agents()
        # Доп. проверка папок приложений по сигнатурам (только подозрительные).
        for base in ("/Applications", os.path.join(HOME,"Applications")):
            if not os.path.isdir(base): continue
            try: names=os.listdir(base)
            except Exception: continue
            for f in names:
                low=f.lower()
                for tok in ADWARE:
                    if tok in low:
                        suspicious.append({"label": f, "path": os.path.join(base,f),
                                           "reason": f"приложение · известная сигнатура «{tok}»",
                                           "run_at_load": False}); break
        self.q.put(("threats", (suspicious, clean), None))

    def _render_threats(self, payload):
        # payload: (suspicious, clean) — каждый элемент dict {label, path, reason, run_at_load}
        suspicious, clean = payload if isinstance(payload, tuple) else (payload, [])
        for w in self.th_box.winfo_children(): w.destroy()
        self.th_found=[]
        if not suspicious:
            tk.Label(self.th_box, text=L("✅ Подозрительных объектов не обнаружено"), bg=BG0, fg=GREEN,
                     font=("SF Pro Display",17,"bold")).pack(anchor="w", pady=10)
            tk.Label(self.th_box, text=f"Проверены LaunchAgents, LaunchDaemons и папки приложений. "
                     f"Чистых записей автозапуска: {len(clean)} (включая системные Apple).",
                     bg=BG0, fg=MUTED, font=("SF Pro Text",11), wraplength=640, justify="left").pack(anchor="w")
            return
        tk.Label(self.th_box, text=f"⚠️ Подозрительных объектов: {len(suspicious)}", bg=BG0, fg=YELLOW,
                 font=("SF Pro Display",15,"bold")).pack(anchor="w", pady=(0,2))
        tk.Label(self.th_box, text="Только для ручного разбора — это эвристика, а не приговор. "
                 "Проверьте элемент, прежде чем перемещать его в Корзину.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",10), wraplength=640, justify="left").pack(anchor="w", pady=(0,6))
        wrap=tk.Frame(self.th_box, bg=GLASS); wrap.pack(fill="both", expand=True)
        for rec in suspicious:
            p=rec["path"]; reason=rec.get("reason") or "подозрительно"
            r=tk.Frame(wrap, bg=GLASS); r.pack(fill="x", padx=10, pady=2)
            v=tk.BooleanVar(value=False)   # по умолчанию НЕ выбрано (только ручной разбор)
            tk.Checkbutton(r, variable=v, bg=GLASS, selectcolor=BG0, activebackground=GLASS, bd=0, highlightthickness=0).pack(side="left")
            tk.Label(r, text=reason, bg=GLASS, fg=YELLOW, font=("SF Pro Text",10), anchor="e").pack(side="right", padx=6)
            txt=f"{rec.get('label','')}  —  {p.replace(HOME,'~')}"
            tk.Label(r, text=txt, bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
            self.th_found.append((v,p))
        bar=tk.Frame(self.th_box, bg=BG0); bar.pack(fill="x", pady=(6,0))
        tk.Label(bar, text=f"Чистых записей автозапуска: {len(clean)}", bg=BG0, fg=MUTED,
                 font=("SF Pro Text",10)).pack(side="left")
        self._btn(bar, "🗑 Переместить выбранное в Корзину", RED, self._threats_remove).pack(side="right")

    def _threats_remove(self):
        sel=[p for v,p in self.th_found if v.get()]
        if not sel: messagebox.showinfo("CleanMac","Ничего не выбрано."); return
        if not messagebox.askyesno("Защита", f"Переместить в Корзину {len(sel)} объектов?\n(Элементы из /Library могут требовать прав администратора.)"): return
        ok=0
        for p in sel:
            if p.endswith(".plist"):
                run(["launchctl","bootout",f"gui/{os.getuid()}/{os.path.basename(p)[:-6]}"])
            if to_trash(p): ok+=1
        messagebox.showinfo("CleanMac", f"Перемещено в Корзину: {ok} из {len(sel)}."); self.nav("threats")

    # ================= PRO / О ПРОГРАММЕ =================
    def show_pro(self):
        tk.Label(self.main, text="🪽 KRYLAN · CleanMac", bg=BG0, fg=TEXT, font=("SF Pro Display",26,"bold")
                 ).pack(anchor="w", padx=24, pady=(24,0))
        tk.Label(self.main, text=f"«{SLOGAN}»", bg=BG0, fg=GREEN, font=("SF Pro Display",14,"bold")
                 ).pack(anchor="w", padx=24, pady=(0,4))
        tk.Label(self.main, text=f"Версия {VERSION}" + ("  ·  ⭐️ Pro активна" if self.is_pro else "  ·  Free"),
                 bg=BG0, fg=(GREEN if self.is_pro else MUTED), font=("SF Pro Text",12,"bold")).pack(anchor="w", padx=24)
        tk.Label(self.main, text=f"Создатель: {AUTHOR}", bg=BG0, fg=TEXT, font=("SF Pro Text",12,"bold")
                 ).pack(anchor="w", padx=24, pady=(6,0))
        if self.update_note:
            tk.Label(self.main, text=self.update_note, bg=BG0, fg=YELLOW, font=("SF Pro Text",12,"bold")).pack(anchor="w", padx=24, pady=(8,0))
        for line in ["", "Оптимизатор для macOS со «стеклянным» интерфейсом.",
                     "Часть экосистемы KRYLAN: Mac · iPhone · Android (в разработке).", "",
                     "• Дашборд: диаграммы, батарея, процессы в реальном времени",
                     "• Автопилот: фоновая чистка и разгрузка памяти при пиках",
                     "• Очистка кэшей/логов → в Корзину (обратимо)",
                     "• Приватность, Защита, Карта диска, Деинсталлятор", "",
                     "Распространяется как .dmg и через Homebrew — не в App Store",
                     "(песочница не позволяет чистильщикам быть в MAS).", "",
                     "⚠️ Сборка пока НЕ нотаризована в Apple: при первом запуске",
                     "скачанного .dmg macOS скажет, что не может проверить программу.",
                     "Снимается меткой карантина — кнопка ниже покажет, как."]:
            tk.Label(self.main, text=line, bg=BG0, fg=(TEXT if line.startswith("•") else MUTED),
                     font=("SF Pro Text",12), justify="left").pack(anchor="w", padx=24)
        row=tk.Frame(self.main, bg=BG0); row.pack(anchor="w", padx=24, pady=16)
        if not self.is_pro:
            self._btn(row,"⭐️ Купить Pro",PURPLE, lambda: run(["/usr/bin/open",BUY_URL])).pack(side="left", padx=(0,8))
        # Были две отдельные кнопки — «Проверить обновления» и «Обновить и
        # перезапустить». Пользователю всё равно приходилось жать сначала одну,
        # потом другую; вторая при этом молча ничего не делала, если обновлений
        # нет. Теперь один пункт: проверяет и сам предлагает обновиться.
        self._btn(row,"🔄 Обновления",GREEN, self._updates_flow).pack(side="left", padx=(0,8))
        self._btn(row,"GitHub",GLASS_HI, lambda: run(["/usr/bin/open",f"https://github.com/{REPO}"])).pack(side="left")
        self._btn(row,"🔓 Не открывается?",YELLOW, self._gatekeeper_help).pack(side="left", padx=(8,0))
        self._btn(row, ("🌐 EN" if LANG=="ru" else "🌐 RU"), GREEN,
                  lambda: self.set_lang("en" if LANG=="ru" else "ru")).pack(side="left", padx=(8,0))
        self._btn(row, ("☀️ Светлая" if THEME=="dark" else "🌙 Тёмная"), PURPLE,
                  lambda: self.set_theme("light" if THEME=="dark" else "dark")).pack(side="left", padx=(8,0))

    def _gatekeeper_help(self):
        """Памятка по «Apple не удалось подтвердить…» — с диагностикой этой копии.

        Сборка не нотаризована, поэтому скачанный .dmg получает метку
        com.apple.quarantine и macOS отказывается запускать приложение. Отказ
        выглядит глухо: процесс убивается сигналом 9 ещё до появления окна —
        ни crash-репорта, ни строки в `log show`. Совет «ПКМ → Открыть» из
        старых инструкций на macOS 15 Sequoia и новее уже не работает: Apple
        убрала этот обход.
        """
        app = "/Applications/CleanMac.app"
        quarantined = None
        if os.path.exists(app):
            quarantined = "com.apple.quarantine" in run(["xattr", app], 10)
        if quarantined is None:
            state = "Приложение не найдено в /Applications (запущено из исходников — Gatekeeper не мешает)."
        elif quarantined:
            state = "❗️ На этой копии метка карантина СТОИТ — она и блокирует запуск."
        else:
            state = "✅ На этой копии метки карантина нет — Gatekeeper запуск не блокирует."
        cmd = f"xattr -dr com.apple.quarantine {app}"
        if messagebox.askyesno("Не открывается после установки?",
                f"{state}\n\n"
                "Причина: сборка пока не нотаризована в Apple (нужен платный Developer ID).\n\n"
                "Способ 1 — одна команда в Терминале:\n"
                f"    {cmd}\n\n"
                "Способ 2 — Системные настройки → Конфиденциальность и безопасность → "
                "внизу «Всё равно открыть».\n\n"
                "Совет «ПКМ → Открыть» на macOS 15 Sequoia и новее уже НЕ работает.\n\n"
                "Скопировать команду в буфер обмена?"):
            try:
                self.clipboard_clear(); self.clipboard_append(cmd)
                self.status("Команда скопирована в буфер обмена")
            except Exception:
                pass

    # ---------- обновления ----------
    def _updates_flow(self):
        """Один пункт вместо двух: сначала проверка, потом предложение обновиться."""
        self.status("🔄 Проверяю обновления…")
        self._spawn(self._updates_flow_w)

    def _updates_flow_w(self):
        latest = self._latest_version()
        if latest and ver_tuple(latest) > ver_tuple(VERSION):
            self.q.put(("updates_offer", latest, None))
        elif latest:
            self.q.put(("update", f"✅ Установлена последняя версия {VERSION}", None))
        else:
            self.q.put(("update", "Не удалось проверить обновления (нет сети).", None))

    def _self_update(self):
        self.status("🔄 Обновляю из GitHub…")
        self._spawn(self._self_update_w)

    def _self_update_w(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        # Самообновление через git pull работает только при запуске из исходников.
        # Установленный .app (frozen) или папка без .git так обновить нельзя —
        # открываем страницу релизов, чтобы скачать свежий .dmg.
        is_git = os.path.isdir(os.path.join(repo, ".git")) and not getattr(sys, "frozen", False)
        if not is_git:
            self.q.put(("selfupdate_dmg", None, None))
            return
        before = run(["git","-C",repo,"rev-parse","--short","HEAD"], 15).strip()
        run(["git","-C",repo,"pull","--ff-only","--autostash"], 60)
        after = run(["git","-C",repo,"rev-parse","--short","HEAD"], 15).strip()
        newver = VERSION
        try:
            with open(os.path.join(repo,"VERSION")) as f: newver = f.read().strip()
        except Exception: pass
        self.q.put(("selfupdate", (before != after, newver), None))

    def _do_restart(self):
        """Перезапуск со свежим кодом: заменяем процесс новым python на обновлённом CleanMac.py."""
        try:
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
        except Exception as e:
            messagebox.showerror("CleanMac", f"Не удалось перезапустить: {e}\nЗакройте и откройте приложение вручную.")

    def _fetch_url(self, url, headers):
        """GET c проверкой TLS. Используется только для https:// (проверка обновлений).

        Раньше был откат на ssl._create_unverified_context() «для сборки без системных
        CA» — но это отключало проверку сертификата и открывало MITM-подмену версии/
        содержимого при проверке обновлений. Проверяем сертификат всегда: системный CA
        или certifi. Никакого небезопасного отката."""
        import ssl
        if not str(url).lower().startswith("https:"):
            return None
        contexts=[None]      # системный CA
        try:
            import certifi; contexts.append(ssl.create_default_context(cafile=certifi.where()))
        except Exception: pass
        req=urllib.request.Request(url, headers=headers)
        for ctx in contexts:
            try:
                kw={"timeout":6}
                if ctx is not None: kw["context"]=ctx
                with urllib.request.urlopen(req, **kw) as r:
                    return r.read().decode()
            except Exception:
                continue
        return None

    def _latest_version(self):
        """Последняя ОПУБЛИКОВАННАЯ версия (то, что реально можно скачать).

        Сравнивать с файлом VERSION в main нельзя как с основным источником —
        так обещали бы версию, которой ещё нет в Releases. Он только запасной.
        """
        import json
        data=self._fetch_url(f"https://api.github.com/repos/{REPO}/releases/latest",
                             {"User-Agent":"CleanMac","Accept":"application/vnd.github+json"})
        if data:
            try:
                tag=(json.loads(data).get("tag_name") or "").lstrip("v").strip()
                if tag: return tag
            except Exception: pass
        raw=self._fetch_url(f"https://raw.githubusercontent.com/{REPO}/main/VERSION",
                            {"User-Agent":"CleanMac"})
        return raw.strip() if raw else None

    def _check_update(self, manual=False):
        latest=self._latest_version()
        if latest and ver_tuple(latest) > ver_tuple(VERSION):
            self.q.put(("update", f"⬆️ Доступна версия {latest} (у вас {VERSION})", None))
        elif latest and manual:
            self.q.put(("update", f"✅ Установлена последняя версия {VERSION}", None))
        elif manual:
            self.q.put(("update", "Не удалось проверить обновления (нет сети).", None))

    def _on_close(self):
        """Аккуратное закрытие: снимаем флаг (потоки-сэмплеры и циклы after прекращают
        обращаться к разрушаемым виджетам → нет TclError/трейсбеков), затем destroy."""
        self._alive = False
        try: self.destroy()
        except Exception: pass

    # ---------- сэмплер ----------
    def _sampler(self):
        while getattr(self, "_alive", True):
            cpu=stat_cpu(); ram=stat_mem(); sused,_=stat_swap()
            disk,dfree,dtot=stat_disk(); vm=stat_vm(); batt=stat_batt(); procs=stat_procs()
            swap_sev=min(100, sused/8192*100)
            health=(0.30*(100-ram)+0.20*(100-swap_sev)+0.20*(100-disk)+0.15*(100-cpu)+0.15*(batt["health"] or 100))
            self.q.put(("stats", {"cpu":cpu,"ram":ram,"swap":swap_sev,"swap_mb":sused,"disk":disk,
                        "health":health,"batt":batt,"procs":procs,"vm":vm,"dfree":dfree,"dtot":dtot}, None))
            time.sleep(1.4)

    def _net_sampler(self):
        """Лёгкий поток сети: обновляет скорость раз в секунду независимо от тяжёлого сэмплера.
        Так интернет на дашборде идёт по-настоящему в реальном времени."""
        stat_net()  # инициализация prev
        while getattr(self, "_alive", True):
            time.sleep(1.0)
            d,u = stat_net()
            self.net_down, self.net_up = d, u
            self.net_down_hist.append(d); self.net_up_hist.append(u)

    def _animate(self):
        # КРИТИЧНО: любое исключение в отрисовке НЕ должно обрывать цикл.
        # Анимируем только когда дашборд видим и в фокусе — иначе app зря жрёт CPU.
        active=False
        try:
            active = (getattr(self,"_visible",True) and self.page=="dash"
                      and hasattr(self,"cv") and self.cv.winfo_exists())
            if active:
                self._frame = getattr(self, "_frame", 0) + 1
                for k in self.disp: self.disp[k]+=(self.tgt[k]-self.disp[k])*0.30
                self._draw_dash()
                if hasattr(self,"live_dot"):
                    base=col_for(self.disp["health"], inv=True)
                    on=(self._frame//8)%2==0
                    self.live_dot.configure(fg=base if on else _blend(base,BG0,0.55))
        except Exception:
            pass
        # 15 fps когда смотрим; раз в 0.6 с когда окно неактивно/свёрнуто
        if getattr(self, "_alive", True):
            self.after(85 if active else 600, self._animate)

    # ---------- очередь ----------
    def _spawn(self, fn, *args, label=None):
        """Запустить фоновую задачу так, чтобы её падение было видно.

        Раньше воркеры стартовали голым threading.Thread(target=...). Если такой
        воркер бросал исключение до своего self.q.put(...), поток тихо умирал:
        сообщение в очередь не приходило, и интерфейс навсегда оставался на
        «⏳ Идёт…» — без ошибки, без подсказки, без возможности повторить.
        Теперь исключение ловится и уходит в очередь как ("error", ...).
        """
        name = label or getattr(fn, "__name__", "задача").strip("_").replace("_w", "")
        def guard():
            try:
                fn(*args)
            except Exception as e:
                if getattr(self, "_alive", False):
                    self.q.put(("error", name, f"{e.__class__.__name__}: {e}"))
        t = threading.Thread(target=guard, daemon=True); t.start(); return t

    def _poll(self):
        try:
            while True:
                kind,a,b=self.q.get_nowait()
                if kind=="error":
                    # Воркер упал: снимаем «идёт…» и честно говорим, что именно сломалось.
                    self.status(f"⚠️ Ошибка в задаче «{a}»")
                    messagebox.showerror("CleanMac",
                        f"Задача «{a}» завершилась с ошибкой:\n\n{b}\n\n"
                        "Ничего не удалено. Можно повторить — если повторяется, "
                        f"сообщите об ошибке: https://github.com/{REPO}/issues")
                elif kind=="stats":
                    self.tgt.update({"cpu":a["cpu"],"ram":a["ram"],"swap":a["swap"],"disk":a["disk"],
                                     "health":a["health"],"batt":a["batt"]["pct"]})
                    self.swap_mb=a["swap_mb"]; self.batt=a["batt"]; self.procs=a["procs"]; self.vm=a["vm"]
                    self.disk_free=a["dfree"]; self.disk_total=a["dtot"]
                    self.cpu_hist.append(a["cpu"]); self.ram_hist.append(a["ram"])
                    self.health_hist.append(a["health"]); self.disk_hist.append(a["disk"])
                    # сеть обновляется отдельным _net_sampler (раз в секунду, реальное время)
                    self.status(f'Здоровье {int(a["health"])} · CPU {int(a["cpu"])}% · ОЗУ {int(a["ram"])}% · бат {a["batt"]["pct"]}%')
                    self._maybe_alert(a["disk"], a["batt"].get("health", 100))
                    self._render_advice()
                elif kind=="catsize":
                    lbl=self.cat_size_lbl.get(a)
                    if lbl: lbl.configure(text=("—" if a is None else "пропуск" if b=="skip" else ("—" if b is None else human(b))))
                elif kind=="total": self.total_lbl.configure(text=f"Найдено: {human(a)}")
                elif kind=="cleaned":
                    record_cleanup(a, "clean")
                    self.total_lbl.configure(text=f"Очищено: {human(a)} ({b}) → Корзина")
                    messagebox.showinfo("CleanMac", f"В Корзину: {human(a)} ({b} объектов)."); self.found={}
                elif kind=="optimized":
                    record_cleanup(a, "autopilot")
                    messagebox.showinfo("CleanMac", f"Оптимизация выполнена.\nОсвобождено кэша: {human(a)}.")
                    if self.page=="autopilot": self._ap_refresh()
                elif kind=="boosted":
                    steps="\n".join("• "+s for s in (b or []))
                    messagebox.showinfo("CleanMac",
                        f"🚀 Готово! Компьютер ускорен.\n\nОсвобождено всего: ~{human(a)}\n\n{steps}\n\n"
                        "Всё обратимо: очищенное — в Корзине. Дефрагментация SSD не делалась (она вредна).")
                elif kind=="optprog":
                    idx, total, label, detail = a
                    txt = f"✨ Шаг {idx}/{total}: {label}" + (f" — {detail}" if detail else "")
                    self.status(txt)
                    if getattr(self, "magic_prog", None) and self.magic_prog.winfo_exists():
                        self.magic_prog.configure(text=txt)
                elif kind=="optimized_all":
                    self._render_optimize_summary(a)
                elif kind=="purged":
                    record_cleanup(a, "purge")
                    self.status("Готово")
                    messagebox.showinfo("CleanMac",
                        f"Очищаемое место освобождено: ~{human(a)}.\n"
                        "Снимки APFS удалены. Это безопасный аналог «очистки диска» без дефрагментации.")
                elif kind=="tool" and self.page=="tools":
                    sub,data=a
                    if sub=="large": self._render_large(data)
                    elif sub=="devjunk": self._render_devjunk(data)
                    elif sub=="bigold": self._render_bigold(data)
                    elif sub=="olddl": self._render_olddl(data)
                    elif sub=="mailatt": self._render_mailatt(data)
                    elif sub=="dupes": self._render_dupes(data)
                    elif sub=="vacuum": self._render_vacuum(data)
                    elif sub=="extensions": self._render_extensions(data)
                elif kind=="vacuumed":
                    done, saved, skipped = a
                    self.status("")
                    if done == 0 and skipped > 0:
                        messagebox.showinfo("CleanMac", L("Все найденные браузеры запущены — закройте их и повторите."))
                    else:
                        msg = f"{L('Сжато баз: ')}{done}{L(' · сэкономлено ')}{human(saved)}"
                        if skipped: msg += f"{L(' · пропущено (браузер запущен): ')}{skipped}"
                        messagebox.showinfo("CleanMac", msg)
                    if self.page=="tools": self._tool("vacuum")
                elif kind=="disk" and self.page=="tools": self._render_disk(a)
                elif kind=="sunburst" and self.page=="tools": self._on_sun_tree(a)
                elif kind=="bench" and self.page=="tools": self._render_bench(a)
                elif kind=="trash_info" and self.page=="tools": self._render_trash_info(a)
                elif kind=="maintdone":
                    try: self._mrez.configure(text="✅ Готово: "+a.replace("★","").strip())
                    except Exception: pass
                elif kind=="privacy" and self.page=="privacy": self._render_privacy(a)
                elif kind=="threats" and self.page=="threats": self._render_threats(a)
                elif kind=="smart" and self.page=="smart": self._render_smart(*a)
                elif kind=="smartdone":
                    record_cleanup(a, "smart")
                    messagebox.showinfo("CleanMac", f"Освобождено: {human(a)} → Корзина.")
                    if self.page=="smart": self.nav("smart")
                elif kind=="updater":
                    if self.page=="tools": self._render_updater(a if a is not None else [])
                elif kind=="leftovers":
                    if self.page=="tools": self._render_leftovers(a or [])
                elif kind=="upgraded":
                    self.status("")
                    messagebox.showinfo("CleanMac", "Обновление Homebrew завершено.")
                    if self.page=="tools": self._tool("updater")
                elif kind=="update":
                    self.update_note=a; self.badge.configure(text=a if a.startswith("⬆️") else "")
                    self.status(a if not a.startswith("⬆️") else "")
                    if self.page=="pro": self.nav("pro")
                elif kind=="updates_offer":
                    # Нашли новее — сразу предлагаем обновиться, без второй кнопки.
                    self.update_note=f"⬆️ Доступна версия {a} (у вас {VERSION})"
                    self.badge.configure(text=self.update_note); self.status("")
                    if messagebox.askyesno("Обновление",
                            f"Доступна версия {a}, у вас {VERSION}.\n\nОбновить сейчас?"):
                        self._self_update()
                    elif self.page=="pro": self.nav("pro")
                elif kind=="selfupdate":
                    self.status("")
                    changed, newver = a
                    if changed:
                        if messagebox.askyesno("CleanMac",
                            f"Обновлено до версии {newver}.\nПерезапустить сейчас, чтобы применить?"):
                            self._do_restart()
                    else:
                        messagebox.showinfo("CleanMac", f"У вас уже последняя версия ({newver}).")
                elif kind=="selfupdate_dmg":
                    self.status("")
                    run(["/usr/bin/open", f"https://github.com/{REPO}/releases/latest"])
                    messagebox.showinfo("CleanMac",
                        "Это установленная версия (.app) — обновить её через git нельзя.\n\n"
                        "Открыл страницу релизов: скачайте свежий CleanMac.dmg и перетащите "
                        "приложение в «Программы», заменив старое.")
        except queue.Empty: pass
        except Exception: pass
        if getattr(self, "_alive", True):
            self.after(120, self._poll)


def acquire_single_instance():
    """Не даём запустить второй экземпляр: два CleanMac одновременно могли
    параллельно чистить/перемещать в Корзину и чинить launch-агенты, конкурируя
    за одни файлы. Держим эксклюзивный flock на файле в OPT. Возвращает
    file-объект (держать до выхода) или None, если уже запущен другой экземпляр."""
    try:
        os.makedirs(OPT, exist_ok=True)
        lock = open(os.path.join(OPT, "cleanmac.lock"), "w")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock
    except Exception:
        return None


if __name__ == "__main__":
    _lock = acquire_single_instance()
    if _lock is None:
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showinfo("CleanMac", "CleanMac уже запущен.")
            r.destroy()
        except Exception:
            pass
        sys.exit(0)
    CleanMac().mainloop()
