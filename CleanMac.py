#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN · CleanMac — оптимизатор для macOS со «стеклянным» интерфейсом.
Слоган: «Дай устройству крылья».
Создатель: Кырлан Александр Сергеевич.
Дашборд с диаграммами, автопилот, очистка в Корзину, инструменты,
проверка обновлений (GitHub) и Pro-каркас. Запуск: framework-python 3.12.
"""
import os, time, shutil, hashlib, threading, queue, subprocess, collections, math, re, json
import urllib.request
import tkinter as tk
from tkinter import messagebox

VERSION = "2.9.0"
BRAND   = "KRYLAN"
SLOGAN  = "Дай устройству крылья"
AUTHOR  = "Кырлан Александр Сергеевич"
REPO    = "Alex1986-rgb/CleanMac"          # для проверки обновлений
BUY_URL = "https://alex1986-rgb.gumroad.com/l/cleanmac"   # ссылка на Pro (заглушка)
HOME  = os.path.expanduser("~")
TRASH = os.path.join(HOME, ".Trash")
OPT   = os.path.join(HOME, "mac-optimizer")
CFG   = os.path.join(HOME, ".config", "cleanmac")
LIC   = os.path.join(CFG, "license")
LANG_FILE = os.path.join(CFG, "lang")

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
}
def L(s):
    return TR.get(s, s) if LANG=="en" else s

# ---------- акценты (общие для тем) ----------
GREEN, BLUE, YELLOW, RED, PURPLE, CYAN = "#37d39a", "#4b8cf9", "#f6bb45", "#f2685f", "#a78bfa", "#36c6d6"

# ---------- темы оформления ----------
THEMES = {
    "dark":  {"BG0":"#11151d","BG1":"#1b2330","SIDEBAR":"#0e1219","GLASS":"#222b3a",
              "GLASS_HI":"#2b3647","TRACK":"#333d4e","TEXT":"#eef2f8","MUTED":"#8a94a6"},
    "light": {"BG0":"#eef1f7","BG1":"#e2e8f2","SIDEBAR":"#e6ebf4","GLASS":"#ffffff",
              "GLASS_HI":"#dbe2ee","TRACK":"#ccd5e1","TEXT":"#1b2230","MUTED":"#5f6b7a"},
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
def human(n):
    n = float(n)
    for u in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024 or u == "ТБ":
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024

def run(cmd, t=8):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout
    except Exception:
        return ""

def _lighten(hexc, amt=0.16):
    r,g,b = int(hexc[1:3],16), int(hexc[3:5],16), int(hexc[5:7],16)
    f = lambda c: min(255, int(c+(255-c)*amt))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"

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
    try: return int(run(["/usr/bin/du", "-sk", p], 60).split("\t")[0]) * 1024
    except Exception: return 0

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
    """True, если путь — защищённый корень (его удалять нельзя; подпапки внутри — можно)."""
    rp = os.path.realpath(path)
    return rp in PROTECTED or rp == os.path.realpath(HOME) or len(rp.strip("/").split("/")) < 2

def to_trash(path):
    if not os.path.exists(path): return False
    if is_protected(path): return False          # страховка: не трогаем системные/корневые папки
    base = os.path.basename(path.rstrip("/")) or "item"
    dest = os.path.join(TRASH, base)
    if os.path.exists(dest): dest = os.path.join(TRASH, f"{base}-{int(time.time()*1000)}")
    try: shutil.move(path, dest); return True
    except Exception: return False

# ---------- метрики ----------
def stat_cpu():
    for ln in run(["/usr/bin/top", "-l", "1", "-n", "0"], 5).splitlines():
        if ln.startswith("CPU usage"):
            p = ln.replace("CPU usage:", "").split(",")
            try: return min(100, float(p[0].split("%")[0]) + float(p[1].split("%")[0].strip()))
            except Exception: return 0
    return 0

def stat_mem():
    for ln in run(["memory_pressure"], 5).splitlines():
        if "free percentage" in ln:
            try: return 100 - float(ln.split(":")[1].strip().rstrip("%"))
            except Exception: return 0
    return 0

def stat_vm():
    """Состав памяти (байты): wired/active/compressed/inactive/free."""
    out = run(["vm_stat"]); ps = 16384
    m = re.search(r"page size of (\d+)", out)
    if m: ps = int(m.group(1))
    def g(k):
        mm = re.search(k + r":\s+(\d+)", out); return int(mm.group(1))*ps if mm else 0
    free = g("Pages free") + g("Pages speculative")
    return {"Активная": g("Pages active"), "Связанная": g("Pages wired down"),
            "Сжатая": g("Pages occupied by compressor"),
            "Неактивная": g("Pages inactive"), "Свободная": free}

def stat_swap():
    f = run(["sysctl", "-n", "vm.swapusage"]).split()
    try: return float(f[5].rstrip("M")), float(f[2].rstrip("M"))
    except Exception: return 0, 0

def stat_disk():
    try: st = os.statvfs("/System/Volumes/Data")
    except Exception: st = os.statvfs("/")
    total = st.f_blocks*st.f_frsize; free = st.f_bavail*st.f_frsize
    return ((total-free)/total*100 if total else 0), free, total

_bc = {"health": 0, "cycles": 0, "cond": "—", "t": 0}
def stat_batt():
    pct, charging, tleft = 0, False, ""
    for ln in run(["pmset", "-g", "batt"]).splitlines():
        if "%" in ln:
            seg = ln.split(";")
            try: pct = int(seg[0].split("\t")[-1].strip().rstrip("%"))
            except Exception: pass
            charging = "discharging" not in ln
            for s in seg:
                if "remaining" in s: tleft = s.strip().split(" ")[0]
            break
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
    rows = []
    for ln in run(["/bin/ps", "-axo", "%cpu,rss,comm", "-r"]).splitlines()[1:]:
        p = ln.split(None, 2)
        if len(p) < 3: continue
        try: rows.append((float(p[0]), int(p[1])*1024, p[2].split("/")[-1][:22]))
        except Exception: pass
    return rows[:n]

# ---------- категории очистки ----------
CATEGORIES = [
    ("user_caches", "Кэш приложений (пользовательский)", [os.path.join(HOME,"Library/Caches")], None, "subitems"),
    ("safari", "Кэш Safari", [os.path.join(HOME,"Library/Caches/com.apple.Safari")], "Safari", "whole"),
    ("chrome", "Кэш Google Chrome", [os.path.join(HOME,"Library/Caches/Google")], "Chrome", "whole"),
    ("edge", "Кэш Microsoft Edge", [os.path.join(HOME,"Library/Caches/Microsoft Edge")], "Edge", "whole"),
    ("yandex", "Кэш Yandex", [os.path.join(HOME,"Library/Caches/Yandex")], "Yandex", "whole"),
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
ADWARE = ["genieo","installmac","vsearch","conduit","mackeeper","pirrit","bundlore","adload",
          "spigot","crossrider","trovi","mughthesec","shlayer","searchquick","search-quick",
          "advancedmaccleaner","macsweeper","weknow","aerodynamic","chumsearch","maxxmediasearch"]


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
        self.cat_vars={}; self.cat_size_lbl={}; self.found={}; self._alert_t={}
        self.is_pro = os.path.exists(LIC)
        self.update_note = ""
        self._build()
        self.nav("dash")
        threading.Thread(target=self._sampler, daemon=True).start()
        threading.Thread(target=self._check_update, daemon=True).start()
        self.after(80, self._poll); self.after(33, self._animate)

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
        for key,icon,name in [("dash","📊","Дашборд"),("smart","✨","Умная очистка"),("privacy","🔒","Приватность"),
                          ("threats","🛡","Защита"),("autopilot","🚀","Автопилот"),("cleaner","🧽","Очистка"),
                          ("tools","🛠","Инструменты"),("pro","⭐️","Pro / О программе")]:
            b = tk.Label(self.side, text=f"   {icon}  {L(name)}", bg=SIDEBAR, fg=TEXT, font=("SF Pro Text", 13),
                         anchor="w", padx=10, pady=12, cursor="pointinghand")
            b.pack(fill="x"); b.bind("<Button-1>", lambda e,k=key: self.nav(k))
            b.bind("<Enter>", lambda e,bb=b,k=key: bb.configure(bg=GLASS_HI) if self.page!=k else None)
            b.bind("<Leave>", lambda e,bb=b,k=key: bb.configure(bg=(GLASS if self.page==k else SIDEBAR)))
            self.nav_btns[key]=b
        self.badge = tk.Label(self.side, text="", bg=SIDEBAR, fg=YELLOW, font=("SF Pro Text", 11, "bold"),
                              wraplength=184, justify="left"); self.badge.pack(side="bottom", fill="x", padx=12, pady=(0,6))
        self.statusbar = tk.Label(self.side, text="", bg=SIDEBAR, fg=MUTED, font=("SF Pro Text", 10),
                                  wraplength=184, justify="left"); self.statusbar.pack(side="bottom", fill="x", padx=12, pady=4)
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    def nav(self, key):
        self.page = key
        for k,b in self.nav_btns.items():
            b.configure(bg=GLASS if k==key else SIDEBAR, fg=TEXT if k==key else "#9aa3b2")
        for w in self.main.winfo_children(): w.destroy()
        {"dash":self.show_dash,"smart":self.show_smart,"privacy":self.show_privacy,"threats":self.show_threats,
         "autopilot":self.show_autopilot,"cleaner":self.show_cleaner,
         "tools":self.show_tools,"pro":self.show_pro}[key]()

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

    def _maybe_alert(self, disk, batt_health):
        now = time.time()
        def fire(key, cooldown, title, msg):
            if now - self._alert_t.get(key, 0) > cooldown:
                self._alert_t[key] = now
                run(["osascript", "-e", f'display notification "{msg}" with title "{title}"'])
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
        # вертикальный градиент фона (имитация стекла)
        steps=40
        for i in range(steps):
            t=i/steps
            col="#%02x%02x%02x"%tuple(int(int(BG0[j:j+2],16)+(int(BG1[j:j+2],16)-int(BG0[j:j+2],16))*t) for j in (1,3,5))
            c.create_rectangle(0, h*i/steps, w, h*(i+1)/steps+1, fill=col, outline=col)

    def _ring(self, c, cx,cy,r,frac,color,w,big,small,val):
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        if frac>0.001:
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=90, extent=-frac*359.9, style="arc", outline=color, width=w)
            for ang in (90, 90-frac*359.9):
                px=cx+r*math.cos(math.radians(ang)); py=cy-r*math.sin(math.radians(ang))
                c.create_oval(px-w/2,py-w/2,px+w/2,py+w/2, fill=color, outline=color)
        c.create_text(cx,cy-3, text=val, fill=TEXT, font=("SF Pro Display", big, "bold"))
        c.create_text(cx,cy+r+13, text=small, fill=MUTED, font=("SF Pro Text", 10))

    def _donut(self, c, cx,cy,r,w, segs, center_top="", center_bot=""):
        start=90
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        for frac,color in segs:
            if frac<=0: continue
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=start, extent=-frac*359.9, style="arc", outline=color, width=w)
            start-=frac*359.9
        if center_top: c.create_text(cx,cy-7, text=center_top, fill=TEXT, font=("SF Pro Display", 17, "bold"))
        if center_bot: c.create_text(cx,cy+12, text=center_bot, fill=MUTED, font=("SF Pro Text", 10))

    def _spark(self, c, x,y,w,h, series):
        c.create_line(x,y+h,x+w,y+h, fill=TRACK)
        for deq,color in series:
            n=len(deq); sw=w/max(1,n-1); pts=[]
            for i,v in enumerate(deq): pts += [x+i*sw, y+h-(min(100,v)/100)*h]
            if len(pts)>=4: c.create_line(*pts, fill=color, width=2, smooth=True)

    # ================= ДАШБОРД =================
    def show_dash(self):
        tk.Label(self.main, text=L("Дашборд"), bg=BG0, fg=TEXT, font=("SF Pro Display", 22, "bold")
                 ).pack(anchor="w", padx=24, pady=(16,0))
        tk.Label(self.main, text=L("Состояние системы в реальном времени"), bg=BG0, fg=MUTED,
                 font=("SF Pro Text", 11)).pack(anchor="w", padx=24, pady=(0,6))
        qa=tk.Frame(self.main, bg=BG0); qa.pack(fill="x", padx=22, pady=(0,8))
        self.bri_btn=self._btn(qa, L("☀️ Яркость 100%"), YELLOW, self._brightness_max)
        self.bri_btn.pack(side="left", padx=(2,10))
        cur=get_brightness()
        self.bri_var=tk.IntVar(value=int((cur if cur is not None else 0.7)*100))
        tk.Scale(qa, from_=0, to=100, orient="horizontal", variable=self.bri_var, command=self._bri_slide,
                 bg=BG0, fg=MUTED, troughcolor=TRACK, highlightthickness=0, bd=0, length=140,
                 showvalue=False, activebackground=YELLOW, sliderrelief="flat").pack(side="left", padx=(0,6))
        self.bri_pct=tk.Label(qa, text=f'{self.bri_var.get()}%', bg=BG0, fg=YELLOW, font=("SF Pro Text",11,"bold"))
        self.bri_pct.pack(side="left", padx=(0,14))
        self._btn(qa, L("✨ Умная очистка"), GREEN, lambda: self.nav("smart")).pack(side="left", padx=(0,8))
        self._btn(qa, L("🚀 Автопилот"), BLUE, lambda: self.nav("autopilot")).pack(side="left")
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=14, pady=(0,12))

    def _brightness_max(self):
        set_brightness(1.0)
        try: self.bri_var.set(100); self.bri_pct.configure(text="100%")
        except Exception: pass
        old=self.bri_btn.cget("text"); self.bri_btn.configure(text="  ✓ 100%  ")
        self.after(1200, lambda: self.bri_btn.configure(text=old))

    def _bri_slide(self, val):
        set_brightness(max(0.05, int(val)/100))
        try: self.bri_pct.configure(text=f"{int(val)}%")
        except Exception: pass

    def _card(self, c, x,y,w,h, title=None):
        self._round(c, x,y,x+w,y+h, 16, fill=GLASS, outline=GLASS_HI)
        if title: c.create_text(x+16,y+16, text=title, anchor="w", fill=MUTED, font=("SF Pro Text", 11, "bold"))

    def _draw_dash(self):
        if not (self.page=="dash" and self.cv.winfo_exists()): return
        c=self.cv; c.delete("all")
        W=c.winfo_width() or 760; H=c.winfo_height() or 620
        self._grad(c, W, H)
        m=14; colw=(W-3*m)/2
        # --- Карта 1: Health + 4 кольца (во всю ширину) ---
        x,y,w,h=m,m,W-2*m,150; self._card(c,x,y,w,h)
        lab=("Отлично" if self.disp["health"]>=75 else "Хорошо" if self.disp["health"]>=50 else "Внимание")
        self._ring(c, x+78,y+76,58,self.disp["health"]/100,col_for(self.disp["health"],inv=True),14,26,
                   "ЗДОРОВЬЕ · "+lab, str(int(self.disp["health"])))
        rings=[("cpu","CPU",f'{int(self.disp["cpu"])}%'),("ram","ОЗУ",f'{int(self.disp["ram"])}%'),
               ("swap","SWAP",human(self.swap_mb*1024*1024).replace(" ","")),("disk","ДИСК",f'{int(self.disp["disk"])}%')]
        gx=x+200; gap=(w-220)/4
        for i,(k,l,v) in enumerate(rings):
            self._ring(c, int(gx+gap*i+gap/2), y+72, 40, min(1,self.disp[k]/100), col_for(self.disp[k],inv=True),10,15,l,v)
        # --- Карта 2: история CPU/RAM ---
        y2=y+h+m; x,w,h=m,colw,160; self._card(c,x,y2,w,h,"Нагрузка за минуту")
        self._spark(c, x+16,y2+34,w-32,h-58, [(self.cpu_hist,BLUE),(self.ram_hist,PURPLE)])
        c.create_text(x+16,y2+h-14, text="● CPU", anchor="w", fill=BLUE, font=("SF Pro Text",10))
        c.create_text(x+76,y2+h-14, text="● ОЗУ", anchor="w", fill=PURPLE, font=("SF Pro Text",10))
        # --- Карта 3: состав памяти (пончик) ---
        x3=m+colw+m; self._card(c,x3,y2,colw,h,"Память")
        total=sum(self.vm.values()) or 1
        palette=[GREEN,BLUE,PURPLE,YELLOW,TRACK]
        segs=[(v/total,palette[i%5]) for i,(k,v) in enumerate(self.vm.items())]
        self._donut(c, x3+70,y2+86,46,14, segs, human(total-self.vm.get("Свободная",0)).replace(" ",""), "занято")
        ly=y2+34
        for i,(k,v) in enumerate(self.vm.items()):
            c.create_oval(x3+150,ly+2,x3+160,ly+12, fill=palette[i%5], outline=palette[i%5])
            c.create_text(x3+168,ly+7, anchor="w", fill=TEXT, font=("SF Pro Text",10), text=f"{k}")
            c.create_text(x3+colw-16,ly+7, anchor="e", fill=MUTED, font=("SF Pro Text",10), text=human(v))
            ly+=22
        # --- Карта 4: диск (пончик) ---
        y3=y2+h+m; x,w,h=m,colw,150; self._card(c,x,y3,w,h,"Диск")
        used=self.disk_total-self.disk_free
        self._donut(c, x+70,y3+82,46,14, [(used/max(1,self.disk_total),col_for(self.disp["disk"],inv=True)),
                    (self.disk_free/max(1,self.disk_total),TRACK)], f'{int(self.disp["disk"])}%', "занято")
        c.create_text(x+150,y3+60, anchor="w", fill=TEXT, font=("SF Pro Text",12,"bold"),
                      text=f"Свободно: {human(self.disk_free)}")
        c.create_text(x+150,y3+84, anchor="w", fill=MUTED, font=("SF Pro Text",11),
                      text=f"Всего: {human(self.disk_total)}")
        # --- Карта 5: батарея ---
        x5=m+colw+m; self._card(c,x5,y3,colw,h,"Батарея")
        self._battery(c, x5+24,y3+44,86,38, min(1,self.disp["batt"]/100), self.batt["charging"])
        st="заряжается" if self.batt["charging"] else "разряжается"
        c.create_text(x5+128,y3+50, anchor="w", fill=TEXT, font=("SF Pro Display",20,"bold"), text=f'{self.batt["pct"]}%')
        c.create_text(x5+128,y3+76, anchor="w", fill=MUTED, font=("SF Pro Text",10),
                      text=st+(f' · ~{self.batt["tleft"]}' if self.batt["tleft"] and ":" in self.batt["tleft"] else ""))
        hp=self.batt["health"]
        c.create_text(x5+colw-16,y3+50, anchor="e", fill=(GREEN if hp>=80 else YELLOW if hp>=60 else RED),
                      font=("SF Pro Display",18,"bold"), text=f"{hp}%")
        c.create_text(x5+colw-16,y3+74, anchor="e", fill=MUTED, font=("SF Pro Text",10),
                      text=f"циклов {self.batt['cycles']} · {self.batt['cond']}")
        # --- Карта 6: процессы ---
        y4=y3+h+m; x,w,h=m,W-2*m,150; self._card(c,x,y4,w,h,"Активные процессы")
        py=y4+40
        for cpu,mem,name in self.procs:
            c.create_text(x+16,py, anchor="w", fill=TEXT, font=("SF Pro Text",12), text=name)
            bx=x+200; bw=w-380
            self._round(c,bx,py-6,bx+bw,py+6,6, fill=TRACK, outline=TRACK)
            fw=max(4,min(bw,bw*cpu/100))
            self._round(c,bx,py-6,bx+fw,py+6,6, fill=col_for(cpu,inv=True), outline=col_for(cpu,inv=True))
            c.create_text(bx+bw+40,py, anchor="e", fill=MUTED, font=("SF Pro Text",11), text=f"{cpu:.0f}%")
            c.create_text(x+w-16,py, anchor="e", fill=MUTED, font=("SF Pro Text",11), text=human(mem))
            py+=21
        c.configure(scrollregion=(0,0,W,y4+h+m))

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
        tk.Label(self.main, text=L("Умная очистка"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text="Один проход по всем безопасным категориям. Всё уходит в Корзину.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,10))
        top=tk.Frame(self.main, bg=GLASS); top.pack(fill="x", padx=24, pady=6)
        self.smart_big=tk.Label(top, text="Сканирую…", bg=GLASS, fg=GREEN, font=("SF Pro Display",30,"bold"))
        self.smart_big.pack(side="left", padx=20, pady=16)
        self.smart_sub=tk.Label(top, text="оцениваю объём…", bg=GLASS, fg=MUTED, font=("SF Pro Text",12))
        self.smart_sub.pack(side="left", pady=16)
        self.smart_btn=self._btn(top, "🧹 Очистить всё", GREEN, self._smart_clean)
        self.smart_btn.pack(side="right", padx=18, pady=14)
        self.smart_list=tk.Frame(self.main, bg=GLASS); self.smart_list.pack(fill="both", expand=True, padx=24, pady=(8,16))
        self.smart_found={}
        threading.Thread(target=self._smart_w, daemon=True).start()

    def _smart_w(self):
        found={}; total=0
        for cid,title,paths,skip,mode in CATEGORIES:
            if skip and app_running(skip): continue
            items,ct=[],0
            for p in paths:
                if not os.path.exists(p): continue
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm); s=path_size(fp); ct+=s; items.append((fp,s))
                else: s=path_size(p); ct+=s; items.append((p,s))
            if ct>0: found[cid]=(title,items,ct); total+=ct
        self.q.put(("smart",(found,total),None))

    def _render_smart(self, found, total):
        self.smart_found={c:v[1] for c,v in found.items()}
        self.smart_big.configure(text=human(total)); self.smart_sub.configure(text="можно освободить безопасно")
        for w in self.smart_list.winfo_children(): w.destroy()
        for cid,(title,items,ct) in sorted(found.items(), key=lambda x:-x[1][2]):
            r=tk.Frame(self.smart_list, bg=GLASS); r.pack(fill="x", padx=14, pady=5)
            tk.Label(r, text="🧩  "+title, bg=GLASS, fg=TEXT, font=("SF Pro Text",12), anchor="w").pack(side="left")
            tk.Label(r, text=human(ct), bg=GLASS, fg=GREEN, font=("SF Pro Text",12,"bold")).pack(side="right")
        if not found:
            tk.Label(self.smart_list, text="Чисто! Нечего освобождать.", bg=GLASS, fg=MUTED,
                     font=("SF Pro Text",13)).pack(anchor="w", padx=14, pady=14)

    def _smart_clean(self):
        if not self.smart_found: return
        tot=sum(s for items in self.smart_found.values() for _,s in items)
        if not messagebox.askyesno("Умная очистка", f"Переместить в Корзину ~{human(tot)}?"): return
        self.smart_big.configure(text="Очищаю…"); threading.Thread(target=self._smart_clean_w, daemon=True).start()

    def _smart_clean_w(self):
        freed=0
        for items in list(self.smart_found.values()):
            for fp,s in items:
                if to_trash(fp): freed+=s
        self.q.put(("smartdone", freed, None))

    # ================= АВТОПИЛОТ =================
    def show_autopilot(self):
        tk.Label(self.main, text=L("Автопилот"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text="Фоновый страж следит за памятью и при пике сам чистит и разгружает.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w", padx=24, pady=(0,14))
        card=tk.Frame(self.main, bg=GLASS); card.pack(fill="x", padx=24, pady=6)
        self.ap_state=tk.Label(card, text="…", bg=GLASS, fg=TEXT, font=("SF Pro Display",16,"bold"))
        self.ap_state.pack(side="left", padx=18, pady=18)
        self._btn(card, "Включить", GREEN, lambda: self._ap("start")).pack(side="right", padx=(8,18), pady=14)
        self._btn(card, "Выключить", RED, lambda: self._ap("stop")).pack(side="right", pady=14)
        row=tk.Frame(self.main, bg=BG0); row.pack(fill="x", padx=24, pady=8)
        self._btn(row, "⚡️ Оптимизировать сейчас", BLUE, self._optimize_now).pack(side="left")
        tk.Label(self.main, text="Журнал автопилота:", bg=BG0, fg=MUTED, font=("SF Pro Text",11)
                 ).pack(anchor="w", padx=24, pady=(10,2))
        self.ap_log=tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("SF Mono",11), relief="flat",
                            padx=12, pady=10); self.ap_log.pack(fill="both", expand=True, padx=24, pady=(0,16))
        self._ap_refresh()

    def _ap(self, action):
        ctl=os.path.join(OPT,"ctl.sh")
        if os.path.exists(ctl): run(["/bin/bash",ctl,action]); time.sleep(1)
        self._ap_refresh()

    def _ap_refresh(self):
        ctl=os.path.join(OPT,"ctl.sh"); st="недоступен"
        if os.path.exists(ctl):
            out=run(["/bin/bash",ctl,"status"]); st="🟢 РАБОТАЕТ" if "🟢" in out or "Работает" in out else "🔴 ОСТАНОВЛЕН"
        self.ap_state.configure(text="Автопилот: "+st, fg=(GREEN if "🟢" in st else RED))
        log=os.path.join(OPT,"optimize.log"); self.ap_log.configure(state="normal"); self.ap_log.delete("1.0","end")
        self.ap_log.insert("end", (open(log).read()[-2500:] if os.path.exists(log) else "(журнал пуст — пиков не было)"))
        self.ap_log.configure(state="disabled")

    def _optimize_now(self):
        threading.Thread(target=self._optimize_worker, daemon=True).start()

    def _optimize_worker(self):
        freed=0
        for cid,_,paths,skip,mode in CATEGORIES:
            if cid=="user_caches": continue
            if skip and app_running(skip): continue
            for p in paths:
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm); s=path_size(fp)
                        if to_trash(fp): freed+=s
                elif os.path.exists(p):
                    s=path_size(p)
                    if to_trash(p): freed+=s
        front=run(["osascript","-e",'tell application "System Events" to name of first process whose frontmost is true']).strip()
        for app in ("Microsoft Edge","Google Chrome","Safari","Yandex"):
            if app_running(app) and app!=front: run(["osascript","-e",f'quit app "{app}"'])
        self.q.put(("optimized", freed, None))

    # ================= ОЧИСТКА =================
    def show_cleaner(self):
        tk.Label(self.main, text=L("Очистка"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text="«Анализ» посчитает объём, «Очистить» переместит в Корзину.",
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
        hov=_lighten(color)
        b=tk.Label(parent, text="  "+text+"  ", bg=color, fg="white", font=("SF Pro Text",13,"bold"),
                   padx=14, pady=8, cursor="pointinghand")
        b.bind("<Enter>", lambda e: b.configure(bg=hov)); b.bind("<Leave>", lambda e: b.configure(bg=color))
        b.bind("<Button-1>", lambda e:cmd()); return b

    def run_analyze(self):
        self.total_lbl.configure(text="Анализирую…")
        for cid in self.cat_vars: self.cat_size_lbl[cid].configure(text="…")
        threading.Thread(target=self._analyze_worker, daemon=True).start()

    def _analyze_worker(self):
        self.found={}; total=0
        for cid,title,paths,skip,mode in CATEGORIES:
            if not self.cat_vars[cid].get(): self.q.put(("catsize",cid,None)); continue
            if skip and app_running(skip): self.q.put(("catsize",cid,"skip")); continue
            items,ct=[],0
            for p in paths:
                if not os.path.exists(p): continue
                if mode=="subitems" and os.path.isdir(p):
                    for nm in os.listdir(p):
                        fp=os.path.join(p,nm); s=path_size(fp); ct+=s; items.append((fp,s))
                else: s=path_size(p); ct+=s; items.append((p,s))
            self.found[cid]=items; total+=ct; self.q.put(("catsize",cid,ct))
        self.q.put(("total",total,None))

    def run_clean(self):
        sel=[c for c in self.cat_vars if self.cat_vars[c].get()]
        if not sel: messagebox.showinfo("CleanMac","Не выбрана категория."); return
        if not self.found: messagebox.showinfo("CleanMac","Сначала «Анализ»."); return
        if not messagebox.askyesno("Подтверждение","Переместить найденное в Корзину?"): return
        self.total_lbl.configure(text="Очищаю…"); threading.Thread(target=self._clean_worker,args=(sel,),daemon=True).start()

    def _clean_worker(self, sel):
        freed,moved=0,0
        for cid in sel:
            for fp,s in self.found.get(cid,[]):
                if to_trash(fp): freed+=s; moved+=1
        self.q.put(("cleaned",freed,moved))

    # ================= ИНСТРУМЕНТЫ (интерактивные) =================
    def show_tools(self):
        tk.Label(self.main, text=L("Инструменты"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,8))
        bar=tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=22)
        self.tool_chips={}
        for key,lbl in [("startup","⚙️ Автозагрузка"),("large","📦 Крупные файлы"),
                        ("dupes","👯 Дубликаты"),("uninstall","🧩 Деинсталлятор"),
                        ("disk","🗺 Карта диска"),("maintain","🩺 Обслуживание"),
                        ("shots","📸 Скриншоты"),
                        ("browsers","🌐 Браузеры"),("trash","♻️ Корзина")]:
            b=tk.Label(bar, text=lbl, bg=GLASS, fg=TEXT, font=("SF Pro Text",12), padx=11, pady=8, cursor="pointinghand")
            b.pack(side="left", padx=4); b.bind("<Button-1>", lambda e,k=key:self._tool(k)); self.tool_chips[key]=b
        self.tpanel=tk.Frame(self.main, bg=BG0); self.tpanel.pack(fill="both", expand=True, padx=22, pady=(10,14))
        self._lv=[]; self._tool("startup")

    def _tool(self, key):
        for k,b in self.tool_chips.items(): b.configure(bg=(BLUE if k==key else GLASS), fg=("white" if k==key else TEXT))
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        {"startup":self._t_startup,"large":self._t_large,"dupes":self._t_dupes,
         "uninstall":self._t_uninstall,"disk":self._t_disk,"maintain":self._t_maintain,
         "shots":self._t_shots,
         "browsers":self._t_browsers,"trash":self._t_trash}[key]()

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
        tk.Label(self.tpanel, text="🔎 Сканирую…", bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        threading.Thread(target=self._large_w, daemon=True).start()

    def _large_w(self):
        big,skip=[],{".Trash","Library"}
        for root,dirs,files in os.walk(HOME):
            parts=root.replace(HOME,"").strip("/").split("/")
            if parts and parts[0] in skip: dirs[:]=[]; continue
            for fn in files:
                try:
                    s=os.path.getsize(os.path.join(root,fn))
                    if s>100*1024*1024: big.append((s,os.path.join(root,fn)))
                except Exception: pass
        big.sort(reverse=True); self.q.put(("tool",("large",big[:60]),None))

    def _render_large(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._lv=[]
        self._ptitle("Крупные файлы", "Файлы крупнее 100 МБ. Отметьте лишние → в Корзину.")
        inner=self._scrollarea()
        for s,fp in rows: self._checkrow(inner, fp, fp.replace(HOME,"~"), s)
        if not rows: tk.Label(inner, text="  Ничего крупного не найдено.", bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
        self._actionbar(f"Найдено: {len(rows)} (~{human(sum(s for s,_ in rows))})",
                        lambda: self._trash_sel(lambda: self._tool('large')))

    # --- Дубликаты ---
    def _t_dupes(self):
        self._ptitle("Дубликаты", "Одинаковые файлы в Downloads/Desktop/Documents.")
        tk.Label(self.tpanel, text="🔎 Сканирую…", bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        threading.Thread(target=self._dupes_w, daemon=True).start()

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
        if not groups: tk.Label(inner, text="  Дубликатов не найдено.", bg=GLASS, fg=MUTED).pack(anchor="w", padx=8, pady=8)
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
                btn=tk.Label(r, text="Удалить…", bg=RED, fg="white", font=("SF Pro Text",10,"bold"),
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
                low=f.lower()
                if (bid and bid.lower() in low) or (len(name)>=4 and name.lower() in low):
                    targets.append(os.path.join(d,f))
        sizes=[(t,path_size(t)) for t in targets]; tot=sum(s for _,s in sizes)
        lines="\n".join(f"  {human(s):>8}  {t.replace(HOME,'~')}" for t,s in sizes)
        if not messagebox.askyesno("Удалить "+name, f"В Корзину уйдут (~{human(tot)}):\n\n{lines}\n\nПродолжить?"): return
        freed=sum(s for t,s in sizes if to_trash(t))
        messagebox.showinfo("CleanMac", f"{name}: в Корзину {human(freed)}."); self._tool("uninstall")

    # --- Карта диска ---
    def _t_disk(self):
        self._ptitle("Карта диска", "Крупнейшие папки в домашней директории.")
        tk.Label(self.tpanel, text="🔎 Считаю размеры…", bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
        threading.Thread(target=self._disk_w, daemon=True).start()

    def _disk_w(self):
        rows=[]
        for ln in run(["/usr/bin/du","-d","1","-k",HOME], 180).splitlines():
            try:
                kb,p=ln.split("\t",1)
                if p.rstrip("/")==HOME.rstrip("/"): continue
                rows.append((int(kb)*1024, p))
            except Exception: pass
        rows.sort(reverse=True); self.q.put(("disk", rows[:16], None))

    def _render_disk(self, rows):
        for w in self.tpanel.winfo_children(): w.destroy()
        self._ptitle("Карта диска", "Крупнейшие папки в ~. Клик по строке — открыть в Finder.")
        cv=tk.Canvas(self.tpanel, bg=GLASS, highlightthickness=0); cv.pack(fill="both", expand=True, pady=(4,8))
        mx=rows[0][0] if rows else 1
        pal=[BLUE,GREEN,PURPLE,YELLOW,CYAN,RED]
        def draw(e=None):
            cv.delete("all"); W=cv.winfo_width() or 600; y=14
            for i,(sz,p) in enumerate(rows):
                col=pal[i%len(pal)]; bw=max(6,(W-180)*sz/mx); tag=f"r{i}"
                self._round(cv, 150,y,150+bw,y+22,6, fill=col, outline=col, tags=tag)
                cv.create_text(12,y+11, anchor="w", fill=TEXT, font=("SF Pro Text",11),
                               text=p.replace(HOME,"~")[:26], tags=tag)
                cv.create_text(W-12,y+11, anchor="e", fill=MUTED, font=("SF Pro Text",11), text=human(sz), tags=tag)
                cv.tag_bind(tag,"<Button-1>", lambda e,pp=p: run(["/usr/bin/open",pp]))
                y+=30
            cv.configure(scrollregion=(0,0,W,y))
        cv.bind("<Configure>", draw); draw()

    # --- Обслуживание ---
    def _t_maintain(self):
        self._ptitle("Обслуживание", "Сервисные операции macOS. Для пунктов ★ потребуется пароль администратора.")
        acts=[("⚡️ Освободить память (purge) ★", "purge", True),
              ("🌐 Сбросить кэш DNS ★", "dscacheutil -flushcache; killall -HUP mDNSResponder", True),
              ("🔍 Переиндексировать Spotlight ★", "mdutil -E /", True),
              ("🔤 Очистить кэш шрифтов ★", "atsutil databases -remove", True),
              ("👁 Сбросить кэш Quick Look", "qlmanage -r cache", False),
              ("🧱 Перестроить Launch Services", "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user", False)]
        for label,cmd,admin in acts:
            b=tk.Label(self.tpanel, text=label, bg=GLASS, fg=TEXT, font=("SF Pro Text",12),
                       padx=12, pady=9, cursor="pointinghand", anchor="w")
            b.pack(fill="x", pady=3); b.bind("<Button-1>", lambda e,c=cmd,a=admin,l=label: self._maintain_run(l,c,a))
        self._mrez=tk.Label(self.tpanel, text="", bg=BG0, fg=MUTED, font=("SF Pro Text",12)); self._mrez.pack(anchor="w", pady=8)

    def _maintain_run(self, label, cmd, admin):
        self._mrez.configure(text="⏳ Выполняю: "+label.replace("★","").strip())
        threading.Thread(target=self._maintain_w, args=(label,cmd,admin), daemon=True).start()

    def _maintain_w(self, label, cmd, admin):
        try:
            if admin:
                esc=cmd.replace('"','\\"')
                run(["osascript","-e",f'do shell script "{esc}" with administrator privileges'], 180)
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
            tk.Label(inner, text="Скриншотов не найдено.", bg=GLASS, fg=MUTED,
                     font=("SF Pro Text",12)).pack(anchor="w", padx=10, pady=10)
        self._actionbar(f"Скриншотов: {n} · ~{human(total)} (старше 30 дн. отмечены)",
                        lambda: self._trash_sel(lambda: self._tool("shots")))

    # --- Браузеры / Корзина ---
    def _t_browsers(self):
        self._ptitle("Браузеры", "Закрыть фоновые браузеры для разгрузки памяти (активное окно не трогается).")
        self._btn(self.tpanel, "🌐 Закрыть фоновые браузеры", BLUE, self._do_browsers).pack(anchor="w", pady=8)
        self._brez=tk.Label(self.tpanel, text="", bg=BG0, fg=MUTED, font=("SF Pro Text",12)); self._brez.pack(anchor="w")

    def _do_browsers(self):
        front=run(["osascript","-e",'tell application "System Events" to name of first process whose frontmost is true']).strip()
        closed=[]
        for app in ("Microsoft Edge","Google Chrome","Safari","Yandex"):
            if app_running(app) and app!=front: run(["osascript","-e",f'quit app "{app}"']); closed.append(app)
        self._brez.configure(text=("Закрыты: "+", ".join(closed)) if closed else "Фоновых браузеров нет.")

    def _t_trash(self):
        sz=path_size(TRASH)
        self._ptitle("Корзина", f"Сейчас в Корзине ~{human(sz)}.")
        self._btn(self.tpanel, "♻️ Очистить Корзину (безвозвратно)", RED, self._do_trash).pack(anchor="w", pady=8)

    def _do_trash(self):
        sz=path_size(TRASH)
        if not messagebox.askyesno("Очистить Корзину", f"В Корзине ~{human(sz)}. Удалить безвозвратно?"): return
        run(["osascript","-e",'tell application "Finder" to empty the trash'])
        messagebox.showinfo("CleanMac","Запрошена очистка Корзины.")

    # ================= ПРИВАТНОСТЬ =================
    def show_privacy(self):
        tk.Label(self.main, text=L("Приватность"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text="Очистка следов работы → в Корзину (обратимо). Браузеры должны быть закрыты.",
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
        tk.Label(bar, text="Отметьте, что очистить", bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(side="left")
        self._btn(bar, "🗑 Очистить выбранное", PURPLE, self._pv_clean).pack(side="right")
        threading.Thread(target=self._pv_scan, daemon=True).start()

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
        tk.Label(self.main, text=L("Защита"), bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,2))
        tk.Label(self.main, text="Эвристический поиск известного рекламного/нежелательного ПО в точках автозапуска. Не заменяет антивирус.",
                 bg=BG0, fg=MUTED, font=("SF Pro Text",11), wraplength=640, justify="left").pack(anchor="w", padx=24, pady=(0,8))
        self.th_box=tk.Frame(self.main, bg=BG0); self.th_box.pack(fill="both", expand=True, padx=24, pady=(4,14))
        tk.Label(self.th_box, text="🔎 Сканирую точки автозапуска…", bg=BG0, fg=MUTED, font=("SF Pro Text",12)).pack(anchor="w")
        self.th_found=[]
        threading.Thread(target=self._threats_scan, daemon=True).start()

    def _threats_scan(self):
        findings=[]
        for loc in (os.path.join(HOME,"Library/LaunchAgents"),"/Library/LaunchAgents","/Library/LaunchDaemons"):
            if not os.path.isdir(loc): continue
            try: names=os.listdir(loc)
            except Exception: continue
            for f in names:
                p=os.path.join(loc,f); low=f.lower(); content=""
                try:
                    with open(p,"r",errors="ignore") as fh: content=fh.read().lower()
                except Exception: pass
                for tok in ADWARE:
                    if tok in low or tok in content:
                        findings.append((p, f"автозапуск · «{tok}»")); break
        for base in ("/Applications", os.path.join(HOME,"Applications")):
            if not os.path.isdir(base): continue
            for f in os.listdir(base):
                low=f.lower()
                for tok in ADWARE:
                    if tok in low: findings.append((os.path.join(base,f), f"приложение · «{tok}»")); break
        self.q.put(("threats", findings, None))

    def _render_threats(self, findings):
        for w in self.th_box.winfo_children(): w.destroy()
        self.th_found=[]
        if not findings:
            tk.Label(self.th_box, text="✅ Угроз не обнаружено", bg=BG0, fg=GREEN,
                     font=("SF Pro Display",17,"bold")).pack(anchor="w", pady=10)
            tk.Label(self.th_box, text="Проверены LaunchAgents, LaunchDaemons и папки приложений.",
                     bg=BG0, fg=MUTED, font=("SF Pro Text",11)).pack(anchor="w")
            return
        tk.Label(self.th_box, text=f"⚠️ Подозрительных объектов: {len(findings)}", bg=BG0, fg=YELLOW,
                 font=("SF Pro Display",15,"bold")).pack(anchor="w", pady=(0,6))
        wrap=tk.Frame(self.th_box, bg=GLASS); wrap.pack(fill="both", expand=True)
        for p,reason in findings:
            r=tk.Frame(wrap, bg=GLASS); r.pack(fill="x", padx=10, pady=2)
            v=tk.BooleanVar(value=True)
            tk.Checkbutton(r, variable=v, bg=GLASS, selectcolor=BG0, activebackground=GLASS, bd=0, highlightthickness=0).pack(side="left")
            tk.Label(r, text=reason, bg=GLASS, fg=YELLOW, font=("SF Pro Text",10), anchor="e").pack(side="right", padx=6)
            tk.Label(r, text=p.replace(HOME,"~"), bg=GLASS, fg=TEXT, font=("SF Pro Text",11), anchor="w").pack(side="left", fill="x", expand=True)
            self.th_found.append((v,p))
        bar=tk.Frame(self.th_box, bg=BG0); bar.pack(fill="x", pady=(6,0))
        self._btn(bar, "🗑 Удалить выбранное (в Корзину)", RED, self._threats_remove).pack(side="right")

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
                     "Распространяется как нотаризованный .dmg и через Homebrew",
                     "(не App Store — песочница не позволяет чистильщикам быть в MAS)."]:
            tk.Label(self.main, text=line, bg=BG0, fg=(TEXT if line.startswith("•") else MUTED),
                     font=("SF Pro Text",12), justify="left").pack(anchor="w", padx=24)
        row=tk.Frame(self.main, bg=BG0); row.pack(anchor="w", padx=24, pady=16)
        if not self.is_pro:
            self._btn(row,"⭐️ Купить Pro",PURPLE, lambda: run(["/usr/bin/open",BUY_URL])).pack(side="left", padx=(0,8))
        self._btn(row,"Проверить обновления",BLUE, lambda: threading.Thread(target=self._check_update,args=(True,),daemon=True).start()).pack(side="left", padx=(0,8))
        self._btn(row,"GitHub",GLASS_HI, lambda: run(["/usr/bin/open",f"https://github.com/{REPO}"])).pack(side="left")
        self._btn(row, ("🌐 EN" if LANG=="ru" else "🌐 RU"), GREEN,
                  lambda: self.set_lang("en" if LANG=="ru" else "ru")).pack(side="left", padx=(8,0))
        self._btn(row, ("☀️ Светлая" if THEME=="dark" else "🌙 Тёмная"), PURPLE,
                  lambda: self.set_theme("light" if THEME=="dark" else "dark")).pack(side="left", padx=(8,0))

    # ---------- обновления ----------
    def _check_update(self, manual=False):
        import ssl
        url=f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
        req=urllib.request.Request(url, headers={"User-Agent":"CleanMac"})
        latest=None
        # сначала с проверкой сертификата; для замороженной сборки без CA — fallback
        contexts=[None]
        try:
            import certifi; contexts.append(ssl.create_default_context(cafile=certifi.where()))
        except Exception: pass
        contexts.append(ssl._create_unverified_context())
        for ctx in contexts:
            try:
                kw={"timeout":6}
                if ctx is not None: kw["context"]=ctx
                latest=urllib.request.urlopen(req, **kw).read().decode().strip()
                if latest: break
            except Exception:
                continue
        if latest and latest!=VERSION:
            self.q.put(("update", f"⬆️ Доступна версия {latest} (у вас {VERSION})", None))
        elif latest and manual:
            self.q.put(("update", f"✅ Установлена последняя версия {VERSION}", None))
        elif manual:
            self.q.put(("update", "Не удалось проверить обновления (нет сети).", None))

    # ---------- сэмплер ----------
    def _sampler(self):
        while True:
            cpu=stat_cpu(); ram=stat_mem(); sused,_=stat_swap()
            disk,dfree,dtot=stat_disk(); vm=stat_vm(); batt=stat_batt(); procs=stat_procs()
            swap_sev=min(100, sused/8192*100)
            health=(0.30*(100-ram)+0.20*(100-swap_sev)+0.20*(100-disk)+0.15*(100-cpu)+0.15*(batt["health"] or 100))
            self.q.put(("stats", {"cpu":cpu,"ram":ram,"swap":swap_sev,"swap_mb":sused,"disk":disk,
                        "health":health,"batt":batt,"procs":procs,"vm":vm,"dfree":dfree,"dtot":dtot}, None))
            time.sleep(1.4)

    def _animate(self):
        if self.page=="dash" and hasattr(self,"cv") and self.cv.winfo_exists():
            for k in self.disp: self.disp[k]+=(self.tgt[k]-self.disp[k])*0.22
            self._draw_dash()
        self.after(33, self._animate)

    # ---------- очередь ----------
    def _poll(self):
        try:
            while True:
                kind,a,b=self.q.get_nowait()
                if kind=="stats":
                    self.tgt.update({"cpu":a["cpu"],"ram":a["ram"],"swap":a["swap"],"disk":a["disk"],
                                     "health":a["health"],"batt":a["batt"]["pct"]})
                    self.swap_mb=a["swap_mb"]; self.batt=a["batt"]; self.procs=a["procs"]; self.vm=a["vm"]
                    self.disk_free=a["dfree"]; self.disk_total=a["dtot"]
                    self.cpu_hist.append(a["cpu"]); self.ram_hist.append(a["ram"])
                    self.status(f'Здоровье {int(a["health"])} · CPU {int(a["cpu"])}% · ОЗУ {int(a["ram"])}% · бат {a["batt"]["pct"]}%')
                    self._maybe_alert(a["disk"], a["batt"].get("health", 100))
                elif kind=="catsize":
                    lbl=self.cat_size_lbl.get(a)
                    if lbl: lbl.configure(text=("—" if a is None else "пропуск" if b=="skip" else ("—" if b is None else human(b))))
                elif kind=="total": self.total_lbl.configure(text=f"Найдено: {human(a)}")
                elif kind=="cleaned":
                    self.total_lbl.configure(text=f"Очищено: {human(a)} ({b}) → Корзина")
                    messagebox.showinfo("CleanMac", f"В Корзину: {human(a)} ({b} объектов)."); self.found={}
                elif kind=="optimized":
                    messagebox.showinfo("CleanMac", f"Оптимизация выполнена.\nОсвобождено кэша: {human(a)}.")
                    if self.page=="autopilot": self._ap_refresh()
                elif kind=="tool" and self.page=="tools":
                    sub,data=a
                    if sub=="large": self._render_large(data)
                    elif sub=="dupes": self._render_dupes(data)
                elif kind=="disk" and self.page=="tools": self._render_disk(a)
                elif kind=="maintdone":
                    try: self._mrez.configure(text="✅ Готово: "+a.replace("★","").strip())
                    except Exception: pass
                elif kind=="privacy" and self.page=="privacy": self._render_privacy(a)
                elif kind=="threats" and self.page=="threats": self._render_threats(a)
                elif kind=="smart" and self.page=="smart": self._render_smart(*a)
                elif kind=="smartdone":
                    messagebox.showinfo("CleanMac", f"Освобождено: {human(a)} → Корзина.")
                    if self.page=="smart": self.nav("smart")
                elif kind=="update":
                    self.update_note=a; self.badge.configure(text=a if a.startswith("⬆️") else "")
                    if self.page=="pro": self.nav("pro")
        except queue.Empty: pass
        except Exception: pass
        self.after(120, self._poll)


if __name__ == "__main__":
    CleanMac().mainloop()
