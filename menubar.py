#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN — мини-монитор в строке меню macOS.
Показывает CPU/ОЗУ/батарею; меню: открыть CleanMac, освободить память, выход.
Запуск: /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 menubar.py
Зависимость: rumps (pip install rumps).
"""
import os, re, subprocess, rumps

HOME = os.path.expanduser("~")

def run(cmd, t=5):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout
    except Exception: return ""

def cpu_pct():
    for ln in run(["/usr/bin/top", "-l", "1", "-n", "0"]).splitlines():
        if ln.startswith("CPU usage"):
            p = ln.replace("CPU usage:", "").split(",")
            try: return min(100, float(p[0].split("%")[0]) + float(p[1].split("%")[0].strip()))
            except Exception: return 0
    return 0

def ram_used():
    for ln in run(["memory_pressure"]).splitlines():
        if "free percentage" in ln:
            try: return 100 - float(ln.split(":")[1].strip().rstrip("%"))
            except Exception: return 0
    return 0

def batt():
    for ln in run(["pmset", "-g", "batt"]).splitlines():
        m = re.search(r"(\d+)%", ln)
        if m: return int(m.group(1))
    return 0


class KrylanBar(rumps.App):
    def __init__(self):
        super().__init__("🪽", quit_button=None)
        self.menu = ["Открыть CleanMac", "Освободить память", "Обновить", None, "KRYLAN · Выход"]
        self.timer = rumps.Timer(self.refresh, 3)
        self.timer.start()
        self.refresh(None)

    def refresh(self, _):
        c, r, b = cpu_pct(), ram_used(), batt()
        self.title = f"🪽 {int(c)}% · {int(r)}% · {b}%"
        # подсказка в первом пункте меню
        self.menu["Обновить"].title = f"CPU {int(c)}% · ОЗУ {int(r)}% · Батарея {b}%"

    @rumps.clicked("Открыть CleanMac")
    def open_app(self, _):
        subprocess.Popen(["/usr/bin/open", os.path.join(HOME, "Applications/CleanMac.app")])

    @rumps.clicked("Освободить память")
    def purge(self, _):
        subprocess.Popen(["osascript", "-e",
                          'do shell script "purge" with administrator privileges'])
        rumps.notification("KRYLAN", "Освобождение памяти", "Запрошен purge (нужен пароль).")

    @rumps.clicked("Обновить")
    def upd(self, _):
        self.refresh(None)

    @rumps.clicked("KRYLAN · Выход")
    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    KrylanBar().run()
