#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN Desktop — кросс-платформенный оптимизатор: Windows · macOS · Linux.
«Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
Зависимости: psutil, send2trash.  Запуск: python krylan.py
"""
import os, sys, platform, threading, queue, math, hashlib
import tkinter as tk
from tkinter import messagebox
import psutil
from send2trash import send2trash

VERSION = "1.3.0"
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

def trash_dir():
    if SYSTEM == "Darwin": return os.path.join(HOME, ".Trash")
    if SYSTEM == "Linux":  return os.path.join(HOME, ".local/share/Trash/files")
    return None   # Windows: корзина доступна только через WinAPI

def old_downloads(days=180):
    """Файлы и папки в Загрузках старше N дней: [(size, path)]."""
    import time
    base = os.path.join(HOME, "Downloads")
    out, cutoff = [], time.time() - days * 86400
    if os.path.isdir(base):
        for name in os.listdir(base):
            fp = os.path.join(base, name)
            try:
                if os.path.getmtime(fp) < cutoff:
                    sz = dir_size(fp) if os.path.isdir(fp) else os.path.getsize(fp)
                    out.append((sz, fp))
            except Exception: pass
    out.sort(reverse=True)
    return out

def find_duplicates(bases=None):
    """Точные дубликаты (размер → md5) в пользовательских папках.
    Возвращает (groups, extras, wasted)."""
    bases = bases or [os.path.join(HOME, d) for d in ("Downloads", "Desktop", "Documents")]
    by_size = {}
    for base in bases:
        if not os.path.isdir(base): continue
        for root, _, files in os.walk(base):
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    s = os.path.getsize(fp)
                    if s > 1024*1024: by_size.setdefault(s, []).append(fp)
                except Exception: pass
    groups, extras = [], []
    for s, paths in by_size.items():
        if len(paths) < 2: continue
        bh = {}
        for fp in paths:
            try:
                h = hashlib.md5(open(fp, "rb").read()).hexdigest()
                bh.setdefault(h, []).append(fp)
            except Exception: pass
        for same in bh.values():
            if len(same) > 1:
                groups.append((s, sorted(same))); extras.extend(sorted(same)[1:])
    groups.sort(reverse=True)
    wasted = sum(s*(len(g)-1) for s, g in groups)
    return groups, extras, wasted

# ---------- headless-очистка (для планировщика) ----------
def clean_caches_headless(dry=False):
    """Содержимое кэшей → Корзина. Возвращает (байт, строки отчёта)."""
    freed, lines = 0, []
    for name, p in cleanup_targets():
        sz = dir_size(p); freed += sz
        lines.append(f"  {name}: {human(sz)}")
        if not dry:
            for n in os.listdir(p):
                try: send2trash(os.path.join(p, n))
                except Exception: pass
    return freed, lines

# ---------- планировщик обслуживания ----------
SCHED_LABEL = "com.krylan.desktop.clean"

def _sched_cmd():
    return [sys.executable, os.path.abspath(__file__), "--clean-caches"]

def schedule_status():
    import subprocess
    try:
        if SYSTEM == "Darwin":
            return os.path.isfile(os.path.join(HOME, "Library/LaunchAgents", SCHED_LABEL + ".plist"))
        if SYSTEM == "Linux":
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            return "KRYLAN-CLEAN" in (r.stdout or "")
        r = subprocess.run(["schtasks", "/Query", "/TN", "KRYLAN Clean"], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False

def schedule_enable():
    """Еженедельная авто-очистка кэшей (понедельник 12:00). Всё уходит в Корзину."""
    import subprocess
    cmd = _sched_cmd()
    if SYSTEM == "Darwin":
        args = "".join(f"<string>{c}</string>" for c in cmd)
        plist = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                 f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                 f'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                 f'<plist version="1.0"><dict>'
                 f'<key>Label</key><string>{SCHED_LABEL}</string>'
                 f'<key>ProgramArguments</key><array>{args}</array>'
                 f'<key>StartCalendarInterval</key><dict>'
                 f'<key>Weekday</key><integer>1</integer>'
                 f'<key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer>'
                 f'</dict></dict></plist>')
        path = os.path.join(HOME, "Library/LaunchAgents", SCHED_LABEL + ".plist")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(plist)
        subprocess.run(["launchctl", "load", path], capture_output=True)
    elif SYSTEM == "Linux":
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        cur = r.stdout if r.returncode == 0 else ""
        line = f'0 12 * * 1 {" ".join(cmd)} # KRYLAN-CLEAN'
        if "KRYLAN-CLEAN" not in cur:
            subprocess.run(["crontab", "-"], input=cur.rstrip("\n") + "\n" + line + "\n", text=True)
    else:
        subprocess.run(["schtasks", "/Create", "/F", "/SC", "WEEKLY", "/D", "MON",
                        "/ST", "12:00", "/TN", "KRYLAN Clean",
                        "/TR", " ".join(f'"{c}"' for c in cmd)], capture_output=True)

def schedule_disable():
    import subprocess
    if SYSTEM == "Darwin":
        path = os.path.join(HOME, "Library/LaunchAgents", SCHED_LABEL + ".plist")
        subprocess.run(["launchctl", "unload", path], capture_output=True)
        try: os.remove(path)
        except OSError: pass
    elif SYSTEM == "Linux":
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if r.returncode == 0:
            keep = "\n".join(l for l in r.stdout.splitlines() if "KRYLAN-CLEAN" not in l)
            subprocess.run(["crontab", "-"], input=keep + "\n", text=True)
    else:
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", "KRYLAN Clean"], capture_output=True)


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
        for key, label in [("dash","📊  Дашборд"),("scan","🚀  Сканер"),("procs","🧠  Процессы"),("clean","🧽  Очистка"),("tools","🛠  Инструменты"),("about","ℹ️  О программе")]:
            b = tk.Label(side, text="   "+label, bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 12), anchor="w", padx=10, pady=11, cursor="hand2")
            b.pack(fill="x"); b.bind("<Button-1>", lambda e,k=key: self.nav(k)); self.nav_btns[key] = b
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    def nav(self, key):
        self.page = key
        for k,b in self.nav_btns.items(): b.configure(bg=GLASS if k==key else SIDEBAR)
        for w in self.main.winfo_children(): w.destroy()
        {"dash":self.show_dash, "scan":self.show_scan, "procs":self.show_procs, "clean":self.show_clean, "tools":self.show_tools, "about":self.show_about}[key]()

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
        c.create_rectangle(20,150,W-20,282, fill=GLASS, outline=GLASS)
        info = [f"ОС: {self.info.get('os','—')}",
                f"Диск: свободно {human(self.info.get('disk_free',0))} из {human(self.info.get('disk_total',0))}",
                f"ОЗУ: {human(self.info.get('ram_total',0))} всего, занято {int(self.disp['ram'])}%",
                f"CPU: {self.info.get('cores','?')} ядер",
                f"Сеть: ↓ {human(self.info.get('net_down',0))}/с   ↑ {human(self.info.get('net_up',0))}/с"]
        for i,line in enumerate(info):
            c.create_text(40,173+i*22, anchor="w", fill=TEXT, font=("Segoe UI", 11), text=line)
        c.configure(scrollregion=(0,0,W,300))

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

    # ---------- сканер (one-click, в духе BoostSpeed My Scanner) ----------
    def show_scan(self):
        tk.Label(self.main, text="Сканер", bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text="Полная проверка одним кликом: кэши · корзина · старые загрузки · дубликаты.",
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,10))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24)
        self._btn(bar, "🚀 Сканировать всё", GREEN, self.run_scan).pack(side="left")
        # планировщик
        self.sched_lbl = tk.Label(bar, text="", bg=BG0, fg=MUTED, font=("Segoe UI", 10)); self.sched_lbl.pack(side="right")
        self.sched_btn = tk.Label(bar, text="", bg=GLASS, fg=TEXT, font=("Segoe UI", 10, "bold"),
                                  padx=10, pady=6, cursor="hand2")
        self.sched_btn.pack(side="right", padx=(0,10))
        self.sched_btn.bind("<Button-1>", lambda e: self._sched_toggle())
        self._sched_refresh()
        self.s_action = tk.Frame(self.main, bg=BG0); self.s_action.pack(fill="x", padx=24, pady=(8,0))
        self.sout = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 11), relief="flat", padx=12, pady=10)
        self.sout.pack(fill="both", expand=True, padx=24, pady=12)
        self.sout.insert("end", "Нажмите «Сканировать всё».\n"); self.sout.configure(state="disabled")

    def _sched_refresh(self):
        on = schedule_status()
        self.sched_btn.configure(text=("⏰ Выключить авто-очистку" if on else "⏰ Включить авто-очистку"),
                                 bg=(GLASS if on else BLUE), fg=("white" if not on else TEXT))
        self.sched_lbl.configure(text=("еженедельно, пн 12:00 · кэши → Корзина" if on else ""))

    def _sched_toggle(self):
        if schedule_status():
            schedule_disable()
        else:
            if not messagebox.askyesno("KRYLAN", "Включить еженедельную авто-очистку кэшей?\n"
                                       "Каждый понедельник в 12:00 содержимое кэшей будет уходить в Корзину."): return
            schedule_enable()
        self._sched_refresh()

    def run_scan(self):
        self._sout("🚀 Сканирую… это может занять минуту-другую.")
        threading.Thread(target=self._scan_w, daemon=True).start()

    def _sout(self, t):
        self.sout.configure(state="normal"); self.sout.delete("1.0","end"); self.sout.insert("end", t); self.sout.configure(state="disabled")
        for w in self.s_action.winfo_children(): w.destroy()

    def _scan_w(self):
        res = {}
        caches = [(n, p, dir_size(p)) for n, p in cleanup_targets()]
        res["caches"] = caches; csum = sum(s for _,_,s in caches)
        td = trash_dir(); res["trash"] = dir_size(td) if td else None
        old = old_downloads(); res["old"] = old; osum = sum(s for s,_ in old)
        groups, extras, wasted = find_duplicates(); res["extras"] = extras
        total = csum + osum + wasted + (res["trash"] or 0)
        lines = ["🚀  Результат сканирования\n\n", "Кэши и временные файлы:\n"]
        lines += [f"  {human(s):>9}  {n}\n" for n, p, s in caches]
        lines.append(f"\nКорзина: {human(res['trash']) if res['trash'] is not None else '—'}\n")
        lines.append(f"Старые загрузки (>6 мес): {human(osum)} · {len(old)} шт.\n")
        for s, fp in old[:8]: lines.append(f"  {human(s):>9}  {fp.replace(HOME,'~')}\n")
        lines.append(f"Дубликаты: {human(wasted)} в {len(groups)} группах\n")
        lines.append(f"\n══════════════════════════════════\n")
        lines.append(f"ИТОГО можно освободить: ~{human(total)}\n")
        self.q.put(("scanout", "".join(lines), res))

    def _scan_actions(self, res):
        if sum(s for _,_,s in res["caches"]) > 0:
            self._btn(self.s_action, "🧽 Кэши → Корзина", GREEN,
                      lambda: self._scan_clean_caches()).pack(side="left", padx=(0,6))
        if res["old"]:
            self._btn(self.s_action, f"📥 Старые загрузки → Корзина ({len(res['old'])})", BLUE,
                      lambda o=res["old"]: self._scan_trash_old(o)).pack(side="left", padx=6)
        if res["extras"]:
            self._btn(self.s_action, f"👯 Дубли → Корзина ({len(res['extras'])})", PURPLE,
                      lambda ex=res["extras"]: self._trash_dupes_scan(ex)).pack(side="left", padx=6)

    def _scan_clean_caches(self):
        if not messagebox.askyesno("KRYLAN", "Переместить содержимое кэшей в Корзину?"): return
        self._sout("🧽 Очищаю кэши…")
        def w():
            freed, _ = clean_caches_headless()
            self.q.put(("scanout", f"🧽 Кэши очищены: ~{human(freed)} → Корзина.\n\nЗапустите сканирование заново для свежей сводки.", None))
        threading.Thread(target=w, daemon=True).start()

    def _scan_trash_old(self, old):
        if not messagebox.askyesno("KRYLAN", f"Переместить {len(old)} старых файлов из Загрузок в Корзину?"): return
        ok = 0
        for s, fp in old:
            try: send2trash(fp); ok += 1
            except Exception: pass
        messagebox.showinfo("KRYLAN", f"В Корзину: {ok} файлов."); self.run_scan()

    def _trash_dupes_scan(self, extras):
        if not messagebox.askyesno("KRYLAN", f"Удалить {len(extras)} лишних копий в Корзину?"): return
        ok = 0
        for p in extras:
            try: send2trash(p); ok += 1
            except Exception: pass
        messagebox.showinfo("KRYLAN", f"В Корзину: {ok} файлов."); self.run_scan()

    # ---------- процессы (диспетчер задач) ----------
    def show_procs(self):
        tk.Label(self.main, text="Процессы", bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text="Топ по памяти. «Завершить» закрывает выбранный процесс.", bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,8))
        head = tk.Frame(self.main, bg=BG0); head.pack(fill="x", padx=26)
        tk.Label(head, text="Процесс", bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), anchor="w", width=28).pack(side="left")
        tk.Label(head, text="ОЗУ", bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), width=10).pack(side="left")
        tk.Label(head, text="CPU", bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), width=8).pack(side="left")
        self.proc_box = tk.Frame(self.main, bg=GLASS); self.proc_box.pack(fill="both", expand=True, padx=24, pady=(4,14))
        self._procs_refresh()

    def _procs_refresh(self):
        if self.page != "procs" or not self.proc_box.winfo_exists(): return
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
            try:
                rss = p.info["memory_info"].rss if p.info["memory_info"] else 0
                rows.append((rss, p.info.get("cpu_percent") or 0, p.info["pid"], p.info["name"] or "?"))
            except Exception: pass
        rows.sort(reverse=True)
        for w in self.proc_box.winfo_children(): w.destroy()
        for rss, cpu, pid, name in rows[:14]:
            r = tk.Frame(self.proc_box, bg=GLASS); r.pack(fill="x", padx=8, pady=1)
            tk.Label(r, text=name[:30], bg=GLASS, fg=TEXT, font=("Segoe UI", 11), anchor="w", width=28).pack(side="left")
            tk.Label(r, text=human(rss), bg=GLASS, fg=MUTED, font=("Segoe UI", 10), width=10).pack(side="left")
            tk.Label(r, text=f"{cpu:.0f}%", bg=GLASS, fg=load_color(min(100, cpu)), font=("Segoe UI", 10), width=7).pack(side="left")
            b = tk.Label(r, text="Завершить", bg=RED, fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
            b.pack(side="right"); b.bind("<Button-1>", lambda e, pp=pid, nn=name: self._kill_proc(pp, nn))
        self.after(2500, self._procs_refresh)

    def _kill_proc(self, pid, name):
        if not messagebox.askyesno("KRYLAN", f"Завершить процесс «{name}» (PID {pid})?"): return
        try:
            psutil.Process(pid).terminate()
        except Exception as e:
            messagebox.showerror("KRYLAN", f"Не удалось завершить: {e}")
        self._procs_refresh()

    # ---------- инструменты (в духе BoostSpeed) ----------
    def show_tools(self):
        tk.Label(self.main, text="Инструменты", bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,8))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=22)
        for lbl, cmd in [("⚙️ Автозагрузка", self.t_startup), ("👯 Дубликаты", self.t_dupes), ("📦 Крупные файлы", self.t_large),
                         ("🗺 Карта диска", self.t_diskmap), ("🧳 Деинсталлятор", self.t_uninstall)]:
            self._btn(bar, lbl, GLASS, cmd).pack(side="left", padx=4)
        self._dupe_extras = []
        self.t_action = tk.Frame(self.main, bg=BG0); self.t_action.pack(fill="x", padx=24, pady=(8,0))
        self.tout = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 11), relief="flat", padx=12, pady=10)
        self.tout.pack(fill="both", expand=True, padx=24, pady=12)
        self.tout.insert("end", "Выберите инструмент.\n"); self.tout.configure(state="disabled")

    def _out(self, t):
        self.tout.configure(state="normal"); self.tout.delete("1.0","end"); self.tout.insert("end", t); self.tout.configure(state="disabled")
        for w in self.t_action.winfo_children(): w.destroy()

    def t_startup(self):
        self._out("⚙️ Сканирую автозагрузку…"); threading.Thread(target=self._startup_w, daemon=True).start()

    def _startup_w(self):
        lines = ["⚙️  Автозагрузка\n\n"]
        if SYSTEM == "Windows":
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                i = 0
                while True:
                    try:
                        n, v, _ = winreg.EnumValue(k, i); lines.append(f"  • {n}\n      {v}\n"); i += 1
                    except OSError: break
            except Exception as e:
                lines.append(f"  ошибка чтения реестра: {e}\n")
            lines.append("\nОтключить: Диспетчер задач → вкладка «Автозагрузка».\n")
        elif SYSTEM == "Darwin":
            la = os.path.join(HOME, "Library/LaunchAgents")
            for f in (sorted(os.listdir(la)) if os.path.isdir(la) else []): lines.append(f"  • {f}\n")
            lines.append("\nОтключить: переименуйте .plist → .plist.disabled.\n")
        else:
            ad = os.path.join(HOME, ".config/autostart")
            for f in (sorted(os.listdir(ad)) if os.path.isdir(ad) else []): lines.append(f"  • {f}\n")
            lines.append("\nОтключить: удалите .desktop из ~/.config/autostart.\n")
        self.q.put(("tout", "".join(lines), None))

    def t_large(self):
        self._out("📦 Ищу файлы >100 МБ…"); threading.Thread(target=self._large_w, daemon=True).start()

    def _large_w(self):
        big, skip = [], {"Library", "AppData", ".cache"}
        for root, dirs, files in os.walk(HOME):
            parts = root.replace(HOME, "").strip(os.sep).split(os.sep)
            if parts and parts[0] in skip: dirs[:] = []; continue
            for fn in files:
                try:
                    s = os.path.getsize(os.path.join(root, fn))
                    if s > 100*1024*1024: big.append((s, os.path.join(root, fn)))
                except Exception: pass
        big.sort(reverse=True)
        t = "📦  Крупные файлы (топ-25):\n\n" + "".join(f"  {human(s):>9}  {fp.replace(HOME,'~')}\n" for s, fp in big[:25])
        self.q.put(("tout", t or "  ничего\n", None))

    def t_dupes(self):
        self._out("👯 Ищу дубликаты…"); threading.Thread(target=self._dupes_w, daemon=True).start()

    def _dupes_w(self):
        groups, extras, wasted = find_duplicates()
        t = f"👯  Дубликаты: групп {len(groups)}, освободить ~{human(wasted)}\n\n"
        for s, same in groups[:20]:
            t += f"  {human(s)} ×{len(same)}:\n" + "".join(f"      {p.replace(HOME,'~')}\n" for p in same) + "\n"
        self.q.put(("dupes", t if groups else "  дубликатов нет.\n", extras))

    def _trash_dupes(self, extras):
        if not extras or not messagebox.askyesno("KRYLAN", f"Удалить {len(extras)} лишних копий в Корзину?"): return
        ok = 0
        for p in extras:
            try: send2trash(p); ok += 1
            except Exception: pass
        messagebox.showinfo("KRYLAN", f"В Корзину: {ok} файлов."); self.t_dupes()

    def t_diskmap(self):
        self._out("🗺 Считаю размеры папок…"); threading.Thread(target=self._diskmap_w, daemon=True).start()

    def _diskmap_w(self):
        sizes = []
        try:
            for name in sorted(os.listdir(HOME)):
                p = os.path.join(HOME, name)
                if os.path.isdir(p) and not os.path.islink(p):
                    sizes.append((dir_size(p), name))
        except Exception: pass
        sizes.sort(reverse=True)
        top = sizes[:18]
        mx = top[0][0] if top and top[0][0] > 0 else 1
        lines = ["🗺  Карта диска — домашняя папка (топ-18):\n\n"]
        for s, name in top:
            bar = "█" * max(1, int(s / mx * 28))
            lines.append(f"  {human(s):>9}  {bar}  {name}\n")
        lines.append("\nСамые тяжёлые папки — кандидаты на разбор в «Крупные файлы».\n")
        self.q.put(("tout", "".join(lines), None))

    def t_uninstall(self):
        self._out("🧳 Собираю список приложений…"); threading.Thread(target=self._uninstall_w, daemon=True).start()

    def _uninstall_w(self):
        lines = ["🧳  Деинсталлятор — установленные приложения\n\n"]
        if SYSTEM == "Windows":
            try:
                import winreg
                apps = []
                for hive, path in [(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                                   (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")]:
                    try:
                        k = winreg.OpenKey(hive, path)
                        for i in range(winreg.QueryInfoKey(k)[0]):
                            try:
                                sk = winreg.OpenKey(k, winreg.EnumKey(k, i))
                                name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                try: size, _ = winreg.QueryValueEx(sk, "EstimatedSize")
                                except OSError: size = 0
                                apps.append((int(size or 0) * 1024, name))
                            except OSError: pass
                    except OSError: pass
                apps.sort(reverse=True)
                for s, n in apps[:30]:
                    lines.append(f"  {human(s):>9}  {n}\n" if s else f"      —      {n}\n")
                lines.append("\nУдаление: Параметры → Приложения → выбрать → «Удалить».\n")
            except Exception as e:
                lines.append(f"  ошибка чтения реестра: {e}\n")
        elif SYSTEM == "Darwin":
            apps = []
            for base in ("/Applications", os.path.join(HOME, "Applications")):
                if not os.path.isdir(base): continue
                for name in sorted(os.listdir(base)):
                    if name.endswith(".app"):
                        apps.append((dir_size(os.path.join(base, name)), name[:-4]))
            apps.sort(reverse=True)
            for s, n in apps[:30]:
                lines.append(f"  {human(s):>9}  {n}\n")
            lines.append("\nУдаление: перетащите .app из «Программ» в Корзину\n"
                         "(остатки ищите в ~/Library/Application Support и Caches).\n")
        else:
            import subprocess
            try:
                out = subprocess.run(["dpkg-query", "-W", "-f", "${Installed-Size}\t${Package}\n"],
                                     capture_output=True, text=True, timeout=20)
                apps = []
                for line in out.stdout.splitlines():
                    try:
                        sz, name = line.split("\t", 1)
                        apps.append((int(sz) * 1024, name))
                    except ValueError: pass
                apps.sort(reverse=True)
                for s, n in apps[:30]:
                    lines.append(f"  {human(s):>9}  {n}\n")
                lines.append("\nУдаление: sudo apt remove <пакет>.\n")
            except Exception:
                lines.append("  dpkg не найден — посмотрите менеджер пакетов вашего дистрибутива.\n")
        self.q.put(("tout", "".join(lines), None))

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
        try: prev, prev_t = psutil.net_io_counters(), time.time()
        except Exception: prev, prev_t = None, time.time()
        while True:
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                ram = psutil.virtual_memory().percent
                du = psutil.disk_usage(HOME if SYSTEM != "Windows" else os.environ.get("SystemDrive", "C:") + "\\")
                b = psutil.sensors_battery()
                up = down = 0
                try:
                    cur = psutil.net_io_counters(); now = time.time(); dt = max(0.2, now - prev_t)
                    if prev: up = (cur.bytes_sent - prev.bytes_sent)/dt; down = (cur.bytes_recv - prev.bytes_recv)/dt
                    prev, prev_t = cur, now
                except Exception: pass
                self.q.put(("stats", {"cpu":cpu,"ram":ram,"disk":du.percent,
                            "batt": (b.percent if b else None),
                            "disk_free": du.free, "disk_total": du.total,
                            "net_up": max(0,up), "net_down": max(0,down)}, None))
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
                    self.info["net_up"]=a.get("net_up",0); self.info["net_down"]=a.get("net_down",0)
                    self.info["os"] = self.info.get("os","")
                elif kind == "clsize":
                    if a in self.cl_lbl: self.cl_lbl[a].configure(text=human(b))
                elif kind == "cltotal": self.cl_total.configure(text=f"Найдено: {human(a)}")
                elif kind == "cldone":
                    self.cl_total.configure(text=f"Очищено: {human(a)} → Корзина")
                    messagebox.showinfo("KRYLAN", f"В Корзину: {human(a)}."); self.found = {}
                elif kind == "tout":
                    if self.page == "tools": self._out(a)
                elif kind == "scanout":
                    if self.page == "scan":
                        self._sout(a)
                        if b: self._scan_actions(b)
                elif kind == "dupes":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, f"🗑 Удалить {len(b)} лишних копий", RED,
                                      lambda ex=b: self._trash_dupes(ex)).pack(side="left", pady=4)
        except queue.Empty: pass
        except Exception: pass
        self.after(120, self._poll)


if __name__ == "__main__":
    if "--clean-caches" in sys.argv:
        # headless-режим для планировщика: кэши → Корзина, отчёт в stdout
        dry = "--dry-run" in sys.argv
        freed, lines = clean_caches_headless(dry=dry)
        print(("[dry-run] " if dry else "") + f"KRYLAN: кэшей ~{human(freed)}" +
              (" (ничего не удалено)" if dry else " → Корзина"))
        print("\n".join(lines))
        sys.exit(0)
    Krylan().mainloop()
