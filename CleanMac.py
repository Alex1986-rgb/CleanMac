#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CleanMac 2.0 — оптимизатор для macOS со «стеклянным» интерфейсом.
Дашборд с диаграммами, автопилот, очистка в Корзину, инструменты,
проверка обновлений (GitHub) и Pro-каркас. Запуск: framework-python 3.12.
"""
import os, time, shutil, hashlib, threading, queue, subprocess, collections, math, re, json
import urllib.request
import tkinter as tk
from tkinter import messagebox

VERSION = "2.0.0"
REPO    = "Alex1986-rgb/CleanMac"          # для проверки обновлений
BUY_URL = "https://alex1986-rgb.gumroad.com/l/cleanmac"   # ссылка на Pro (заглушка)
HOME  = os.path.expanduser("~")
TRASH = os.path.join(HOME, ".Trash")
OPT   = os.path.join(HOME, "mac-optimizer")
CFG   = os.path.join(HOME, ".config", "cleanmac")
LIC   = os.path.join(CFG, "license")

# ---------- палитра «тёмное стекло» ----------
BG0, BG1 = "#11151d", "#1b2330"     # градиент фона
SIDEBAR  = "#0e1219"
GLASS    = "#222b3a"                 # карточка
GLASS_HI = "#2b3647"
TRACK    = "#333d4e"
TEXT     = "#eef2f8"
MUTED    = "#8a94a6"
GREEN, BLUE, YELLOW, RED, PURPLE, CYAN = "#37d39a", "#4b8cf9", "#f6bb45", "#f2685f", "#a78bfa", "#36c6d6"

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

def path_size(p):
    if not os.path.exists(p): return 0
    try: return int(run(["/usr/bin/du", "-sk", p], 60).split("\t")[0]) * 1024
    except Exception: return 0

def app_running(name):
    return name.lower() in run(["/bin/ps", "-axo", "comm"]).lower()

def to_trash(path):
    if not os.path.exists(path): return False
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
]


class CleanMac(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CleanMac")
        self.geometry("1000x720"); self.minsize(960, 680)
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
        self.cat_vars={}; self.cat_size_lbl={}; self.found={}
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
        tk.Label(self.side, text="  🧹 CleanMac", bg=SIDEBAR, fg=TEXT,
                 font=("SF Pro Display", 19, "bold")).pack(anchor="w", pady=(22,0), padx=12)
        tk.Label(self.side, text=f"  v{VERSION} · оптимизатор", bg=SIDEBAR, fg=MUTED,
                 font=("SF Pro Text", 10)).pack(anchor="w", padx=12, pady=(0,18))
        self.nav_btns = {}
        for key,label in [("dash","📊  Дашборд"),("autopilot","🚀  Автопилот"),
                          ("cleaner","🧽  Очистка"),("tools","🛠  Инструменты"),("pro","⭐️  Pro / О программе")]:
            b = tk.Label(self.side, text="   "+label, bg=SIDEBAR, fg=TEXT, font=("SF Pro Text", 13),
                         anchor="w", padx=10, pady=12, cursor="pointinghand")
            b.pack(fill="x"); b.bind("<Button-1>", lambda e,k=key: self.nav(k)); self.nav_btns[key]=b
        self.badge = tk.Label(self.side, text="", bg=SIDEBAR, fg=YELLOW, font=("SF Pro Text", 11, "bold"),
                              wraplength=184, justify="left"); self.badge.pack(side="bottom", fill="x", padx=12, pady=(0,6))
        self.statusbar = tk.Label(self.side, text="", bg=SIDEBAR, fg=MUTED, font=("SF Pro Text", 10),
                                  wraplength=184, justify="left"); self.statusbar.pack(side="bottom", fill="x", padx=12, pady=4)
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    def nav(self, key):
        self.page = key
        for k,b in self.nav_btns.items(): b.configure(bg=GLASS if k==key else SIDEBAR)
        for w in self.main.winfo_children(): w.destroy()
        {"dash":self.show_dash,"autopilot":self.show_autopilot,"cleaner":self.show_cleaner,
         "tools":self.show_tools,"pro":self.show_pro}[key]()

    def status(self,t): self.statusbar.configure(text=t)

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
        tk.Label(self.main, text="Дашборд", bg=BG0, fg=TEXT, font=("SF Pro Display", 22, "bold")
                 ).pack(anchor="w", padx=24, pady=(16,0))
        tk.Label(self.main, text="Состояние системы в реальном времени", bg=BG0, fg=MUTED,
                 font=("SF Pro Text", 11)).pack(anchor="w", padx=24, pady=(0,6))
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=14, pady=(0,12))

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

    # ================= АВТОПИЛОТ =================
    def show_autopilot(self):
        tk.Label(self.main, text="Автопилот", bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
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
        tk.Label(self.main, text="Очистка", bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
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
        self.total_lbl=tk.Label(bar, text="Готово к анализу", bg=BG0, fg=TEXT, font=("SF Pro Text",13,"bold")); self.total_lbl.pack(side="left")
        self._btn(bar,"Очистить",GREEN,self.run_clean).pack(side="right", padx=(8,0))
        self._btn(bar,"Анализ",BLUE,self.run_analyze).pack(side="right")

    def _btn(self, parent, text, color, cmd):
        b=tk.Label(parent, text="  "+text+"  ", bg=color, fg="white", font=("SF Pro Text",13,"bold"),
                   padx=14, pady=8, cursor="pointinghand"); b.bind("<Button-1>", lambda e:cmd()); return b

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

    # ================= ИНСТРУМЕНТЫ =================
    def show_tools(self):
        tk.Label(self.main, text="Инструменты", bg=BG0, fg=TEXT, font=("SF Pro Display",22,"bold")
                 ).pack(anchor="w", padx=24, pady=(16,10))
        btns=tk.Frame(self.main, bg=BG0); btns.pack(fill="x", padx=20)
        tools=[("⚙️ Автозагрузка",self.tool_startup),("📦 Крупные файлы (>100 МБ)",self.tool_large),
               ("👯 Дубликаты",self.tool_dupes),("🌐 Закрыть фоновые браузеры",self.tool_browsers),
               ("🗑 Очистить Корзину",self.tool_trash)]
        for i,(lbl,cmd) in enumerate(tools):
            b=tk.Label(btns, text=lbl, bg=GLASS, fg=TEXT, font=("SF Pro Text",12), padx=12, pady=10, cursor="pointinghand")
            b.grid(row=i//2, column=i%2, sticky="ew", padx=6, pady=6); b.bind("<Button-1>", lambda e,c=cmd:c())
        btns.grid_columnconfigure(0, weight=1); btns.grid_columnconfigure(1, weight=1)
        self.out=tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("SF Mono",11), relief="flat", padx=12, pady=10)
        self.out.pack(fill="both", expand=True, padx=24, pady=14)
        self.out.insert("end","Выберите инструмент выше.\n"); self.out.configure(state="disabled")

    def _o(self,t,clear=True):
        self.out.configure(state="normal")
        if clear: self.out.delete("1.0","end")
        self.out.insert("end",t); self.out.configure(state="disabled")

    def tool_startup(self):
        self._o("⚙️  Автозагрузка\n\nЭлементы входа (Login Items):\n")
        li=run(["osascript","-e",'tell application "System Events" to get the name of every login item']).strip()
        self._o(("  "+li if li else "  (пусто)")+"\n", clear=False)
        la=os.path.join(HOME,"Library/LaunchAgents"); self._o("\nLaunchAgents:\n", clear=False)
        if os.path.isdir(la):
            for f in sorted(os.listdir(la)):
                self._o(f'  {"🟢" if f.endswith(".plist") else "⚪️ выкл"}  {f}\n', clear=False)

    def tool_large(self):
        self._o("📦  Поиск файлов >100 МБ…"); threading.Thread(target=self._large_w, daemon=True).start()

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
        big.sort(reverse=True)
        t="📦  Крупные файлы (топ-30):\n\n"+"".join(f"  {human(s):>9}  {fp.replace(HOME,'~')}\n" for s,fp in big[:30])
        self.q.put(("textout", t or "  пусто\n", None))

    def tool_dupes(self):
        self._o("👯  Поиск дубликатов в Downloads/Desktop/Documents…"); threading.Thread(target=self._dupes_w, daemon=True).start()

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
                if len(same)>1: groups.append((s,same))
        groups.sort(reverse=True); wasted=sum(s*(len(g)-1) for s,g in groups)
        t=f"👯  Групп: {len(groups)}, освободить ~{human(wasted)}\n\n"
        for s,same in groups[:20]:
            t+=f"  {human(s)} ×{len(same)}:\n"+"".join(f"      {p.replace(HOME,'~')}\n" for p in same)+"\n"
        self.q.put(("textout", t if groups else "  дубликатов нет.\n", None))

    @staticmethod
    def _hash(fp):
        try:
            h=hashlib.md5()
            with open(fp,"rb") as f:
                for b in iter(lambda:f.read(1<<20), b""): h.update(b)
            return h.hexdigest()
        except Exception: return None

    def tool_browsers(self):
        front=run(["osascript","-e",'tell application "System Events" to name of first process whose frontmost is true']).strip()
        closed=[]
        for app in ("Microsoft Edge","Google Chrome","Safari","Yandex"):
            if app_running(app) and app!=front: run(["osascript","-e",f'quit app "{app}"']); closed.append(app)
        self._o("🌐  "+("Закрыты: "+", ".join(closed) if closed else "Фоновых браузеров нет.")+"\n")

    def tool_trash(self):
        sz=path_size(TRASH)
        if not messagebox.askyesno("Очистить Корзину", f"В Корзине ~{human(sz)}. Удалить безвозвратно?"): return
        run(["osascript","-e",'tell application "Finder" to empty the trash']); self._o(f"🗑  Запрошена очистка Корзины (~{human(sz)}).\n")

    # ================= PRO / О ПРОГРАММЕ =================
    def show_pro(self):
        tk.Label(self.main, text="CleanMac", bg=BG0, fg=TEXT, font=("SF Pro Display",26,"bold")
                 ).pack(anchor="w", padx=24, pady=(24,2))
        tk.Label(self.main, text=f"Версия {VERSION}" + ("  ·  ⭐️ Pro активна" if self.is_pro else "  ·  Free"),
                 bg=BG0, fg=(GREEN if self.is_pro else MUTED), font=("SF Pro Text",12,"bold")).pack(anchor="w", padx=24)
        if self.update_note:
            tk.Label(self.main, text=self.update_note, bg=BG0, fg=YELLOW, font=("SF Pro Text",12,"bold")).pack(anchor="w", padx=24, pady=(8,0))
        for line in ["", "Оптимизатор для macOS со «стеклянным» интерфейсом.", "",
                     "• Дашборд: диаграммы, батарея, процессы в реальном времени",
                     "• Автопилот: фоновая чистка и разгрузка памяти при пиках",
                     "• Очистка кэшей/логов → в Корзину (обратимо)",
                     "• Инструменты: автозагрузка, крупные файлы, дубликаты", "",
                     "Распространяется как нотаризованный .dmg (не App Store —",
                     "ограничения песочницы не позволяют чистильщикам быть в MAS)."]:
            tk.Label(self.main, text=line, bg=BG0, fg=(TEXT if line.startswith("•") else MUTED),
                     font=("SF Pro Text",12), justify="left").pack(anchor="w", padx=24)
        row=tk.Frame(self.main, bg=BG0); row.pack(anchor="w", padx=24, pady=16)
        if not self.is_pro:
            self._btn(row,"⭐️ Купить Pro",PURPLE, lambda: run(["/usr/bin/open",BUY_URL])).pack(side="left", padx=(0,8))
        self._btn(row,"Проверить обновления",BLUE, lambda: threading.Thread(target=self._check_update,args=(True,),daemon=True).start()).pack(side="left", padx=(0,8))
        self._btn(row,"GitHub",GLASS_HI, lambda: run(["/usr/bin/open",f"https://github.com/{REPO}"])).pack(side="left")

    # ---------- обновления ----------
    def _check_update(self, manual=False):
        try:
            url=f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
            req=urllib.request.Request(url, headers={"User-Agent":"CleanMac"})
            latest=urllib.request.urlopen(req, timeout=6).read().decode().strip()
            if latest and latest!=VERSION:
                self.q.put(("update", f"⬆️ Доступна версия {latest} (у вас {VERSION})", None))
            elif manual:
                self.q.put(("update", f"✅ Установлена последняя версия {VERSION}", None))
        except Exception:
            if manual: self.q.put(("update", "Не удалось проверить обновления (нет сети/репозитория).", None))

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
                elif kind=="textout": self._o(a)
                elif kind=="update":
                    self.update_note=a; self.badge.configure(text=a if a.startswith("⬆️") else "")
                    if self.page=="pro": self.nav("pro")
        except queue.Empty: pass
        except Exception: pass
        self.after(120, self._poll)


if __name__ == "__main__":
    CleanMac().mainloop()
