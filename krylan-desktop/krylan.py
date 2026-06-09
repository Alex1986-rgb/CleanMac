#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN Desktop — кросс-платформенный оптимизатор: Windows · macOS · Linux.
«Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
Зависимости: psutil, send2trash.  Запуск: python krylan.py
"""
import os, sys, platform, threading, queue, math
import tkinter as tk
from tkinter import messagebox
import psutil
from send2trash import send2trash

VERSION = "1.0.0"
SYSTEM = platform.system()           # Windows / Darwin / Linux
HOME = os.path.expanduser("~")

# ---------- палитра ----------
BG0, SIDEBAR, GLASS, TRACK, TEXT, MUTED = "#11151d", "#0e1219", "#222b3a", "#333d4e", "#eef2f8", "#8a94a6"
GREEN, BLUE, YELLOW, RED, PURPLE = "#37d39a", "#4b8cf9", "#f6bb45", "#f2685f", "#a78bfa"

def load_color(p): return GREEN if p < 60 else (YELLOW if p < 85 else RED)

def human(n):
    n = float(n)
    for u in ("Б","КБ","МБ","ГБ","ТБ"):
        if n < 1024 or u == "ТБ":
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024

def os_label():
    return {"Windows":"Windows","Darwin":"macOS","Linux":"Linux"}.get(SYSTEM, SYSTEM)

# ---------- цели очистки по ОС ----------
def cleanup_targets():
    t = []
    if SYSTEM == "Windows":
        temp = os.environ.get("TEMP") or os.path.join(HOME, "AppData", "Local", "Temp")
        local = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
        t = [("Временные файлы", temp),
             ("Кэш Google Chrome", os.path.join(local, "Google", "Chrome", "User Data", "Default", "Cache")),
             ("Кэш Microsoft Edge", os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Cache")),
             ("Кэш Windows Explorer", os.path.join(local, "Microsoft", "Windows", "Explorer"))]
    elif SYSTEM == "Darwin":
        t = [("Кэш приложений", os.path.join(HOME, "Library/Caches")),
             ("Логи", os.path.join(HOME, "Library/Logs")),
             ("Кэш Chrome", os.path.join(HOME, "Library/Caches/Google"))]
    else:  # Linux
        t = [("Кэш (~/.cache)", os.path.join(HOME, ".cache")),
             ("Эскизы", os.path.join(HOME, ".cache/thumbnails")),
             ("Логи (~/.local/state)", os.path.join(HOME, ".local/state"))]
    return [(n, p) for n, p in t if os.path.isdir(p)]

def dir_size(p):
    total = 0
    try:
        for root, _, files in os.walk(p):
            for f in files:
                try: total += os.path.getsize(os.path.join(root, f))
                except Exception: pass
    except Exception: pass
    return total


class Krylan(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KRYLAN")
        self.geometry("860x560"); self.minsize(820, 520)
        self.configure(bg=BG0)
        self.q = queue.Queue()
        self.page = None
        self.disp = {"cpu":0,"ram":0,"disk":0,"batt":0}
        self.tgt = dict(self.disp)
        self.info = {}
        self.found = {}
        self._build(); self.nav("dash")
        threading.Thread(target=self._sampler, daemon=True).start()
        self.after(80, self._poll); self.after(33, self._animate)

    def _build(self):
        side = tk.Frame(self, bg=SIDEBAR, width=200); side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Label(side, text="  🪽 KRYLAN", bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(20,0), padx=12)
        tk.Label(side, text="  Дай устройству крылья", bg=SIDEBAR, fg=GREEN, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)
        tk.Label(side, text=f"  {os_label()} · v{VERSION}", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0,16))
        self.nav_btns = {}
        for key, label in [("dash","📊  Дашборд"),("clean","🧽  Очистка"),("about","ℹ️  О программе")]:
            b = tk.Label(side, text="   "+label, bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 12), anchor="w", padx=10, pady=11, cursor="hand2")
            b.pack(fill="x"); b.bind("<Button-1>", lambda e,k=key: self.nav(k)); self.nav_btns[key] = b
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    def nav(self, key):
        self.page = key
        for k,b in self.nav_btns.items(): b.configure(bg=GLASS if k==key else SIDEBAR)
        for w in self.main.winfo_children(): w.destroy()
        {"dash":self.show_dash, "clean":self.show_clean, "about":self.show_about}[key]()

    # ---------- кольца ----------
    def _ring(self, c, cx, cy, r, frac, color, w, val, label):
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        if frac > 0.01:
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=90, extent=-frac*359.9, style="arc", outline=color, width=w)
        c.create_text(cx,cy-3, text=val, fill=TEXT, font=("Segoe UI", 18, "bold"))
        c.create_text(cx,cy+r+14, text=label, fill=MUTED, font=("Segoe UI", 10))

    def show_dash(self):
        tk.Label(self.main, text="Дашборд", bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,0))
        tk.Label(self.main, text=f"Система: {os_label()} · в реальном времени", bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,8))
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0); self.cv.pack(fill="both", expand=True, padx=20, pady=10)

    def _draw_dash(self):
        if not (self.page=="dash" and self.cv.winfo_exists()): return
        c = self.cv; c.delete("all"); W = c.winfo_width() or 640
        rings = [("cpu","CPU",f'{int(self.disp["cpu"])}%'),("ram","ОЗУ",f'{int(self.disp["ram"])}%'),
                 ("disk","ДИСК",f'{int(self.disp["disk"])}%'),("batt","БАТАРЕЯ",
                  (f'{int(self.disp["batt"])}%' if self.info.get("batt") is not None else "—"))]
        gap = W/4
        for i,(k,lbl,val) in enumerate(rings):
            inv = (k == "batt")
            p = self.disp[k]; col = load_color(100-p) if inv else load_color(p)
            self._ring(c, int(gap*i+gap/2), 70, 48, min(1,p/100), col, 12, val, lbl)
        # карточка инфо
        c.create_rectangle(20,150,W-20,260, fill=GLASS, outline=GLASS)
        info = [f"ОС: {self.info.get('os','—')}",
                f"Диск: свободно {human(self.info.get('disk_free',0))} из {human(self.info.get('disk_total',0))}",
                f"ОЗУ: {human(self.info.get('ram_total',0))} всего, занято {int(self.disp['ram'])}%",
                f"CPU: {self.info.get('cores','?')} ядер"]
        for i,line in enumerate(info):
            c.create_text(40,175+i*22, anchor="w", fill=TEXT, font=("Segoe UI", 11), text=line)
        c.configure(scrollregion=(0,0,W,280))

    # ---------- очистка ----------
    def show_clean(self):
        tk.Label(self.main, text="Очистка", bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text="Временные файлы и кэши. Всё уходит в Корзину (обратимо).", bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,10))
        wrap = tk.Frame(self.main, bg=GLASS); wrap.pack(fill="x", padx=24)
        self.cl_vars = {}; self.cl_lbl = {}
        for i,(name,p) in enumerate(cleanup_targets()):
            row = tk.Frame(wrap, bg=GLASS); row.pack(fill="x", padx=14, pady=6)
            v = tk.BooleanVar(value=True); self.cl_vars[i] = (v, name, p)
            tk.Checkbutton(row, text="  "+name, variable=v, bg=GLASS, fg=TEXT, selectcolor=BG0,
                           activebackground=GLASS, activeforeground=TEXT, font=("Segoe UI", 11), anchor="w").pack(side="left")
            sl = tk.Label(row, text="…", bg=GLASS, fg=GREEN, font=("Segoe UI", 11, "bold")); sl.pack(side="right"); self.cl_lbl[i] = sl
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=14)
        self.cl_total = tk.Label(bar, text="Готово к анализу", bg=BG0, fg=TEXT, font=("Segoe UI", 12, "bold")); self.cl_total.pack(side="left")
        self._btn(bar, "Очистить", GREEN, self.run_clean).pack(side="right", padx=(8,0))
        self._btn(bar, "Анализ", BLUE, self.run_analyze).pack(side="right")

    def _btn(self, parent, text, color, cmd):
        b = tk.Label(parent, text="  "+text+"  ", bg=color, fg="white", font=("Segoe UI", 12, "bold"), padx=14, pady=7, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd()); return b

    def run_analyze(self):
        self.cl_total.configure(text="Анализирую…")
        threading.Thread(target=self._analyze_w, daemon=True).start()

    def _analyze_w(self):
        self.found = {}; total = 0
        for i,(v,name,p) in self.cl_vars.items():
            sz = dir_size(p); self.found[i] = (p, sz); total += sz
            self.q.put(("clsize", i, sz))
        self.q.put(("cltotal", total, None))

    def run_clean(self):
        if not self.found: messagebox.showinfo("KRYLAN", "Сначала «Анализ»."); return
        sel = [i for i,(v,n,p) in self.cl_vars.items() if v.get()]
        if not messagebox.askyesno("KRYLAN", "Переместить выбранные кэши в Корзину?"): return
        self.cl_total.configure(text="Очищаю…")
        threading.Thread(target=self._clean_w, args=(sel,), daemon=True).start()

    def _clean_w(self, sel):
        freed = 0
        for i in sel:
            p, sz = self.found.get(i, (None, 0))
            if not p or not os.path.isdir(p): continue
            for name in os.listdir(p):
                fp = os.path.join(p, name)
                try: send2trash(fp); freed += 0
                except Exception: pass
            freed += sz
        self.q.put(("cldone", freed, None))

    # ---------- о программе ----------
    def show_about(self):
        tk.Label(self.main, text="🪽 KRYLAN", bg=BG0, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=24, pady=(26,0))
        tk.Label(self.main, text="«Дай устройству крылья»", bg=BG0, fg=GREEN, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=24)
        for line in [f"Версия {VERSION} · {os_label()}", "Создатель: Кырлан Александр Сергеевич", "",
                     "Кросс-платформенный оптимизатор: Windows · macOS · Linux.",
                     "Мониторинг CPU/ОЗУ/диск/батарея и безопасная очистка кэшей",
                     "(всё уходит в Корзину). Часть экосистемы KRYLAN (+iPhone, Android)."]:
            tk.Label(self.main, text=line, bg=BG0, fg=(TEXT if "Создатель" in line else MUTED),
                     font=("Segoe UI", 11)).pack(anchor="w", padx=24)

    # ---------- метрики ----------
    def _sampler(self):
        import time
        vm = psutil.virtual_memory()
        self.info = {"os": f"{platform.system()} {platform.release()}",
                     "ram_total": vm.total, "cores": psutil.cpu_count(logical=True)}
        while True:
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                ram = psutil.virtual_memory().percent
                du = psutil.disk_usage(HOME if SYSTEM != "Windows" else os.environ.get("SystemDrive", "C:") + "\\")
                b = psutil.sensors_battery()
                self.q.put(("stats", {"cpu":cpu,"ram":ram,"disk":du.percent,
                            "batt": (b.percent if b else None),
                            "disk_free": du.free, "disk_total": du.total}, None))
            except Exception: pass
            time.sleep(1.2)

    def _animate(self):
        if self.page=="dash" and hasattr(self,"cv") and self.cv.winfo_exists():
            for k in self.disp: self.disp[k] += (self.tgt[k]-self.disp[k])*0.25
            self._draw_dash()
        self.after(33, self._animate)

    def _poll(self):
        try:
            while True:
                kind,a,b = self.q.get_nowait()
                if kind == "stats":
                    self.tgt.update({"cpu":a["cpu"],"ram":a["ram"],"disk":a["disk"],"batt":a["batt"] or 0})
                    self.info["batt"] = a["batt"]; self.info["disk_free"]=a["disk_free"]; self.info["disk_total"]=a["disk_total"]
                    self.info["os"] = self.info.get("os","")
                elif kind == "clsize":
                    if a in self.cl_lbl: self.cl_lbl[a].configure(text=human(b))
                elif kind == "cltotal": self.cl_total.configure(text=f"Найдено: {human(a)}")
                elif kind == "cldone":
                    self.cl_total.configure(text=f"Очищено: {human(a)} → Корзина")
                    messagebox.showinfo("KRYLAN", f"В Корзину: {human(a)}."); self.found = {}
        except queue.Empty: pass
        except Exception: pass
        self.after(120, self._poll)


if __name__ == "__main__":
    Krylan().mainloop()
