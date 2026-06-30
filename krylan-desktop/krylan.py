#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN Desktop — кросс-платформенный оптимизатор: Windows · macOS · Linux.
«Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
Зависимости: psutil, send2trash.  Запуск: python krylan.py
"""
import os, sys, platform, threading, queue, math, hashlib, json, random, time, atexit
import tkinter as tk
from tkinter import messagebox, filedialog
import psutil
from send2trash import send2trash

# Общий модуль экосистемы (единый источник истины для human/load_color).
# Рядом лежит вендорная копия (krylan_core.py) — этого достаточно для
# standalone-сборки (PyInstaller подхватит её автоматически). При запуске из
# дерева репозитория предпочитаем корневой оригинал, чтобы логика не расходилась.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import krylan_core

VERSION = "1.18.0"
SYSTEM = platform.system()           # Windows / Darwin / Linux
HOME = os.path.expanduser("~")

# ---------- палитра: navy HUD (как в macOS CleanMac) ----------
# Глубокий навигационный синий с неоновыми акцентами. Тёмная тема для всего UI;
# фон дашборда рисуется радиальным свечением (см. _grad), поэтому BG0 — его край.
BG0, SIDEBAR, GLASS, TRACK, TEXT, MUTED = "#091327", "#0a1426", "#102444", "#22436f", "#e4eefb", "#7088b2"
GREEN, BLUE, YELLOW, RED, PURPLE = "#2fe5a0", "#2f8fff", "#ffd60a", "#ff5a52", "#a98bff"
CYAN = "#36d6ff"

def _blend(h1, h2, t):
    """Линейная интерполяция двух hex-цветов (#rrggbb) в hex. t∈[0,1]."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    a = (int(h1[1:3],16), int(h1[3:5],16), int(h1[5:7],16))
    b = (int(h2[1:3],16), int(h2[3:5],16), int(h2[5:7],16))
    return "#%02x%02x%02x" % tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def load_color(p): return krylan_core.load_color(p, GREEN, YELLOW, RED)

def col_for(p, inv=False):
    """Цвет HUD-гейджа по значению 0..100. inv=True — где БОЛЬШЕ это хорошо
    (здоровье, батарея); иначе хорошо МАЛЕНЬКОЕ (загрузка cpu/ram/disk)."""
    v = p if inv else 100 - p
    return GREEN if v >= 50 else YELLOW if v >= 25 else RED

human = krylan_core.human

# ---------- локализация RU/EN ----------
LANG_FILE = os.path.join(HOME, ".krylan_lang")
def _load_lang():
    try:
        v = open(LANG_FILE).read().strip()
        return v if v in ("ru", "en") else "ru"
    except Exception:
        return "ru"
LANG = _load_lang()

I18N = {
    "Дай устройству крылья": "Give your device wings",
    "Дашборд": "Dashboard", "Сканер": "Scanner", "Процессы": "Processes",
    "Очистка": "Cleanup", "Инструменты": "Tools", "О программе": "About",
    "Автопилот": "Autopilot",
    "🟢 Автопилот работает": "🟢 Autopilot running",
    "🔴 Автопилот остановлен": "🔴 Autopilot stopped",
    "Включить": "Enable", "Выключить": "Disable",
    "⚡ Оптимизировать сейчас": "⚡ Optimize now",
    "Порог памяти, %": "Memory threshold, %",
    "Интервал проверки, с": "Check interval, s",
    "  Разрешить закрывать фоновые браузеры при пике памяти":
        "  Allow closing background browsers on memory spikes",
    "  Запускать страж автоматически при входе в систему":
        "  Start the guardian automatically at login",
    "Журнал автопилота:": "Autopilot log:",
    "🚀 Ускорить — очистить и разгрузить": "🚀 Boost — clean & free up", "🔍 Сканировать": "🔍 Scan",
    "🚀 Сканировать всё": "🚀 Scan everything", "Анализ": "Analyze", "Очистить": "Clean",
    "Система: {os} · в реальном времени": "System: {os} · real-time",
    "⚙️ Автозагрузка": "⚙️ Startup", "👯 Дубликаты": "👯 Duplicates",
    "📦 Крупные файлы": "📦 Large files", "🗺 Карта диска": "🗺 Disk map",
    "🧳 Деинсталлятор": "🧳 Uninstaller", "📂 Пустые папки": "📂 Empty folders",
    "📈 Что выросло": "📈 What grew", "🔒 Приватность": "🔒 Privacy", "🩺 Диск": "🩺 Disk",
    "🧩 Расширения браузеров": "🧩 Browser extensions",
    "🧩 Читаю расширения браузеров…": "🧩 Reading browser extensions…",
    "🧩  Расширения браузеров (только просмотр)": "🧩  Browser extensions (read-only)",
    "  расширений не найдено.\n": "  no extensions found.\n",
    "Всего расширений: {n}.": "Total extensions: {n}.",
    "KRYLAN ничего не удаляет. Отключить лишние можно в самом браузере: меню → «Расширения».":
        "KRYLAN deletes nothing. You can disable unwanted ones in the browser itself: menu → “Extensions”.",
    "РЕКОМЕНДАЦИИ": "RECOMMENDATIONS",
    "ОЗУ": "RAM", "ДИСК": "DISK", "БАТАРЕЯ": "BATTERY",
    "ОС: {os}": "OS: {os}",
    "Диск: свободно {free} из {total}": "Disk: {free} free of {total}",
    "ОЗУ: {total} всего, занято {pct}%": "RAM: {total} total, {pct}% used",
    "CPU: {cores} ядер": "CPU: {cores} cores",
    "Сеть: ↓ {down}/с   ↑ {up}/с": "Network: ↓ {down}/s   ↑ {up}/s",
    "Готово к анализу": "Ready to analyze", "Анализ": "Analyze",
    "Топ по памяти. «Завершить» закрывает выбранный процесс.":
        "Top by memory. “End” closes the selected process.",
    "Завершить": "End",
    "Полная проверка одним кликом: кэши · корзина · старые загрузки · дубликаты.":
        "Full one-click check: caches · trash · old downloads · duplicates.",
    "Временные файлы и кэши. Всё уходит в Корзину (обратимо).":
        "Temporary files and caches. Everything goes to Trash (reversible).",
    # --- инструменты (кнопки) ---
    "🖼 Похожие фото": "🖼 Similar photos", "🧩 Битые файлы": "🧩 Broken files",
    "🔄 Обновления": "🔄 Updates", "📄 Отчёт": "📄 Report",
    # --- контекстное меню Проводника (Windows) ---
    "🖱 Контекстное меню": "🖱 Context menu",
    "🖱 Читаю контекстное меню Проводника…": "🖱 Reading Explorer context menu…",
    "🖱  Контекстное меню Проводника": "🖱  Explorer context menu",
    "Только Windows.": "Windows only.",
    "Этот инструмент читает пункты меню Проводника из реестра "
    "Windows (HKCR) и обратимо показывает/скрывает их флагом "
    "LegacyDisable. На macOS/Linux он недоступен.":
        "This tool reads Explorer menu items from the Windows registry (HKCR) "
        "and reversibly shows/hides them with the LegacyDisable flag. "
        "It is unavailable on macOS/Linux.",
    "(нет пунктов)": "(no items)",
    "включён": "enabled", "выключен": "disabled",
    "только просмотр": "read-only",
    "«выключить» добавляет обратимый флаг LegacyDisable "
    "(ключ реестра НЕ удаляется); «включить» снимает его. "
    "Хендлеры (shellex) показаны только для просмотра.":
        "“disable” adds a reversible LegacyDisable flag "
        "(the registry key is NOT deleted); “enable” removes it. "
        "Handlers (shellex) are shown for viewing only.",
    "🚫 {verb}": "🚫 {verb}", "✓ {verb}": "✓ {verb}",
    "Скрыть пункт «{verb}» из контекстного меню?\n(обратимо: флаг LegacyDisable)":
        "Hide item “{verb}” from the context menu?\n(reversible: LegacyDisable flag)",
    "Показать пункт «{verb}» в контекстном меню?\n(снять флаг LegacyDisable)":
        "Show item “{verb}” in the context menu?\n(remove the LegacyDisable flag)",
    "Нужны права администратора для изменения этого пункта.":
        "Administrator rights are required to change this item.",
    "Не удалось изменить пункт: {e}": "Could not change the item: {e}",
    # --- сканер ---
    "Нажмите «Сканировать всё».": "Press “Scan everything”.",
    "⏰ Выключить авто-очистку": "⏰ Disable auto-clean",
    "⏰ Включить авто-очистку": "⏰ Enable auto-clean",
    "еженедельно, пн 12:00 · кэши → Корзина": "weekly, Mon 12:00 · caches → Trash",
    "Включить еженедельную авто-очистку кэшей?\nКаждый понедельник в 12:00 содержимое кэшей будет уходить в Корзину.":
        "Enable weekly cache auto-clean?\nEvery Monday at 12:00 cache contents will be moved to Trash.",
    "Ускорить компьютер одним кликом?\n\nБезопасно: кэши и временные файлы уйдут в Корзину":
        "Boost the computer in one click?\n\nSafe: caches and temporary files go to Trash",
    ", освободится «очищаемое» место": ", “purgeable” space will be freed",
    ". Дефрагментация SSD НЕ делается — она вредна.":
        ". No SSD defragmentation is performed — it is harmful.",
    "🚀 Ускоряю… кэши → Корзина, освобождаю место…":
        "🚀 Boosting… caches → Trash, freeing space…",
    "🚀 Сканирую… это может занять минуту-другую.":
        "🚀 Scanning… this may take a minute or two.",
    "🧽 Очищаю кэши…": "🧽 Cleaning caches…",
    "Переместить содержимое кэшей в Корзину?": "Move cache contents to Trash?",
    "🧽 Кэши → Корзина": "🧽 Caches → Trash",
    # --- очистка ---
    "Анализирую…": "Analyzing…", "Очищаю…": "Cleaning…",
    "Сначала «Анализ».": "Run “Analyze” first.",
    "Переместить выбранные кэши в Корзину?": "Move the selected caches to Trash?",
    # --- процессы / режим фокуса ---
    "🎯 Режим фокуса: «⏸ Пауза» обратимо приостанавливает приложение, «▶ Возобновить всё» — возвращает работу.":
        "🎯 Focus mode: “⏸ Pause” reversibly suspends an app, “▶ Resume all” brings it back.",
    "Процесс": "Process",
    "▶ Возобновить всё": "▶ Resume all",
    "Ничего не приостановлено": "Nothing suspended",
    "Приостановленных процессов нет.": "No suspended processes.",
    "⏸ Пауза": "⏸ Pause",
    "«{name}» — системный процесс, пауза запрещена.":
        "“{name}” is a system process; pausing is not allowed.",
    "KRYLAN — Режим фокуса": "KRYLAN — Focus mode",
    "Режим фокуса": "Focus mode",
    "🎯  Режим фокуса": "🎯  Focus mode",
    "Приостанавливает фоновые программы на время фокуса и возвращает их обратно — ничего не закрывается и не теряется. Системные процессы не трогаются.":
        "Pauses background apps for the focus session and brings them back — nothing is closed or lost. System processes are never touched.",
    "▶ Выключить фокус": "▶ Disable focus",
    "🎯 Включить фокус": "🎯 Enable focus",
    "Авто-возврат:": "Auto-resume:",
    "выкл": "off", "мин": "min",
    "Кандидаты (тяжёлые фоновые приложения) — отметьте, что приостановить:":
        "Candidates (heavy background apps) — check what to pause:",
    "  Подходящих фоновых приложений не найдено.": "  No suitable background apps found.",
    "Журнал фокуса:": "Focus log:",
    "(журнал пуст)": "(log is empty)",
    "🎯 Фокус включён · на паузе: {n}": "🎯 Focus on · paused: {n}",
    "авто-возврат через {m}:{s:02d}": "auto-resume in {m}:{s:02d}",
    "🔵 Фокус выключен · всё работает": "🔵 Focus off · everything running",
    "Отметьте хотя бы одно приложение для паузы.": "Check at least one app to pause.",
    "Приостановить выбранные приложения ({n})?\n\nЭто обратимо: они «замёрзнут» и перестанут отвечать, пока вы не нажмёте «▶ Выключить фокус» (или не сработает авто-возврат). Ничего не закрывается, данные не теряются.":
        "Pause the selected apps ({n})?\n\nThis is reversible: they will freeze and stop responding until you press “▶ Disable focus” (or auto-resume triggers). Nothing is closed, no data is lost.",
    "🎯 Фокус включён · приостановлено: {n}": "🎯 Focus on · paused: {n}",
    " (пропущено: {s})": " (skipped: {s})",
    "⏲ Авто-возврат через {m} мин": "⏲ Auto-resume in {m} min",
    "⏲ Сработал авто-возврат": "⏲ Auto-resume triggered",
    "⏸ Приостановлено: {name}": "⏸ Paused: {name}",
    "▶ Возобновлено процессов: {n}": "▶ Processes resumed: {n}",
    "Приостановить «{name}» (PID {pid})?\n\n⚠️ Это обратимо ЗАМОРОЗИТ приложение до возобновления — оно перестанет отвечать, пока вы не нажмёте «▶ Возобновить всё».\n\nНесохранённые данные в нём станут недоступны до возобновления.":
        "Suspend “{name}” (PID {pid})?\n\n⚠️ This will reversibly FREEZE the app until resumed — it will stop responding until you press “▶ Resume all”.\n\nUnsaved data in it will be unavailable until resumed.",
    "Процесс «{name}» уже завершён.": "Process “{name}” has already ended.",
    "Недостаточно прав, чтобы приостановить «{name}» — пропущено.":
        "Insufficient permissions to suspend “{name}” — skipped.",
    "Не удалось приостановить: {e}": "Could not suspend: {e}",
    "▶ Возобновлено процессов: {n}.": "▶ Processes resumed: {n}.",
    "Завершить процесс «{name}» (PID {pid})?": "End process “{name}” (PID {pid})?",
    "Не удалось завершить: {e}": "Could not end: {e}",
    # --- инструменты: статусы и заголовки ---
    "Выберите инструмент.": "Select a tool.",
    "⚙️ Сканирую автозагрузку…": "⚙️ Scanning startup items…",
    "🔄 Проверяю обновления приложений…": "🔄 Checking for app updates…",
    "📄 Собираю отчёт о состоянии…": "📄 Building status report…",
    "📦 Ищу файлы >100 МБ…": "📦 Looking for files >100 MB…",
    "👯 Ищу дубликаты…": "👯 Looking for duplicates…",
    "🖼 Ищу похожие фото…": "🖼 Looking for similar photos…",
    "🗺 Считаю размеры папок…": "🗺 Measuring folder sizes…",
    "🧳 Собираю список приложений…": "🧳 Collecting the app list…",
    "🔒 Ищу следы браузеров…": "🔒 Looking for browser traces…",
    "📈 Сравниваю с прошлой проверкой…": "📈 Comparing with the last check…",
    "📂 Ищу пустые папки…": "📂 Looking for empty folders…",
    "🧩 Ищу битые и пустые файлы…": "🧩 Looking for broken and empty files…",
    "🩺 Читаю состояние диска…": "🩺 Reading disk status…",
    # --- кнопки действий в очереди ---
    "🗑 Удалить {n} лишних копий": "🗑 Delete {n} extra copies",
    "🗑 Удалить {n} лишних похожих": "🗑 Delete {n} extra similar",
    "🔒 Очистить следы ({n})": "🔒 Clean traces ({n})",
    "📂 Удалить пустые папки ({n})": "📂 Delete empty folders ({n})",
    "🧩 Удалить битые/пустые ({n})": "🧩 Delete broken/empty ({n})",
    "📥 Старые загрузки → Корзина ({n})": "📥 Old downloads → Trash ({n})",
    "👯 Дубли → Корзину ({n})": "👯 Duplicates → Trash ({n})",
    # --- messagebox: общие ---
    "Удалить {n} лишних копий в Корзину?": "Delete {n} extra copies to Trash?",
    "Удалить {n} лишних похожих фото в Корзину?\n(в каждой группе остаётся первое)":
        "Delete {n} extra similar photos to Trash?\n(the first one in each group is kept)",
    "Переместить {n} старых файлов из Загрузок в Корзину?":
        "Move {n} old files from Downloads to Trash?",
    "Переместить {n} файлов следов в Корзину?\nВы выйдете из аккаунтов в браузерах.":
        "Move {n} trace files to Trash?\nYou will be signed out of your browser accounts.",
    "Переместить {n} пустых папок в Корзину?": "Move {n} empty folders to Trash?",
    "Переместить {n} битых/пустых файлов в Корзину?":
        "Move {n} broken/empty files to Trash?",
    "В Корзину: {n} файлов.": "To Trash: {n} files.",
    "В Корзину: {n} папок.": "To Trash: {n} folders.",
    "В Корзину: {size}.": "To Trash: {size}.",
    # --- ✨ волшебная кнопка: авто-оптимизация ---
    "✨ Оптимизировать": "✨ Optimize",
    "один клик — безопасная очистка по всем параметрам, всё в Корзину":
        "one click — safe cleanup across the board, everything to Trash",
    "✨ Оптимизирую… безопасные шаги, всё уходит в Корзину…":
        "✨ Optimizing… safe steps, everything goes to Trash…",
    "📂 Пустые папки → Корзина: {n}": "📂 Empty folders → Trash: {n}",
    "🧩 Битые/пустые файлы → Корзина: {n}": "🧩 Broken/empty files → Trash: {n}",
    "⏭ Кэш {br} пропущен — браузер запущен": "⏭ {br} cache skipped — browser is running",
    "✨  Оптимизация завершена.": "✨  Optimization complete.",
    "Освобождено: ~{size} · шагов: {n}": "Freed: ~{size} · steps: {n}",
    "Всё обратимо — очищенное в Корзине.": "Everything is reversible — cleaned items are in Trash.",
    "Найдено для ревью (ничего не удалено):": "Found for review (nothing deleted):",
    "  👯 дубли: {n} лишних · ~{size}": "  👯 duplicates: {n} extra · ~{size}",
    "  🖼 похожие фото: {n} лишних": "  🖼 similar photos: {n} extra",
    "  📦 крупные файлы: {n} · ~{size}": "  📦 large files: {n} · ~{size}",
    "🔍 Открыть инструмент ревью": "🔍 Open review tool",
    # --- ✨ оптимизация: расширенные ОС-зависимые шаги ---
    "✅ Сделано на этом устройстве ({os}):": "✅ Done on this device ({os}):",
    "⏭ Пропущено (недоступно на этом устройстве):":
        "⏭ Skipped (not available on this device):",
    "🖼 Кэш миниатюр (Quick Look) сброшен": "🖼 Thumbnail (Quick Look) cache reset",
    "🖼 Кэш миниатюр → Корзина: {size}": "🖼 Thumbnail cache → Trash: {size}",
    "⏭ Часть миниатюр занята — пропущено: {n}": "⏭ Some thumbnails are in use — skipped: {n}",
    "⏭ Кэш миниатюр не найден — пропущено": "⏭ No thumbnail cache found — skipped",
    "⏭ Кэш миниатюр пропущен ({why})": "⏭ Thumbnail cache skipped ({why})",
    "🌐 DNS-кэш сброшен (ipconfig /flushdns)": "🌐 DNS cache flushed (ipconfig /flushdns)",
    "🌐 DNS-кэш сброшен (dscacheutil)": "🌐 DNS cache flushed (dscacheutil)",
    "🌐 DNS-кэш сброшен (resolvectl)": "🌐 DNS cache flushed (resolvectl)",
    "⏭ Сброс DNS пропущен — нужны права/недоступно":
        "⏭ DNS flush skipped — needs privileges/unavailable",
    "💽 Тип диска не определён — обслуживание пропущено":
        "💽 Disk type not detected — maintenance skipped",
    "💽 SSD: TRIM (defrag /L) выполнен": "💽 SSD: TRIM (defrag /L) done",
    "💽 HDD: дефрагментация (defrag /O) выполнена": "💽 HDD: defragmentation (defrag /O) done",
    "💽 SSD: TRIM пропущен — нужны права администратора":
        "💽 SSD: TRIM skipped — administrator rights required",
    "💽 HDD: оптимизация пропущена — нужны права администратора":
        "💽 HDD: optimization skipped — administrator rights required",
    "💽 SSD (macOS): TRIM обслуживается системой автоматически":
        "💽 SSD (macOS): TRIM is maintained automatically by the system",
    "💽 HDD (macOS/APFS): дефрагментация не требуется":
        "💽 HDD (macOS/APFS): defragmentation is not needed",
    "💽 SSD: TRIM (fstrim) выполнен": "💽 SSD: TRIM (fstrim) done",
    "💽 SSD: TRIM пропущен — нужны права root (fstrim)":
        "💽 SSD: TRIM skipped — needs root (fstrim)",
    "💽 HDD (Linux): дефрагментация обычно не требуется":
        "💽 HDD (Linux): defragmentation is usually not needed",
    "💽 Обслуживание диска недоступно для этой ОС":
        "💽 Disk maintenance is not available for this OS",
    "⏭ Обслуживание диска пропущено — нет прав/недоступно":
        "⏭ Disk maintenance skipped — no privileges/unavailable",
    "📦 Кэш Homebrew очищен (brew cleanup)": "📦 Homebrew cache cleaned (brew cleanup)",
    "⏭ brew cleanup пропущен": "⏭ brew cleanup skipped",
    "⏭ Homebrew не установлен — пропущено": "⏭ Homebrew is not installed — skipped",
    "📦 Кэш apt и журналы systemd очищены": "📦 apt cache and systemd journals cleaned",
    "⏭ Кэш apt/журналы пропущены — нужны права root":
        "⏭ apt cache/journals skipped — needs root",
    # --- journald vacuum (Linux) ---
    "🗒 Журналы systemd: {size}": "🗒 systemd journals: {size}",
    "🗒 Журналы systemd ужаты до 100 МБ (было {size})":
        "🗒 systemd journals vacuumed to 100 MB (was {size})",
    "⏭ Ужатие журналов пропущено — нужны права root":
        "⏭ Journal vacuum skipped — needs root",
    "🗒 Журналы systemd будут ужаты до 100 МБ (сейчас {size})":
        "🗒 systemd journals will be vacuumed to 100 MB (now {size})",
    "⏭ Очистка пакетных кэшей пропущена": "⏭ Package cache cleanup skipped",
    "🧠 Неактивная память освобождена (purge)": "🧠 Inactive memory freed (purge)",
    "⏭ Освобождение памяти пропущено — нужны права root (purge)":
        "⏭ Memory freeing skipped — needs root (purge)",
    "🧠 Буферы записи сброшены (sync)": "🧠 Write buffers flushed (sync)",
    "⏭ Глубокая очистка кэшей памяти пропущена — нужны права root":
        "⏭ Deep memory-cache drop skipped — needs root",
    "⏭ Освобождение памяти: безопасного способа в Windows нет — пропущено":
        "⏭ Memory freeing: no safe method on Windows — skipped",
    "⏭ Освобождение памяти пропущено": "⏭ Memory freeing skipped",
    # --- 👁 предпросмотр оптимизации (dry-run, read-only) ---
    "👁 Предпросмотр": "👁 Preview",
    "предпросмотр — покажет, что будет сделано и сколько освободится, ничего не меняя":
        "preview — shows what will be done and how much will be freed, changing nothing",
    "👁 Считаю предпросмотр… ничего не удаляется и не меняется…":
        "👁 Computing preview… nothing is deleted or changed…",
    "👁  Предпросмотр оптимизации (ничего не изменено)": "👁  Optimization preview (nothing changed)",
    "Оценка освобождения: ~{size} · шагов: {n}": "Estimated to free: ~{size} · steps: {n}",
    "Это режим только для чтения — реальная очистка не запускалась.":
        "This is a read-only mode — no real cleanup was performed.",
    "▶ Будет сделано на этом устройстве ({os}):": "▶ Will be done on this device ({os}):",
    "⏭ Будет пропущено (недоступно на этом устройстве):":
        "⏭ Will be skipped (not available on this device):",
    "🧽 Кэши и логи → Корзина: {size} (предпросмотр)":
        "🧽 Caches and logs → Trash: {size} (preview)",
    "📂 Пустые папки → Корзина: {n} (предпросмотр)":
        "📂 Empty folders → Trash: {n} (preview)",
    "🧩 Битые/пустые файлы → Корзина: {n} (предпросмотр)":
        "🧩 Broken/empty files → Trash: {n} (preview)",
    "🖼 Кэш миниатюр → Корзина: {size} (предпросмотр)":
        "🖼 Thumbnail cache → Trash: {size} (preview)",
    "🖼 Кэш миниатюр (Quick Look) будет сброшен":
        "🖼 Thumbnail (Quick Look) cache will be reset",
    "🌐 DNS-кэш будет сброшен": "🌐 DNS cache will be flushed",
    "📦 Кэш Homebrew будет очищен (brew cleanup)":
        "📦 Homebrew cache will be cleaned (brew cleanup)",
    "📦 Кэш apt и журналы systemd будут очищены":
        "📦 apt cache and systemd journals will be cleaned",
    "🧠 Неактивная память будет освобождена (purge)":
        "🧠 Inactive memory will be freed (purge)",
    "🧠 Буферы записи будут сброшены (sync)": "🧠 Write buffers will be flushed (sync)",
    # --- статусы очистки ---
    "Найдено: {size}": "Found: {size}",
    "Очищено: {size} → Корзина": "Cleaned: {size} → Trash",
    "⏸ На паузе: {n}": "⏸ Paused: {n}",
    # --- disk_advice ---
    "Диск заполнен на {p}% — запустите Сканер и удалите дубликаты/крупные файлы.":
        "Disk is {p}% full — run the Scanner and remove duplicates/large files.",
    "Диск на {p}% — очистите кэши и старые загрузки.":
        "Disk at {p}% — clean caches and old downloads.",
    "Память на {p}% — завершите тяжёлые процессы.":
        "Memory at {p}% — end heavy processes.",
    "Память на {p}% — близко к пределу.": "Memory at {p}% — close to the limit.",
    "Низкий заряд ({p}%) — подключите зарядку.":
        "Low battery ({p}%) — plug in the charger.",
    "Система в порядке — критичных проблем нет.":
        "System is fine — no critical issues.",
    # --- о программе ---
    "«Дай устройству крылья»": "“Give your device wings”",
    "Версия {v} · {os}": "Version {v} · {os}",
    "Создатель: Кырлан Александр Сергеевич":
        "Creator: Alexander Sergeevich Kyrlan",
    "Кросс-платформенный оптимизатор: Windows · macOS · Linux.":
        "Cross-platform optimizer: Windows · macOS · Linux.",
    "Мониторинг CPU/ОЗУ/диск/батарея и безопасная очистка кэшей":
        "Monitors CPU/RAM/disk/battery and safely cleans caches",
    "(всё уходит в Корзину). Часть экосистемы KRYLAN (+iPhone, Android).":
        "(everything goes to Trash). Part of the KRYLAN ecosystem (+iPhone, Android).",
    # --- сканер: тексты отчёта ---
    "🚀  Готово! Компьютер ускорен.": "🚀  Done! The computer is boosted.",
    "🧽 Кэши и логи → Корзина: {size}": "🧽 Caches and logs → Trash: {size}",
    "🧊 Освобождено места: {size}": "🧊 Space freed: {size}",
    "⚡️ Готово — компьютер ускорен": "⚡️ Done — the computer is boosted",
    "Освобождено всего: ~{size}": "Total freed: ~{size}",
    "Всё обратимо — очищенное в Корзине. Без дефрага SSD.":
        "Everything is reversible — cleaned items are in Trash. No SSD defrag.",
    "🚀  Результат сканирования": "🚀  Scan result",
    "Кэши и временные файлы:": "Caches and temporary files:",
    "Корзина: {val}": "Trash: {val}",
    "Старые загрузки (>6 мес): {size} · {n} шт.":
        "Old downloads (>6 mo): {size} · {n} items",
    "Дубликаты: {size} в {n} группах": "Duplicates: {size} in {n} groups",
    "ИТОГО можно освободить: ~{size}": "TOTAL can be freed: ~{size}",
    "🧽 Кэши очищены: ~{size} → Корзина.\n\nЗапустите сканирование заново для свежей сводки.":
        "🧽 Caches cleaned: ~{size} → Trash.\n\nRun the scan again for a fresh summary.",
    # --- автозагрузка ---
    "⚙️  Автозагрузка": "⚙️  Startup",
    "ошибка чтения реестра: {e}": "registry read error: {e}",
    "Отключить: Диспетчер задач → вкладка «Автозагрузка».":
        "Disable: Task Manager → “Startup” tab.",
    "Отключить: переименуйте .plist → .plist.disabled.":
        "Disable: rename .plist → .plist.disabled.",
    "Отключить: удалите .desktop из ~/.config/autostart.":
        "Disable: remove .desktop from ~/.config/autostart.",
    # --- обновления ---
    "🔄  Обновления приложений\n\n  {hint}": "🔄  App updates\n\n  {hint}",
    "🔄  Обновления приложений ({mgr})": "🔄  App updates ({mgr})",
    "✓ Все приложения актуальны.": "✓ All apps are up to date.",
    "Найдено обновлений: {n}": "Updates found: {n}",
    "Обновить всё:  brew upgrade": "Update all:  brew upgrade",
    "Обновить всё:  winget upgrade --all": "Update all:  winget upgrade --all",
    "Обновить всё:  sudo apt upgrade": "Update all:  sudo apt upgrade",
    "Менеджер пакетов не найден (brew / winget / apt).":
        "Package manager not found (brew / winget / apt).",
    "Не удалось проверить обновления: {e}": "Could not check for updates: {e}",
    "ОС не поддерживается.": "OS is not supported.",
    # --- отчёт ---
    "📄  Отчёт сохранён\n\n  {path}\n\n  Открыт в браузере.\n\n  Всего в кэшах: {caches}\n  Свободно на диске: {free}":
        "📄  Report saved\n\n  {path}\n\n  Opened in the browser.\n\n  Total in caches: {caches}\n  Free disk space: {free}",
    "📄  Не удалось сохранить отчёт: {e}": "📄  Could not save the report: {e}",
    "KRYLAN — отчёт о состоянии": "KRYLAN — status report",
    "Сформировано:": "Generated:",
    "KRYLAN Desktop · только безопасная очистка (всё в Корзину). Создатель: Кырлан Александр Сергеевич.":
        "KRYLAN Desktop · safe cleanup only (everything to Trash). Creator: Alexander Sergeevich Kyrlan.",
    "Система": "System", "CPU": "CPU", "Диск": "Disk",
    "Оперативная память": "Memory",
    "Кэши (кандидаты на очистку)": "Caches (cleanup candidates)",
    "Всего в кэшах": "Total in caches",
    "{pct}% занято ({used} из {total})": "{pct}% used ({used} of {total})",
    "{pct}% занято · свободно {free} из {total}":
        "{pct}% used · free {free} of {total}",
    # --- крупные файлы ---
    "📦  Крупные файлы (топ-25):": "📦  Large files (top 25):",
    "  ничего\n": "  nothing\n",
    # --- дубликаты ---
    "👯  Дубликаты: групп {n}, освободить ~{size}":
        "👯  Duplicates: {n} groups, free ~{size}",
    "  дубликатов нет.\n": "  no duplicates.\n",
    # --- похожие фото ---
    "🖼  Похожие фото\n\n  Не установлен Pillow.\n  Установите: pip install Pillow\n":
        "🖼  Similar photos\n\n  Pillow is not installed.\n  Install: pip install Pillow\n",
    "🖼  Похожие фото: групп {n}, лишних {extra}":
        "🖼  Similar photos: {n} groups, {extra} extra",
    "похожих ×{n}:": "similar ×{n}:",
    "  похожих фото нет.\n": "  no similar photos.\n",
    # --- карта диска ---
    "🗺  Карта диска — домашняя папка (топ-18):":
        "🗺  Disk map — home folder (top 18):",
    "Самые тяжёлые папки — кандидаты на разбор в «Крупные файлы».":
        "The heaviest folders are candidates for review in “Large files”.",
    # --- деинсталлятор ---
    "🧳  Деинсталлятор — установленные приложения":
        "🧳  Uninstaller — installed applications",
    "Удаление: Параметры → Приложения → выбрать → «Удалить».":
        "Remove: Settings → Apps → select → “Uninstall”.",
    "Удаление: перетащите .app из «Программ» в Корзину\n(остатки ищите в ~/Library/Application Support и Caches).":
        "Remove: drag the .app from “Applications” to Trash\n(look for leftovers in ~/Library/Application Support and Caches).",
    "Удаление: sudo apt remove <пакет>.": "Remove: sudo apt remove <package>.",
    "  dpkg не найден — посмотрите менеджер пакетов вашего дистрибутива.\n":
        "  dpkg not found — check your distribution’s package manager.\n",
    # --- приватность ---
    "🔒  Приватность — следы браузеров": "🔒  Privacy — browser traces",
    "  следов не найдено.\n": "  no traces found.\n",
    "⚠️ Сначала закройте: {browsers} — иначе файлы заняты.":
        "⚠️ Close these first: {browsers} — otherwise the files are locked.",
    "Всего следов: ~{size}. История и cookies уйдут в Корзину (вы выйдете из аккаунтов).":
        "Total traces: ~{size}. History and cookies go to Trash (you will be signed out).",
    # --- что выросло ---
    "📈  Что выросло": "📈  What grew",
    "Первый снимок сохранён. Запустите ещё раз позже —\nи KRYLAN покажет, какие папки выросли или уменьшились.":
        "First snapshot saved. Run again later —\nand KRYLAN will show which folders grew or shrank.",
    "Текущие размеры:": "Current sizes:",
    "📈  Изменения с прошлой проверки": "📈  Changes since the last check",
    "  Изменений нет — размеры папок не поменялись.\n":
        "  No changes — folder sizes are unchanged.\n",
    "▲ выросло · ▼ уменьшилось. Растущие папки — кандидаты на разбор.":
        "▲ grew · ▼ shrank. Growing folders are candidates for review.",
    # --- пустые папки ---
    "📂  Пустые папки: {n}": "📂  Empty folders: {n}",
    "…и ещё {n}\n": "…and {n} more\n",
    "  пустых папок не найдено.\n": "  no empty folders found.\n",
    "Пустые папки остаются после удаления программ и распаковки архивов. Уйдут в Корзину.":
        "Empty folders are left after removing apps and extracting archives. They go to Trash.",
    # --- битые файлы ---
    "🧩  Битые и пустые файлы: {n} (пустых {zero}, битых ссылок {links})":
        "🧩  Broken and empty files: {n} (empty {zero}, broken links {links})",
    "пусто ": "empty ", "ссылка": "link  ",
    "  битых и пустых файлов не найдено.\n":
        "  no broken or empty files found.\n",
    "Пустые файлы (0 байт) и битые символические ссылки бесполезны. Уйдут в Корзину.":
        "Empty files (0 bytes) and broken symlinks are useless. They go to Trash.",
    # --- 🔗 Битые ярлыки ---
    "🔗 Битые ярлыки": "🔗 Broken shortcuts",
    "🔗 Ищу битые ярлыки…": "🔗 Looking for broken shortcuts…",
    "🔗  Битые ярлыки: {n}": "🔗  Broken shortcuts: {n}",
    "  битых ярлыков не найдено.\n": "  no broken shortcuts found.\n",
    "Ярлыки, чья цель удалена, бесполезны. Уйдут в Корзину.":
        "Shortcuts whose target is gone are useless. They go to Trash.",
    "🔗 Удалить битые ярлыки ({n})": "🔗 Delete broken shortcuts ({n})",
    "Переместить {n} битых ярлыков в Корзину?":
        "Move {n} broken shortcuts to Trash?",
    # --- 📦🕒 Большие и старые ---
    "📦🕒 Большие и старые": "📦🕒 Big & old",
    "📦🕒 Ищу большие старые файлы…": "📦🕒 Looking for big old files…",
    "📦🕒  Большие и старые файлы: {n} (≥{mb} МБ · не трогали ≥{days} дн.)":
        "📦🕒  Big & old files: {n} (≥{mb} MB · untouched ≥{days} days)",
    "  больших старых файлов не найдено.\n": "  no big old files found.\n",
    "Крупные файлы, которые давно не открывали и не меняли. Уйдут в Корзину.":
        "Large files untouched and unchanged for a long time. They go to Trash.",
    "📦🕒 Удалить большие старые ({n})": "📦🕒 Delete big & old ({n})",
    "Переместить {n} больших старых файлов в Корзину?":
        "Move {n} big old files to Trash?",
    # --- диск (SMART) ---
    "🩺  Здоровье диска": "🩺  Disk health",
    "Статус: ": "Status: ",
    "✅ SMART в норме (Verified)": "✅ SMART is healthy (Verified)",
    "⚠️ проверьте диск в Дисковой утилите":
        "⚠️ check the disk in Disk Utility",
    "Статус «OK» = SMART в норме.": "Status “OK” = SMART is healthy.",
    "smartctl не найден: sudo apt install smartmontools":
        "smartctl not found: sudo apt install smartmontools",
    "не удалось прочитать SMART: {e}": "could not read SMART: {e}",
    "Занято {pct}% · свободно {free} из {total}":
        "Used {pct}% · free {free} of {total}",
    "⚠️ Меньше 10% свободного места замедляет систему — освободите диск.":
        "⚠️ Less than 10% free space slows the system down — free up the disk.",
    # --- 🩺 Диск-доктор (read-only проверка на ошибки) ---
    "🩺 Диск-доктор": "🩺 Disk Doctor",
    "🩺 Проверяю диск на ошибки (только чтение)…":
        "🩺 Checking the disk for errors (read-only)…",
    "🩺  Диск-доктор (только чтение)": "🩺  Disk Doctor (read-only)",
    "⚠️ Найдены ошибки — нужна проверка/ремонт.":
        "⚠️ Errors found — a check/repair is needed.",
    "✅ Ошибок не найдено — диск в порядке.":
        "✅ No errors found — the disk is OK.",
    "Не удалось определить итог — см. вывод выше.":
        "Could not determine the result — see the output above.",
    "chkdsk недоступен в этой среде.": "chkdsk is not available in this environment.",
    "diskutil недоступен в этой среде.": "diskutil is not available in this environment.",
    "Нет вывода — возможно, нужны права администратора.":
        "No output — administrator rights may be required.",
    "SMART (здоровье диска):": "SMART (disk health):",
    "Установите smartmontools: sudo apt install smartmontools":
        "Install smartmontools: sudo apt install smartmontools",
    "Не удалось прочитать SMART (нужны права root?).":
        "Could not read SMART (root rights needed?).",
    "ℹ️ fsck на смонтированном диске не запускается — это небезопасно.":
        "ℹ️ fsck is not run on a mounted disk — that would be unsafe.",
    "не удалось выполнить проверку: {e}": "could not run the check: {e}",
    "Диск-доктор только читает состояние и ничего не меняет.":
        "Disk Doctor only reads the state and changes nothing.",
    # --- вес/статус автозагрузки ---
    "вкл": "on", "выкл": "off", "статус ?": "status ?",
    "Системная автозагрузка (Location · Command):":
        "System startup (Location · Command):",
    "«вкл/выкл» — реальный статус из реестра. "
    "Отключить: Диспетчер задач → вкладка «Автозагрузка».":
        "“on/off” is the real status from the registry. "
        "Disable: Task Manager → Startup tab.",
    # --- 📦 Snap/Flatpak (Linux): очистка неиспользуемого ---
    "📦 Snap/Flatpak": "📦 Snap/Flatpak",
    "📦 Ищу неиспользуемые snap/flatpak…": "📦 Looking for unused snap/flatpak…",
    "📦  Snap / Flatpak — неиспользуемое (Linux)": "📦  Snap / Flatpak — unused (Linux)",
    "Только Linux: эта функция доступна на Linux.":
        "Linux only: this feature is available on Linux.",
    "Flatpak не установлен — пропущено.": "Flatpak is not installed — skipped.",
    "Snap не установлен — пропущено.": "Snap is not installed — skipped.",
    "Flatpak: есть неиспользуемые среды выполнения для удаления.":
        "Flatpak: there are unused runtimes to remove.",
    "Flatpak: неиспользуемого не найдено.": "Flatpak: nothing unused found.",
    "Snap: отключённых ревизий: {n}": "Snap: disabled revisions: {n}",
    "Snap: отключённых ревизий не найдено.": "Snap: no disabled revisions found.",
    "⚠️ Удаление ревизий snap требует прав root — пропущено (запустите с sudo).":
        "⚠️ Removing snap revisions needs root — skipped (run with sudo).",
    "Безопасно: удаляются только официально неиспользуемые среды (flatpak --unused) и отключённые ревизии snap. Установленные приложения не трогаются.":
        "Safe: only officially unused runtimes (flatpak --unused) and disabled snap revisions are removed. Installed apps are untouched.",
    "🧹 Очистить неиспользуемое": "🧹 Clean unused",
    "Удалить неиспользуемые flatpak-среды и {n} отключённых ревизий snap?":
        "Remove unused flatpak runtimes and {n} disabled snap revisions?",
    "📦  Snap / Flatpak — очистка завершена": "📦  Snap / Flatpak — cleanup done",
    "✅ Flatpak: неиспользуемое удалено (flatpak --unused).":
        "✅ Flatpak: unused removed (flatpak --unused).",
    "⏭ Flatpak: удаление пропущено.": "⏭ Flatpak: removal skipped.",
    "✅ Snap: удалено отключённых ревизий: {n}": "✅ Snap: disabled revisions removed: {n}",
    "⏭ Snap: ревизии пропущены (нет прав/ошибка): {n}":
        "⏭ Snap: revisions skipped (no rights/error): {n}",
    # --- 🗜 Сжать базы браузеров (VACUUM SQLite) ---
    "🗜 Сжать базы браузеров": "🗜 Compact browser databases",
    "🗜 Ищу базы браузеров…": "🗜 Looking for browser databases…",
    "🗜  Сжатие баз браузеров (VACUUM)": "🗜  Compacting browser databases (VACUUM)",
    "  баз для сжатия не найдено.\n": "  no databases to compact found.\n",
    "⚠️ Сначала закройте: {browsers} — их базы заняты и будут пропущены.":
        "⚠️ Close these first: {browsers} — their databases are locked and will be skipped.",
    "Найдено баз: {n} (~{size}). VACUUM перепаковывает файл без потери данных.":
        "Databases found: {n} (~{size}). VACUUM repacks the file without losing data.",
    "🗜 Сжать базы ({n})": "🗜 Compact databases ({n})",
    "Сжать {n} баз закрытых браузеров?\nДанные не удаляются — только перепаковка (VACUUM).":
        "Compact {n} databases of closed browsers?\nNo data is deleted — repack only (VACUUM).",
    "🗜  Сжатие завершено": "🗜  Compaction done",
    "Сжато баз: {n}": "Databases compacted: {n}",
    "Сэкономлено: {size}": "Saved: {size}",
    "⏭ Пропущено (браузер запущен): {n}": "⏭ Skipped (browser running): {n}",
    "Сжато: {n}, сэкономлено {size}.": "Compacted: {n}, saved {size}.",
    # --- 🔥 Шредер (безвозвратное затирание) ---
    "🔥 Шредер": "🔥 Shredder",
    "🔥  Шредер — безвозвратное затирание файлов":
        "🔥  Shredder — permanent file wiping",
    "Выберите файлы — KRYLAN перезапишет их случайными данными и удалит. Это НЕОБРАТИМО (не Корзина).":
        "Pick files — KRYLAN overwrites them with random data and deletes them. This is IRREVERSIBLE (not Trash).",
    "Файлы не выбраны.": "No files selected.",
    "⚠️ БЕЗВОЗВРАТНО затереть и удалить {n} файл(ов)?\n\nЭто НЕЛЬЗЯ отменить — файлы НЕ попадут в Корзину, восстановить их будет невозможно.":
        "⚠️ Permanently wipe and delete {n} file(s)?\n\nThis CANNOT be undone — files do NOT go to Trash and cannot be recovered.",
    "🔥 Затираю файлы случайными данными…": "🔥 Wiping files with random data…",
    "🔥  Шредер — готово": "🔥  Shredder — done",
    "Затёрто и удалено безвозвратно: {n}": "Wiped and permanently deleted: {n}",
    "Пропущено (защищено/недоступно): {n}": "Skipped (protected/unavailable): {n}",
    "Безвозвратно затёрто: {n} файл(ов).": "Permanently wiped: {n} file(s).",
    # --- экспорт находок (CSV/HTML) ---
    "💾 Экспорт CSV": "💾 Export CSV",
    "💾 Экспорт HTML": "💾 Export HTML",
    "Нечего экспортировать — сначала выполните скан.": "Nothing to export — run a scan first.",
    "💾 Экспортировано:\n{path}": "💾 Exported:\n{path}",
    "Не удалось экспортировать: {e}": "Export failed: {e}",
    "KRYLAN — экспорт находок: {what}": "KRYLAN — findings export: {what}",
    "Размер": "Size", "Байты": "Bytes", "Путь": "Path", "Группа": "Group",
    "Возраст, дн.": "Age, days", "Тип": "Type", "Пакет": "Package",
    # --- bloatware-листер (Windows) ---
    "🧹 Предустановленное": "🧹 Preinstalled",
    "🧹 Собираю список предустановленных приложений…": "🧹 Collecting preinstalled apps…",
    "🧹  Предустановленное (bloatware)": "🧹  Preinstalled (bloatware)",
    "Только Windows. На этой ОС инструмент недоступен.": "Windows only. Not available on this OS.",
    "🧹  Предустановленное (bloatware) — только показ, ничего не удаляется":
        "🧹  Preinstalled (bloatware) — view only, nothing is removed",
    "Всего UWP-пакетов: {n}, из них помечено как bloat: {b}":
        "Total UWP packages: {n}, flagged as bloat: {b}",
    "Как удалить безопасно: Параметры → Приложения → найдите пакет → Удалить.":
        "Safe removal: Settings → Apps → find the package → Uninstall.",
    "Либо в PowerShell: Get-AppxPackage <имя> | Remove-AppxPackage (на свой риск).":
        "Or in PowerShell: Get-AppxPackage <name> | Remove-AppxPackage (at your own risk).",
    "  Известного предустановленного bloat не найдено.":
        "  No known preinstalled bloat found.",
    # --- многотомная корзина ---
    "♻️ Корзины томов": "♻️ Volume trash bins",
    "♻️ Считаю размер корзин на всех томах…": "♻️ Measuring trash bins on all volumes…",
    "♻️  Корзины томов": "♻️  Volume trash bins",
    "Суммарно в корзинах: {size}": "Total in trash bins: {size}",
    "⚠️ Очистка корзины НЕОБРАТИМА (как Шредер). Только по явной кнопке.":
        "⚠️ Emptying trash is IRREVERSIBLE (like the Shredder). Explicit button only.",
    "  Корзин на томах не найдено (или они пусты).":
        "  No volume trash bins found (or they are empty).",
    "♻️ Очистить корзины (НЕОБРАТИМО)": "♻️ Empty trash bins (IRREVERSIBLE)",
    "⚠️ БЕЗВОЗВРАТНО очистить корзины на всех томах ({n})?\n\nЭто НЕЛЬЗЯ отменить — содержимое корзин будет удалено навсегда.":
        "⚠️ Permanently empty trash bins on all volumes ({n})?\n\nThis CANNOT be undone — trash contents will be deleted forever.",
    "♻️ Очищаю корзины томов…": "♻️ Emptying volume trash bins…",
    "♻️  Корзины томов — очищено": "♻️  Volume trash bins — emptied",
    "Удалено элементов (необратимо): {n}": "Items deleted (irreversible): {n}",
}
def L(s):
    if LANG == "en":
        return I18N.get(s, s)
    return s

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

# ---------- экспорт находок: чистый CSV по RFC 4180 ----------
def findings_to_csv(rows, headers):
    """Чистая функция: (строки, заголовки) → CSV-текст по RFC 4180.

    • Поле берётся в кавычки, если содержит запятую, кавычку, CR или LF;
      внутренние кавычки удваиваются ("" вместо ").
    • Перевод строки между записями — CRLF (\\r\\n), как требует RFC 4180.
    • None → пустое поле; всё остальное приводится через str().
    Без побочных эффектов — удобно тестировать."""
    def field(v):
        s = "" if v is None else str(v)
        if any(c in s for c in (',', '"', '\n', '\r')):
            return '"' + s.replace('"', '""') + '"'
        return s
    out = []
    if headers:
        out.append(",".join(field(h) for h in headers))
    for row in rows:
        out.append(",".join(field(c) for c in row))
    return "\r\n".join(out)

# ---------- bloatware-листер (Windows UWP): чистый классификатор ----------
# Известный предустановленный bloat по подстрокам имён пакетов (регистронезависимо).
_BLOATWARE_PATTERNS = (
    "king.com", "candycrush",            # Candy Crush King.*
    "microsoft.xbox", "xboxgaming", "xboxapp",  # Xbox-обвес
    "microsoft.3dviewer", "microsoft.3dbuilder", "microsoft.print3d",
    "microsoft.mixedreality.portal",
    "microsoft.bingnews", "microsoft.bingweather", "microsoft.bingfinance",
    "microsoft.bingsports",
    "microsoft.zunemusic", "microsoft.zunevideo",  # Groove / Movies & TV
    "microsoft.skypeapp",
    "microsoft.gethelp", "microsoft.getstarted",
    "microsoft.people",
    "microsoft.windowsfeedbackhub",
    "microsoft.solitairecollection",
    "microsoft.windowsmaps",
    "microsoft.wallet", "microsoft.todos",
    "microsoft.officehub", "microsoft.microsoftofficehub",
    "microsoft.yourphone",  # Phone Link / Связь с телефоном
    "disney", "spotify", "netflix", "tiktok", "facebook", "instagram",
)

def is_bloatware(package_name):
    """Чистая функция: имя UWP-пакета → True, если это известный предустановленный
    bloat (по белому списку подстрок, регистронезависимо). Без побочных эффектов."""
    if not package_name:
        return False
    low = str(package_name).lower()
    return any(p in low for p in _BLOATWARE_PATTERNS)

# ---------- многотомная корзина: чистый сборщик путей ----------
def trash_locations():
    """Чистая функция: список существующих директорий корзин на ВСЕХ томах.

    • macOS:  ~/.Trash + /Volumes/*/.Trashes/<uid>
    • Linux:  ~/.local/share/Trash + /media|/run/media|/mnt/*/.Trash-<uid>
    • Windows: $Recycle.Bin на каждом доступном диске
    Никогда не падает: отсутствующие/недоступные пути просто пропускаются."""
    found = []
    def add(p):
        try:
            if p and os.path.isdir(p):
                found.append(p)
        except Exception:
            pass
    try:
        uid = os.getuid()
    except Exception:
        uid = None
    if SYSTEM == "Darwin":
        add(os.path.join(HOME, ".Trash"))
        try:
            for vol in os.listdir("/Volumes"):
                base = os.path.join("/Volumes", vol, ".Trashes")
                if uid is not None:
                    add(os.path.join(base, str(uid)))
                add(base)
        except Exception:
            pass
    elif SYSTEM == "Linux":
        add(os.path.join(HOME, ".local/share/Trash"))
        suffix = ".Trash-%s" % uid if uid is not None else None
        for mroot in ("/media", "/run/media", "/mnt"):
            try:
                for entry in os.listdir(mroot):
                    mp = os.path.join(mroot, entry)
                    # /run/media/<user>/<vol> — на уровень глубже
                    candidates = [mp]
                    try:
                        if os.path.isdir(mp):
                            candidates += [os.path.join(mp, sub) for sub in os.listdir(mp)]
                    except Exception:
                        pass
                    for c in candidates:
                        if suffix:
                            add(os.path.join(c, suffix))
            except Exception:
                pass
    elif SYSTEM == "Windows":
        try:
            import string
            for letter in string.ascii_uppercase:
                add(os.path.join("%s:\\" % letter, "$Recycle.Bin"))
        except Exception:
            pass
    return found

# ---------- защита путей при удалении (в Корзину) ----------
def _protected_roots():
    """Пути, которые НИКОГДА нельзя отправлять в Корзину целиком (защита от ошибки):
    домашний корень и его стандартные папки. Подпапки/файлы ВНУТРИ — можно."""
    roots = {HOME}
    for d in ("Downloads", "Desktop", "Documents", "Pictures", "Movies", "Music",
              "Library", ".config", ".cache", ".local", "AppData"):
        roots.add(os.path.join(HOME, d))
    return {os.path.realpath(p) for p in roots}

def is_protected(path):
    """True, если путь нельзя удалять: пусто/относительный/символ. корень тома или
    защищённая папка (HOME и стандартные подпапки). Пустой и относительный путь
    опасен — realpath раскрывает его в CWD/произвольное место под ним."""
    if not path or not os.path.isabs(path):
        return True
    rp = os.path.realpath(path)
    if rp in _protected_roots():
        return True
    # корень тома: "/" или "/Volumes/Foo" (≤2 сегмента) — не трогаем
    return len(rp.strip("/").split("/")) < 2

def safe_trash(path):
    """Обёртка над send2trash с защитой пути. Возвращает True при успехе.
    Удаление обратимо (Корзина). Никогда не бросает."""
    if is_protected(path):
        return False
    try:
        send2trash(path); return True
    except Exception:
        return False

# ---------- 🔥 Шредер: безвозвратное затирание файлов ----------
def shred_file(path, passes=1):
    """НЕОБРАТИМО затирает один обычный файл: перезаписывает его случайными
    байтами `passes` раз (1–3), сбрасывает на диск (flush + os.fsync) после
    каждого прохода и затем удаляет (os.remove). Возвращает True при успехе.

    Защита (любой случай → False, цель НЕ трогаем):
      • защищённый путь (is_protected: пусто/относительный/HOME/корень тома);
      • не существует, не обычный файл (каталог), или это символическая ссылка
        — по симлинку НЕ идём, чтобы не затереть его цель;
      • любая ошибка ввода-вывода.

    В отличие от Корзины (safe_trash) операция необратима — вызывать только
    по явному запросу пользователя, НЕ в составе авто-оптимизации.
    """
    try:
        passes = max(1, min(3, int(passes)))
    except (TypeError, ValueError):
        passes = 1
    if is_protected(path):
        return False
    # симлинк — не следуем (os.path.islink истинен и для битых ссылок);
    # затираем только реальные обычные файлы.
    if os.path.islink(path) or not os.path.isfile(path):
        return False
    try:
        size = os.path.getsize(path)
        with open(path, "r+b", buffering=0) as f:
            for _ in range(passes):
                f.seek(0)
                remaining = size
                # пишем кусками, чтобы не держать большой файл целиком в памяти
                while remaining > 0:
                    chunk = min(remaining, 1024 * 1024)
                    f.write(os.urandom(chunk))
                    remaining -= chunk
                f.flush()
                os.fsync(f.fileno())
        os.remove(path)
        return True
    except Exception:
        return False

# ---------- отчёт «что выросло с прошлой проверки» (BoostSpeed-style) ----------
def _snapshot_path():
    return os.path.join(HOME, ".krylan_snapshot.json")

def take_snapshot(bases=None):
    """Снимок размеров папок домашнего каталога: {путь: размер_в_байтах}."""
    # Library намеренно исключён: 60+ ГБ кэшей сканируются слишком долго
    # и не относятся к пользовательским папкам, чей рост интересен.
    bases = bases or [os.path.join(HOME, d) for d in
                      ("Downloads", "Desktop", "Documents", "Pictures", "Movies", "Music")]
    return {p: dir_size(p) for p in bases if os.path.isdir(p)}

def growth_report(snapshot_file=None, save=True):
    """Сравнивает текущие размеры с прошлым снимком.
    Возвращает (changes, is_first) где changes = [(delta, path, old, new)] по убыванию |delta|.
    Сохраняет новый снимок (если save)."""
    import json
    sf = snapshot_file or _snapshot_path()
    prev = {}
    if os.path.isfile(sf):
        try:
            with open(sf, encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:
            prev = {}
    cur = take_snapshot()
    is_first = not prev
    changes = []
    for path, new in cur.items():
        old = prev.get(path, new if is_first else 0)
        delta = new - old
        changes.append((delta, path, old, new))
    changes.sort(key=lambda x: abs(x[0]), reverse=True)
    if save:
        try:
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(cur, f)
        except Exception:
            pass
    return changes, is_first

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

def find_empty_dirs(bases=None):
    """Пустые папки в пользовательских каталогах. Папка считается пустой,
    если не содержит файлов ни на одном уровне (только пустые подпапки).
    Пропускаем скрытые и системные служебные каталоги."""
    bases = bases or [os.path.join(HOME, d) for d in
                      ("Downloads", "Desktop", "Documents", "Pictures", "Movies", "Music")]
    skip = {".git", "node_modules", ".Trash", "Library"}
    empties = []
    for base in bases:
        if not os.path.isdir(base): continue
        # снизу вверх: к моменту проверки родителя его пустые дети уже учтены
        for root, dirs, files in os.walk(base, topdown=False):
            name = os.path.basename(root)
            if name in skip or name.startswith("."):
                continue
            if root == base:
                continue
            try:
                entries = [e for e in os.listdir(root) if not e.startswith(".DS_Store")]
            except OSError:
                continue
            # пусто, если нет файлов и все подпапки уже признаны пустыми
            has_file = any(os.path.isfile(os.path.join(root, e)) for e in entries)
            subdirs = [os.path.join(root, e) for e in entries if os.path.isdir(os.path.join(root, e))]
            if not has_file and all(d in empties for d in subdirs):
                empties.append(root)
    return empties

def find_broken_files(bases=None):
    """Битые и пустые файлы в пользовательских каталогах.
    Возвращает список кортежей (kind, path), где kind ∈ {"zero","symlink"}:
      • "zero"    — файлы нулевого размера (0 байт), НЕ скрытые;
      • "symlink" — битые символические ссылки (islink, но цель отсутствует).
    Пропускаем скрытые каталоги (на ".") и системные служебные папки.
    Без побочных эффектов — пригодно для юнит-тестов."""
    bases = bases or [os.path.join(HOME, d) for d in ("Desktop", "Documents", "Downloads")]
    skip = {".git", "node_modules", ".Trash", "Library", "AppData", ".cache"}
    found = []
    for base in bases:
        if not os.path.isdir(base): continue
        for root, dirs, files in os.walk(base):
            # не спускаемся в скрытые и системные каталоги
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip]
            for fn in files:
                if fn.startswith("."): continue
                fp = os.path.join(root, fn)
                try:
                    if os.path.islink(fp):
                        # битая ссылка: цель не существует
                        if not os.path.exists(fp):
                            found.append(("symlink", fp))
                        continue
                    if os.path.isfile(fp) and os.path.getsize(fp) == 0:
                        found.append(("zero", fp))
                except OSError:
                    pass
    return found

# фрагмент для частичного хеша (первые N байт файла) — дешёвый отсев
_PARTIAL_HASH_BYTES = 64 * 1024

def _file_hash(fp, limit=None):
    """blake2b-хеш файла. limit=None → весь файл, иначе первые limit байт.
    Быстрый, из стандартной библиотеки (без внешних зависимостей). Читаем
    кусками — большие файлы не держим в памяти целиком. None при ошибке I/O."""
    h = hashlib.blake2b()
    try:
        with open(fp, "rb") as fh:
            if limit is None:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            else:
                remaining = limit
                while remaining > 0:
                    chunk = fh.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        break
                    h.update(chunk)
                    remaining -= len(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _hash_buckets(paths, limit):
    """Сгруппировать пути по хешу (полному или частичному). {hash: [paths]}."""
    buckets = {}
    for fp in paths:
        h = _file_hash(fp, limit)
        if h is not None:
            buckets.setdefault(h, []).append(fp)
    return buckets

def find_duplicates(bases=None):
    """Точные дубликаты в пользовательских папках. Возвращает (groups, extras, wasted).

    Двухфазно (в духе Czkawka), результат идентичен полному хешированию,
    но быстрее за счёт раннего отсева:
      1) группировка по размеру (size) — мгновенно;
      2) частичный хеш первых ~64 КБ (blake2b) — дёшево отсеивает непохожие;
      3) полный хеш blake2b ТОЛЬКО для файлов, совпавших по частичному.
    blake2b из стандартной библиотеки — без внешних зависимостей."""
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
        # фаза 2 — частичный хеш отсеивает кандидатов с разным началом
        for partial_paths in _hash_buckets(paths, _PARTIAL_HASH_BYTES).values():
            if len(partial_paths) < 2:
                continue
            # фаза 3 — полный хеш только для прошедших частичный отбор
            for same in _hash_buckets(partial_paths, None).values():
                if len(same) > 1:
                    groups.append((s, sorted(same))); extras.extend(sorted(same)[1:])
    groups.sort(reverse=True)
    wasted = sum(s*(len(g)-1) for s, g in groups)
    return groups, extras, wasted

# ---------- очистка неиспользуемых snap/flatpak (Linux) ----------
def parse_disabled_snaps(text):
    """Парсер вывода `snap list --all` → список (name, revision) для ревизий
    со статусом "disabled" (старые ревизии, оставшиеся после обновлений).
    ЧИСТАЯ функция (тестируется на сэмплах), без I/O.

    Формат строки snap (колонки разделены пробелами):
        Name  Version  Rev  Tracking  Publisher  Notes
    Заголовок (начинается с "Name") и пустые строки пропускаем. Ревизия
    считается отключённой, если в колонке Notes есть "disabled"."""
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        cols = line.split()
        if len(cols) < 6:
            continue
        if cols[0].lower() == "name":   # заголовок таблицы
            continue
        name, rev, notes = cols[0], cols[2], cols[5]
        if "disabled" in notes.lower():
            out.append((name, rev))
    return out

# ---------- VACUUM баз SQLite браузеров ----------
def vacuum_sqlite(path):
    """Сжать одну базу SQLite на месте через VACUUM. Возвращает (before, after)
    в байтах. ЧИСТАЯ по контракту: только sqlite3 из стандартной библиотеки,
    данные НЕ удаляются (VACUUM лишь перепаковывает файл). Любая ошибка/не-БД →
    (size, size) (изменений нет). Вызывать ТОЛЬКО при закрытом браузере —
    иначе файл занят и VACUUM либо упадёт, либо повредит данные."""
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
    """Файлы баз SQLite браузеров (history/cookies/favicons), пригодные для
    VACUUM. Возвращает [(браузер, путь)]. Только существующие файлы.

    Chromium-семейство (Chrome/Edge/Brave) хранит БЕЗ расширения .sqlite —
    это файлы History/Cookies/Favicons (формат SQLite). Firefox — *.sqlite."""
    import glob
    out = []
    chromium_files = ("History", "Cookies", "Favicons", "Web Data", "Top Sites")
    for browser, base in _chromium_ext_profiles():
        if not os.path.isdir(base):
            continue
        # <UserData>/<Profile>/<file> — профили: Default, Profile 1, …
        for prof in glob.glob(os.path.join(base, "*")):
            if not os.path.isdir(prof):
                continue
            for fn in chromium_files:
                fp = os.path.join(prof, fn)
                if os.path.isfile(fp):
                    out.append((browser, fp))
    # Firefox: <profile>/*.sqlite (places.sqlite, cookies.sqlite, favicons.sqlite…)
    if SYSTEM == "Darwin":
        ff = os.path.join(HOME, "Library/Application Support/Firefox/Profiles")
    elif SYSTEM == "Windows":
        roam = os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming"))
        ff = os.path.join(roam, "Mozilla", "Firefox", "Profiles")
    else:
        ff = os.path.join(HOME, ".mozilla/firefox")
    for fp in glob.glob(os.path.join(ff, "*", "*.sqlite")):
        if os.path.isfile(fp):
            out.append(("Firefox", fp))
    return out

# ---------- похожие изображения (perceptual hash / dHash) ----------
SIMILAR_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".gif")

def dhash(image, size=8):
    """Difference hash изображения PIL.Image → int.
    grayscale → resize(size+1, size) → сравнение соседних пикселей по строкам."""
    img = image.convert("L").resize((size + 1, size))
    px = img.load()
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = (bits << 1) | (1 if px[col, row] > px[col + 1, row] else 0)
    return bits

def hamming(a, b):
    """Расстояние Хэмминга двух int."""
    return bin(a ^ b).count("1")

def find_similar_images(bases=None, threshold=10):
    """Группы похожих (near-duplicate) изображений по dHash.
    Возвращает список групп — каждая список путей (≥2). Pillow импортируется лениво."""
    from PIL import Image
    bases = bases or [os.path.join(HOME, d) for d in ("Desktop", "Documents", "Downloads", "Pictures")]
    items = []  # (path, hash)
    for base in bases:
        if not os.path.isdir(base): continue
        for root, _, files in os.walk(base):
            for fn in files:
                if not fn.lower().endswith(SIMILAR_EXTS): continue
                fp = os.path.join(root, fn)
                try:
                    with Image.open(fp) as im:
                        h = dhash(im)
                    items.append((fp, h))
                except Exception:
                    continue  # битые/нечитаемые пропускаем
    groups, used = [], set()
    for i in range(len(items)):
        if i in used: continue
        fp_i, h_i = items[i]
        grp = [fp_i]
        for j in range(i + 1, len(items)):
            if j in used: continue
            fp_j, h_j = items[j]
            if hamming(h_i, h_j) <= threshold:
                grp.append(fp_j); used.add(j)
        if len(grp) >= 2:
            used.add(i); groups.append(sorted(grp))
    return groups

# ---------- следы браузеров (Privacy Cleaner) ----------
def running_browsers():
    """Названия запущенных браузеров (по процессам psutil)."""
    keys = {"chrome": "Chrome", "msedge": "Edge", "edge": "Edge",
            "firefox": "Firefox", "yandex": "Yandex"}
    found = set()
    for p in psutil.process_iter(["name"]):
        n = (p.info.get("name") or "").lower()
        for k, label in keys.items():
            if k in n: found.add(label)
    return found

def privacy_targets():
    """Файлы следов: [(браузер, что, путь)]. Только существующие."""
    import glob
    t = []
    if SYSTEM == "Darwin":
        ch = os.path.join(HOME, "Library/Application Support/Google/Chrome/Default")
        ed = os.path.join(HOME, "Library/Application Support/Microsoft Edge/Default")
        ff = os.path.join(HOME, "Library/Application Support/Firefox/Profiles")
    elif SYSTEM == "Windows":
        local = os.environ.get("LOCALAPPDATA", os.path.join(HOME, "AppData", "Local"))
        roam = os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming"))
        ch = os.path.join(local, "Google", "Chrome", "User Data", "Default")
        ed = os.path.join(local, "Microsoft", "Edge", "User Data", "Default")
        ff = os.path.join(roam, "Mozilla", "Firefox", "Profiles")
    else:
        ch = os.path.join(HOME, ".config/google-chrome/Default")
        ed = os.path.join(HOME, ".config/microsoft-edge/Default")
        ff = os.path.join(HOME, ".mozilla/firefox")
    for label, base in [("Chrome", ch), ("Edge", ed)]:
        for item, fn in [("История", "History"), ("Cookies", "Cookies"),
                         ("Посещённые ссылки", "Visited Links")]:
            t.append((label, item, os.path.join(base, fn)))
    for prof in glob.glob(os.path.join(ff, "*")):
        for item, fn in [("История", "places.sqlite"), ("Cookies", "cookies.sqlite")]:
            t.append(("Firefox", item, os.path.join(prof, fn)))
    return [(b, i, p) for b, i, p in t if os.path.isfile(p)]

# ---------- расширения браузеров (read-only) ----------
def parse_chromium_extension(manifest_dict, messages_dict=None):
    """Имя Chromium-расширения из manifest.json.

    Поле name может быть локализованной ссылкой вида "__MSG_appName__" —
    тогда раскрываем её из messages.json (_locales/<lang>/messages.json),
    структура которого: {"appName": {"message": "..."}}.
    Чистая, без I/O — полностью тестируема.
    """
    name = ""
    if isinstance(manifest_dict, dict):
        name = (manifest_dict.get("name") or "").strip()
    if not name:
        return ""
    if name.startswith("__MSG_") and name.endswith("__"):
        key = name[len("__MSG_"):-len("__")]
        if isinstance(messages_dict, dict):
            entry = messages_dict.get(key) or messages_dict.get(key.lower())
            if isinstance(entry, dict):
                msg = (entry.get("message") or "").strip()
                if msg:
                    return msg
        return key  # graceful: показываем ключ, если перевод не найден
    return name

def _chromium_ext_profiles():
    """Базовые папки User Data Chromium-браузеров: [(браузер, путь)]."""
    if SYSTEM == "Darwin":
        sup = os.path.join(HOME, "Library/Application Support")
        return [("Chrome", os.path.join(sup, "Google/Chrome")),
                ("Edge",   os.path.join(sup, "Microsoft Edge")),
                ("Brave",  os.path.join(sup, "BraveSoftware/Brave-Browser"))]
    if SYSTEM == "Windows":
        local = os.environ.get("LOCALAPPDATA", os.path.join(HOME, "AppData", "Local"))
        return [("Chrome", os.path.join(local, "Google", "Chrome", "User Data")),
                ("Edge",   os.path.join(local, "Microsoft", "Edge", "User Data")),
                ("Brave",  os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data"))]
    return [("Chrome", os.path.join(HOME, ".config/google-chrome")),
            ("Edge",   os.path.join(HOME, ".config/microsoft-edge")),
            ("Brave",  os.path.join(HOME, ".config/BraveSoftware/Brave-Browser"))]

def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _chromium_ext_name(ext_dir, ext_id):
    """Имя расширения по папке <id> (берём самую свежую версию). Graceful."""
    try:
        versions = [v for v in os.listdir(ext_dir)
                    if os.path.isdir(os.path.join(ext_dir, v))]
    except OSError:
        return ext_id
    for ver in sorted(versions, reverse=True):
        vdir = os.path.join(ext_dir, ver)
        man = _read_json(os.path.join(vdir, "manifest.json"))
        if not isinstance(man, dict):
            continue
        messages = None
        name = (man.get("name") or "").strip()
        if name.startswith("__MSG_"):
            default_locale = (man.get("default_locale") or "en")
            for loc in (default_locale, "en", "en_US"):
                mp = os.path.join(vdir, "_locales", loc, "messages.json")
                messages = _read_json(mp)
                if messages:
                    break
        resolved = parse_chromium_extension(man, messages)
        if resolved:
            return resolved
    return ext_id

def list_browser_extensions():
    """Установленные расширения браузеров: [(браузер, имя, id)]. Read-only, graceful."""
    import glob
    out = []
    seen = set()
    # Chromium-семейство: <UserData>/<Profile>/Extensions/<id>/<version>/manifest.json
    for browser, base in _chromium_ext_profiles():
        if not os.path.isdir(base):
            continue
        for ext_root in glob.glob(os.path.join(base, "*", "Extensions")):
            if not os.path.isdir(ext_root):
                continue
            for ext_id in sorted(os.listdir(ext_root)):
                ext_dir = os.path.join(ext_root, ext_id)
                if not os.path.isdir(ext_dir):
                    continue
                key = (browser, ext_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append((browser, _chromium_ext_name(ext_dir, ext_id), ext_id))
    # Firefox: <profile>/extensions/*.xpi — имя/id из имени файла (упрощённо)
    if SYSTEM == "Darwin":
        ff = os.path.join(HOME, "Library/Application Support/Firefox/Profiles")
    elif SYSTEM == "Windows":
        roam = os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming"))
        ff = os.path.join(roam, "Mozilla", "Firefox", "Profiles")
    else:
        ff = os.path.join(HOME, ".mozilla/firefox")
    for xpi in glob.glob(os.path.join(ff, "*", "extensions", "*.xpi")):
        ext_id = os.path.splitext(os.path.basename(xpi))[0]
        key = ("Firefox", ext_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(("Firefox", ext_id, ext_id))
    return out

# ---------- здоровье диска ----------
def disk_advice(disk_pct, ram_pct, batt_pct=None):
    """Безопасные советы по метрикам. Возвращает [(цвет, текст)]."""
    out = []
    if disk_pct >= 90:
        out.append((RED, L("Диск заполнен на {p}% — запустите Сканер и удалите дубликаты/крупные файлы.").format(p=int(disk_pct))))
    elif disk_pct >= 80:
        out.append((YELLOW, L("Диск на {p}% — очистите кэши и старые загрузки.").format(p=int(disk_pct))))
    if ram_pct >= 85:
        out.append((RED, L("Память на {p}% — завершите тяжёлые процессы.").format(p=int(ram_pct))))
    elif ram_pct >= 70:
        out.append((YELLOW, L("Память на {p}% — близко к пределу.").format(p=int(ram_pct))))
    if batt_pct is not None and 0 < batt_pct <= 20:
        out.append((YELLOW, L("Низкий заряд ({p}%) — подключите зарядку.").format(p=int(batt_pct))))
    if not out:
        out.append((GREEN, L("Система в порядке — критичных проблем нет.")))
    return out

# ---------- Режим фокуса (обратимая пауза процессов) ----------
# Жёсткий чёрный список: эти процессы НИКОГДА не приостанавливаем — пауза
# системного процесса способна «заморозить» рабочий стол или весь сеанс.
# Сравнение по имени без учёта регистра. Списки расширены критичными для
# каждой ОС службами (звук, оконный сервер, оболочка, ввод, безопасность).
FOCUS_BLACKLIST_UNIX = (
    # ядро/инициализация/сессия
    "kernel_task", "launchd", "init", "systemd", "logind", "systemd-logind",
    "loginwindow", "WindowServer", "Window Manager", "SystemUIServer",
    # оболочка рабочего стола (macOS / Linux DE)
    "Finder", "Dock", "Spotlight", "ControlCenter", "NotificationCenter",
    "gnome-shell", "plasmashell", "kwin", "kwin_x11", "kwin_wayland",
    "Xorg", "Xwayland", "mutter", "cinnamon", "xfwm4", "marco",
    # звук / ввод / питание
    "coreaudiod", "pulseaudio", "pipewire", "wireplumber",
    "dbus-daemon", "dbus", "powerd", "ibus-daemon",
    # безопасность / агенты системы
    "securityd", "trustd", "opendirectoryd", "mds", "mds_stores",
    "cfprefsd", "distnoted", "syslogd", "polkitd",
    # сам интерпретатор/приложение
    "python", "python3", "Python", "krylan", "krylan.py",
)
FOCUS_BLACKLIST_WINDOWS = (
    # ядро/инициализация/сессия
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "fontdrvhost.exe",
    # оболочка рабочего стола / ввод / звин
    "explorer.exe", "dwm.exe", "ctfmon.exe", "ShellExperienceHost.exe",
    "StartMenuExperienceHost.exe", "SearchHost.exe", "sihost.exe",
    "audiodg.exe", "taskhostw.exe", "RuntimeBroker.exe",
    # безопасность / антивирус
    "MsMpEng.exe", "SecurityHealthService.exe", "spoolsv.exe",
    # сам интерпретатор/приложение
    "python.exe", "pythonw.exe", "krylan.exe",
)

def focus_blacklist():
    """Чёрный список имён для текущей ОС (нижний регистр для сравнения)."""
    base = FOCUS_BLACKLIST_WINDOWS if SYSTEM == "Windows" else FOCUS_BLACKLIST_UNIX
    return {n.lower() for n in base}

def is_suspendable(proc_info, self_pid=None, min_pid=100):
    """Можно ли безопасно (обратимо) приостановить процесс в Режиме фокуса.

    Вход: dict / namedtuple / объект с полями name (str), pid (int) и
    опционально cpu, mem. psutil НЕ вызывается — функция чистая и тестируемая.

    Возвращает False (НЕ трогаем) для:
      • записей без имени или pid;
      • самого KRYLAN (self_pid; по умолчанию os.getpid());
      • низких PID (pid < min_pid) — это почти всегда системные службы/ядро;
        на Windows под этот порог попадают System(4)/csrss/wininit и т. п.;
      • имён из жёсткого чёрного списка текущей ОС (без учёта регистра).
    Иначе True — это пользовательское фоновое приложение.
    """
    if self_pid is None:
        self_pid = os.getpid()
    name = _proc_field(proc_info, "name")
    pid = _proc_field(proc_info, "pid")
    if not name or pid is None:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid == int(self_pid):
        return False
    if pid < int(min_pid):
        return False
    if str(name).lower() in focus_blacklist():
        return False
    return True

def pick_focus_targets(processes, current_app=None, self_pid=None,
                       min_cpu=0.0, min_mem=0):
    """Выбрать кандидатов на обратимую паузу — тяжёлые фоновые приложения.

    Вход: список процессов (dict/namedtuple/объект) c name/pid/cpu/mem.
    current_app — имя активного приложения (его НЕ приостанавливаем, чтобы
    не заморозить окно, с которым работает пользователь).
    min_cpu/min_mem — необязательные пороги «тяжести» (по умолчанию 0 — берём
    всё suspendable). psutil не вызывается — функция чистая.

    Возвращает список suspendable-кандидатов, отсортированный по убыванию
    (mem, cpu): самые прожорливые первыми.
    """
    cur = str(current_app).lower() if current_app else None
    out = []
    for p in processes:
        if not is_suspendable(p, self_pid=self_pid):
            continue
        name = str(_proc_field(p, "name") or "")
        if cur and name.lower() == cur:
            continue
        cpu = _proc_field(p, "cpu") or 0
        mem = _proc_field(p, "mem") or 0
        if cpu < min_cpu and mem < min_mem:
            continue
        out.append(p)
    out.sort(key=lambda p: (_proc_field(p, "mem") or 0, _proc_field(p, "cpu") or 0),
             reverse=True)
    return out

def focus_suspend(pids):
    """Обратимо приостановить процессы по PID через psutil (SIGSTOP/нативно).

    Никогда не бросает: исчезнувший процесс / отказ в доступе пропускаются.
    Финальная проверка безопасности (is_suspendable) выполняется и здесь —
    даже если в pids случайно попал системный процесс, он не будет тронут.
    Возвращает список PID, которые РЕАЛЬНО были приостановлены.
    """
    done = []
    for pid in pids:
        try:
            p = psutil.Process(int(pid))
            if not is_suspendable({"name": p.name(), "pid": p.pid}):
                continue
            p.suspend()
            done.append(int(pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue
    return done

def focus_resume(pids):
    """Возобновить процессы по PID (resume). Зеркало focus_suspend.

    Никогда не бросает. Возвращает список PID, которые реально возобновлены
    (исчезнувшие считаем «возобновлёнными» — их и так больше нет в паузе).
    """
    done = []
    for pid in pids:
        try:
            psutil.Process(int(pid)).resume()
            done.append(int(pid))
        except psutil.NoSuchProcess:
            done.append(int(pid))   # процесса нет — он точно не «заморожен»
        except psutil.AccessDenied:
            continue
        except Exception:
            continue
    return done

# Глобальный набор приостановленных PID — страховка для atexit-резюма,
# чтобы НИЧЕГО не осталось «замороженным» даже при аварийном выходе.
_FOCUS_PAUSED_GLOBAL = set()

def _focus_resume_atexit():
    """Гарантированный resume всех приостановленных при завершении процесса."""
    if _FOCUS_PAUSED_GLOBAL:
        focus_resume(list(_FOCUS_PAUSED_GLOBAL))
        _FOCUS_PAUSED_GLOBAL.clear()

atexit.register(_focus_resume_atexit)

def _proc_field(p, key):
    """Достаёт поле из dict / namedtuple / объекта (name, pid, cpu, mem)."""
    if isinstance(p, dict):
        return p.get(key)
    return getattr(p, key, None)

def focus_candidates(procs, self_pid=None):
    """Чистый фильтр кандидатов на «паузу» Режима фокуса.

    Вход: список процессов. Каждый элемент — dict ИЛИ namedtuple/объект
    с полями: name (str), pid (int), cpu (float, %), mem (int, байты RSS).
    psutil здесь НЕ вызывается — функция полностью тестируема.

    Исключаются: процессы из чёрного списка (по имени, без учёта регистра),
    сам KRYLAN (self_pid; по умолчанию os.getpid()), записи без имени/pid.
    Возвращает список тех же элементов, отсортированный по убыванию
    (mem, cpu) — самые тяжёлые первыми.
    """
    if self_pid is None:
        self_pid = os.getpid()
    bl = focus_blacklist()
    out = []
    for p in procs:
        name = _proc_field(p, "name")
        pid = _proc_field(p, "pid")
        if not name or pid is None:
            continue
        if int(pid) == int(self_pid):
            continue
        if str(name).lower() in bl:
            continue
        out.append(p)
    out.sort(key=lambda p: (_proc_field(p, "mem") or 0, _proc_field(p, "cpu") or 0),
             reverse=True)
    return out

def disk_health_report():
    lines = ["🩺  " + L("Здоровье диска") + "\n\n"]
    try:
        if SYSTEM == "Darwin":
            out = run(["diskutil", "info", "disk0"], timeout=20).stdout or ""
            for row in out.splitlines():
                if any(k in row for k in ("SMART", "Device / Media Name", "Disk Size", "Solid State")):
                    lines.append("  " + row.strip() + "\n")
            ok = "Verified" in out
            lines.append("\n  " + L("Статус: ") + (L("✅ SMART в норме (Verified)") if ok else L("⚠️ проверьте диск в Дисковой утилите")) + "\n")
        elif SYSTEM == "Windows":
            # wmic УДАЛЁН в Windows 11 24H2 → используем PowerShell Get-PhysicalDisk.
            # Format-List стабильно парсится и не режет колонки по ширине.
            out = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                       "Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,Size "
                       "| Format-List"], timeout=30).stdout or ""
            body = [r.strip() for r in out.splitlines() if r.strip()]
            if body:
                lines += ["  " + r + "\n" for r in body]
            else:
                lines.append("  " + L("не удалось прочитать SMART: {e}").format(e="Get-PhysicalDisk") + "\n")
            lines.append("\n  " + L("Статус «OK» = SMART в норме.") + "\n")
        else:
            r = run(["smartctl", "-H", "/dev/sda"], timeout=20)
            if r.returncode in (0, 4) and r.stdout:
                lines += ["  " + x + "\n" for x in r.stdout.splitlines()[-4:]]
            else:
                lines.append("  " + L("smartctl не найден: sudo apt install smartmontools") + "\n")
    except Exception as e:
        lines.append("  " + L("не удалось прочитать SMART: {e}").format(e=e) + "\n")
    du = psutil.disk_usage(HOME if SYSTEM != "Windows" else os.environ.get("SystemDrive", "C:") + "\\")
    lines.append("\n  " + L("Занято {pct}% · свободно {free} из {total}").format(pct=f"{du.percent:.0f}", free=human(du.free), total=human(du.total)) + "\n")
    if du.percent > 90:
        lines.append("  " + L("⚠️ Меньше 10% свободного места замедляет систему — освободите диск.") + "\n")
    return "".join(lines)

# ---------- Диск-доктор: read-only проверка диска на ошибки (аналог BoostSpeed) ----------
# ВАЖНО: только ЧТЕНИЕ. Ничего не чинит и не меняет:
#   • Windows: chkdsk БЕЗ флагов — read-only скан, без /f (не требует перезагрузки).
#   • macOS:   diskutil verifyVolume / — НЕ repairVolume.
#   • Linux:   smartctl -H — НЕ fsck (на смонтированном ФС никогда).
def parse_disk_check(text):
    """Парсер итога read-only проверки диска (chkdsk / verifyVolume) → dict.

    ЧИСТАЯ функция (тестируется на сэмплах). Возвращает:
      {"errors": bool|None, "summary": str}
        • errors=False — явно «ошибок не найдено» (No problems / appears to be OK …);
        • errors=True  — явно найдены ошибки / проблемы / corruption;
        • errors=None  — не смогли уверенно определить (пустой/непонятный вывод).
    Берёт первую уверенную сигнатуру; «ошибки» имеют приоритет над «всё ок»,
    чтобы не проглядеть реальную проблему."""
    low = (text or "").lower()
    if not low.strip():
        return {"errors": None, "summary": ""}
    # сначала ищем явные индикаторы ПРОБЛЕМ (приоритет над «ок»)
    bad = (
        "found problems", "errors found", "corruption", "corrupt",
        "failed to verify", "could not be verified",
        "windows found problems", "errors on the volume",
        "bad sectors", "the volume was found to be corrupt",
        "repair the volume",
    )
    for sig in bad:
        if sig in low:
            return {"errors": True, "summary": L("⚠️ Найдены ошибки — нужна проверка/ремонт.")}
    good = (
        "no problems", "found no problems", "appears to be ok",
        "the volume appears to be ok", "windows has scanned the file system and found no problems",
        "no further action is required", "0 kb in bad sectors",
        "the volume seems to be ok", "verification successful",
    )
    for sig in good:
        if sig in low:
            return {"errors": False, "summary": L("✅ Ошибок не найдено — диск в порядке.")}
    return {"errors": None, "summary": L("Не удалось определить итог — см. вывод выше.")}

def disk_doctor_report():
    """Read-only «Диск-доктор»: проверка диска на ошибки + здоровье, по ОС.
    Ничего не чинит и не меняет. Команды через run() (без консолей, с таймаутами,
    graceful при отсутствии бинарника/прав)."""
    lines = ["🩺  " + L("Диск-доктор (только чтение)") + "\n\n"]
    raw = ""
    try:
        if SYSTEM == "Windows":
            # chkdsk БЕЗ /f → read-only скан, не требует перезагрузки, ничего не правит.
            drive = os.environ.get("SystemDrive", "C:")
            r = run(["chkdsk", drive], timeout=300)
            raw = (r.stdout or "") + "\n" + (r.stderr or "")
            if r.returncode == 127:
                lines.append("  " + L("chkdsk недоступен в этой среде.") + "\n")
            elif not raw.strip():
                lines.append("  " + L("Нет вывода — возможно, нужны права администратора.") + "\n")
            else:
                tail = [x.strip() for x in raw.splitlines() if x.strip()][-6:]
                lines += ["  " + x + "\n" for x in tail]
            verdict = parse_disk_check(raw)
            lines.append("\n  " + verdict["summary"] + "\n")
            # дополняем SMART, если доступно
            sr = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                      "Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus | Format-List"],
                     timeout=30)
            sbody = [x.strip() for x in (sr.stdout or "").splitlines() if x.strip()]
            if sbody:
                lines.append("\n  " + L("SMART (здоровье диска):") + "\n")
                lines += ["    " + x + "\n" for x in sbody]
        elif SYSTEM == "Darwin":
            # verifyVolume — read-only; repairVolume НЕ вызываем.
            r = run(["diskutil", "verifyVolume", "/"], timeout=300)
            raw = (r.stdout or "") + "\n" + (r.stderr or "")
            if r.returncode == 127:
                lines.append("  " + L("diskutil недоступен в этой среде.") + "\n")
            elif not raw.strip():
                lines.append("  " + L("Нет вывода — возможно, нужны права администратора.") + "\n")
            else:
                tail = [x.strip() for x in raw.splitlines() if x.strip()][-8:]
                lines += ["  " + x + "\n" for x in tail]
            verdict = parse_disk_check(raw)
            lines.append("\n  " + verdict["summary"] + "\n")
        else:
            # Linux: только SMART (read-only). fsck на смонтированном НЕ запускаем.
            r = run(["smartctl", "-H", "/dev/sda"], timeout=30)
            if r.returncode == 127:
                lines.append("  " + L("Установите smartmontools: sudo apt install smartmontools") + "\n")
            elif r.stdout:
                lines += ["  " + x + "\n" for x in r.stdout.splitlines()[-6:]]
                verdict = parse_disk_check(r.stdout)
                if verdict["errors"] is not None:
                    lines.append("\n  " + verdict["summary"] + "\n")
            else:
                lines.append("  " + L("Не удалось прочитать SMART (нужны права root?).") + "\n")
            lines.append("\n  " + L("ℹ️ fsck на смонтированном диске не запускается — это небезопасно.") + "\n")
    except Exception as e:
        lines.append("  " + L("не удалось выполнить проверку: {e}").format(e=e) + "\n")
    lines.append("\n  " + L("Диск-доктор только читает состояние и ничего не меняет.") + "\n")
    return "".join(lines)

# ---------- вес/статус автозагрузки (Windows StartupApproved) ----------
def parse_startup_approved(blob):
    """Статус записи автозагрузки из реестра ...\\StartupApproved\\Run.

    ЧИСТАЯ функция (тестируется). Значение — REG_BINARY (12 байт): первый байт
    кодирует включённость. Соглашение Windows: чётный первый байт = ВКЛЮЧЕНО
    (0x02, 0x06 …), нечётный = ОТКЛЮЧЕНО (0x03, 0x07 …). Принимает bytes/
    bytearray/list[int]; при пустом/непонятном входе → None (неизвестно).
    Возвращает True (вкл) / False (выкл) / None (неизвестно)."""
    if blob is None:
        return None
    try:
        first = blob[0]
    except (IndexError, TypeError):
        return None
    if isinstance(first, (bytes, bytearray)):
        first = first[0] if first else None
    if first is None:
        return None
    try:
        return (int(first) % 2) == 0
    except (TypeError, ValueError):
        return None

def ctxmenu_status(values):
    """Статус verb-пункта контекстного меню Проводника по списку ИМЁН его значений.

    ЧИСТАЯ функция (тестируется без winreg). Соглашение Windows: пункт
    `HKCR\\...\\shell\\<verb>` СКРЫТ из меню, если у него есть строковое
    значение `LegacyDisable` (само значение пустое; важно лишь наличие).
    Добавление/удаление этого флага скрывает/показывает пункт ОБРАТИМО,
    без удаления ключа.

    Принимает любой итерируемый список имён значений (регистр игнорируется).
    Возвращает "выключен", если LegacyDisable присутствует, иначе "включён"."""
    try:
        names = {str(n).lower() for n in (values or [])}
    except TypeError:
        names = set()
    return "выключен" if "legacydisable" in names else "включён"

# ---------- Software Updater: устаревшие приложения через нативный менеджер ----------
# Только ЧТЕНИЕ списка. Обновление пользователь запускает сам (команда-подсказка).
def parse_brew_outdated(text):
    """`brew outdated --verbose` → [(имя, текущая, новая)]."""
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or "<" not in ln:
            continue
        left, new = ln.rsplit("<", 1)
        left, new = left.strip(), new.strip()
        if "(" in left and ")" in left:
            name = left.split("(")[0].strip()
            cur = left[left.find("(") + 1:left.find(")")].strip()
        else:
            parts = left.split()
            name = parts[0] if parts else left
            cur = parts[1] if len(parts) > 1 else "?"
        if name:
            out.append((name, cur, new))
    return out

def parse_apt_upgradable(text):
    """`apt list --upgradable` → [(имя, текущая, новая)]."""
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if "/" not in ln or "[upgradable from:" not in ln:
            continue
        name = ln.split("/", 1)[0].strip()
        parts = ln.split()
        new = parts[1] if len(parts) > 1 else "?"
        cur = ln.split("[upgradable from:", 1)[1].strip(" ]")
        out.append((name, cur, new))
    return out

def parse_winget_upgrade(text):
    """`winget upgrade` (табличный вывод) → [(имя, текущая, новая)]."""
    import re
    lines = [l for l in text.splitlines() if l.strip()]
    start = 0
    for i, l in enumerate(lines):
        s = l.strip()
        if s and set(s) <= set("- "):   # строка-разделитель из дефисов
            start = i + 1
            break
    out = []
    for l in lines[start:]:
        cols = re.split(r"\s{2,}", l.strip())
        if len(cols) >= 4:
            name, _id, cur, new = cols[0], cols[1], cols[2], cols[3]
            if cur and new and cur != new and not cur.lower().startswith("version"):
                out.append((name, cur, new))
    return out

def list_updates():
    """Список устаревших приложений через менеджер пакетов ОС.
    Возвращает (manager|None, items, hint). Команды только читают состояние."""
    # run() сам прячет консоль на Windows и не бросает (returncode 127 = нет бинарника).
    if SYSTEM == "Darwin":
        r = run(["brew", "outdated", "--verbose"], timeout=90)
        if r.returncode == 127:
            return (None, [], L("Менеджер пакетов не найден (brew / winget / apt)."))
        return ("Homebrew", parse_brew_outdated(r.stdout or ""), L("Обновить всё:  brew upgrade"))
    if SYSTEM == "Windows":
        r = run(["winget", "upgrade"], timeout=120)
        if r.returncode == 127:
            return (None, [], L("Менеджер пакетов не найден (brew / winget / apt)."))
        return ("winget", parse_winget_upgrade(r.stdout or ""), L("Обновить всё:  winget upgrade --all"))
    if SYSTEM == "Linux":
        r = run(["apt", "list", "--upgradable"], timeout=90)
        if r.returncode == 127:
            return (None, [], L("Менеджер пакетов не найден (brew / winget / apt)."))
        return ("apt", parse_apt_upgradable(r.stdout or ""), L("Обновить всё:  sudo apt upgrade"))
    return (None, [], L("ОС не поддерживается."))

# ---------- Health Report: HTML-отчёт о состоянии и кандидатах на очистку ----------
def build_html_report(title, sections, generated=""):
    """Чистая функция: (заголовок, [(секция, [(метка, значение)])]) → HTML-строка.
    Без побочных эффектов — удобно тестировать."""
    import html as _h
    esc = _h.escape
    out = [
        f"<!doctype html><html lang='{LANG}'><head><meta charset='utf-8'>",
        f"<title>{esc(title)}</title>",
        "<style>",
        "body{margin:0;background:#11151d;color:#eef2f8;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}",
        ".wrap{max-width:760px;margin:0 auto;padding:32px 22px}",
        "h1{font-size:26px;margin:0 0 4px}.slogan{color:#37d39a;font-weight:700;margin:0 0 18px}",
        ".gen{color:#8a94a6;font-size:13px;margin-bottom:22px}",
        ".card{background:#222b3a;border-radius:16px;padding:18px 20px;margin:0 0 16px}",
        ".card h2{font-size:16px;margin:0 0 12px;color:#37d39a}",
        ".row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #333d4e}",
        ".row:last-child{border-bottom:0}.row .v{font-weight:700}",
        ".foot{color:#8a94a6;font-size:12px;margin-top:18px}",
        "</style></head><body><div class='wrap'>",
        f"<h1>🪽 {esc(title)}</h1>",
        f"<p class='slogan'>{esc(L('Дай устройству крылья'))}</p>",
    ]
    if generated:
        out.append(f"<p class='gen'>{esc(L('Сформировано:'))} {esc(generated)}</p>")
    for sec_title, rows in sections:
        out.append("<div class='card'>")
        out.append(f"<h2>{esc(sec_title)}</h2>")
        for label, value in rows:
            out.append(f"<div class='row'><span>{esc(str(label))}</span>"
                       f"<span class='v'>{esc(str(value))}</span></div>")
        out.append("</div>")
    out.append("<p class='foot'>" + esc(L("KRYLAN Desktop · только безопасная очистка (всё в Корзину). "
               "Создатель: Кырлан Александр Сергеевич.")) + "</p>")
    out.append("</div></body></html>")
    return "".join(out)

# ---------- headless-очистка (для планировщика) ----------
def clean_caches_headless(dry=False):
    """Содержимое кэшей → Корзина. Возвращает (байт, строки отчёта)."""
    freed, lines = 0, []
    for name, p in cleanup_targets():
        sz = dir_size(p); freed += sz
        lines.append(f"  {name}: {human(sz)}")
        if not dry:
            for n in os.listdir(p):
                safe_trash(os.path.join(p, n))
    return freed, lines

# ---------- «волшебная кнопка»: безопасная авто-оптимизация ----------
# Имена кэшей браузеров среди cleanup_targets() — чистим их ТОЛЬКО если
# соответствующий браузер закрыт (иначе содержимое заблокировано / опасно).
_BROWSER_CACHE_KEYS = {
    "Chrome": ("chrome", "google"),
    "Edge":   ("edge", "microsoft edge"),
    "Firefox":("firefox", "mozilla"),
    "Yandex": ("yandex",),
}

def _is_browser_cache(name):
    """name из cleanup_targets() относится к кэшу браузера? → метка браузера или None."""
    low = name.lower()
    for label, keys in _BROWSER_CACHE_KEYS.items():
        if any(k in low for k in keys):
            return label
    return None

# ---------- безопасный subprocess-хелпер ----------
def _no_window_kwargs():
    """Доп. kwargs для subprocess, чтобы на Windows GUI-приложение не мигало
    чёрным окном консоли при каждом вызове.

    • На Windows: creationflags=CREATE_NO_WINDOW + STARTUPINFO со SW_HIDE.
      Это надёжно прячет консоль и для GUI-, и для console-бинарников.
    • На остальных ОС: пустой dict (флага не существует).

    Применяется ВО ВСЕХ subprocess-вызовах приложения (см. run() и прямые
    subprocess.run в disk_health_report/list_updates/schedule_*/_boost_w)."""
    if SYSTEM != "Windows":
        return {}
    import subprocess
    kw = {}
    flags = 0
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    kw["creationflags"] = flags
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kw["startupinfo"] = si
    except Exception:
        pass
    return kw

def run(args, timeout=60):
    """Запускает команду без оболочки и возвращает CompletedProcess.

    Никогда не бросает: при отсутствии бинарника / таймауте / любой ошибке
    возвращает объект с returncode≠0 и пустым stdout (чтобы вызывающий код
    мог честно «пропустить с причиной» вместо падения). НЕ запрашивает sudo.

    На Windows прячет консольное окно (CREATE_NO_WINDOW) и принудительно
    задаёт stdin=DEVNULL — иначе PyInstaller --windowed (stdin/out=None)
    может уронить дочерний процесс, которому нужен дескриптор.
    """
    import subprocess
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL,
                              **_no_window_kwargs())
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "timeout")
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "not found")
    except Exception as e:  # PermissionError и пр.
        return subprocess.CompletedProcess(args, 1, "", str(e))

def has_root():
    """True, если процесс уже идёт с правами root/админа (БЕЗ запроса)."""
    try:
        if SYSTEM == "Windows":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False

# ---------- детект типа накопителя (SSD / HDD) ----------
def parse_physicaldisk_mediatype(text):
    """Парсер вывода PowerShell `Get-PhysicalDisk … MediaType` → "SSD"|"HDD"|None.

    ЧИСТАЯ функция (тестируется на сэмплах). MediaType может быть:
      • "SSD"          → SSD
      • "HDD"          → HDD
      • "Unspecified"  → не определили (None)
      • число 4/3      → 4=SSD, 3=HDD (числовой enum старых сборок)
    Берём первый информативный (не Unspecified) диск; «Unspecified» игнорируем
    в пользу явного SSD/HDD."""
    saw_ssd = saw_hdd = False
    for raw in (text or "").splitlines():
        # терпим формат "MediaType : SSD" (Format-List) и просто "SSD"
        val = raw.split(":", 1)[1] if ":" in raw else raw
        v = val.strip().lower()
        if not v:
            continue
        if "ssd" in v or v == "4":
            saw_ssd = True
        elif "hdd" in v or v == "3":
            saw_hdd = True
        # "unspecified"/"0"/прочее — пропускаем
    if saw_ssd:
        return "SSD"
    if saw_hdd:
        return "HDD"
    return None

def detect_media_type():
    """Тип системного накопителя: "SSD" | "HDD" | None (не определили).

    Чистый по контракту: использует только run()-хелпер, ничего не бросает.
      • Windows: PowerShell `Get-PhysicalDisk | Select MediaType` → SSD/HDD.
      • Linux:   `/sys/block/<dev>/queue/rotational` (0=SSD, 1=HDD).
      • macOS:   `diskutil info /` → строка "Solid State".
    """
    try:
        if SYSTEM == "Windows":
            # Format-List даёт стабильно парсимый "MediaType : SSD" без обрезки
            # по ширине терминала (Get-PhysicalDisk | Format-Table режет колонки).
            r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "Get-PhysicalDisk | Select-Object MediaType | Format-List"],
                    timeout=30)
            return parse_physicaldisk_mediatype(r.stdout or "")
        if SYSTEM == "Darwin":
            r = run(["diskutil", "info", "/"], timeout=20)
            for row in (r.stdout or "").splitlines():
                if "Solid State" in row:
                    return "SSD" if "Yes" in row else "HDD"
            return None
        # Linux: определяем блочное устройство, на котором смонтирован "/"
        dev = None
        rr = run(["findmnt", "-no", "SOURCE", "/"], timeout=10)
        src = (rr.stdout or "").strip()
        if src.startswith("/dev/"):
            import re
            base = os.path.basename(src)
            # nvme0n1p2 → nvme0n1 ; sda1 → sda
            m = re.match(r"(nvme\d+n\d+|[a-z]+)", base)
            if m:
                dev = m.group(1)
        if dev:
            rot_path = "/sys/block/%s/queue/rotational" % dev
            try:
                with open(rot_path) as f:
                    val = f.read().strip()
                return "HDD" if val == "1" else "SSD"
            except Exception:
                return None
        return None
    except Exception:
        return None

# ---------- чистый план обслуживания диска (TRIM / дефраг / пропуск) ----------
def disk_maintenance_plan(system, media_type, has_root):
    """Адаптивный план обслуживания накопителя — ЧИСТАЯ функция (легко тестить).

    Args:
        system:     "Windows" | "Darwin" | "Linux".
        media_type: "SSD" | "HDD" | None.
        has_root:   bool — есть ли уже права администратора (sudo НЕ запрашиваем).

    Returns:
        (command|None, label, do)  где
          command — список аргументов для run() или None (нечего выполнять);
          label   — человекочитаемая подпись (что сделано / почему пропущено);
          do      — bool: True → выполнить command; False → только пометка.

    Правила безопасности:
      • SSD НИКОГДА не дефрагментируется.
      • Шаги, требующие root без прав → do=False с причиной (без sudo-промптов).
      • macOS: TRIM автоматический, APFS не дефрагментируется → пометка.
    """
    if media_type is None:
        return (None, L("💽 Тип диска не определён — обслуживание пропущено"), False)

    if system == "Windows":
        # defrag.exe (и /L TRIM, и /O оптимизация) ТРЕБУЕТ прав администратора —
        # без них процесс завершится ошибкой/UAC-промптом. Без админа → пропуск.
        sysdrv = os.environ.get("SystemDrive", "C:")  # обычно "C:"
        if media_type == "SSD":
            if not has_root:
                return (None, L("💽 SSD: TRIM пропущен — нужны права администратора"), False)
            return (["defrag", sysdrv, "/L"],
                    L("💽 SSD: TRIM (defrag /L) выполнен"), True)
        # HDD → безопасная оптимизация (дефраг/консолидация)
        if not has_root:
            return (None, L("💽 HDD: оптимизация пропущена — нужны права администратора"), False)
        return (["defrag", sysdrv, "/O"],
                L("💽 HDD: дефрагментация (defrag /O) выполнена"), True)

    if system == "Darwin":
        if media_type == "SSD":
            return (None, L("💽 SSD (macOS): TRIM обслуживается системой автоматически"), False)
        return (None, L("💽 HDD (macOS/APFS): дефрагментация не требуется"), False)

    if system == "Linux":
        if media_type == "SSD":
            if has_root:
                return (["fstrim", "-v", "/"],
                        L("💽 SSD: TRIM (fstrim) выполнен"), True)
            return (None, L("💽 SSD: TRIM пропущен — нужны права root (fstrim)"), False)
        # HDD на ext4/btrfs/xfs дефрагментация обычно не нужна
        return (None, L("💽 HDD (Linux): дефрагментация обычно не требуется"), False)

    return (None, L("💽 Обслуживание диска недоступно для этой ОС"), False)

# ---------- ОС-зависимые безопасные шаги оптимизации ----------
def dns_flush_plan(system):
    """Команда сброса DNS-кэша по ОС → (command|None, label)."""
    if system == "Windows":
        return (["ipconfig", "/flushdns"], L("🌐 DNS-кэш сброшен (ipconfig /flushdns)"))
    if system == "Darwin":
        # на macOS обе команды требуют root; запускаем «как есть», при ошибке — пропуск
        return (["dscacheutil", "-flushcache"], L("🌐 DNS-кэш сброшен (dscacheutil)"))
    # Linux: resolvectl, иначе systemd-resolve
    return (["resolvectl", "flush-caches"], L("🌐 DNS-кэш сброшен (resolvectl)"))

def thumbnail_targets():
    """Каталоги/файлы кэша миниатюр для прямого удаления (Linux/Windows)."""
    import glob
    if SYSTEM == "Linux":
        d = os.path.join(HOME, ".cache", "thumbnails")
        return [d] if os.path.isdir(d) else []
    if SYSTEM == "Windows":
        local = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
        base = os.path.join(local, "Microsoft", "Windows", "Explorer")
        return glob.glob(os.path.join(base, "thumbcache_*.db"))
    return []

# ---------- journald vacuum (Linux): bounded, обратимо-безопасно ----------
def parse_journal_disk_usage(text):
    """Парсер вывода `journalctl --disk-usage` → размер в байтах (int) или None.

    ЧИСТАЯ функция (тестируется на сэмплах). Типичный вывод:
      "Archived and active journals take up 1.2G in the file system."
      "Journals take up 512.0M in the file system."
    Берём первое число с единицей (B/K/M/G/T, опционально с «B»/«iB»).
    Десятичные множители (×1000) journalctl и так печатает в SI-стиле, но мы
    используем двоичные множители (×1024) — для оценки этого достаточно.
    """
    import re
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*([KMGTP]?)i?B?\b", text)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    mult = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3,
            "T": 1024**4, "P": 1024**5}.get(m.group(2).upper(), 1)
    return int(num * mult)


def journald_vacuum(dry=False):
    """Журналы systemd (Linux): показать размер и (не-dry) ужать до 100 МБ.

    Bounded и безопасно: `journalctl --vacuum-size=100M` НЕ стирает журналы
    целиком — оставляет последние 100 МБ. sudo НЕ запрашиваем: если нет root —
    помечаем «нужны права», ничего не выполняя.

    Returns:
        (size|None, label, did)  где
          size  — текущий размер журналов в байтах (или None, если не прочитан);
          label — человекочитаемая подпись (что сделано / показано / пропущено);
          did   — bool: True → ужатие реально выполнено; False → только показ/пропуск.

    На не-Linux: (None, "", False) — шаг пропускается без записи.
    """
    if SYSTEM != "Linux":
        return (None, "", False)
    r = run(["journalctl", "--disk-usage"], timeout=20)
    size = parse_journal_disk_usage(r.stdout or "") if r.returncode == 0 else None
    size_h = human(size) if size is not None else "—"
    if dry:
        return (size, L("🗒 Журналы systemd будут ужаты до 100 МБ (сейчас {size})").format(size=size_h), False)
    if not has_root():
        # без root vacuum завершится ошибкой/без эффекта — честный пропуск, без sudo.
        return (size, L("⏭ Ужатие журналов пропущено — нужны права root"), False)
    rv = run(["journalctl", "--vacuum-size=100M"], timeout=120)
    if rv.returncode == 0:
        return (size, L("🗒 Журналы systemd ужаты до 100 МБ (было {size})").format(size=size_h), True)
    return (size, L("⏭ Ужатие журналов пропущено — нужны права root"), False)


# ---------- 🔗 битые ярлыки (broken shortcuts): report + Корзина по выбору ----------
def _desktop_entry_target_ok(path):
    """Существует ли цель .desktop-файла? True, если ярлык рабочий.

    Разбираем поля Exec=/TryExec=/URL=. Логика (как у freedesktop):
      • URL= (тип Link) → проверяем локальный путь (file:// или абсолютный);
        не-локальные схемы (http/…) считаем рабочими.
      • TryExec= → если задан, цель должна существовать/находиться в PATH.
      • Exec=    → первый токен (бинарник) должен существовать/быть в PATH.
    Пустой/нечитаемый/без полей → считаем рабочим (не трогаем из осторожности).
    ЧИСТАЯ по контракту (только чтение файла), без побочных эффектов.
    """
    import shlex
    exec_cmd = tryexec = url = None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("Exec=") and exec_cmd is None:
                    exec_cmd = line[len("Exec="):].strip()
                elif line.startswith("TryExec=") and tryexec is None:
                    tryexec = line[len("TryExec="):].strip()
                elif line.startswith("URL=") and url is None:
                    url = line[len("URL="):].strip()
    except Exception:
        return True  # нечитаемый — не наш кандидат на удаление

    def _bin_exists(token):
        if not token:
            return True
        # абсолютный путь — проверяем напрямую; иначе ищем в PATH
        if os.path.isabs(token):
            return os.path.exists(token)
        import shutil as _sh
        return _sh.which(token) is not None

    # тип Link (URL=)
    if url is not None and exec_cmd is None and tryexec is None:
        if url.startswith("file://"):
            from urllib.parse import urlparse, unquote
            return os.path.exists(unquote(urlparse(url).path))
        if os.path.isabs(url):
            return os.path.exists(url)
        return True  # http(s)/прочие схемы — рабочий ярлык
    # TryExec имеет приоритет (явная проверка наличия)
    if tryexec is not None:
        return _bin_exists(tryexec)
    if exec_cmd is not None:
        try:
            parts = shlex.split(exec_cmd)
        except ValueError:
            parts = exec_cmd.split()
        first = parts[0] if parts else ""
        return _bin_exists(first)
    return True  # ни одного целевого поля — не трогаем


def find_broken_shortcuts(bases=None):
    """Битые ярлыки в пользовательских каталогах: [(kind, path)].

    Linux/macOS: .desktop-файлы, чья цель (Exec/TryExec/URL) не существует.
    Windows: .lnk-файлы нулевого размера (минимальная проверка без парсинга
    бинарного формата) — kind="lnk-empty".
    Не дублирует find_broken_files (там — 0-байтовые файлы и битые симлинки):
    тут именно ярлыки с отсутствующей целью.

    Пропускаем скрытые/системные каталоги. Без побочных эффектов (тестируемо).
    """
    bases = bases or [os.path.join(HOME, d) for d in ("Desktop", "Documents", "Downloads")] + [
        os.path.join(HOME, ".local", "share", "applications")]
    skip = {".git", "node_modules", ".Trash", "Library", "AppData", ".cache"}
    found = []
    for base in bases:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip]
            for fn in files:
                fp = os.path.join(root, fn)
                low = fn.lower()
                try:
                    if low.endswith(".desktop"):
                        if os.path.islink(fp) and not os.path.exists(fp):
                            continue  # битый симлинк — забота find_broken_files
                        if not _desktop_entry_target_ok(fp):
                            found.append(("desktop", fp))
                    elif low.endswith(".lnk"):
                        # без парсинга бинарного .lnk: пустой ярлык заведомо битый
                        if not os.path.islink(fp) and os.path.isfile(fp) and os.path.getsize(fp) == 0:
                            found.append(("lnk-empty", fp))
                except OSError:
                    pass
    return found


# ---------- 📦🕒 большие и старые файлы (size ≥ N МБ И возраст ≥ M дней) ----------
def scan_big_old(base, min_mb=200, min_days=180, top=100, now=None):
    """Файлы размером ≥ min_mb МБ И не открывавшиеся/менявшиеся ≥ min_days дней.

    Возвращает отсортированный по размеру (убыв.) список [(size, path, age_days)].
    Объединяет два фильтра (размер × возраст) — это НЕ дубль old_downloads
    (только Загрузки, без порога размера) и не «крупные файлы» (без возраста).

    Безопасно и тестируемо:
      • симлинки пропускаем (os.path.islink) — не идём по чужим целям;
      • is_protected() исключает защищённые пути (HOME/стандартные папки/корень);
      • возраст = по max(mtime, atime) — «последнее касание» (открыли ИЛИ изменили);
      • now передаётся в тестах для детерминизма (по умолчанию time.time()).
    """
    import time
    if now is None:
        now = time.time()
    min_bytes = int(min_mb) * 1024 * 1024
    cutoff_age = int(min_days) * 86400
    out = []
    if not os.path.isdir(base):
        return out
    for root, _dirs, files in os.walk(base):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                if os.path.islink(fp):
                    continue
                st = os.stat(fp)
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


def optimize_all_plan(dry=False, browsers_running=None, emit=None):
    """Оркестратор «✨ Оптимизировать»: безопасные шаги БЕЗ подтверждений.

    Последовательно (всё обратимо — в Корзину):
      1) кэши/логи по ОС → Корзина (кэш браузера пропускается, если он запущен);
      2) пустые папки → Корзина;
      3) битые/нулевые файлы → Корзина.

    НЕ трогает: Корзину, приложения/процессы, дубли/похожие/крупные/старые загрузки.

    Args:
        dry:   True → ничего не удаляет, только считает (для тестов/предпросмотра).
        browsers_running: набор меток запущенных браузеров; None → определить через
                          running_browsers() (в dry оставляем пустым, чтобы не лезть в psutil).
        emit:  callable(text) — колбэк живого прогресса (по одному на каждый шаг).

    Returns:
        dict: {"freed": int, "steps": [str], "skipped": [str], "details": {...}}
    """
    if browsers_running is None:
        browsers_running = set() if dry else running_browsers()
    freed = 0
    steps, skipped = [], []
    details = {"caches": 0, "empty_dirs": 0, "broken": 0}

    def _say(msg):
        steps.append(msg)
        if emit:
            try: emit(msg)
            except Exception: pass

    # 1) кэши и логи по ОС
    cache_freed = 0
    for name, p in cleanup_targets():
        br = _is_browser_cache(name)
        if br and br in browsers_running:
            skipped.append(L("⏭ Кэш {br} пропущен — браузер запущен").format(br=br))
            continue
        sz = dir_size(p)
        cache_freed += sz
        if not dry:
            try:
                for n in os.listdir(p):
                    safe_trash(os.path.join(p, n))
            except Exception: pass
    freed += cache_freed
    details["caches"] = cache_freed
    _say(L("🧽 Кэши и логи → Корзина: {size}").format(size=human(cache_freed)))

    # 2) пустые папки
    empties = find_empty_dirs()
    if not dry:
        for d in empties:
            safe_trash(d)
    details["empty_dirs"] = len(empties)
    _say(L("📂 Пустые папки → Корзина: {n}").format(n=len(empties)))

    # 3) битые и нулевые файлы
    broken = find_broken_files()
    bfreed = 0
    for _kind, fp in broken:
        try: bfreed += os.path.getsize(fp)
        except Exception: pass
        if not dry:
            safe_trash(fp)
    freed += bfreed
    details["broken"] = len(broken)
    _say(L("🧩 Битые/пустые файлы → Корзина: {n}").format(n=len(broken)))

    # 4) кэш миниатюр (Linux ~/.cache/thumbnails · Windows thumbcache_*.db · macOS qlmanage)
    try:
        if SYSTEM == "Darwin":
            if not dry:
                r = run(["qlmanage", "-r", "cache"], timeout=30)
                if r.returncode == 0:
                    _say(L("🖼 Кэш миниатюр (Quick Look) сброшен"))
                else:
                    skipped.append(L("⏭ Кэш миниатюр пропущен ({why})").format(why=r.stderr.strip() or "qlmanage"))
            else:
                _say(L("🖼 Кэш миниатюр (Quick Look) сброшен"))
        else:
            tgts = thumbnail_targets()
            tfreed, removed, busy = 0, 0, 0
            for t in tgts:
                try:
                    tfreed += dir_size(t) if os.path.isdir(t) else os.path.getsize(t)
                except Exception:
                    pass
                if not dry:
                    try:
                        for n in (os.listdir(t) if os.path.isdir(t) else [None]):
                            if not safe_trash(os.path.join(t, n) if n else t):
                                raise OSError("protected or failed")
                        removed += 1
                    except Exception:
                        busy += 1   # файл занят (Explorer) → честный пропуск
            freed += tfreed
            details["thumbnails"] = tfreed
            if tgts:
                _say(L("🖼 Кэш миниатюр → Корзина: {size}").format(size=human(tfreed)))
                if busy:
                    skipped.append(L("⏭ Часть миниатюр занята — пропущено: {n}").format(n=busy))
            else:
                skipped.append(L("⏭ Кэш миниатюр не найден — пропущено"))
    except Exception as e:
        skipped.append(L("⏭ Кэш миниатюр пропущен ({why})").format(why=e))

    # 5) сброс DNS-кэша
    try:
        cmd, label = dns_flush_plan(SYSTEM)
        if dry:
            _say(label)
        else:
            r = run(cmd, timeout=20)
            ok = r.returncode == 0
            if not ok and SYSTEM == "Linux":
                # запасной вариант для старых systemd
                r = run(["systemd-resolve", "--flush-caches"], timeout=20)
                ok = r.returncode == 0
            if not ok and SYSTEM == "Darwin":
                # на macOS требуется также пнуть mDNSResponder
                run(["killall", "-HUP", "mDNSResponder"], timeout=10)
            if ok:
                if SYSTEM == "Darwin":
                    run(["killall", "-HUP", "mDNSResponder"], timeout=10)
                _say(label)
            else:
                skipped.append(L("⏭ Сброс DNS пропущен — нужны права/недоступно"))
    except Exception:
        skipped.append(L("⏭ Сброс DNS пропущен — нужны права/недоступно"))

    # 6) обслуживание диска: детект SSD/HDD → TRIM / дефраг / пропуск-с-причиной
    try:
        media = detect_media_type()
        details["media_type"] = media
        cmd, label, do = disk_maintenance_plan(SYSTEM, media, has_root())
        if not do:
            skipped.append(label)            # пометка-причина (mac авто, нет root, SSD не дефраг и т.п.)
        elif dry:
            _say(label)
        else:
            r = run(cmd, timeout=300)
            if r.returncode == 0:
                _say(label)
            else:
                skipped.append(L("⏭ Обслуживание диска пропущено — нет прав/недоступно"))
    except Exception:
        skipped.append(L("⏭ Обслуживание диска пропущено — нет прав/недоступно"))

    # 7) пакетные кэши/логи менеджеров (без root → пропуск)
    try:
        if SYSTEM == "Darwin":
            if run(["brew", "--version"], timeout=15).returncode == 0:
                if dry:
                    _say(L("📦 Кэш Homebrew очищен (brew cleanup)"))
                else:
                    r = run(["brew", "cleanup", "-s"], timeout=180)
                    if r.returncode == 0:
                        _say(L("📦 Кэш Homebrew очищен (brew cleanup)"))
                    else:
                        skipped.append(L("⏭ brew cleanup пропущен"))
            else:
                skipped.append(L("⏭ Homebrew не установлен — пропущено"))
        elif SYSTEM == "Linux":
            if has_root():
                if not dry:
                    run(["apt-get", "clean"], timeout=120)
                _say(L("📦 Кэш apt и журналы systemd очищены"))
            else:
                skipped.append(L("⏭ Кэш apt/журналы пропущены — нужны права root"))
        # Windows: безопасного userland пакетного кэша нет → молча пропускаем
    except Exception:
        skipped.append(L("⏭ Очистка пакетных кэшей пропущена"))

    # 7b) journald vacuum (Linux): bounded — ужать журналы до 100 МБ (оставляет хвост)
    try:
        if SYSTEM == "Linux":
            jsize, jlabel, jdid = journald_vacuum(dry=dry)
            if jsize is not None:
                details["journal"] = jsize
            if jdid or dry:
                _say(jlabel)
            else:
                skipped.append(jlabel)
    except Exception:
        skipped.append(L("⏭ Ужатие журналов пропущено — нужны права root"))

    # 8) освобождение неактивной памяти (безопасно, где есть)
    try:
        if SYSTEM == "Darwin":
            if has_root():
                if not dry:
                    run(["purge"], timeout=60)
                _say(L("🧠 Неактивная память освобождена (purge)"))
            else:
                skipped.append(L("⏭ Освобождение памяти пропущено — нужны права root (purge)"))
        elif SYSTEM == "Linux":
            if not dry:
                run(["sync"], timeout=30)   # сброс буферов на диск (без root)
            _say(L("🧠 Буферы записи сброшены (sync)"))
            if not has_root():
                skipped.append(L("⏭ Глубокая очистка кэшей памяти пропущена — нужны права root"))
        else:
            skipped.append(L("⏭ Освобождение памяти: безопасного способа в Windows нет — пропущено"))
    except Exception:
        skipped.append(L("⏭ Освобождение памяти пропущено"))

    return {"freed": freed, "steps": steps, "skipped": skipped, "details": details}

# ---------- 👁 предпросмотр оптимизации (dry-run, строго read-only) ----------
def optimize_preview(system, media_type, has_root, browsers_running=None):
    """«Сухой» отчёт: ЧТО сделает «✨ Оптимизировать» и СКОЛЬКО освободит —
    БЕЗ единого изменения на диске.

    ЧИСТАЯ и read-only функция (легко тестируется): принимает параметры
    устройства, чтобы не зависеть от detect_media_type()/has_root()/psutil.
    Никаких safe_trash/run/команд — только dir_size, find_* и план-функции
    (disk_maintenance_plan / dns_flush_plan), у которых нет побочных эффектов.

    Args:
        system:     "Windows" | "Darwin" | "Linux".
        media_type: "SSD" | "HDD" | None.
        has_root:   bool — есть ли уже права администратора/root.
        browsers_running: набор меток запущенных браузеров (по умолчанию пусто —
                          в предпросмотре не лезем в psutil).

    Returns:
        dict: {
          "will_do":  [str],   # шаги, которые реально выполнятся на устройстве
          "skipped":  [str],   # шаги, которые будут пропущены (с причиной)
          "freed_est": int,    # оценка освобождения в байтах (кэши+битые+миниатюры)
          "details":  {...},   # caches/empty_dirs/broken/thumbnails/media_type
        }
    """
    if browsers_running is None:
        browsers_running = set()
    will_do, skipped = [], []
    freed_est = 0
    details = {"caches": 0, "empty_dirs": 0, "broken": 0, "media_type": media_type}

    # 1) кэши и логи по ОС (только подсчёт)
    cache_est = 0
    for name, p in cleanup_targets():
        br = _is_browser_cache(name)
        if br and br in browsers_running:
            skipped.append(L("⏭ Кэш {br} пропущен — браузер запущен").format(br=br))
            continue
        cache_est += dir_size(p)
    freed_est += cache_est
    details["caches"] = cache_est
    will_do.append(L("🧽 Кэши и логи → Корзина: {size} (предпросмотр)").format(size=human(cache_est)))

    # 2) пустые папки (только подсчёт)
    empties = find_empty_dirs()
    details["empty_dirs"] = len(empties)
    will_do.append(L("📂 Пустые папки → Корзина: {n} (предпросмотр)").format(n=len(empties)))

    # 3) битые/нулевые файлы (только подсчёт размера)
    broken = find_broken_files()
    bfreed = 0
    for _kind, fp in broken:
        try: bfreed += os.path.getsize(fp)
        except Exception: pass
    freed_est += bfreed
    details["broken"] = len(broken)
    will_do.append(L("🧩 Битые/пустые файлы → Корзина: {n} (предпросмотр)").format(n=len(broken)))

    # 4) кэш миниатюр (read-only оценка)
    if system == "Darwin":
        will_do.append(L("🖼 Кэш миниатюр (Quick Look) будет сброшен"))
    else:
        tgts = thumbnail_targets()
        if tgts:
            tfreed = 0
            for t in tgts:
                try:
                    tfreed += dir_size(t) if os.path.isdir(t) else os.path.getsize(t)
                except Exception: pass
            freed_est += tfreed
            details["thumbnails"] = tfreed
            will_do.append(L("🖼 Кэш миниатюр → Корзина: {size} (предпросмотр)").format(size=human(tfreed)))
        else:
            skipped.append(L("⏭ Кэш миниатюр не найден — пропущено"))

    # 5) сброс DNS-кэша — на всех ОС есть команда, в реальном прогоне может
    #    упасть без прав, но план показываем как «будет выполнено».
    will_do.append(L("🌐 DNS-кэш будет сброшен"))

    # 6) обслуживание диска: тот же план, что и в реальном прогоне
    cmd, label, do = disk_maintenance_plan(system, media_type, has_root)
    if do:
        will_do.append(label)
    else:
        skipped.append(label)

    # 7) пакетные кэши/логи менеджеров (зависят от ОС/прав)
    if system == "Darwin":
        # наличие brew read-only не проверяем в предпросмотре — показываем как план
        will_do.append(L("📦 Кэш Homebrew будет очищен (brew cleanup)"))
    elif system == "Linux":
        if has_root:
            will_do.append(L("📦 Кэш apt и журналы systemd будут очищены"))
        else:
            skipped.append(L("⏭ Кэш apt/журналы пропущены — нужны права root"))
        # journald vacuum (read-only показ размера; реально ужмётся при наличии root)
        if system == SYSTEM:   # размер читаем только на «своей» ОС, иначе бинарника нет
            jsize, _lbl, _did = journald_vacuum(dry=True)
            jh = human(jsize) if jsize is not None else "—"
        else:
            jh = "—"
        if has_root:
            will_do.append(L("🗒 Журналы systemd будут ужаты до 100 МБ (сейчас {size})").format(size=jh))
        else:
            skipped.append(L("⏭ Ужатие журналов пропущено — нужны права root"))
    # Windows: безопасного userland пакетного кэша нет → ничего не добавляем

    # 8) освобождение неактивной памяти
    if system == "Darwin":
        if has_root:
            will_do.append(L("🧠 Неактивная память будет освобождена (purge)"))
        else:
            skipped.append(L("⏭ Освобождение памяти пропущено — нужны права root (purge)"))
    elif system == "Linux":
        will_do.append(L("🧠 Буферы записи будут сброшены (sync)"))
        if not has_root:
            skipped.append(L("⏭ Глубокая очистка кэшей памяти пропущена — нужны права root"))
    else:
        skipped.append(L("⏭ Освобождение памяти: безопасного способа в Windows нет — пропущено"))

    return {"will_do": will_do, "skipped": skipped,
            "freed_est": freed_est, "details": details}

# ====================================================================
# ===================  АВТОПИЛОТ (кросс-платформенно)  ===============
# ====================================================================
# Фоновый страж следит за памятью и при пике сам безопасно чистит кэши
# (всё в Корзину через safe_trash). НИКОГДА: реестр, дефраг SSD, остановка
# служб, фейк-бустеры. Логика «решения» вынесена в чистую функцию ради
# тестируемости; UI и поток лишь её используют.

AUTOPILOT_DEFAULTS = {
    "enabled": False,        # страж активен
    "threshold": 85,         # порог ОЗУ, % (пик)
    "interval": 30,          # период проверки, сек
    "streak": 3,             # сколько проверок подряд выше порога → действие
    "close_browsers": False, # закрывать фоновые браузеры при пике (по умолч. ВЫКЛ)
    "autostart": False,      # запуск стража при входе в систему
}

def config_dir():
    """Каталог конфигурации per-OS (без внешних зависимостей):
      • Windows → %APPDATA%\\KRYLAN
      • macOS   → ~/Library/Application Support/KRYLAN
      • Linux   → $XDG_CONFIG_HOME или ~/.config → /KRYLAN
    """
    if SYSTEM == "Windows":
        base = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
    elif SYSTEM == "Darwin":
        base = os.path.join(HOME, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
    return os.path.join(base, "KRYLAN")

def config_path():
    return os.path.join(config_dir(), "autopilot.json")

def autopilot_log_path():
    return os.path.join(config_dir(), "autopilot.log")

def load_autopilot_config():
    """Читает настройки автопилота из JSON, дополняя значениями по умолчанию.
    Никогда не бросает — при любой ошибке возвращает копию дефолтов."""
    cfg = dict(AUTOPILOT_DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in AUTOPILOT_DEFAULTS:
                if k in data:
                    cfg[k] = data[k]
    except Exception:
        pass
    # нормализация типов/границ
    try: cfg["threshold"] = max(50, min(99, int(cfg["threshold"])))
    except Exception: cfg["threshold"] = AUTOPILOT_DEFAULTS["threshold"]
    try: cfg["interval"] = max(5, min(3600, int(cfg["interval"])))
    except Exception: cfg["interval"] = AUTOPILOT_DEFAULTS["interval"]
    try: cfg["streak"] = max(1, min(10, int(cfg["streak"])))
    except Exception: cfg["streak"] = AUTOPILOT_DEFAULTS["streak"]
    for k in ("enabled", "close_browsers", "autostart"):
        cfg[k] = bool(cfg[k])
    return cfg

def save_autopilot_config(cfg):
    """Сохраняет настройки в JSON. Возвращает True при успехе, иначе False
    (не бросает — чтобы не ронять UI)."""
    try:
        os.makedirs(config_dir(), exist_ok=True)
        clean = {k: cfg.get(k, AUTOPILOT_DEFAULTS[k]) for k in AUTOPILOT_DEFAULTS}
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def autopilot_should_optimize(samples, threshold, streak):
    """Чистое решение стража: нужно ли запускать оптимизацию.

    samples — последовательность последних замеров RAM% (новые в конце).
    Возвращает True, если ПОСЛЕДНИЕ `streak` замеров ВСЕ строго выше threshold.
    Это «пик подряд N раз», как на Mac-флагмане. Без побочных эффектов —
    идеально для юнит-тестов.
    """
    try:
        streak = int(streak)
    except Exception:
        return False
    if streak < 1 or len(samples) < streak:
        return False
    tail = list(samples)[-streak:]
    return all(s > threshold for s in tail)

def close_background_browsers(active_name=None, self_pid=None):
    """Мягко завершает ФОНОВЫЕ браузеры (terminate(), не kill) кросс-платформенно.

    • Трогает только chrome/msedge/firefox/yandex (по имени процесса).
    • НЕ трогает активное окно (active_name) и собственный процесс.
    • НИКОГДА не убивает системные службы и не использует kill().
    Возвращает список завершённых имён (для журнала). Не бросает.
    """
    keys = ("chrome", "msedge", "firefox", "yandex")
    if self_pid is None:
        self_pid = os.getpid()
    active = (active_name or "").lower()
    # Семейство активного браузера (напр. "chrome") — НЕ трогаем целиком,
    # включая его дочерние процессы ("Google Chrome Helper"), иначе уроним
    # браузер, с которым пользователь сейчас работает.
    active_key = next((k for k in keys if k in active), None)
    closed = []
    for p in psutil.process_iter(["name", "pid"]):
        try:
            nm = (p.info.get("name") or "")
            low = nm.lower()
            if p.info.get("pid") == self_pid:
                continue
            if not any(k in low for k in keys):
                continue
            if active_key and active_key in low:   # активное семейство браузера — пропускаем
                continue
            p.terminate()                        # мягко — НЕ kill
            closed.append(nm)
        except Exception:
            continue
    return closed

def _foreground_app_name():
    """Имя активного (переднего) приложения — best-effort, кросс-платформенно.
    Нужно только чтобы НЕ закрыть браузер, с которым работает пользователь.
    При любой ошибке/недоступности возвращает '' (тогда закрываем все фоновые
    одинаково — безопасно, т.к. это включается лишь явным переключателем)."""
    try:
        if SYSTEM == "Darwin":
            r = run(["osascript", "-e",
                     'tell application "System Events" to name of first process whose frontmost is true'], 5)
            return (r.stdout or "").strip()
        if SYSTEM == "Windows":
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try: return psutil.Process(pid.value).name()
            except Exception: return ""
        # Linux: надёжного безголового способа нет → пусто (безопасно)
        return ""
    except Exception:
        return ""

# ---------- автозапуск при входе в систему (кросс-платформенно) ----------
AUTOSTART_LABEL = "com.krylan.desktop.autopilot"
AUTOSTART_NAME = "KRYLAN Autopilot"

def _autostart_cmd():
    """Команда запуска стража при входе: тот же интерпретатор + этот файл
    с флагом --autopilot (фоновый страж без окна управления — см. main)."""
    return [sys.executable, os.path.abspath(__file__), "--autopilot"]

def autostart_target_path():
    """Путь к артефакту автозапуска per-OS (для статуса/тестов).
      • macOS → ~/Library/LaunchAgents/<label>.plist
      • Linux → ~/.config/autostart/krylan-autopilot.desktop
      • Windows → реестр HKCU\\...\\Run (файла нет) → возвращаем None
    """
    if SYSTEM == "Darwin":
        return os.path.join(HOME, "Library", "LaunchAgents", AUTOSTART_LABEL + ".plist")
    if SYSTEM == "Linux":
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
        return os.path.join(base, "autostart", "krylan-autopilot.desktop")
    return None  # Windows: реестр, не файл

def autostart_status():
    """True, если автозапуск стража настроен. Не бросает."""
    try:
        if SYSTEM == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run")
            try:
                winreg.QueryValueEx(key, AUTOSTART_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        path = autostart_target_path()
        return bool(path) and os.path.isfile(path)
    except Exception:
        return False

def autostart_enable():
    """Включает автозапуск стража при входе в систему. Обратимо, без sudo.
    Возвращает True при успехе, False при ошибке (НЕ бросает — честный статус)."""
    try:
        return _autostart_enable_impl()
    except Exception:
        return False

def _autostart_enable_impl():
    cmd = _autostart_cmd()
    if SYSTEM == "Darwin":
        args = "".join(f"<string>{c}</string>" for c in cmd)
        plist = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                 '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                 '<plist version="1.0"><dict>'
                 f'<key>Label</key><string>{AUTOSTART_LABEL}</string>'
                 f'<key>ProgramArguments</key><array>{args}</array>'
                 '<key>RunAtLoad</key><true/>'
                 '</dict></plist>')
        path = autostart_target_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(plist)
        run(["launchctl", "load", path], 10)
        return True
    if SYSTEM == "Linux":
        path = autostart_target_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        exec_line = " ".join(cmd)
        desktop = ("[Desktop Entry]\n"
                   "Type=Application\n"
                   "Name=KRYLAN Autopilot\n"
                   "Comment=Фоновый страж памяти KRYLAN\n"
                   f"Exec={exec_line}\n"
                   "X-GNOME-Autostart-enabled=true\n"
                   "Terminal=false\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(desktop)
        return True
    # Windows: HKCU\...\Run
    import winreg
    value = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run")
    try:
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)
    return True

def autostart_disable():
    """Выключает автозапуск стража. Обратимо. Возвращает True при успехе."""
    try:
        return _autostart_disable_impl()
    except Exception:
        return False

def _autostart_disable_impl():
    if SYSTEM == "Darwin":
        path = autostart_target_path()
        run(["launchctl", "unload", path], 10)
        try: os.remove(path)
        except OSError: pass
        return True
    if SYSTEM == "Linux":
        path = autostart_target_path()
        try: os.remove(path)
        except OSError: pass
        return True
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                         winreg.KEY_SET_VALUE)
    try:
        winreg.DeleteValue(key, AUTOSTART_NAME)
    except FileNotFoundError:
        pass
    finally:
        winreg.CloseKey(key)
    return True

# ---------- фоновый страж (guardian) ----------
def autopilot_log(message):
    """Дописывает строку в журнал автопилота (дата-время + сообщение).
    Не бросает. Создаёт каталог при необходимости."""
    try:
        os.makedirs(config_dir(), exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(autopilot_log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass

def read_autopilot_log(limit=2500):
    """Последние ~limit символов журнала (для UI). Не бросает."""
    try:
        with open(autopilot_log_path(), "r", encoding="utf-8") as f:
            return f.read()[-limit:]
    except Exception:
        return ""

def autopilot_optimize_once(close_browsers=False, on_log=None):
    """Один безопасный проход оптимизации, как делает страж на пике.

    Выполняет план optimize_all_plan (кэши/пустые/битые → Корзина), при
    разрешении мягко закрывает фоновые браузеры. Пишет результат в журнал.
    Возвращает dict плана (с ключом 'freed'). Не бросает.
    """
    def _log(msg):
        autopilot_log(msg)
        if on_log:
            try: on_log(msg)
            except Exception: pass
    try:
        plan = optimize_all_plan()
        _log(L("⚡ Оптимизация: освобождено ~{size} → Корзина").format(size=human(plan.get("freed", 0))))
    except Exception as e:
        plan = {"freed": 0, "steps": [], "skipped": [], "details": {}}
        _log(L("⚠ Оптимизация прервана: {why}").format(why=e))
    if close_browsers:
        try:
            closed = close_background_browsers(active_name=_foreground_app_name())
            if closed:
                _log(L("🌐 Закрыты фоновые браузеры: {names}").format(names=", ".join(sorted(set(closed)))))
        except Exception:
            pass
    return plan


class Guardian:
    """Поток-демон: раз в interval сек читает RAM% (psutil); если порог
    превышен подряд `streak` раз — запускает безопасную оптимизацию.

    Потокобезопасен (Event для останова, Lock для настроек). НЕ блокирует UI.
    Сам ничего не рисует — общается через колбэк on_event(kind, payload).
    """
    def __init__(self, cfg=None, on_event=None, sampler=None):
        self.cfg = dict(AUTOPILOT_DEFAULTS)
        if cfg: self.cfg.update(cfg)
        self.on_event = on_event
        # sampler() → текущий RAM% (внедряемо для тестов); по умолчанию psutil
        self._sampler = sampler or (lambda: psutil.virtual_memory().percent)
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._samples = []

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def update_config(self, cfg):
        with self._lock:
            self.cfg.update(cfg)

    def _emit(self, kind, payload=None):
        if self.on_event:
            try: self.on_event(kind, payload)
            except Exception: pass

    def start(self):
        if self.is_running():
            return
        self._stop.clear()
        self._samples = []
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        autopilot_log(L("🟢 Автопилот включён (порог {t}%, проверка каждые {i} с)")
                      .format(t=self.cfg["threshold"], i=self.cfg["interval"]))
        self._emit("started")

    def stop(self):
        if not self.is_running():
            return
        self._stop.set()
        autopilot_log(L("🔴 Автопилот остановлен"))
        self._emit("stopped")

    def _loop(self):
        while not self._stop.is_set():
            with self._lock:
                threshold = self.cfg["threshold"]
                streak = self.cfg["streak"]
                interval = self.cfg["interval"]
                close_b = self.cfg["close_browsers"]
            try:
                ram = self._sampler()
                self._samples.append(ram)
                if len(self._samples) > 50:
                    self._samples = self._samples[-50:]
                if autopilot_should_optimize(self._samples, threshold, streak):
                    autopilot_log(L("📈 Пик памяти: ОЗУ {r:.0f}% ≥ {t}% подряд {n} раз — оптимизирую")
                                  .format(r=ram, t=threshold, n=streak))
                    self._emit("optimizing", ram)
                    plan = autopilot_optimize_once(close_browsers=close_b)
                    self._samples = []   # сброс серии после действия
                    self._emit("optimized", plan)
            except Exception:
                pass
            # дробный сон, чтобы быстро реагировать на stop()
            self._stop.wait(max(1, int(interval)))

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)


def run_autopilot_headless():
    """Безоконный режим стража для автозапуска при входе (--autopilot).
    Читает сохранённый конфиг и крутит цикл, пока процесс жив."""
    cfg = load_autopilot_config()
    g = Guardian(cfg=cfg)
    g.start()
    autopilot_log(L("🛡 Фоновый страж запущен при входе в систему"))
    try:
        while g.is_running():
            g.join(timeout=3600)
    except KeyboardInterrupt:
        g.stop()

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
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            return "KRYLAN-CLEAN" in (r.stdout or "")
        r = subprocess.run(["schtasks", "/Query", "/TN", "KRYLAN Clean"], capture_output=True,
                           stdin=subprocess.DEVNULL, **_no_window_kwargs())
        return r.returncode == 0
    except Exception:
        return False

def schedule_enable():
    """Еженедельная авто-очистка кэшей (понедельник 12:00). Всё уходит в Корзину.
    Возвращает True при успехе. Отсутствие планировщика (crontab/launchctl/schtasks)
    не должно ронять Tk-callback — глушим как и schedule_status()."""
    import subprocess
    cmd = _sched_cmd()
    try:
        return _schedule_enable_impl(subprocess, cmd)
    except Exception:
        return False

def _schedule_enable_impl(subprocess, cmd):
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
                        "/TR", " ".join(f'"{c}"' for c in cmd)], capture_output=True,
                       stdin=subprocess.DEVNULL, **_no_window_kwargs())
    return True

def schedule_disable():
    """Снять авто-очистку. Отсутствие планировщика не должно ронять Tk-callback."""
    import subprocess
    try:
        return _schedule_disable_impl(subprocess)
    except Exception:
        return False

def _schedule_disable_impl(subprocess):
    if SYSTEM == "Darwin":
        path = os.path.join(HOME, "Library/LaunchAgents", SCHED_LABEL + ".plist")
        subprocess.run(["launchctl", "unload", path], capture_output=True)
        try: os.remove(path)
        except OSError: pass
    elif SYSTEM == "Linux":
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        if r.returncode == 0:
            keep = "\n".join(l for l in r.stdout.splitlines() if "KRYLAN-CLEAN" not in l)
            subprocess.run(["crontab", "-"], input=keep + "\n", text=True)
    else:
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", "KRYLAN Clean"], capture_output=True,
                       stdin=subprocess.DEVNULL, **_no_window_kwargs())
    return True


class Krylan(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KRYLAN")
        self.geometry("860x560"); self.minsize(820, 520)
        self.configure(bg=BG0)
        self.q = queue.Queue()
        self.page = None
        self.disp = {"cpu":0,"ram":0,"disk":0,"batt":0,"health":100}
        self.tgt = dict(self.disp)
        self.swap_mb = 0            # текущий объём swap (МБ) для HUD-гейджа
        self.info = {}
        self.found = {}
        self._paused = set()           # PID приостановленных (Режим фокуса)
        self._focus_log = []           # журнал событий Режима фокуса (последние)
        self._focus_deadline = None    # время авто-возврата (epoch) или None
        self._focus_after = None       # id запланированного after для таймера
        # ----- Автопилот: конфиг + фоновый страж -----
        self.ap_cfg = load_autopilot_config()
        self.guardian = Guardian(cfg=self.ap_cfg,
                                 on_event=lambda kind, payload=None: self.q.put(("apevent", kind, payload)))
        self._build(); self.nav("dash")
        # если в прошлый раз автопилот был включён — поднимаем страж сразу
        if self.ap_cfg.get("enabled"):
            try: self.guardian.start()
            except Exception: pass
        threading.Thread(target=self._sampler, daemon=True).start()
        self.after(80, self._poll); self.after(33, self._animate)
        # при закрытии окна никого не оставляем «замороженным»
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        side = tk.Frame(self, bg=SIDEBAR, width=200); side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Label(side, text="  🪽 KRYLAN", bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(20,0), padx=12)
        tk.Label(side, text="  "+L("Дай устройству крылья"), bg=SIDEBAR, fg=GREEN, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)
        tk.Label(side, text=f"  {os_label()} · v{VERSION}", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0,16))
        self.nav_btns = {}
        for key, base in [("dash","📊  Дашборд"),("scan","🚀  Сканер"),("procs","🧠  Процессы"),("focus","🎯  Режим фокуса"),("clean","🧽  Очистка"),("autopilot","🤖  Автопилот"),("tools","🛠  Инструменты"),("about","ℹ️  О программе")]:
            icon, name = base.split("  ", 1)
            b = tk.Label(side, text=f"   {icon}  "+L(name), bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 12), anchor="w", padx=10, pady=11, cursor="hand2")
            b.pack(fill="x"); b.bind("<Button-1>", lambda e,k=key: self.nav(k)); self.nav_btns[key] = b
        # переключатель языка
        lng = tk.Label(side, text=("🌐 EN" if LANG=="ru" else "🌐 RU"), bg=SIDEBAR, fg=GREEN,
                       font=("Segoe UI", 11, "bold"), cursor="hand2", padx=12, pady=10)
        lng.pack(side="bottom", anchor="w"); lng.bind("<Button-1>", lambda e: self._toggle_lang())
        self.main = tk.Frame(self, bg=BG0); self.main.pack(side="left", fill="both", expand=True)

    def _toggle_lang(self):
        global LANG
        LANG = "en" if LANG == "ru" else "ru"
        try: open(LANG_FILE, "w").write(LANG)
        except Exception: pass
        cur = getattr(self, "page", "dash")
        for w in self.winfo_children(): w.destroy()
        self._build(); self.nav(cur)

    def nav(self, key):
        self.page = key
        for k,b in self.nav_btns.items(): b.configure(bg=GLASS if k==key else SIDEBAR)
        for w in self.main.winfo_children(): w.destroy()
        {"dash":self.show_dash, "scan":self.show_scan, "procs":self.show_procs, "focus":self.show_focus, "clean":self.show_clean, "autopilot":self.show_autopilot, "tools":self.show_tools, "about":self.show_about}[key]()

    # ---------- HUD-фон: радиальное свечение + звёздное небо ----------
    def _grad(self, c, w, h):
        """Радиальное свечение HUD: ярче к центру-верху, темнее к краям."""
        base = "#060d1e"; glow = "#173d72"
        c.create_rectangle(0, 0, w, h, fill=base, outline=base)
        cxp, cyp = w*0.5, h*0.30
        rings = 11; maxr = max(w, h)*1.0
        for i in range(rings, 0, -1):
            t = i/rings; rr = maxr*t
            col = _blend(glow, base, t)        # внешние кольца тёмные, центр — свечение
            c.create_oval(cxp-rr, cyp-rr*0.85, cxp+rr, cyp+rr*0.85, fill=col, outline=col)
        self._starfield(c, w, h)

    def _starfield(self, c, w, h):
        """Натуральное звёздное небо: звёзды разного размера, мерцание, блики у ярких."""
        if not hasattr(self, "_stars"):
            rnd = random.Random(42); self._stars = []
            for _ in range(80):
                self._stars.append((rnd.random(), rnd.random(),
                                    rnd.uniform(0.4, 2.2),       # размер
                                    rnd.uniform(0, 6.28),        # фаза мерцания
                                    rnd.uniform(0.25, 1.0),      # базовая яркость
                                    rnd.uniform(0.02, 0.09),     # скорость мерцания
                                    rnd.random() < 0.08))        # яркая (с бликом-крестом)
        fr = getattr(self, "fr", 0)
        for fx, fy, sz, ph, bb, spd, bright in self._stars:
            x, y = fx*w, fy*h
            tw = bb*(0.5 + 0.5*math.sin(fr*spd + ph))
            r = sz*(0.55 + 0.55*tw)
            v = min(255, int(190*tw)+18)
            col = "#%02x%02x%02x" % (v, v, min(255, v+22))   # чуть голубоватый белый
            c.create_oval(x-r, y-r, x+r, y+r, fill=col, outline=col)
            if bright and tw > 0.62:                          # тонкий блик-крест у ярких
                g = r*2.8; gc = _blend("#cfe0ff", BG0, 1-(tw-0.62)/0.38*0.55)
                c.create_line(x-g, y, x+g, y, fill=gc, width=1)
                c.create_line(x, y-g, x, y+g, fill=gc, width=1)

    # ---------- кольцо-гейдж HUD: насечки + светящаяся дуга ----------
    def _ring(self, c, cx, cy, r, frac, color, w, val, label):
        glow = _blend(color, BG0, 0.5)
        # внешний круг-след
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=TRACK, width=w)
        # HUD-насечки по периметру: горят неоном до текущего значения; каждая 6-я — длинная
        N = 28
        for i in range(N):
            a = math.radians(90 - (i/N)*360); lit = (i/N) <= frac; major = (i % 6 == 0)
            rr1 = r+4; rr2 = r + (13 if major else (10 if lit else 7))
            c.create_line(cx+rr1*math.cos(a), cy-rr1*math.sin(a),
                          cx+rr2*math.cos(a), cy-rr2*math.sin(a),
                          fill=(color if lit else _blend(color, BG0, 0.68)),
                          width=(2 if (lit or major) else 1))
        # дуга прогресса со свечением + белая точка-конец
        if frac > 0.001:
            ext = -frac*359.9
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=ext, style="arc", outline=glow, width=w+7)
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=ext, style="arc", outline=color, width=w)
            ea = math.radians(90+ext); px = cx+r*math.cos(ea); py = cy-r*math.sin(ea)
            c.create_oval(px-w/2-1, py-w/2-1, px+w/2+1, py+w/2+1, fill="#ffffff", outline=color)
        # внутреннее декоративное кольцо (HUD-глубина)
        ri = r-w-6
        if ri > 6: c.create_oval(cx-ri, cy-ri, cx+ri, cy+ri, outline=_blend(color, BG0, 0.8), width=1)
        c.create_text(cx, cy-2, text=val, fill=TEXT, font=("Segoe UI", 14, "bold"))
        c.create_text(cx, cy+r+15, text=label, fill=MUTED, font=("Segoe UI", 9, "bold"))

    # ---------- бегущая кардиограмма «пульс системы» ----------
    def _ekg(self, c, x, y, w, h, fr, color):
        """ЭКГ-волна со свечением, бегущая слева направо."""
        def beat(t):
            if 0.12 < t < 0.17:  return 0.18*math.sin((t-0.12)/0.05*math.pi)   # P
            if 0.18 < t < 0.205: return -0.12                                  # Q
            if 0.205 < t < 0.235:return 1.0                                    # R
            if 0.235 < t < 0.27: return -0.42                                  # S
            if 0.32 < t < 0.45:  return 0.24*math.sin((t-0.32)/0.13*math.pi)   # T
            return 0.0
        baseline = y+h*0.55; amp = h*0.42; cyc = 118.0; off = (fr*1.7) % cyc
        pts = []
        for px in range(0, int(w)+1, 3):
            t = ((px+off) % cyc)/cyc
            pts += [x+px, baseline-beat(t)*amp]
        if len(pts) >= 4:
            c.create_line(*pts, fill=_blend(color, BG0, 0.40), width=4, capstyle="round")
            c.create_line(*pts, fill=color, width=2, capstyle="round")
        hx = x+((cyc-off+0.22*cyc) % cyc)
        c.create_oval(hx-3, baseline-amp-3, hx+3, baseline-amp+3, fill=color, outline=color)

    # ---------- характеристики устройства (имя/чип/ОЗУ/ОС) ----------
    def _device_info(self):
        if hasattr(self, "_devinfo"): return self._devinfo
        import socket as _sk
        try: name = _sk.gethostname().split(".")[0]
        except Exception: name = "Device"
        try:
            import multiprocessing as _mp
            cores = self.info.get("cores") or _mp.cpu_count()
        except Exception:
            cores = self.info.get("cores", "?")
        ram = human(self.info.get("ram_total", 0)) if self.info.get("ram_total") else ""
        self._devinfo = {"name": name or os_label(),
                         "chip": f"{cores}-ядерный CPU" if cores else "",
                         "ram": ram,
                         "os": f"{platform.system()} {platform.release()}".strip()}
        return self._devinfo

    # ---------- фирменный глобус (вращающаяся каркасная планета) ----------
    def _globe(self, c, cx, cy, r, fr):
        # пульс-сердцебиение
        ph = (fr * 0.03) % 1.0
        puls = math.exp(-((ph-0.16)**2)/0.004) + 0.6*math.exp(-((ph-0.34)**2)/0.004)
        puls = max(0.0, puls)
        # ореол: несколько слабых овалов
        for k in range(4):
            rr = r + k*4 + puls*7
            col = _blend(CYAN, BG0, 0.55 + k*0.11)
            c.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, outline=col, width=1)
        # кольцо-импульс на ударе
        if puls > 0.15:
            ri = r + 8 + puls*16
            c.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                          outline=_blend(CYAN, BG0, 0.25), width=2)
        # тёмная сфера + яркий лимб на ударе
        c.create_oval(cx-r, cy-r, cx+r, cy+r,
                      fill=_blend(BG0, CYAN, 0.12),
                      outline=_blend(CYAN, BG0, max(0.0, 0.7-puls*0.6)), width=2)
        # параллели
        for lat in (-0.66, -0.33, 0.0, 0.33, 0.66):
            rx = r * math.sqrt(1 - lat*lat); yy = cy - r*lat
            c.create_oval(cx-rx, yy-rx*0.18, cx+rx, yy+rx*0.18,
                          outline=_blend(CYAN, BG0, 0.45), width=1)
        # меридианы (вращаются)
        phase = fr * 0.04
        for k in range(6):
            ang = phase + k*math.pi/6
            rx = abs(r * math.cos(ang))
            c.create_oval(cx-rx, cy-r, cx+rx, cy+r,
                          outline=_blend(CYAN, BG0, 0.40), width=1)
        # узлы-«города»: розовые точки на передней полусфере
        for i in range(7):
            na = phase + i * (2*math.pi/7)
            if math.sin(na) > -0.1:
                lat = -0.55 + i*0.18
                px = cx + r*0.92 * math.cos(na) * math.sqrt(max(0.0, 1-lat*lat))
                py = cy - r*0.92 * lat
                d = 2.3 + puls*1.6
                c.create_oval(px-d, py-d, px+d, py+d, fill="#ff66d4", outline="")

    def show_dash(self):
        tk.Label(self.main, text=L("Дашборд"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,0))
        tk.Label(self.main, text=L("Система: {os} · в реальном времени").format(os=os_label()), bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,8))
        # ✨ главная «волшебная кнопка» — один клик делает всё безопасное
        hero = tk.Frame(self.main, bg=BG0); hero.pack(fill="x", padx=24, pady=(0,6))
        big = tk.Label(hero, text="  " + L("✨ Оптимизировать") + "  ", bg=GREEN, fg="white",
                       font=("Segoe UI", 15, "bold"), padx=22, pady=12, cursor="hand2")
        big.pack(side="left")
        big.bind("<Button-1>", lambda e: self.run_optimize())
        # 👁 предпросмотр (dry-run) — read-only, ничего не меняет
        prev = tk.Label(hero, text="  " + L("👁 Предпросмотр") + "  ", bg=BLUE, fg="white",
                        font=("Segoe UI", 15, "bold"), padx=18, pady=12, cursor="hand2")
        prev.pack(side="left", padx=(10,0))
        prev.bind("<Button-1>", lambda e: self.run_preview())
        tk.Label(hero, text=L("один клик — безопасная очистка по всем параметрам, всё в Корзину"),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=12)
        # живой прогресс оптимизации (скрыт, пока не нажата кнопка)
        self.opt_action = tk.Frame(self.main, bg=BG0)
        self.opt_out = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 10), relief="flat",
                               padx=12, pady=8, height=8, state="disabled")
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0); self.cv.pack(fill="both", expand=True, padx=20, pady=10)

    def _draw_dash(self):
        if not (self.page=="dash" and self.cv.winfo_exists()): return
        c = self.cv; c.delete("all")
        W = c.winfo_width() or 760; H = c.winfo_height() or 600
        self._grad(c, W, H)
        fr = getattr(self, "fr", 0)
        # ===== радиальная «рубка»: планета в центре, метрики по углам =====
        cx = W/2; cy = H*0.47
        gr = max(54, min(W*0.115, H*0.165, 110))
        gauge_r = max(26, min(38, min(W, H)*0.05))
        orbit = min(gr+90, cy-gauge_r-24, (H-cy)-gauge_r-44, W/2-gauge_r-16)
        orbit = max(orbit, gr+gauge_r+20)
        # часы — верх-центр (HUD)
        c.create_text(cx, 20, fill=CYAN, font=("Consolas", 22, "bold"), text=time.strftime("%H:%M"))
        c.create_text(cx, 41, fill=MUTED, font=("Segoe UI", 9, "bold"), text="СИСТЕМА · РЕАЛЬНОЕ ВРЕМЯ")
        # интернет — верх-право
        c.create_text(W-22, 18, anchor="e", fill=MUTED, font=("Segoe UI", 10, "bold"), text="🌐 ИНТЕРНЕТ")
        c.create_text(W-22, 40, anchor="e", fill=GREEN, font=("Segoe UI", 13, "bold"),
                      text=f"↓ {human(self.info.get('net_down', 0))}/с")
        c.create_text(W-22, 60, anchor="e", fill=BLUE, font=("Segoe UI", 13, "bold"),
                      text=f"↑ {human(self.info.get('net_up', 0))}/с")
        # кардиограмма «пульс системы» — верх-лево (ЭКГ)
        c.create_text(22, 13, anchor="w", fill=MUTED, font=("Segoe UI", 9, "bold"), text="♥ ПУЛЬС СИСТЕМЫ")
        self._ekg(c, 22, 22, max(140, cx-150), 42, fr, RED)
        # ===== метрики-гейджи вокруг планеты =====
        sval = human(self.swap_mb*1024*1024).replace(" ", "")
        batt = self.info.get("batt")
        gauges = [("ЗДОРОВЬЕ", str(int(self.disp["health"])), self.disp["health"]/100,
                   col_for(self.disp["health"], inv=True)),
                  ("CPU", f'{int(self.disp["cpu"])}%', self.disp["cpu"]/100, col_for(self.disp["cpu"])),
                  (L("ОЗУ"), f'{int(self.disp["ram"])}%', self.disp["ram"]/100, col_for(self.disp["ram"])),
                  (L("ДИСК"), f'{int(self.disp["disk"])}%', self.disp["disk"]/100, col_for(self.disp["disk"])),
                  ("SWAP", sval, min(1, self.swap_mb/8192.0), CYAN),
                  (L("БАТАРЕЯ"), (f'{int(self.disp["batt"])}%' if batt is not None else "—"),
                   self.disp["batt"]/100, col_for(self.disp["batt"], inv=True))]
        angles = [-120, -60, 0, 60, 120, 180]   # верх-центр (часы) и низ-центр (устройство) свободны
        for (label, val, frac, color), deg in zip(gauges, angles):
            a = math.radians(deg)
            gxp = cx+orbit*math.cos(a); gyp = cy+orbit*math.sin(a)
            ex = cx+gr*math.cos(a); ey = cy+gr*math.sin(a)
            lx = gxp-gauge_r*math.cos(a); ly = gyp-gauge_r*math.sin(a)
            c.create_line(ex, ey, lx, ly, fill=_blend(CYAN, BG0, 0.42), width=1)   # светящийся коннектор
            c.create_oval(ex-2, ey-2, ex+2, ey+2, fill=CYAN, outline=CYAN)         # узел у планеты
            c.create_oval(lx-2, ly-2, lx+2, ly+2, fill=_blend(color, BG0, 0.2), outline=color)  # узел у гейджа
            self._ring(c, gxp, gyp, gauge_r, min(1, frac), color, 8, val, label)
        # ===== ЦЕНТР: вращающаяся планета-устройство =====
        self._globe(c, cx, cy, gr, fr)
        # характеристики устройства — под планетой
        di = self._device_info()
        c.create_text(cx, cy+gr+18, fill=TEXT, font=("Segoe UI", 14, "bold"), text=di["name"])
        sub = f'{di["chip"]} · {di["ram"]}' if di["chip"] and di["ram"] else (di["chip"] or di["ram"])
        if sub:
            c.create_text(cx, cy+gr+38, fill=CYAN, font=("Segoe UI", 10, "bold"), text=sub)
        c.create_text(cx, H-16, fill=MUTED, font=("Segoe UI", 9),
                      text=f'{os_label()} · {di["os"]}')
        c.configure(scrollregion=(0, 0, W, H))

    # ---------- очистка ----------
    def show_clean(self):
        tk.Label(self.main, text=L("Очистка"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text=L("Временные файлы и кэши. Всё уходит в Корзину (обратимо)."), bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,10))
        wrap = tk.Frame(self.main, bg=GLASS); wrap.pack(fill="x", padx=24)
        self.cl_vars = {}; self.cl_lbl = {}
        for i,(name,p) in enumerate(cleanup_targets()):
            row = tk.Frame(wrap, bg=GLASS); row.pack(fill="x", padx=14, pady=6)
            v = tk.BooleanVar(value=True); self.cl_vars[i] = (v, name, p)
            tk.Checkbutton(row, text="  "+name, variable=v, bg=GLASS, fg=TEXT, selectcolor=BG0,
                           activebackground=GLASS, activeforeground=TEXT, font=("Segoe UI", 11), anchor="w").pack(side="left")
            sl = tk.Label(row, text="…", bg=GLASS, fg=GREEN, font=("Segoe UI", 11, "bold")); sl.pack(side="right"); self.cl_lbl[i] = sl
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=14)
        self.cl_total = tk.Label(bar, text=L("Готово к анализу"), bg=BG0, fg=TEXT, font=("Segoe UI", 12, "bold")); self.cl_total.pack(side="left")
        self._btn(bar, L("Очистить"), GREEN, self.run_clean).pack(side="right", padx=(8,0))
        self._btn(bar, L("Анализ"), BLUE, self.run_analyze).pack(side="right")

    def _btn(self, parent, text, color, cmd):
        b = tk.Label(parent, text="  "+text+"  ", bg=color, fg="white", font=("Segoe UI", 12, "bold"), padx=14, pady=7, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd()); return b

    def run_analyze(self):
        self.cl_total.configure(text=L("Анализирую…"))
        threading.Thread(target=self._analyze_w, daemon=True).start()

    def _analyze_w(self):
        self.found = {}; total = 0
        for i,(v,name,p) in self.cl_vars.items():
            sz = dir_size(p); self.found[i] = (p, sz); total += sz
            self.q.put(("clsize", i, sz))
        self.q.put(("cltotal", total, None))

    def run_clean(self):
        if not self.found: messagebox.showinfo("KRYLAN", L("Сначала «Анализ».")); return
        sel = [i for i,(v,n,p) in self.cl_vars.items() if v.get()]
        if not messagebox.askyesno("KRYLAN", L("Переместить выбранные кэши в Корзину?")): return
        self.cl_total.configure(text=L("Очищаю…"))
        threading.Thread(target=self._clean_w, args=(sel,), daemon=True).start()

    def _clean_w(self, sel):
        freed = 0
        for i in sel:
            p, sz = self.found.get(i, (None, 0))
            if not p or not os.path.isdir(p): continue
            for name in os.listdir(p):
                fp = os.path.join(p, name)
                safe_trash(fp)
            freed += sz
        self.q.put(("cldone", freed, None))

    # ---------- сканер (one-click, в духе BoostSpeed My Scanner) ----------
    def show_scan(self):
        tk.Label(self.main, text=L("Сканер"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text=L("Полная проверка одним кликом: кэши · корзина · старые загрузки · дубликаты."),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,10))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24)
        # Главная «✨ Оптимизировать» — на дашборде; здесь оставляем только Сканер.
        self._btn(bar, L("🔍 Сканировать"), BLUE, self.run_scan).pack(side="left")
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
        self.sout.insert("end", L("Нажмите «Сканировать всё».")+"\n"); self.sout.configure(state="disabled")

    def _sched_refresh(self):
        on = schedule_status()
        self.sched_btn.configure(text=(L("⏰ Выключить авто-очистку") if on else L("⏰ Включить авто-очистку")),
                                 bg=(GLASS if on else BLUE), fg=("white" if not on else TEXT))
        self.sched_lbl.configure(text=(L("еженедельно, пн 12:00 · кэши → Корзина") if on else ""))

    def _sched_toggle(self):
        if schedule_status():
            schedule_disable()
        else:
            if not messagebox.askyesno("KRYLAN", L("Включить еженедельную авто-очистку кэшей?\n"
                                       "Каждый понедельник в 12:00 содержимое кэшей будет уходить в Корзину.")): return
            schedule_enable()
        self._sched_refresh()

    def run_boost(self):
        if not messagebox.askyesno("KRYLAN", L("Ускорить компьютер одним кликом?\n\n"
            "Безопасно: кэши и временные файлы уйдут в Корзину") +
            (L(", освободится «очищаемое» место") if SYSTEM=="Darwin" else "") +
            L(". Дефрагментация SSD НЕ делается — она вредна.")): return
        self._sout(L("🚀 Ускоряю… кэши → Корзина, освобождаю место…"))
        threading.Thread(target=self._boost_w, daemon=True).start()

    def _boost_w(self):
        steps = []
        freed, lines = clean_caches_headless()
        steps.append(L("🧽 Кэши и логи → Корзина: {size}").format(size=human(freed)))
        purged = 0
        if SYSTEM == "Darwin":
            try:
                du = psutil.disk_usage(HOME); before = du.free
                run_cmd = ["tmutil","thinlocalsnapshots","/","999999999999","4"]
                import subprocess; subprocess.run(run_cmd, capture_output=True, timeout=120)
                purged = max(0, psutil.disk_usage(HOME).free - before)
            except Exception: pass
            if purged: steps.append(L("🧊 Освобождено места: {size}").format(size=human(purged)))
        steps.append(L("⚡️ Готово — компьютер ускорен"))
        out = L("🚀  Готово! Компьютер ускорен.") + "\n\n" + "\n".join("  • "+s for s in steps)
        out += "\n\n  " + L("Освобождено всего: ~{size}").format(size=human(freed+purged)) + "\n  " + L("Всё обратимо — очищенное в Корзине. Без дефрага SSD.")
        # Boost запускается со страницы «scan» (через _sout), поэтому результат нужно
        # слать тегом "scanout" — тег "tout" рендерится только на странице tools и был бы потерян.
        self.q.put(("scanout", out, None))

    # ---------- ✨ «волшебная кнопка»: один клик — всё безопасное ----------
    def run_optimize(self):
        """Запуск авто-оптимизации БЕЗ диалогов-подтверждений (всё обратимо)."""
        self._opt_reset(L("✨ Оптимизирую… безопасные шаги, всё уходит в Корзину…") + "\n\n")
        threading.Thread(target=self._optimize_all_w, daemon=True).start()

    # ---------- 👁 предпросмотр (dry-run): только читает, ничего не меняет ----------
    def run_preview(self):
        """Запуск предпросмотра оптимизации — строго read-only (без удаления)."""
        self._opt_reset(L("👁 Считаю предпросмотр… ничего не удаляется и не меняется…") + "\n\n")
        threading.Thread(target=self._preview_w, daemon=True).start()

    def _preview_w(self):
        # детект устройства делаем здесь (вне чистой функции), сам предпросмотр
        # ничего не меняет — только подсчёт через optimize_preview().
        media = detect_media_type()
        plan = optimize_preview(SYSTEM, media, has_root())
        do_block = (L("▶ Будет сделано на этом устройстве ({os}):").format(os=os_label()) + "\n"
                    + "".join("  • " + s + "\n" for s in plan["will_do"]))
        skip_block = ""
        if plan["skipped"]:
            skip_block = ("\n" + L("⏭ Будет пропущено (недоступно на этом устройстве):") + "\n"
                          + "".join("  ↪ " + s + "\n" for s in plan["skipped"]))
        summary = (L("👁  Предпросмотр оптимизации (ничего не изменено)") + "\n\n"
                   + L("Оценка освобождения: ~{size} · шагов: {n}").format(
                        size=human(plan["freed_est"]), n=len(plan["will_do"])) + "\n"
                   + L("Это режим только для чтения — реальная очистка не запускалась.") + "\n\n"
                   + do_block + skip_block)
        self.q.put(("optpreview", summary, None))

    def _opt_reset(self, t):
        """Сброс панели прогресса оптимизации (живой лог + место под кнопку ревью)."""
        if not (self.page == "dash" and hasattr(self, "opt_out")): return
        # показываем панель прогресса над кольцами (один раз)
        if not self.opt_out.winfo_ismapped():
            self.opt_action.pack(fill="x", padx=24, before=self.cv)
            self.opt_out.pack(fill="x", padx=24, pady=(4,4), before=self.cv)
        self.opt_out.configure(state="normal"); self.opt_out.delete("1.0", "end")
        self.opt_out.insert("end", t); self.opt_out.configure(state="disabled")
        for w in self.opt_action.winfo_children(): w.destroy()

    def _optimize_all_w(self):
        # живой прогресс: каждый шаг оркестратора шлём в очередь
        plan = optimize_all_plan(emit=lambda m: self.q.put(("optstep", "  • " + m + "\n", None)))
        for sk in plan["skipped"]:
            self.q.put(("optstep", "  ↪ " + sk + "\n", None))
        # ревью-сканирование (без удаления): дубли, похожие фото, крупные файлы
        groups, extras, wasted = find_duplicates()
        try:
            from PIL import Image  # noqa: F401
            sim_groups = find_similar_images()
        except Exception:
            sim_groups = []
        sim_extra = sum(max(0, len(g) - 1) for g in sim_groups)
        big = []
        skip = {"Library", "AppData", ".cache"}
        for root, dirs, files in os.walk(HOME):
            parts = root.replace(HOME, "").strip(os.sep).split(os.sep)
            if parts and parts[0] in skip: dirs[:] = []; continue
            for fn in files:
                try:
                    s = os.path.getsize(os.path.join(root, fn))
                    if s > 100*1024*1024: big.append(s)
                except Exception: pass
        review = {"dupes": len(extras), "dupes_size": wasted,
                  "similar": sim_extra, "large": len(big), "large_size": sum(big)}
        done_block = (L("✅ Сделано на этом устройстве ({os}):").format(os=os_label()) + "\n"
                      + "".join("  • " + s + "\n" for s in plan["steps"]))
        skip_block = ""
        if plan["skipped"]:
            skip_block = ("\n" + L("⏭ Пропущено (недоступно на этом устройстве):") + "\n"
                          + "".join("  ↪ " + s + "\n" for s in plan["skipped"]))
        summary = (L("✨  Оптимизация завершена.") + "\n\n"
                   + L("Освобождено: ~{size} · шагов: {n}").format(
                        size=human(plan["freed"]), n=len(plan["steps"])) + "\n"
                   + L("Всё обратимо — очищенное в Корзине.") + "\n\n"
                   + done_block + skip_block + "\n"
                   + L("Найдено для ревью (ничего не удалено):") + "\n"
                   + L("  👯 дубли: {n} лишних · ~{size}").format(n=review["dupes"], size=human(review["dupes_size"])) + "\n"
                   + L("  🖼 похожие фото: {n} лишних").format(n=review["similar"]) + "\n"
                   + L("  📦 крупные файлы: {n} · ~{size}").format(n=review["large"], size=human(review["large_size"])) + "\n")
        self.q.put(("optdone", summary, review))

    def run_scan(self):
        self._sout(L("🚀 Сканирую… это может занять минуту-другую."))
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
        lines = [L("🚀  Результат сканирования") + "\n\n", L("Кэши и временные файлы:") + "\n"]
        lines += [f"  {human(s):>9}  {n}\n" for n, p, s in caches]
        lines.append("\n" + L("Корзина: {val}").format(val=(human(res['trash']) if res['trash'] is not None else '—')) + "\n")
        lines.append(L("Старые загрузки (>6 мес): {size} · {n} шт.").format(size=human(osum), n=len(old)) + "\n")
        for s, fp in old[:8]: lines.append(f"  {human(s):>9}  {fp.replace(HOME,'~')}\n")
        lines.append(L("Дубликаты: {size} в {n} группах").format(size=human(wasted), n=len(groups)) + "\n")
        lines.append(f"\n══════════════════════════════════\n")
        lines.append(L("ИТОГО можно освободить: ~{size}").format(size=human(total)) + "\n")
        self.q.put(("scanout", "".join(lines), res))

    def _scan_actions(self, res):
        if sum(s for _,_,s in res["caches"]) > 0:
            self._btn(self.s_action, L("🧽 Кэши → Корзина"), GREEN,
                      lambda: self._scan_clean_caches()).pack(side="left", padx=(0,6))
        if res["old"]:
            self._btn(self.s_action, L("📥 Старые загрузки → Корзина ({n})").format(n=len(res['old'])), BLUE,
                      lambda o=res["old"]: self._scan_trash_old(o)).pack(side="left", padx=6)
        if res["extras"]:
            self._btn(self.s_action, L("👯 Дубли → Корзину ({n})").format(n=len(res['extras'])), PURPLE,
                      lambda ex=res["extras"]: self._trash_dupes_scan(ex)).pack(side="left", padx=6)

    def _scan_clean_caches(self):
        if not messagebox.askyesno("KRYLAN", L("Переместить содержимое кэшей в Корзину?")): return
        self._sout(L("🧽 Очищаю кэши…"))
        def w():
            freed, _ = clean_caches_headless()
            self.q.put(("scanout", L("🧽 Кэши очищены: ~{size} → Корзина.\n\nЗапустите сканирование заново для свежей сводки.").format(size=human(freed)), None))
        threading.Thread(target=w, daemon=True).start()

    def _scan_trash_old(self, old):
        if not messagebox.askyesno("KRYLAN", L("Переместить {n} старых файлов из Загрузок в Корзину?").format(n=len(old))): return
        ok = 0
        for s, fp in old:
            if safe_trash(fp): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.run_scan()

    def _trash_dupes_scan(self, extras):
        if not messagebox.askyesno("KRYLAN", L("Удалить {n} лишних копий в Корзину?").format(n=len(extras))): return
        ok = 0
        for p in extras:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.run_scan()

    # ---------- процессы (диспетчер задач) ----------
    def show_procs(self):
        tk.Label(self.main, text=L("Процессы"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,2))
        tk.Label(self.main, text=L("Топ по памяти. «Завершить» закрывает выбранный процесс."), bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0,2))
        tk.Label(self.main, text=L("🎯 Режим фокуса: «⏸ Пауза» обратимо приостанавливает приложение, «▶ Возобновить всё» — возвращает работу."),
                 bg=BG0, fg=PURPLE, font=("Segoe UI", 9)).pack(anchor="w", padx=24, pady=(0,8))
        head = tk.Frame(self.main, bg=BG0); head.pack(fill="x", padx=26)
        tk.Label(head, text=L("Процесс"), bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), anchor="w", width=26).pack(side="left")
        tk.Label(head, text=L("ОЗУ"), bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), width=10).pack(side="left")
        tk.Label(head, text="CPU", bg=BG0, fg=MUTED, font=("Segoe UI", 10, "bold"), width=8).pack(side="left")
        self.proc_box = tk.Frame(self.main, bg=GLASS); self.proc_box.pack(fill="both", expand=True, padx=24, pady=(4,6))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=24, pady=(0,12))
        self.focus_lbl = tk.Label(bar, text="", bg=BG0, fg=PURPLE, font=("Segoe UI", 11, "bold")); self.focus_lbl.pack(side="left")
        self._btn(bar, L("▶ Возобновить всё"), GREEN, self._resume_all).pack(side="right")
        self._procs_refresh()

    def _focus_label(self):
        if hasattr(self, "focus_lbl") and self.focus_lbl.winfo_exists():
            n = len(self._paused)
            self.focus_lbl.configure(text=(L("⏸ На паузе: {n}").format(n=n) if n else L("Ничего не приостановлено")))

    def _procs_refresh(self):
        if self.page != "procs" or not self.proc_box.winfo_exists(): return
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
            try:
                rss = p.info["memory_info"].rss if p.info["memory_info"] else 0
                rows.append((rss, p.info.get("cpu_percent") or 0, p.info["pid"], p.info["name"] or "?"))
            except Exception: pass
        rows.sort(reverse=True)
        # безопасные кандидаты на паузу (через чистую функцию)
        cand = focus_candidates([{"name": name, "pid": pid, "cpu": cpu, "mem": rss}
                                 for rss, cpu, pid, name in rows])
        safe_pids = {c["pid"] for c in cand}
        for w in self.proc_box.winfo_children(): w.destroy()
        for rss, cpu, pid, name in rows[:14]:
            paused = pid in self._paused
            rbg = _blend(GLASS, PURPLE, 0.18) if paused else GLASS
            r = tk.Frame(self.proc_box, bg=rbg); r.pack(fill="x", padx=8, pady=1)
            label = (name[:24] + ("  ⏸" if paused else ""))
            tk.Label(r, text=label, bg=rbg, fg=(PURPLE if paused else TEXT), font=("Segoe UI", 11), anchor="w", width=26).pack(side="left")
            tk.Label(r, text=human(rss), bg=rbg, fg=MUTED, font=("Segoe UI", 10), width=10).pack(side="left")
            tk.Label(r, text=f"{cpu:.0f}%", bg=rbg, fg=load_color(min(100, cpu)), font=("Segoe UI", 10), width=7).pack(side="left")
            b = tk.Label(r, text=L("Завершить"), bg=RED, fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
            b.pack(side="right"); b.bind("<Button-1>", lambda e, pp=pid, nn=name: self._kill_proc(pp, nn))
            # «⏸ Пауза» только для безопасных кандидатов
            if pid in safe_pids:
                pb = tk.Label(r, text=L("⏸ Пауза"), bg=PURPLE, fg="white", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
                pb.pack(side="right", padx=(0,6)); pb.bind("<Button-1>", lambda e, pp=pid, nn=name: self._pause_proc(pp, nn))
        self._focus_label()
        self.after(2500, self._procs_refresh)

    def _is_pausable(self, pid, name):
        """Финальная проверка безопасности перед suspend (защита и в UI, и тут)."""
        if int(pid) == os.getpid(): return False
        return str(name).lower() not in focus_blacklist()

    def _pause_proc(self, pid, name):
        if not self._is_pausable(pid, name):
            messagebox.showwarning("KRYLAN", L("«{name}» — системный процесс, пауза запрещена.").format(name=name)); return
        if not messagebox.askyesno(
                L("KRYLAN — Режим фокуса"),
                L("Приостановить «{name}» (PID {pid})?\n\n"
                "⚠️ Это обратимо ЗАМОРОЗИТ приложение до возобновления — "
                "оно перестанет отвечать, пока вы не нажмёте «▶ Возобновить всё».\n\n"
                "Несохранённые данные в нём станут недоступны до возобновления.").format(name=name, pid=pid)):
            return
        try:
            psutil.Process(pid).suspend()
            self._paused.add(pid)
            _FOCUS_PAUSED_GLOBAL.add(pid)
            self._focus_add_log(L("⏸ Приостановлено: {name}").format(name=name))
        except psutil.NoSuchProcess:
            messagebox.showinfo("KRYLAN", L("Процесс «{name}» уже завершён.").format(name=name))
        except psutil.AccessDenied:
            # нет прав (root/чужой пользователь) — тихо пропускаем, без падения
            messagebox.showinfo("KRYLAN", L("Недостаточно прав, чтобы приостановить «{name}» — пропущено.").format(name=name))
        except Exception as e:
            messagebox.showerror("KRYLAN", L("Не удалось приостановить: {e}").format(e=e))
        self._focus_label()
        self._procs_refresh()

    def _resume_all(self, silent=False):
        """Возобновить ВСЕ приостановленные процессы. Безопасно вызывать всегда.

        Через чистую focus_resume(); синхронизирует и self._paused, и
        глобальный набор (страховка atexit). Сбрасывает таймер авто-возврата.
        """
        pids = list(self._paused)
        focus_resume(pids)
        resumed = len(pids)
        self._paused.clear()
        for pid in pids:
            _FOCUS_PAUSED_GLOBAL.discard(pid)
        self._focus_cancel_timer()
        if resumed:
            self._focus_add_log(L("▶ Возобновлено процессов: {n}").format(n=resumed))
        if not silent:
            if resumed:
                messagebox.showinfo("KRYLAN", L("▶ Возобновлено процессов: {n}.").format(n=resumed))
            else:
                messagebox.showinfo("KRYLAN", L("Приостановленных процессов нет."))
        self._focus_label()

    # ---------- журнал и таймер Режима фокуса ----------
    def _focus_add_log(self, text):
        ts = time.strftime("%H:%M:%S")
        self._focus_log.append(f"[{ts}] {text}")
        self._focus_log = self._focus_log[-200:]      # держим хвост
        self._focus_log_refresh()

    def _focus_cancel_timer(self):
        self._focus_deadline = None
        if self._focus_after is not None:
            try: self.after_cancel(self._focus_after)
            except Exception: pass
            self._focus_after = None

    def _on_close(self):
        # никого не оставляем «замороженным» после выхода
        self._resume_all(silent=True)
        self.destroy()

    def _kill_proc(self, pid, name):
        if not messagebox.askyesno("KRYLAN", L("Завершить процесс «{name}» (PID {pid})?").format(name=name, pid=pid)): return
        try:
            psutil.Process(pid).terminate()
            self._paused.discard(pid)
            _FOCUS_PAUSED_GLOBAL.discard(pid)
        except Exception as e:
            messagebox.showerror("KRYLAN", L("Не удалось завершить: {e}").format(e=e))
        self._procs_refresh()

    # ---------- Режим фокуса (отдельная страница) ----------
    def _active_app_name(self):
        """Имя активного приложения переднего плана (best-effort, чтобы не
        приостанавливать окно, с которым работает пользователь). На неудаче — None."""
        try:
            if SYSTEM == "Darwin":
                r = run(["osascript", "-e",
                         'tell application "System Events" to get name of first process whose frontmost is true'],
                        timeout=4)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
        except Exception:
            pass
        return None

    def show_focus(self):
        tk.Label(self.main, text=L("Режим фокуса"), bg=BG0, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(self.main, text=L("Приостанавливает фоновые программы на время фокуса и возвращает их "
                 "обратно — ничего не закрывается и не теряется. Системные процессы не трогаются."),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10), wraplength=620, justify="left"
                 ).pack(anchor="w", padx=24, pady=(0, 10))

        # --- статус + кнопки включить/выключить ---
        card = tk.Frame(self.main, bg=GLASS); card.pack(fill="x", padx=24, pady=6)
        self.focus_state = tk.Label(card, text="…", bg=GLASS, fg=TEXT, font=("Segoe UI", 14, "bold"))
        self.focus_state.pack(side="left", padx=18, pady=14)
        self._btn(card, L("▶ Выключить фокус"), GREEN, lambda: self._resume_all()).pack(side="right", padx=(8, 18), pady=10)
        self._btn(card, L("🎯 Включить фокус"), PURPLE, self._focus_enable).pack(side="right", pady=10)

        # --- таймер авто-возврата ---
        trow = tk.Frame(self.main, bg=BG0); trow.pack(fill="x", padx=24, pady=(2, 4))
        tk.Label(trow, text=L("Авто-возврат:"), bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        if not hasattr(self, "focus_timer_var"):
            self.focus_timer_var = tk.IntVar(value=0)
        for label, mins in [(L("выкл"), 0), ("25 " + L("мин"), 25), ("50 " + L("мин"), 50)]:
            tk.Radiobutton(trow, text=label, value=mins, variable=self.focus_timer_var,
                           bg=BG0, fg=TEXT, selectcolor=GLASS, activebackground=BG0,
                           activeforeground=TEXT, font=("Segoe UI", 10)).pack(side="left", padx=4)

        tk.Label(self.main, text=L("Кандидаты (тяжёлые фоновые приложения) — отметьте, что приостановить:"),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(8, 2))
        self.focus_box = tk.Frame(self.main, bg=GLASS)
        self.focus_box.pack(fill="both", expand=False, padx=24, pady=(0, 6))
        self.focus_vars = {}     # pid -> (BooleanVar, name)

        tk.Label(self.main, text=L("Журнал фокуса:"), bg=BG0, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(4, 2))
        self.focus_log = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 10),
                                 relief="flat", padx=12, pady=8, height=6)
        self.focus_log.pack(fill="both", expand=True, padx=24, pady=(0, 14))

        self._focus_candidates_refresh()
        self._focus_log_refresh()
        self._focus_state_refresh()

    def _focus_candidates_refresh(self):
        if self.page != "focus" or not (hasattr(self, "focus_box") and self.focus_box.winfo_exists()):
            return
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
            try:
                rss = p.info["memory_info"].rss if p.info["memory_info"] else 0
                rows.append({"name": p.info["name"] or "?", "pid": p.info["pid"],
                             "cpu": p.info.get("cpu_percent") or 0, "mem": rss})
            except Exception:
                pass
        active = self._active_app_name()
        cands = pick_focus_targets(rows, current_app=active)[:14]
        prev = {pid: var.get() for pid, (var, _n) in self.focus_vars.items()}
        for w in self.focus_box.winfo_children(): w.destroy()
        self.focus_vars = {}
        if not cands:
            tk.Label(self.focus_box, text=L("  Подходящих фоновых приложений не найдено."),
                     bg=GLASS, fg=MUTED, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=10, pady=8)
        for c in cands:
            pid, name = c["pid"], c["name"]
            paused = pid in self._paused
            var = tk.BooleanVar(value=prev.get(pid, not paused))
            self.focus_vars[pid] = (var, name)
            rbg = _blend(GLASS, PURPLE, 0.18) if paused else GLASS
            r = tk.Frame(self.focus_box, bg=rbg); r.pack(fill="x", padx=8, pady=1)
            cb = tk.Checkbutton(r, variable=var, bg=rbg, fg=TEXT, selectcolor=BG0,
                                activebackground=rbg, activeforeground=TEXT,
                                text="  " + (name[:26] + ("  ⏸" if paused else "")),
                                font=("Segoe UI", 11), anchor="w", width=30)
            cb.pack(side="left")
            tk.Label(r, text=human(c["mem"]), bg=rbg, fg=MUTED, font=("Segoe UI", 10), width=10).pack(side="left")
            tk.Label(r, text=f"{c['cpu']:.0f}%", bg=rbg, fg=load_color(min(100, c["cpu"])),
                     font=("Segoe UI", 10), width=7).pack(side="left")
        self.after(3000, self._focus_candidates_refresh)

    def _focus_log_refresh(self):
        if not (hasattr(self, "focus_log") and self.focus_log.winfo_exists()):
            return
        body = "\n".join(self._focus_log) if self._focus_log else L("(журнал пуст)")
        self.focus_log.configure(state="normal"); self.focus_log.delete("1.0", "end")
        self.focus_log.insert("end", body); self.focus_log.see("end")
        self.focus_log.configure(state="disabled")

    def _focus_state_refresh(self):
        if not (hasattr(self, "focus_state") and self.focus_state.winfo_exists()):
            return
        n = len(self._paused)
        if n:
            extra = ""
            if self._focus_deadline:
                left = max(0, int(self._focus_deadline - time.time()))
                extra = "  ·  " + L("авто-возврат через {m}:{s:02d}").format(m=left // 60, s=left % 60)
            self.focus_state.configure(text=L("🎯 Фокус включён · на паузе: {n}").format(n=n) + extra, fg=PURPLE)
        else:
            self.focus_state.configure(text=L("🔵 Фокус выключен · всё работает"), fg=BLUE)
        self.after(1000, self._focus_state_refresh)

    def _focus_enable(self):
        # выбранные чекбоксами кандидаты
        chosen = [pid for pid, (var, _n) in self.focus_vars.items() if var.get()]
        if not chosen:
            messagebox.showinfo("KRYLAN", L("Отметьте хотя бы одно приложение для паузы.")); return
        if not messagebox.askyesno(
                L("KRYLAN — Режим фокуса"),
                L("Приостановить выбранные приложения ({n})?\n\n"
                  "Это обратимо: они «замёрзнут» и перестанут отвечать, пока вы не "
                  "нажмёте «▶ Выключить фокус» (или не сработает авто-возврат). "
                  "Ничего не закрывается, данные не теряются.").format(n=len(chosen))):
            return
        done = focus_suspend(chosen)
        for pid in done:
            self._paused.add(pid)
            _FOCUS_PAUSED_GLOBAL.add(pid)
        skipped = len(chosen) - len(done)
        self._focus_add_log(L("🎯 Фокус включён · приостановлено: {n}").format(n=len(done))
                            + (L(" (пропущено: {s})").format(s=skipped) if skipped else ""))
        # таймер авто-возврата
        self._focus_cancel_timer()
        mins = int(self.focus_timer_var.get()) if hasattr(self, "focus_timer_var") else 0
        if mins > 0 and done:
            self._focus_deadline = time.time() + mins * 60
            self._focus_after = self.after(mins * 60 * 1000, self._focus_auto_resume)
            self._focus_add_log(L("⏲ Авто-возврат через {m} мин").format(m=mins))
        self._focus_candidates_refresh()

    def _focus_auto_resume(self):
        self._focus_add_log(L("⏲ Сработал авто-возврат"))
        self._resume_all(silent=True)
        self._focus_candidates_refresh()

    # ---------- инструменты (в духе BoostSpeed) ----------
    def show_tools(self):
        tk.Label(self.main, text=L("Инструменты"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,8))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=22)
        for lbl, cmd in [("⚙️ Автозагрузка", self.t_startup), ("👯 Дубликаты", self.t_dupes), ("🖼 Похожие фото", self.t_similar), ("📦 Крупные файлы", self.t_large),
                         ("🗺 Карта диска", self.t_diskmap), ("🧳 Деинсталлятор", self.t_uninstall),
                         ("🖱 Контекстное меню", self.t_ctxmenu),
                         ("📂 Пустые папки", self.t_empty), ("🧩 Битые файлы", self.t_broken),
                         ("🔗 Битые ярлыки", self.t_shortcuts), ("📦🕒 Большие и старые", self.t_bigold),
                         ("📈 Что выросло", self.t_growth),
                         ("🔒 Приватность", self.t_privacy), ("🧩 Расширения браузеров", self.t_extensions),
                         ("🩺 Диск", self.t_smart), ("🩺 Диск-доктор", self.t_diskdoctor),
                         ("🗜 Сжать базы браузеров", self.t_vacuum),
                         ("📦 Snap/Flatpak", self.t_snapflatpak),
                         ("🧹 Предустановленное", self.t_bloatware),
                         ("♻️ Корзины томов", self.t_voltrash),
                         ("🔥 Шредер", self.t_shred),
                         ("🔄 Обновления", self.t_updates), ("📄 Отчёт", self.t_report)]:
            self._btn(bar, L(lbl), GLASS, cmd).pack(side="left", padx=4)
        self._dupe_extras = []
        self.t_action = tk.Frame(self.main, bg=BG0); self.t_action.pack(fill="x", padx=24, pady=(8,0))
        self.tout = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 11), relief="flat", padx=12, pady=10)
        self.tout.pack(fill="both", expand=True, padx=24, pady=12)
        self.tout.insert("end", L("Выберите инструмент.")+"\n"); self.tout.configure(state="disabled")

    def _out(self, t):
        self.tout.configure(state="normal"); self.tout.delete("1.0","end"); self.tout.insert("end", t); self.tout.configure(state="disabled")
        for w in self.t_action.winfo_children(): w.destroy()
        # новый инструмент запущен — прежние находки больше не актуальны для экспорта
        self._last_findings = None

    # ---------- экспорт находок (CSV/HTML) ----------
    def _set_findings(self, name, headers, rows):
        """Сохранить последний структурированный результат скана для экспорта.
        Вызывается из рабочих потоков перед q.put — присваивание атрибута атомарно,
        а читается он в главном потоке (кнопка «Экспорт»)."""
        self._last_findings = {"name": name, "headers": list(headers), "rows": list(rows)}

    def _export_findings(self, fmt):
        """Сохранить последний результат скана в ~/KRYLAN-<что>.<csv|html> и открыть.
        fmt: 'csv' | 'html'. Read-only по отношению к находкам."""
        import webbrowser
        f = getattr(self, "_last_findings", None)
        if not f or not f.get("rows"):
            messagebox.showinfo("KRYLAN", L("Нечего экспортировать — сначала выполните скан.")); return
        name, headers, rows = f["name"], f["headers"], f["rows"]
        path = os.path.join(HOME, "KRYLAN-%s.%s" % (name, fmt))
        try:
            if fmt == "csv":
                data = findings_to_csv(rows, headers)
                with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                    fh.write(data)
            else:  # html — переиспользуем общий генератор отчёта
                import datetime
                # каждую строку рендерим как (первый столбец → остальные через ·)
                sec_rows = []
                for r in rows:
                    label = str(r[0]) if r else ""
                    value = "  ·  ".join(str(c) for c in r[1:]) if len(r) > 1 else ""
                    sec_rows.append((label, value))
                title = L("KRYLAN — экспорт находок: {what}").format(what=name)
                html = build_html_report(
                    title,
                    [(" / ".join(str(h) for h in headers), sec_rows)],
                    generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(html)
            webbrowser.open("file://" + path)
            messagebox.showinfo("KRYLAN", L("💾 Экспортировано:\n{path}").format(path=path))
        except Exception as e:
            messagebox.showerror("KRYLAN", L("Не удалось экспортировать: {e}").format(e=e))

    def _add_export_buttons(self):
        """Добавить кнопки «💾 Экспорт CSV/HTML» в панель действий инструмента,
        если есть сохранённый результат скана."""
        f = getattr(self, "_last_findings", None)
        if not f or not f.get("rows"):
            return
        self._btn(self.t_action, L("💾 Экспорт CSV"), BLUE,
                  lambda: self._export_findings("csv")).pack(side="left", padx=(8,4), pady=4)
        self._btn(self.t_action, L("💾 Экспорт HTML"), BLUE,
                  lambda: self._export_findings("html")).pack(side="left", padx=4, pady=4)

    def t_startup(self):
        self._out(L("⚙️ Сканирую автозагрузку…")); threading.Thread(target=self._startup_w, daemon=True).start()

    def _startup_w(self):
        lines = [L("⚙️  Автозагрузка") + "\n\n"]
        if SYSTEM == "Windows":
            try:
                import winreg
                # карта «вкл/выкл» из StartupApproved\Run (байтовый флаг)
                approved = {}
                try:
                    ak = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run")
                    try:
                        j = 0
                        while True:
                            try:
                                an, av, _ = winreg.EnumValue(ak, j)
                                approved[an] = parse_startup_approved(av); j += 1
                            except OSError: break
                    finally:
                        winreg.CloseKey(ak)
                except Exception:
                    pass  # ключа может не быть — тогда статус неизвестен
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                try:
                    i = 0
                    while True:
                        try:
                            n, v, _ = winreg.EnumValue(k, i)
                            st = approved.get(n)
                            tag = (L("вкл") if st else L("выкл")) if st is not None else L("статус ?")
                            lines.append(f"  • {n}  [{tag}]\n      {v}\n"); i += 1
                        except OSError: break
                finally:
                    winreg.CloseKey(k)
            except Exception as e:
                lines.append("  " + L("ошибка чтения реестра: {e}").format(e=e) + "\n")
            # Win32_StartupCommand: Location/Command (если доступно)
            try:
                r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                         "Get-CimInstance Win32_StartupCommand | "
                         "Select-Object Name,Location,Command | Format-List"], timeout=30)
                body = [x.strip() for x in (r.stdout or "").splitlines() if x.strip()]
                if body:
                    lines.append("\n" + L("Системная автозагрузка (Location · Command):") + "\n")
                    lines += ["  " + x + "\n" for x in body]
            except Exception:
                pass
            lines.append("\n" + L("«вкл/выкл» — реальный статус из реестра. "
                                  "Отключить: Диспетчер задач → вкладка «Автозагрузка».") + "\n")
        elif SYSTEM == "Darwin":
            la = os.path.join(HOME, "Library/LaunchAgents")
            for f in (sorted(os.listdir(la)) if os.path.isdir(la) else []): lines.append(f"  • {f}\n")
            lines.append("\n" + L("Отключить: переименуйте .plist → .plist.disabled.") + "\n")
        else:
            ad = os.path.join(HOME, ".config/autostart")
            for f in (sorted(os.listdir(ad)) if os.path.isdir(ad) else []): lines.append(f"  • {f}\n")
            lines.append("\n" + L("Отключить: удалите .desktop из ~/.config/autostart.") + "\n")
        self.q.put(("tout", "".join(lines), None))

    def t_updates(self):
        self._out(L("🔄 Проверяю обновления приложений…")); threading.Thread(target=self._updates_w, daemon=True).start()

    def _updates_w(self):
        mgr, items, hint = list_updates()
        if mgr is None:
            self.q.put(("tout", L("🔄  Обновления приложений\n\n  {hint}").format(hint=hint) + "\n", None)); return
        lines = [L("🔄  Обновления приложений ({mgr})").format(mgr=mgr) + "\n\n"]
        if not items:
            lines.append("  " + L("✓ Все приложения актуальны.") + "\n")
        else:
            lines.append("  " + L("Найдено обновлений: {n}").format(n=len(items)) + "\n\n")
            for name, cur, new in items[:50]:
                lines.append(f"  • {name}\n      {cur}  →  {new}\n")
            lines.append(f"\n  {hint}\n")
        self.q.put(("tout", "".join(lines), None))

    def t_report(self):
        self._out(L("📄 Собираю отчёт о состоянии…")); threading.Thread(target=self._report_w, daemon=True).start()

    def _report_w(self):
        import webbrowser, datetime
        vm = psutil.virtual_memory()
        drive = HOME if SYSTEM != "Windows" else os.environ.get("SystemDrive", "C:") + "\\"
        du = psutil.disk_usage(drive)
        sysrows = [
            (L("Система"), os_label()),
            ("CPU", f"{psutil.cpu_percent(interval=0.3):.0f}%"),
            (L("Оперативная память"), L("{pct}% занято ({used} из {total})").format(pct=f"{vm.percent:.0f}", used=human(vm.used), total=human(vm.total))),
            (L("Диск"), L("{pct}% занято · свободно {free} из {total}").format(pct=f"{du.percent:.0f}", free=human(du.free), total=human(du.total))),
        ]
        cacherows, total = [], 0
        for name, p in cleanup_targets():
            sz = dir_size(p); total += sz
            cacherows.append((name, human(sz)))
        cacherows.append((L("Всего в кэшах"), human(total)))
        gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        htmlrep = build_html_report(L("KRYLAN — отчёт о состоянии"),
                                    [(L("Система"), sysrows), (L("Кэши (кандидаты на очистку)"), cacherows)],
                                    generated=gen)
        path = os.path.join(HOME, "KRYLAN-report.html")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(htmlrep)
            webbrowser.open("file://" + path)
            msg = L("📄  Отчёт сохранён\n\n  {path}\n\n  Открыт в браузере.\n\n  Всего в кэшах: {caches}\n  Свободно на диске: {free}").format(path=path, caches=human(total), free=human(du.free)) + "\n"
        except Exception as e:
            msg = L("📄  Не удалось сохранить отчёт: {e}").format(e=e) + "\n"
        self.q.put(("tout", msg, None))

    def t_large(self):
        self._out(L("📦 Ищу файлы >100 МБ…")); threading.Thread(target=self._large_w, daemon=True).start()

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
        t = L("📦  Крупные файлы (топ-25):") + "\n\n" + "".join(f"  {human(s):>9}  {fp.replace(HOME,'~')}\n" for s, fp in big[:25])
        self._set_findings("large", [L("Размер"), L("Байты"), L("Путь")],
                           [[human(s), s, fp] for s, fp in big])
        self.q.put(("toutx", t or L("  ничего\n"), None))

    def t_dupes(self):
        self._out(L("👯 Ищу дубликаты…")); threading.Thread(target=self._dupes_w, daemon=True).start()

    def _dupes_w(self):
        groups, extras, wasted = find_duplicates()
        t = L("👯  Дубликаты: групп {n}, освободить ~{size}").format(n=len(groups), size=human(wasted)) + "\n\n"
        for s, same in groups[:20]:
            t += f"  {human(s)} ×{len(same)}:\n" + "".join(f"      {p.replace(HOME,'~')}\n" for p in same) + "\n"
        rows = []
        for gi, (s, same) in enumerate(groups, 1):
            for p in same:
                rows.append([gi, human(s), s, p])
        self._set_findings("dupes", [L("Группа"), L("Размер"), L("Байты"), L("Путь")], rows)
        self.q.put(("dupes", t if groups else L("  дубликатов нет.\n"), extras))

    def _trash_dupes(self, extras):
        if not extras or not messagebox.askyesno("KRYLAN", L("Удалить {n} лишних копий в Корзину?").format(n=len(extras))): return
        ok = 0
        for p in extras:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_dupes()

    def t_similar(self):
        self._out(L("🖼 Ищу похожие фото…")); threading.Thread(target=self._similar_w, daemon=True).start()

    def _similar_w(self):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.q.put(("tout", L("🖼  Похожие фото\n\n  Не установлен Pillow.\n  Установите: pip install Pillow\n"), None)); return
        groups = find_similar_images()
        extras = [p for g in groups for p in g[1:]]
        t = L("🖼  Похожие фото: групп {n}, лишних {extra}").format(n=len(groups), extra=len(extras)) + "\n\n"
        for g in groups[:20]:
            t += "  " + L("похожих ×{n}:").format(n=len(g)) + "\n" + "".join(f"      {p.replace(HOME,'~')}\n" for p in g) + "\n"
        self.q.put(("similar", t if groups else L("  похожих фото нет.\n"), extras))

    def _trash_similar(self, extras):
        if not extras or not messagebox.askyesno("KRYLAN", L("Удалить {n} лишних похожих фото в Корзину?\n(в каждой группе остаётся первое)").format(n=len(extras))): return
        ok = 0
        for p in extras:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_similar()

    def t_diskmap(self):
        self._out(L("🗺 Считаю размеры папок…")); threading.Thread(target=self._diskmap_w, daemon=True).start()

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
        lines = [L("🗺  Карта диска — домашняя папка (топ-18):") + "\n\n"]
        for s, name in top:
            bar = "█" * max(1, int(s / mx * 28))
            lines.append(f"  {human(s):>9}  {bar}  {name}\n")
        lines.append("\n" + L("Самые тяжёлые папки — кандидаты на разбор в «Крупные файлы».") + "\n")
        self.q.put(("tout", "".join(lines), None))

    def t_uninstall(self):
        self._out(L("🧳 Собираю список приложений…")); threading.Thread(target=self._uninstall_w, daemon=True).start()

    def _uninstall_w(self):
        lines = [L("🧳  Деинсталлятор — установленные приложения") + "\n\n"]
        if SYSTEM == "Windows":
            try:
                import winreg
                apps = []
                for hive, path in [(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                                   (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")]:
                    try:
                        k = winreg.OpenKey(hive, path)
                        try:
                            for i in range(winreg.QueryInfoKey(k)[0]):
                                try:
                                    sk = winreg.OpenKey(k, winreg.EnumKey(k, i))
                                    try:
                                        name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                        try: size, _ = winreg.QueryValueEx(sk, "EstimatedSize")
                                        except OSError: size = 0
                                        apps.append((int(size or 0) * 1024, name))
                                    finally:
                                        winreg.CloseKey(sk)
                                except OSError: pass
                        finally:
                            winreg.CloseKey(k)
                    except OSError: pass
                apps.sort(reverse=True)
                for s, n in apps[:30]:
                    lines.append(f"  {human(s):>9}  {n}\n" if s else f"      —      {n}\n")
                lines.append("\n" + L("Удаление: Параметры → Приложения → выбрать → «Удалить».") + "\n")
            except Exception as e:
                lines.append("  " + L("ошибка чтения реестра: {e}").format(e=e) + "\n")
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
            lines.append("\n" + L("Удаление: перетащите .app из «Программ» в Корзину\n"
                         "(остатки ищите в ~/Library/Application Support и Caches).") + "\n")
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
                lines.append("\n" + L("Удаление: sudo apt remove <пакет>.") + "\n")
            except Exception:
                lines.append(L("  dpkg не найден — посмотрите менеджер пакетов вашего дистрибутива.\n"))
        self.q.put(("tout", "".join(lines), None))

    # ---------- 🖱 Менеджер контекстного меню Проводника (Windows) ----------
    # Управление ВИДИМОСТЬЮ пунктов меню — НЕ «чистка реестра».
    # Verb-пункты (shell\<verb>) скрываются/показываются ОБРАТИМО строковым
    # флагом LegacyDisable (ключ НИКОГДА не удаляется). Shellex-хендлеры —
    # только просмотр (их отключение рискованнее).
    CTXMENU_VERB_ROOTS = [
        (r"*\shell",                  "Файлы (*)"),
        (r"Directory\shell",          "Папки"),
        (r"Directory\Background\shell", "Фон папки"),
    ]
    CTXMENU_HANDLER_ROOTS = [
        (r"*\shellex\ContextMenuHandlers",                  "Файлы (*) · хендлеры"),
        (r"Directory\shellex\ContextMenuHandlers",          "Папки · хендлеры"),
        (r"Directory\Background\shellex\ContextMenuHandlers", "Фон папки · хендлеры"),
    ]

    def t_ctxmenu(self):
        self._out(L("🖱 Читаю контекстное меню Проводника…"))
        threading.Thread(target=self._ctxmenu_w, daemon=True).start()

    def _ctxmenu_w(self):
        lines = [L("🖱  Контекстное меню Проводника") + "\n\n"]
        toggles = []  # [(root, verb, "включён"/"выключен")] — для кнопок
        if SYSTEM != "Windows":
            lines.append("  " + L("Только Windows.") + "\n\n")
            lines.append("  " + L("Этот инструмент читает пункты меню Проводника из реестра "
                                  "Windows (HKCR) и обратимо показывает/скрывает их флагом "
                                  "LegacyDisable. На macOS/Linux он недоступен.") + "\n")
            self.q.put(("ctxmenu", "".join(lines), None)); return
        try:
            import winreg
        except Exception as e:
            lines.append("  " + L("ошибка чтения реестра: {e}").format(e=e) + "\n")
            self.q.put(("ctxmenu", "".join(lines), None)); return

        # --- verb-пункты (управляемые) ---
        for root, title in self.CTXMENU_VERB_ROOTS:
            lines.append("  " + title + "  (" + root + ")\n")
            verbs = []
            try:
                rk = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, root)
                try:
                    for i in range(winreg.QueryInfoKey(rk)[0]):
                        try: verbs.append(winreg.EnumKey(rk, i))
                        except OSError: break
                finally:
                    winreg.CloseKey(rk)
            except OSError:
                lines.append("      " + L("(нет пунктов)") + "\n\n"); continue
            if not verbs:
                lines.append("      " + L("(нет пунктов)") + "\n")
            for verb in sorted(verbs):
                vpath = root + "\\" + verb
                value_names, command = [], ""
                try:
                    vk = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, vpath)
                    try:
                        for j in range(winreg.QueryInfoKey(vk)[1]):
                            try: value_names.append(winreg.EnumValue(vk, j)[0])
                            except OSError: break
                    finally:
                        winreg.CloseKey(vk)
                except OSError:
                    pass
                try:
                    ck = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, vpath + "\\command")
                    try:
                        command = winreg.QueryValueEx(ck, "")[0] or ""
                    finally:
                        winreg.CloseKey(ck)
                except OSError:
                    pass
                status = ctxmenu_status(value_names)
                tag = L("включён") if status == "включён" else L("выключен")
                lines.append(f"      • {verb}  [{tag}]\n")
                if command:
                    lines.append(f"          {command}\n")
                toggles.append((root, verb, status))
            lines.append("\n")

        # --- shellex-хендлеры (только просмотр) ---
        for root, title in self.CTXMENU_HANDLER_ROOTS:
            lines.append("  " + title + "  (" + root + ")  — " + L("только просмотр") + "\n")
            try:
                rk = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, root)
                try:
                    handlers = []
                    for i in range(winreg.QueryInfoKey(rk)[0]):
                        try:
                            hn = winreg.EnumKey(rk, i)
                        except OSError:
                            break
                        clsid = ""
                        try:
                            hk = winreg.OpenKey(rk, hn)
                            try: clsid = winreg.QueryValueEx(hk, "")[0] or ""
                            finally: winreg.CloseKey(hk)
                        except OSError:
                            pass
                        handlers.append((hn, clsid))
                finally:
                    winreg.CloseKey(rk)
                if not handlers:
                    lines.append("      " + L("(нет пунктов)") + "\n")
                for hn, clsid in sorted(handlers):
                    lines.append(f"      • {hn}" + (f"  {clsid}\n" if clsid else "\n"))
            except OSError:
                lines.append("      " + L("(нет пунктов)") + "\n")
            lines.append("\n")

        lines.append("  " + L("«выключить» добавляет обратимый флаг LegacyDisable "
                              "(ключ реестра НЕ удаляется); «включить» снимает его. "
                              "Хендлеры (shellex) показаны только для просмотра.") + "\n")
        self.q.put(("ctxmenu", "".join(lines), toggles or None))

    def _ctxmenu_toggle(self, root, verb, disable):
        """Скрыть (disable=True) / показать (disable=False) verb-пункт меню
        обратимым флагом LegacyDisable. Ключ реестра НИКОГДА не удаляется."""
        if SYSTEM != "Windows":
            return
        if not messagebox.askyesno("KRYLAN",
                (L("Скрыть пункт «{verb}» из контекстного меню?\n(обратимо: флаг LegacyDisable)")
                 if disable else
                 L("Показать пункт «{verb}» в контекстном меню?\n(снять флаг LegacyDisable)")).format(verb=verb)):
            return
        try:
            import winreg
            vpath = root + "\\" + verb
            k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, vpath, 0,
                               winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
            try:
                if disable:
                    winreg.SetValueEx(k, "LegacyDisable", 0, winreg.REG_SZ, "")
                else:
                    try: winreg.DeleteValue(k, "LegacyDisable")
                    except OSError: pass  # уже отсутствует — пункт и так виден
            finally:
                winreg.CloseKey(k)
        except PermissionError:
            messagebox.showerror("KRYLAN", L("Нужны права администратора для изменения этого пункта."))
        except Exception as e:
            messagebox.showerror("KRYLAN", L("Не удалось изменить пункт: {e}").format(e=e))
        self.t_ctxmenu()  # перечитать актуальный статус

    def t_privacy(self):
        self._out(L("🔒 Ищу следы браузеров…")); threading.Thread(target=self._privacy_w, daemon=True).start()

    def _privacy_w(self):
        targets = privacy_targets()
        running = running_browsers()
        lines = [L("🔒  Приватность — следы браузеров") + "\n\n"]
        total = 0
        for b, item, p in targets:
            try: sz = os.path.getsize(p)
            except OSError: sz = 0
            total += sz
            lines.append(f"  {human(sz):>9}  {b}: {item}\n")
        if not targets:
            lines.append(L("  следов не найдено.\n"))
        if running:
            lines.append("\n" + L("⚠️ Сначала закройте: {browsers} — иначе файлы заняты.").format(browsers=', '.join(sorted(running))) + "\n")
        lines.append("\n" + L("Всего следов: ~{size}. История и cookies уйдут в Корзину (вы выйдете из аккаунтов).").format(size=human(total)) + "\n")
        files = [] if running else [p for _, _, p in targets]
        self.q.put(("privacy", "".join(lines), files))

    def _privacy_clean(self, files):
        if not messagebox.askyesno("KRYLAN", L("Переместить {n} файлов следов в Корзину?\nВы выйдете из аккаунтов в браузерах.").format(n=len(files))): return
        ok = 0
        for p in files:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_privacy()

    def t_extensions(self):
        self._out(L("🧩 Читаю расширения браузеров…")); threading.Thread(target=self._extensions_w, daemon=True).start()

    def _extensions_w(self):
        exts = list_browser_extensions()
        lines = [L("🧩  Расширения браузеров (только просмотр)") + "\n\n"]
        if not exts:
            lines.append(L("  расширений не найдено.\n"))
        else:
            by_browser = {}
            for browser, name, ext_id in exts:
                by_browser.setdefault(browser, []).append((name, ext_id))
            for browser in sorted(by_browser):
                items = sorted(by_browser[browser], key=lambda x: x[0].lower())
                lines.append(f"  {browser} ({len(items)}):\n")
                for name, ext_id in items:
                    lines.append(f"    • {name}\n        id: {ext_id}\n")
                lines.append("\n")
            lines.append("  " + L("Всего расширений: {n}.").format(n=len(exts)) + "\n")
        lines.append("\n" + L("KRYLAN ничего не удаляет. Отключить лишние можно в самом браузере: меню → «Расширения».") + "\n")
        self.q.put(("tout", "".join(lines), None))

    def t_growth(self):
        self._out(L("📈 Сравниваю с прошлой проверкой…")); threading.Thread(target=self._growth_w, daemon=True).start()

    def _growth_w(self):
        changes, is_first = growth_report()
        if is_first:
            lines = [L("📈  Что выросло") + "\n\n",
                     L("Первый снимок сохранён. Запустите ещё раз позже —\n"
                     "и KRYLAN покажет, какие папки выросли или уменьшились.") + "\n\n",
                     L("Текущие размеры:") + "\n"]
            for delta, path, old, new in changes:
                lines.append(f"  {human(new):>9}  {path.replace(HOME,'~')}\n")
        else:
            lines = [L("📈  Изменения с прошлой проверки") + "\n\n"]
            shown = False
            for delta, path, old, new in changes:
                if delta == 0: continue
                shown = True
                sign = "▲" if delta > 0 else "▼"
                lines.append(f"  {sign} {human(abs(delta)):>9}   {human(new):>9}  {path.replace(HOME,'~')}\n")
            if not shown:
                lines.append(L("  Изменений нет — размеры папок не поменялись.\n"))
            lines.append("\n" + L("▲ выросло · ▼ уменьшилось. Растущие папки — кандидаты на разбор.") + "\n")
        self.q.put(("tout", "".join(lines), None))

    def t_empty(self):
        self._out(L("📂 Ищу пустые папки…")); threading.Thread(target=self._empty_w, daemon=True).start()

    def _empty_w(self):
        empties = find_empty_dirs()
        lines = [L("📂  Пустые папки: {n}").format(n=len(empties)) + "\n\n"]
        for p in empties[:40]:
            lines.append(f"  {p.replace(HOME,'~')}\n")
        if len(empties) > 40:
            lines.append("  " + L("…и ещё {n}\n").format(n=len(empties)-40))
        if not empties:
            lines.append(L("  пустых папок не найдено.\n"))
        lines.append("\n" + L("Пустые папки остаются после удаления программ и распаковки архивов. Уйдут в Корзину.") + "\n")
        self._set_findings("empty", [L("Путь")], [[p] for p in empties])
        self.q.put(("empty", "".join(lines), empties))

    def _empty_clean(self, dirs):
        if not dirs or not messagebox.askyesno("KRYLAN", L("Переместить {n} пустых папок в Корзину?").format(n=len(dirs))): return
        ok = 0
        # от глубоких к верхним, чтобы вложенные пустые тоже ушли
        for p in sorted(dirs, key=lambda x: x.count(os.sep), reverse=True):
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} папок.").format(n=ok)); self.t_empty()

    def t_broken(self):
        self._out(L("🧩 Ищу битые и пустые файлы…")); threading.Thread(target=self._broken_w, daemon=True).start()

    def _broken_w(self):
        items = find_broken_files()
        zero = [p for k, p in items if k == "zero"]
        links = [p for k, p in items if k == "symlink"]
        lines = [L("🧩  Битые и пустые файлы: {n} (пустых {zero}, битых ссылок {links})").format(n=len(items), zero=len(zero), links=len(links)) + "\n\n"]
        label = {"zero": L("пусто "), "symlink": L("ссылка")}
        for k, p in items[:60]:
            lines.append(f"  [{label[k]}]  {p.replace(HOME,'~')}\n")
        if len(items) > 60:
            lines.append("  " + L("…и ещё {n}\n").format(n=len(items)-60))
        if not items:
            lines.append(L("  битых и пустых файлов не найдено.\n"))
        lines.append("\n" + L("Пустые файлы (0 байт) и битые символические ссылки бесполезны. Уйдут в Корзину.") + "\n")
        files = [p for _, p in items]
        self._set_findings("broken", [L("Тип"), L("Путь")],
                           [[label.get(k, k).strip(), p] for k, p in items])
        self.q.put(("broken", "".join(lines), files))

    def _broken_clean(self, files):
        if not files or not messagebox.askyesno("KRYLAN", L("Переместить {n} битых/пустых файлов в Корзину?").format(n=len(files))): return
        ok = 0
        for p in files:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_broken()

    def t_shortcuts(self):
        self._out(L("🔗 Ищу битые ярлыки…")); threading.Thread(target=self._shortcuts_w, daemon=True).start()

    def _shortcuts_w(self):
        items = find_broken_shortcuts()
        lines = [L("🔗  Битые ярлыки: {n}").format(n=len(items)) + "\n\n"]
        for _k, p in items[:60]:
            lines.append(f"  {p.replace(HOME,'~')}\n")
        if len(items) > 60:
            lines.append("  " + L("…и ещё {n}\n").format(n=len(items)-60))
        if not items:
            lines.append(L("  битых ярлыков не найдено.\n"))
        lines.append("\n" + L("Ярлыки, чья цель удалена, бесполезны. Уйдут в Корзину.") + "\n")
        files = [p for _, p in items]
        self.q.put(("shortcuts", "".join(lines), files))

    def _shortcuts_clean(self, files):
        if not files or not messagebox.askyesno("KRYLAN", L("Переместить {n} битых ярлыков в Корзину?").format(n=len(files))): return
        ok = 0
        for p in files:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_shortcuts()

    # пороги «больших и старых» (МБ / дней); список → файлы для удаления по выбору
    BIGOLD_MIN_MB = 200
    BIGOLD_MIN_DAYS = 180

    def t_bigold(self):
        self._out(L("📦🕒 Ищу большие старые файлы…")); threading.Thread(target=self._bigold_w, daemon=True).start()

    def _bigold_w(self):
        bases = [os.path.join(HOME, d) for d in
                 ("Downloads", "Desktop", "Documents", "Pictures", "Movies", "Music")]
        items = []
        for base in bases:
            items.extend(scan_big_old(base, self.BIGOLD_MIN_MB, self.BIGOLD_MIN_DAYS, top=0))
        items.sort(reverse=True)
        items = items[:100]
        lines = [L("📦🕒  Большие и старые файлы: {n} (≥{mb} МБ · не трогали ≥{days} дн.)").format(
                 n=len(items), mb=self.BIGOLD_MIN_MB, days=self.BIGOLD_MIN_DAYS) + "\n\n"]
        for size, p, age in items[:60]:
            lines.append(f"  {human(size):>9}  ·{age:>4}д  {p.replace(HOME,'~')}\n")
        if len(items) > 60:
            lines.append("  " + L("…и ещё {n}\n").format(n=len(items)-60))
        if not items:
            lines.append(L("  больших старых файлов не найдено.\n"))
        lines.append("\n" + L("Крупные файлы, которые давно не открывали и не меняли. Уйдут в Корзину.") + "\n")
        files = [p for _s, p, _a in items]
        self._set_findings("bigold", [L("Размер"), L("Байты"), L("Возраст, дн."), L("Путь")],
                           [[human(size), size, age, p] for size, p, age in items])
        self.q.put(("bigold", "".join(lines), files))

    def _bigold_clean(self, files):
        if not files or not messagebox.askyesno("KRYLAN", L("Переместить {n} больших старых файлов в Корзину?").format(n=len(files))): return
        ok = 0
        for p in files:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_bigold()

    def t_shred(self):
        # НЕОБРАТИМАЯ операция: только по явному выбору файлов пользователем.
        # Шаг 1 — диалог выбора файлов; пустой выбор → выходим без действий.
        paths = filedialog.askopenfilenames(title=L("🔥 Шредер"))
        paths = [p for p in (paths or []) if p]
        if not paths:
            self._out(L("🔥  Шредер — безвозвратное затирание файлов") + "\n\n  " +
                      L("Файлы не выбраны.") + "\n\n" +
                      L("Выберите файлы — KRYLAN перезапишет их случайными данными и удалит. Это НЕОБРАТИМО (не Корзина)."))
            return
        # Шаг 2 — явное подтверждение со списком (последний шанс отменить).
        preview = "\n".join("  • " + p.replace(HOME, "~") for p in paths[:20])
        if len(paths) > 20:
            preview += "\n  " + L("…и ещё {n}\n").format(n=len(paths) - 20)
        if not messagebox.askyesno(
                "KRYLAN",
                L("⚠️ БЕЗВОЗВРАТНО затереть и удалить {n} файл(ов)?\n\nЭто НЕЛЬЗЯ отменить — файлы НЕ попадут в Корзину, восстановить их будет невозможно.").format(n=len(paths))
                + "\n\n" + preview,
                icon="warning", default="no"):
            return
        self._out(L("🔥 Затираю файлы случайными данными…"))
        threading.Thread(target=self._shred_w, args=(list(paths),), daemon=True).start()

    def _shred_w(self, paths):
        ok = skipped = 0
        for p in paths:
            if shred_file(p, passes=1):
                ok += 1
            else:
                skipped += 1
        lines = [L("🔥  Шредер — готово") + "\n\n",
                 "  " + L("Затёрто и удалено безвозвратно: {n}").format(n=ok) + "\n"]
        if skipped:
            lines.append("  " + L("Пропущено (защищено/недоступно): {n}").format(n=skipped) + "\n")
        self.q.put(("shred", "".join(lines), ok))

    # ---------- 🧹 Предустановленное (Windows bloatware-листер, read-only) ----------
    def t_bloatware(self):
        self._out(L("🧹 Собираю список предустановленных приложений…"))
        threading.Thread(target=self._bloatware_w, daemon=True).start()

    def _bloatware_w(self):
        if SYSTEM != "Windows":
            self.q.put(("tout", L("🧹  Предустановленное (bloatware)") + "\n\n  " +
                        L("Только Windows. На этой ОС инструмент недоступен.") + "\n", None))
            return
        r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Get-AppxPackage | Select-Object -ExpandProperty Name"], timeout=60)
        names = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        bloat = [n for n in names if is_bloatware(n)]
        lines = [L("🧹  Предустановленное (bloatware) — только показ, ничего не удаляется") + "\n\n"]
        lines.append(L("Всего UWP-пакетов: {n}, из них помечено как bloat: {b}").format(n=len(names), b=len(bloat)) + "\n\n")
        if bloat:
            for n in sorted(bloat):
                lines.append(f"  • {n}\n")
            lines.append("\n" + L("Как удалить безопасно: Параметры → Приложения → найдите пакет → Удалить.") + "\n")
            lines.append(L("Либо в PowerShell: Get-AppxPackage <имя> | Remove-AppxPackage (на свой риск).") + "\n")
        else:
            lines.append(L("  Известного предустановленного bloat не найдено.") + "\n")
        # экспортируемый результат
        self._set_findings("bloatware", [L("Пакет")], [[n] for n in sorted(bloat)])
        self.q.put(("toutx", "".join(lines), None))

    # ---------- ♻️ Корзины томов (многотомная корзина) ----------
    def t_voltrash(self):
        self._out(L("♻️ Считаю размер корзин на всех томах…"))
        threading.Thread(target=self._voltrash_w, daemon=True).start()

    def _voltrash_w(self):
        locs = trash_locations()
        sized = [(dir_size(p), p) for p in locs]
        sized.sort(reverse=True)
        total = sum(s for s, _ in sized)
        lines = [L("♻️  Корзины томов") + "\n\n"]
        if sized:
            for s, p in sized:
                lines.append(f"  {human(s):>9}  {p.replace(HOME,'~')}\n")
            lines.append("\n" + L("Суммарно в корзинах: {size}").format(size=human(total)) + "\n")
            lines.append("\n" + L("⚠️ Очистка корзины НЕОБРАТИМА (как Шредер). Только по явной кнопке.") + "\n")
        else:
            lines.append(L("  Корзин на томах не найдено (или они пусты).") + "\n")
        self._set_findings("trash-volumes", [L("Размер"), L("Байты"), L("Путь")],
                           [[human(s), s, p] for s, p in sized])
        # b — список путей для очистки (только если есть что чистить)
        self.q.put(("voltrash", "".join(lines), [p for _s, p in sized] if total > 0 else None))

    def _voltrash_empty(self, paths):
        """НЕОБРАТИМО очистить содержимое корзин на всех томах. Только по явной кнопке."""
        if not paths:
            return
        if not messagebox.askyesno(
                "KRYLAN",
                L("⚠️ БЕЗВОЗВРАТНО очистить корзины на всех томах ({n})?\n\nЭто НЕЛЬЗЯ отменить — содержимое корзин будет удалено навсегда.").format(n=len(paths)),
                icon="warning", default="no"):
            return
        self._out(L("♻️ Очищаю корзины томов…"))
        threading.Thread(target=self._voltrash_empty_w, args=(list(paths),), daemon=True).start()

    def _voltrash_empty_w(self, paths):
        import shutil
        removed = 0
        for base in paths:
            try:
                for name in os.listdir(base):
                    target = os.path.join(base, name)
                    try:
                        if os.path.islink(target) or os.path.isfile(target):
                            os.remove(target); removed += 1
                        elif os.path.isdir(target):
                            shutil.rmtree(target, ignore_errors=True); removed += 1
                    except Exception:
                        pass
            except Exception:
                pass
        lines = [L("♻️  Корзины томов — очищено") + "\n\n",
                 "  " + L("Удалено элементов (необратимо): {n}").format(n=removed) + "\n"]
        self.q.put(("shred", "".join(lines), removed))

    def t_smart(self):
        self._out(L("🩺 Читаю состояние диска…"))
        threading.Thread(target=lambda: self.q.put(("tout", disk_health_report(), None)), daemon=True).start()

    def t_diskdoctor(self):
        # read-only проверка диска на ошибки (ничего не чинит); может идти долго
        self._out(L("🩺 Проверяю диск на ошибки (только чтение)…"))
        threading.Thread(target=lambda: self.q.put(("tout", disk_doctor_report(), None)), daemon=True).start()

    # ---------- 🗜 Сжать базы браузеров (VACUUM SQLite) ----------
    def t_vacuum(self):
        self._out(L("🗜 Ищу базы браузеров…")); threading.Thread(target=self._vacuum_w, daemon=True).start()

    def _vacuum_w(self):
        dbs = browser_sqlite_dbs()
        running = running_browsers()
        # сопоставляем браузер → запущен ли (Brave не в running_browsers → считаем
        # закрытым, как и было; основной критерий — Chrome/Edge/Firefox).
        lines = [L("🗜  Сжатие баз браузеров (VACUUM)") + "\n\n"]
        total = 0
        candidates = []   # пути закрытых браузеров — можно сжимать
        for browser, fp in dbs:
            try: sz = os.path.getsize(fp)
            except OSError: sz = 0
            total += sz
            busy = browser in running
            lines.append(f"  {human(sz):>9}  {browser}: {os.path.basename(fp)}"
                         + ("  ⏸" if busy else "") + "\n")
            if not busy:
                candidates.append(fp)
        if not dbs:
            lines.append(L("  баз для сжатия не найдено.\n"))
        if running:
            lines.append("\n" + L("⚠️ Сначала закройте: {browsers} — их базы заняты и будут пропущены.")
                         .format(browsers=', '.join(sorted(running))) + "\n")
        lines.append("\n" + L("Найдено баз: {n} (~{size}). VACUUM перепаковывает файл без потери данных.")
                     .format(n=len(candidates), size=human(total)) + "\n")
        self.q.put(("vacuum", "".join(lines), candidates))

    def _vacuum_run(self, files):
        if not files or not messagebox.askyesno("KRYLAN",
                L("Сжать {n} баз закрытых браузеров?\nДанные не удаляются — только перепаковка (VACUUM).").format(n=len(files))):
            return
        self._out(L("🗜 Ищу базы браузеров…"))
        threading.Thread(target=self._vacuum_do_w, args=(list(files),), daemon=True).start()

    def _vacuum_do_w(self, files):
        # повторно проверяем, что браузеры всё ещё закрыты (иначе пропускаем)
        running = running_browsers()
        busy_files = {fp for b, fp in browser_sqlite_dbs() if b in running}
        done = saved = skipped = 0
        for fp in files:
            if fp in busy_files:
                skipped += 1
                continue
            before, after = vacuum_sqlite(fp)
            if after < before:
                saved += (before - after)
            done += 1
        lines = [L("🗜  Сжатие завершено") + "\n\n",
                 "  " + L("Сжато баз: {n}").format(n=done) + "\n",
                 "  " + L("Сэкономлено: {size}").format(size=human(saved)) + "\n"]
        if skipped:
            lines.append("  " + L("⏭ Пропущено (браузер запущен): {n}").format(n=skipped) + "\n")
        self.q.put(("vacuumdone", "".join(lines), (done, saved)))

    # ---------- 📦 Snap/Flatpak (Linux): очистка неиспользуемого ----------
    def t_snapflatpak(self):
        self._out(L("📦 Ищу неиспользуемые snap/flatpak…")); threading.Thread(target=self._snapflatpak_w, daemon=True).start()

    def _snapflatpak_w(self):
        lines = [L("📦  Snap / Flatpak — неиспользуемое (Linux)") + "\n\n"]
        if SYSTEM != "Linux":
            lines.append("  " + L("Только Linux: эта функция доступна на Linux.") + "\n")
            self.q.put(("tout", "".join(lines), None)); return
        import shutil as _sh
        has_flatpak = _sh.which("flatpak") is not None
        has_snap = _sh.which("snap") is not None
        # flatpak: «есть ли неиспользуемое» — dry-run через `flatpak uninstall --unused`
        flatpak_unused = False
        if has_flatpak:
            r = run(["flatpak", "uninstall", "--unused", "--dry-run"], timeout=30)
            # непустой stdout с упоминанием runtime → есть что чистить
            flatpak_unused = bool((r.stdout or "").strip())
            lines.append("  " + (L("Flatpak: есть неиспользуемые среды выполнения для удаления.")
                                 if flatpak_unused else L("Flatpak: неиспользуемого не найдено.")) + "\n")
        else:
            lines.append("  " + L("Flatpak не установлен — пропущено.") + "\n")
        # snap: отключённые ревизии из `snap list --all`
        disabled = []
        if has_snap:
            r = run(["snap", "list", "--all"], timeout=30)
            disabled = parse_disabled_snaps(r.stdout or "")
            if disabled:
                lines.append("  " + L("Snap: отключённых ревизий: {n}").format(n=len(disabled)) + "\n")
                for name, rev in disabled[:30]:
                    lines.append(f"      {name}  rev {rev}\n")
                if not has_root():
                    lines.append("  " + L("⚠️ Удаление ревизий snap требует прав root — пропущено (запустите с sudo).") + "\n")
            else:
                lines.append("  " + L("Snap: отключённых ревизий не найдено.") + "\n")
        else:
            lines.append("  " + L("Snap не установлен — пропущено.") + "\n")
        lines.append("\n" + L("Безопасно: удаляются только официально неиспользуемые среды (flatpak --unused) и отключённые ревизии snap. Установленные приложения не трогаются.") + "\n")
        # действие предлагаем, только если есть что чистить (snap-ревизии — лишь при root)
        snap_to_remove = disabled if (disabled and has_root()) else []
        payload = {"flatpak": has_flatpak and flatpak_unused, "snaps": snap_to_remove}
        has_action = payload["flatpak"] or bool(snap_to_remove)
        self.q.put(("snapflatpak", "".join(lines), payload if has_action else None))

    def _snapflatpak_clean(self, payload):
        snaps = payload.get("snaps", [])
        if not messagebox.askyesno("KRYLAN",
                L("Удалить неиспользуемые flatpak-среды и {n} отключённых ревизий snap?").format(n=len(snaps))):
            return
        self._out(L("📦 Ищу неиспользуемые snap/flatpak…"))
        threading.Thread(target=self._snapflatpak_do_w, args=(payload,), daemon=True).start()

    def _snapflatpak_do_w(self, payload):
        lines = [L("📦  Snap / Flatpak — очистка завершена") + "\n\n"]
        if payload.get("flatpak"):
            r = run(["flatpak", "uninstall", "--unused", "-y"], timeout=300)
            lines.append("  " + (L("✅ Flatpak: неиспользуемое удалено (flatpak --unused).")
                                 if r.returncode == 0 else L("⏭ Flatpak: удаление пропущено.")) + "\n")
        ok = skip = 0
        for name, rev in payload.get("snaps", []):
            r = run(["snap", "remove", name, "--revision=" + str(rev)], timeout=120)
            if r.returncode == 0:
                ok += 1
            else:
                skip += 1
        if ok:
            lines.append("  " + L("✅ Snap: удалено отключённых ревизий: {n}").format(n=ok) + "\n")
        if skip:
            lines.append("  " + L("⏭ Snap: ревизии пропущены (нет прав/ошибка): {n}").format(n=skip) + "\n")
        self.q.put(("tout", "".join(lines), None))

    # ---------- о программе ----------
    def show_about(self):
        tk.Label(self.main, text="🪽 KRYLAN", bg=BG0, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=24, pady=(26,0))
        tk.Label(self.main, text=L("«Дай устройству крылья»"), bg=BG0, fg=GREEN, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=24)
        creator = L("Создатель: Кырлан Александр Сергеевич")
        for line in [L("Версия {v} · {os}").format(v=VERSION, os=os_label()), creator, "",
                     L("Кросс-платформенный оптимизатор: Windows · macOS · Linux."),
                     L("Мониторинг CPU/ОЗУ/диск/батарея и безопасная очистка кэшей"),
                     L("(всё уходит в Корзину). Часть экосистемы KRYLAN (+iPhone, Android).")]:
            tk.Label(self.main, text=line, bg=BG0, fg=(TEXT if line == creator else MUTED),
                     font=("Segoe UI", 11)).pack(anchor="w", padx=24)

    # ====================  СТРАНИЦА «АВТОПИЛОТ»  ====================
    def show_autopilot(self):
        tk.Label(self.main, text=L("Автопилот"), bg=BG0, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(self.main, text=L("Фоновый страж следит за памятью и при пике сам безопасно чистит и разгружает."),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0, 12))

        # --- карта состояния + Включить/Выключить ---
        card = tk.Frame(self.main, bg=GLASS); card.pack(fill="x", padx=24, pady=6)
        self.ap_state = tk.Label(card, text="…", bg=GLASS, fg=TEXT, font=("Segoe UI", 15, "bold"))
        self.ap_state.pack(side="left", padx=18, pady=16)
        self._btn(card, L("Включить"), GREEN, lambda: self._ap_toggle(True)).pack(side="right", padx=(8, 18), pady=12)
        self._btn(card, L("Выключить"), RED, lambda: self._ap_toggle(False)).pack(side="right", pady=12)

        # --- действия ---
        row = tk.Frame(self.main, bg=BG0); row.pack(fill="x", padx=24, pady=8)
        self._btn(row, L("⚡ Оптимизировать сейчас"), BLUE, self._ap_optimize_now).pack(side="left")

        # --- настройки порога/интервала ---
        opt = tk.Frame(self.main, bg=GLASS); opt.pack(fill="x", padx=24, pady=6)
        tk.Label(opt, text=L("Порог памяти, %"), bg=GLASS, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 4))
        self.ap_thr_var = tk.IntVar(value=self.ap_cfg["threshold"])
        self.ap_thr_lbl = tk.Label(opt, text=f"{self.ap_cfg['threshold']}%", bg=GLASS, fg=TEXT,
                                   font=("Segoe UI", 10, "bold"))
        self.ap_thr_lbl.grid(row=0, column=2, sticky="w", padx=8)
        tk.Scale(opt, from_=50, to=99, orient="horizontal", variable=self.ap_thr_var,
                 showvalue=False, length=240, bg=GLASS, fg=TEXT, troughcolor=TRACK,
                 highlightthickness=0, command=self._ap_thr_changed).grid(row=0, column=1, sticky="w", pady=(8, 0))
        tk.Label(opt, text=L("Интервал проверки, с"), bg=GLASS, fg=MUTED,
                 font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(4, 12))
        self.ap_int_var = tk.IntVar(value=self.ap_cfg["interval"])
        self.ap_int_lbl = tk.Label(opt, text=f"{self.ap_cfg['interval']} с", bg=GLASS, fg=TEXT,
                                   font=("Segoe UI", 10, "bold"))
        self.ap_int_lbl.grid(row=1, column=2, sticky="w", padx=8)
        tk.Scale(opt, from_=5, to=300, orient="horizontal", variable=self.ap_int_var,
                 showvalue=False, length=240, bg=GLASS, fg=TEXT, troughcolor=TRACK,
                 highlightthickness=0, command=self._ap_int_changed).grid(row=1, column=1, sticky="w")

        # --- переключатель закрытия браузеров (по умолчанию ВЫКЛ) ---
        self.ap_close_var = tk.BooleanVar(value=self.ap_cfg["close_browsers"])
        tk.Checkbutton(self.main, variable=self.ap_close_var, command=self._ap_close_changed,
                       text=L("  Разрешить закрывать фоновые браузеры при пике памяти"),
                       bg=BG0, fg=TEXT, selectcolor=GLASS, activebackground=BG0, activeforeground=TEXT,
                       font=("Segoe UI", 10), anchor="w").pack(anchor="w", padx=22, pady=(8, 0))

        # --- автозапуск при входе ---
        self.ap_auto_var = tk.BooleanVar(value=autostart_status())
        tk.Checkbutton(self.main, variable=self.ap_auto_var, command=self._ap_autostart_changed,
                       text=L("  Запускать страж автоматически при входе в систему"),
                       bg=BG0, fg=TEXT, selectcolor=GLASS, activebackground=BG0, activeforeground=TEXT,
                       font=("Segoe UI", 10), anchor="w").pack(anchor="w", padx=22, pady=(2, 0))
        self.ap_auto_hint = tk.Label(self.main, text="", bg=BG0, fg=MUTED, font=("Segoe UI", 9))
        self.ap_auto_hint.pack(anchor="w", padx=44)

        tk.Label(self.main, text=L("Автопилот чистит кэши и разгружает память, не трогая ваши данные. "
                 "Дефрагментация SSD не нужна и вредна — её здесь нет."),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 9), wraplength=560, justify="left"
                 ).pack(anchor="w", padx=24, pady=(8, 6))

        tk.Label(self.main, text=L("Журнал автопилота:"), bg=BG0, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(4, 2))
        self.ap_log = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 10), relief="flat",
                              padx=12, pady=10, height=8)
        self.ap_log.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self._ap_refresh()

    def _ap_refresh(self):
        if not (hasattr(self, "ap_state") and self.ap_state.winfo_exists()):
            return
        running = self.guardian.is_running()
        self.ap_state.configure(text=(L("🟢 Автопилот работает") if running else L("🔴 Автопилот остановлен")),
                                fg=(GREEN if running else RED))
        log = read_autopilot_log(2500) or L("(журнал пуст — пиков памяти ещё не было)")
        self.ap_log.configure(state="normal"); self.ap_log.delete("1.0", "end")
        self.ap_log.insert("end", log); self.ap_log.see("end")
        self.ap_log.configure(state="disabled")

    def _ap_save(self):
        save_autopilot_config(self.ap_cfg)
        self.guardian.update_config(self.ap_cfg)

    def _ap_toggle(self, enable):
        self.ap_cfg["enabled"] = bool(enable)
        self._ap_save()
        if enable: self.guardian.start()
        else: self.guardian.stop()
        self._ap_refresh()

    def _ap_optimize_now(self):
        autopilot_log(L("⚡ Запрошена оптимизация вручную"))
        self._ap_refresh()
        close_b = self.ap_cfg["close_browsers"]
        threading.Thread(target=lambda: (autopilot_optimize_once(close_browsers=close_b),
                                         self.q.put(("apevent", "optimized", None))),
                         daemon=True).start()

    def _ap_thr_changed(self, _v=None):
        self.ap_cfg["threshold"] = int(self.ap_thr_var.get())
        self.ap_thr_lbl.configure(text=f"{self.ap_cfg['threshold']}%")
        self._ap_save()

    def _ap_int_changed(self, _v=None):
        self.ap_cfg["interval"] = int(self.ap_int_var.get())
        self.ap_int_lbl.configure(text=f"{self.ap_cfg['interval']} с")
        self._ap_save()

    def _ap_close_changed(self):
        self.ap_cfg["close_browsers"] = bool(self.ap_close_var.get())
        self._ap_save()

    def _ap_autostart_changed(self):
        want = bool(self.ap_auto_var.get())
        ok = autostart_enable() if want else autostart_disable()
        # отражаем фактический результат (если не получилось — честно вернём чекбокс)
        actual = autostart_status()
        self.ap_auto_var.set(actual)
        self.ap_cfg["autostart"] = actual
        save_autopilot_config(self.ap_cfg)
        if hasattr(self, "ap_auto_hint") and self.ap_auto_hint.winfo_exists():
            if want and not actual:
                self.ap_auto_hint.configure(text=L("Не удалось настроить автозапуск в этой системе."), fg=YELLOW)
            elif actual:
                self.ap_auto_hint.configure(text=L("Автозапуск настроен."), fg=GREEN)
            else:
                self.ap_auto_hint.configure(text=L("Автозапуск выключен."), fg=MUTED)

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
                try: swap_mb = psutil.swap_memory().used / (1024 * 1024)
                except Exception: swap_mb = 0
                # «Здоровье» 0..100: чем меньше загрузка cpu/ram/disk — тем выше.
                health = max(0, 100 - (0.30*cpu + 0.35*ram + 0.35*du.percent))
                up = down = 0
                try:
                    cur = psutil.net_io_counters(); now = time.time(); dt = max(0.2, now - prev_t)
                    if prev: up = (cur.bytes_sent - prev.bytes_sent)/dt; down = (cur.bytes_recv - prev.bytes_recv)/dt
                    prev, prev_t = cur, now
                except Exception: pass
                self.q.put(("stats", {"cpu":cpu,"ram":ram,"disk":du.percent,
                            "batt": (b.percent if b else None),
                            "health": health, "swap_mb": swap_mb,
                            "disk_free": du.free, "disk_total": du.total,
                            "net_up": max(0,up), "net_down": max(0,down)}, None))
            except Exception: pass
            time.sleep(1.2)

    def _animate(self):
        self.fr = getattr(self, "fr", 0) + 1
        if self.page=="dash" and hasattr(self,"cv") and self.cv.winfo_exists():
            for k in self.disp: self.disp[k] += (self.tgt[k]-self.disp[k])*0.25
            self._draw_dash()
        self.after(33, self._animate)

    def _poll(self):
        try:
            while True:
                kind,a,b = self.q.get_nowait()
                if kind == "stats":
                    self.tgt.update({"cpu":a["cpu"],"ram":a["ram"],"disk":a["disk"],"batt":a["batt"] or 0,
                                     "health":a.get("health",100)})
                    self.swap_mb = a.get("swap_mb", 0)
                    self.info["batt"] = a["batt"]; self.info["disk_free"]=a["disk_free"]; self.info["disk_total"]=a["disk_total"]
                    self.info["net_up"]=a.get("net_up",0); self.info["net_down"]=a.get("net_down",0)
                    self.info["os"] = self.info.get("os","")
                elif kind == "clsize":
                    if a in self.cl_lbl: self.cl_lbl[a].configure(text=human(b))
                elif kind == "cltotal": self.cl_total.configure(text=L("Найдено: {size}").format(size=human(a)))
                elif kind == "cldone":
                    self.cl_total.configure(text=L("Очищено: {size} → Корзина").format(size=human(a)))
                    messagebox.showinfo("KRYLAN", L("В Корзину: {size}.").format(size=human(a))); self.found = {}
                elif kind == "optstep":
                    if self.page == "dash" and hasattr(self, "opt_out") and self.opt_out.winfo_exists():
                        self.opt_out.configure(state="normal"); self.opt_out.insert("end", a)
                        self.opt_out.see("end"); self.opt_out.configure(state="disabled")
                elif kind == "optpreview":
                    if self.page == "dash" and hasattr(self, "opt_out") and self.opt_out.winfo_exists():
                        # read-only сводка предпросмотра: заменяем содержимое лога,
                        # кнопок-действий не добавляем (ничего не удаляем).
                        self.opt_out.configure(state="normal")
                        self.opt_out.delete("1.0", "end"); self.opt_out.insert("end", a)
                        self.opt_out.see("end"); self.opt_out.configure(state="disabled")
                        for w in self.opt_action.winfo_children(): w.destroy()
                elif kind == "optdone":
                    if self.page == "dash" and hasattr(self, "opt_out") and self.opt_out.winfo_exists():
                        # summary самодостаточен (содержит все шаги/пропуски): заменяем
                        # живой прогресс целиком, иначе шаги дублируются в логе.
                        self.opt_out.configure(state="normal")
                        self.opt_out.delete("1.0", "end"); self.opt_out.insert("end", a)
                        self.opt_out.see("end"); self.opt_out.configure(state="disabled")
                        for w in self.opt_action.winfo_children(): w.destroy()
                        rev = b or {}
                        if (rev.get("dupes") or rev.get("similar") or rev.get("large")):
                            self._btn(self.opt_action, L("🔍 Открыть инструмент ревью"), BLUE,
                                      lambda: self.nav("tools")).pack(side="left", pady=6)
                elif kind == "tout":
                    if self.page == "tools": self._out(a)
                elif kind == "toutx":
                    # как tout, но результат экспортируемый (большие файлы и т.п.)
                    if self.page == "tools":
                        self._out(a); self._add_export_buttons()
                elif kind == "ctxmenu":
                    if self.page == "tools":
                        self._out(a)
                        # b = [(root, verb, "включён"/"выключен")] — verb-пункты, управляемые
                        for root, verb, status in (b or [])[:20]:
                            if status == "включён":
                                self._btn(self.t_action, L("🚫 {verb}").format(verb=verb), YELLOW,
                                          lambda r=root, v=verb: self._ctxmenu_toggle(r, v, True)).pack(side="left", padx=(0,4), pady=4)
                            else:
                                self._btn(self.t_action, L("✓ {verb}").format(verb=verb), GREEN,
                                          lambda r=root, v=verb: self._ctxmenu_toggle(r, v, False)).pack(side="left", padx=(0,4), pady=4)
                elif kind == "scanout":
                    if self.page == "scan":
                        self._sout(a)
                        if b: self._scan_actions(b)
                elif kind == "dupes":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🗑 Удалить {n} лишних копий").format(n=len(b)), RED,
                                      lambda ex=b: self._trash_dupes(ex)).pack(side="left", pady=4)
                        self._add_export_buttons()
                elif kind == "similar":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🗑 Удалить {n} лишних похожих").format(n=len(b)), RED,
                                      lambda ex=b: self._trash_similar(ex)).pack(side="left", pady=4)
                elif kind == "privacy":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🔒 Очистить следы ({n})").format(n=len(b)), RED,
                                      lambda fs=b: self._privacy_clean(fs)).pack(side="left", pady=4)
                elif kind == "empty":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("📂 Удалить пустые папки ({n})").format(n=len(b)), RED,
                                      lambda ds=b: self._empty_clean(ds)).pack(side="left", pady=4)
                        self._add_export_buttons()
                elif kind == "broken":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🧩 Удалить битые/пустые ({n})").format(n=len(b)), RED,
                                      lambda fs=b: self._broken_clean(fs)).pack(side="left", pady=4)
                        self._add_export_buttons()
                elif kind == "shortcuts":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🔗 Удалить битые ярлыки ({n})").format(n=len(b)), RED,
                                      lambda fs=b: self._shortcuts_clean(fs)).pack(side="left", pady=4)
                elif kind == "bigold":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("📦🕒 Удалить большие старые ({n})").format(n=len(b)), RED,
                                      lambda fs=b: self._bigold_clean(fs)).pack(side="left", pady=4)
                        self._add_export_buttons()
                elif kind == "voltrash":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("♻️ Очистить корзины (НЕОБРАТИМО)"), RED,
                                      lambda ps=b: self._voltrash_empty(ps)).pack(side="left", pady=4)
                        self._add_export_buttons()
                elif kind == "vacuum":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🗜 Сжать базы ({n})").format(n=len(b)), BLUE,
                                      lambda fs=b: self._vacuum_run(fs)).pack(side="left", pady=4)
                elif kind == "vacuumdone":
                    if self.page == "tools":
                        self._out(a)
                        if b:  # b — (done, saved)
                            messagebox.showinfo("KRYLAN", L("Сжато: {n}, сэкономлено {size}.")
                                                .format(n=b[0], size=human(b[1])))
                elif kind == "snapflatpak":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🧹 Очистить неиспользуемое"), RED,
                                      lambda pl=b: self._snapflatpak_clean(pl)).pack(side="left", pady=4)
                elif kind == "shred":
                    if self.page == "tools":
                        self._out(a)
                        if a:  # a — текст отчёта; b — число затёртых файлов
                            messagebox.showinfo("KRYLAN", L("Безвозвратно затёрто: {n} файл(ов).").format(n=b))
                elif kind == "apevent":
                    # события стража: started/stopped/optimizing/optimized — обновляем
                    # страницу автопилота, если она открыта (a=kind стража, b=payload)
                    if self.page == "autopilot":
                        self._ap_refresh()
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
    if "--autopilot" in sys.argv:
        # безоконный фоновый страж (автозапуск при входе в систему)
        run_autopilot_headless()
        sys.exit(0)
    Krylan().mainloop()
