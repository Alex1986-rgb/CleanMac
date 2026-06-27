#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRYLAN Desktop — кросс-платформенный оптимизатор: Windows · macOS · Linux.
«Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
Зависимости: psutil, send2trash.  Запуск: python krylan.py
"""
import os, sys, platform, threading, queue, math, hashlib, json
import tkinter as tk
from tkinter import messagebox
import psutil
from send2trash import send2trash

# Общий модуль экосистемы (единый источник истины для human/load_color).
# Рядом лежит вендорная копия (krylan_core.py) — этого достаточно для
# standalone-сборки (PyInstaller подхватит её автоматически). При запуске из
# дерева репозитория предпочитаем корневой оригинал, чтобы логика не расходилась.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import krylan_core

VERSION = "1.12.2"
SYSTEM = platform.system()           # Windows / Darwin / Linux
HOME = os.path.expanduser("~")

# ---------- палитра ----------
BG0, SIDEBAR, GLASS, TRACK, TEXT, MUTED = "#11151d", "#0e1219", "#222b3a", "#333d4e", "#eef2f8", "#8a94a6"
GREEN, BLUE, YELLOW, RED, PURPLE = "#37d39a", "#4b8cf9", "#f6bb45", "#f2685f", "#a78bfa"
CYAN = "#22d3ee"

def _blend(h1, h2, t):
    """Линейная интерполяция двух hex-цветов (#rrggbb) в hex. t∈[0,1]."""
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    a = (int(h1[1:3],16), int(h1[3:5],16), int(h1[5:7],16))
    b = (int(h2[1:3],16), int(h2[3:5],16), int(h2[5:7],16))
    return "#%02x%02x%02x" % tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def load_color(p): return krylan_core.load_color(p, GREEN, YELLOW, RED)

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
                with open(fp, "rb") as fh:
                    h = hashlib.md5(fh.read()).hexdigest()
                bh.setdefault(h, []).append(fp)
            except Exception: pass
        for same in bh.values():
            if len(same) > 1:
                groups.append((s, sorted(same))); extras.extend(sorted(same)[1:])
    groups.sort(reverse=True)
    wasted = sum(s*(len(g)-1) for s, g in groups)
    return groups, extras, wasted

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
FOCUS_BLACKLIST_UNIX = (
    "kernel_task", "launchd", "WindowServer", "loginwindow",
    "systemd", "Finder", "Dock", "python", "Python",
)
FOCUS_BLACKLIST_WINDOWS = (
    "System", "csrss.exe", "wininit.exe", "winlogon.exe",
    "services.exe", "explorer.exe", "python.exe",
)

def focus_blacklist():
    """Чёрный список имён для текущей ОС (нижний регистр для сравнения)."""
    base = FOCUS_BLACKLIST_WINDOWS if SYSTEM == "Windows" else FOCUS_BLACKLIST_UNIX
    return {n.lower() for n in base}

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
                    run(["journalctl", "--vacuum-size=100M"], timeout=120)
                _say(L("📦 Кэш apt и журналы systemd очищены"))
            else:
                skipped.append(L("⏭ Кэш apt/журналы пропущены — нужны права root"))
        # Windows: безопасного userland пакетного кэша нет → молча пропускаем
    except Exception:
        skipped.append(L("⏭ Очистка пакетных кэшей пропущена"))

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
        self.disp = {"cpu":0,"ram":0,"disk":0,"batt":0}
        self.tgt = dict(self.disp)
        self.info = {}
        self.found = {}
        self._paused = set()           # PID приостановленных (Режим фокуса)
        self._build(); self.nav("dash")
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
        for key, base in [("dash","📊  Дашборд"),("scan","🚀  Сканер"),("procs","🧠  Процессы"),("clean","🧽  Очистка"),("tools","🛠  Инструменты"),("about","ℹ️  О программе")]:
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
        {"dash":self.show_dash, "scan":self.show_scan, "procs":self.show_procs, "clean":self.show_clean, "tools":self.show_tools, "about":self.show_about}[key]()

    # ---------- кольца ----------
    def _ring(self, c, cx, cy, r, frac, color, w, val, label):
        c.create_oval(cx-r,cy-r,cx+r,cy+r, outline=TRACK, width=w)
        if frac > 0.01:
            c.create_arc(cx-r,cy-r,cx+r,cy+r, start=90, extent=-frac*359.9, style="arc", outline=color, width=w)
        c.create_text(cx,cy-3, text=val, fill=TEXT, font=("Segoe UI", 18, "bold"))
        c.create_text(cx,cy+r+14, text=label, fill=MUTED, font=("Segoe UI", 10))

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
        tk.Label(hero, text=L("один клик — безопасная очистка по всем параметрам, всё в Корзину"),
                 bg=BG0, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=12)
        # живой прогресс оптимизации (скрыт, пока не нажата кнопка)
        self.opt_action = tk.Frame(self.main, bg=BG0)
        self.opt_out = tk.Text(self.main, bg="#0f1218", fg=TEXT, font=("Consolas", 10), relief="flat",
                               padx=12, pady=8, height=8, state="disabled")
        self.cv = tk.Canvas(self.main, bg=BG0, highlightthickness=0); self.cv.pack(fill="both", expand=True, padx=20, pady=10)

    def _draw_dash(self):
        if not (self.page=="dash" and self.cv.winfo_exists()): return
        c = self.cv; c.delete("all"); W = c.winfo_width() or 640
        rings = [("cpu","CPU",f'{int(self.disp["cpu"])}%'),("ram",L("ОЗУ"),f'{int(self.disp["ram"])}%'),
                 ("disk",L("ДИСК"),f'{int(self.disp["disk"])}%'),("batt",L("БАТАРЕЯ"),
                  (f'{int(self.disp["batt"])}%' if self.info.get("batt") is not None else "—"))]
        gap = W/4
        for i,(k,lbl,val) in enumerate(rings):
            inv = (k == "batt")
            p = self.disp[k]; col = load_color(100-p) if inv else load_color(p)
            self._ring(c, int(gap*i+gap/2), 70, 48, min(1,p/100), col, 12, val, lbl)
        # карточка инфо
        c.create_rectangle(20,150,W-20,282, fill=GLASS, outline=GLASS)
        info = [L("ОС: {os}").format(os=self.info.get('os','—')),
                L("Диск: свободно {free} из {total}").format(free=human(self.info.get('disk_free',0)), total=human(self.info.get('disk_total',0))),
                L("ОЗУ: {total} всего, занято {pct}%").format(total=human(self.info.get('ram_total',0)), pct=int(self.disp['ram'])),
                L("CPU: {cores} ядер").format(cores=self.info.get('cores','?')),
                L("Сеть: ↓ {down}/с   ↑ {up}/с").format(down=human(self.info.get('net_down',0)), up=human(self.info.get('net_up',0)))]
        for i,line in enumerate(info):
            c.create_text(40,173+i*22, anchor="w", fill=TEXT, font=("Segoe UI", 11), text=line)
        # карточка рекомендаций
        adv = disk_advice(self.disp["disk"], self.disp["ram"],
                          self.info.get("batt") if self.info.get("batt") is not None else None)
        ay0 = 296; ah = 20 + len(adv)*22
        c.create_rectangle(20, ay0, W-20, ay0+ah, fill=GLASS, outline=GLASS)
        c.create_text(40, ay0+14, anchor="w", fill=MUTED, font=("Segoe UI", 10, "bold"), text=L("РЕКОМЕНДАЦИИ"))
        for i,(col,text) in enumerate(adv):
            c.create_oval(40, ay0+30+i*22, 50, ay0+40+i*22, fill=col, outline=col)
            c.create_text(60, ay0+35+i*22, anchor="w", fill=TEXT, font=("Segoe UI", 11), text=text)
        # фирменный глобус — герой-элемент по центру под рекомендациями
        gy0 = ay0 + ah + 22
        gr = 64
        gcy = gy0 + gr + 16
        self._globe(c, W//2, gcy, gr, getattr(self, "fr", 0))
        c.create_text(W//2, gcy+gr+22, fill=MUTED, font=("Segoe UI", 9, "bold"),
                      text="KRYLAN · " + L("Дай устройству крылья"))
        c.configure(scrollregion=(0,0,W,gcy+gr+40))

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
        self._btn(bar, L("🚀 Ускорить — очистить и разгрузить"), GREEN, self.run_boost).pack(side="left", padx=(0,8))
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
        """Возобновить все приостановленные процессы. Безопасно вызывать всегда."""
        resumed = 0
        for pid in list(self._paused):
            try:
                psutil.Process(pid).resume()
                resumed += 1
            except psutil.NoSuchProcess:
                pass            # процесс уже исчез — просто убираем из набора
            except psutil.AccessDenied:
                pass            # нет прав — тихо пропускаем
            except Exception:
                pass
            self._paused.discard(pid)
        if not silent:
            if resumed:
                messagebox.showinfo("KRYLAN", L("▶ Возобновлено процессов: {n}.").format(n=resumed))
            else:
                messagebox.showinfo("KRYLAN", L("Приостановленных процессов нет."))
        self._focus_label()

    def _on_close(self):
        # никого не оставляем «замороженным» после выхода
        self._resume_all(silent=True)
        self.destroy()

    def _kill_proc(self, pid, name):
        if not messagebox.askyesno("KRYLAN", L("Завершить процесс «{name}» (PID {pid})?").format(name=name, pid=pid)): return
        try:
            psutil.Process(pid).terminate()
            self._paused.discard(pid)
        except Exception as e:
            messagebox.showerror("KRYLAN", L("Не удалось завершить: {e}").format(e=e))
        self._procs_refresh()

    # ---------- инструменты (в духе BoostSpeed) ----------
    def show_tools(self):
        tk.Label(self.main, text=L("Инструменты"), bg=BG0, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(18,8))
        bar = tk.Frame(self.main, bg=BG0); bar.pack(fill="x", padx=22)
        for lbl, cmd in [("⚙️ Автозагрузка", self.t_startup), ("👯 Дубликаты", self.t_dupes), ("🖼 Похожие фото", self.t_similar), ("📦 Крупные файлы", self.t_large),
                         ("🗺 Карта диска", self.t_diskmap), ("🧳 Деинсталлятор", self.t_uninstall),
                         ("📂 Пустые папки", self.t_empty), ("🧩 Битые файлы", self.t_broken),
                         ("📈 Что выросло", self.t_growth),
                         ("🔒 Приватность", self.t_privacy), ("🧩 Расширения браузеров", self.t_extensions), ("🩺 Диск", self.t_smart),
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

    def t_startup(self):
        self._out(L("⚙️ Сканирую автозагрузку…")); threading.Thread(target=self._startup_w, daemon=True).start()

    def _startup_w(self):
        lines = [L("⚙️  Автозагрузка") + "\n\n"]
        if SYSTEM == "Windows":
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                try:
                    i = 0
                    while True:
                        try:
                            n, v, _ = winreg.EnumValue(k, i); lines.append(f"  • {n}\n      {v}\n"); i += 1
                        except OSError: break
                finally:
                    winreg.CloseKey(k)
            except Exception as e:
                lines.append("  " + L("ошибка чтения реестра: {e}").format(e=e) + "\n")
            lines.append("\n" + L("Отключить: Диспетчер задач → вкладка «Автозагрузка».") + "\n")
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
        self.q.put(("tout", t or L("  ничего\n"), None))

    def t_dupes(self):
        self._out(L("👯 Ищу дубликаты…")); threading.Thread(target=self._dupes_w, daemon=True).start()

    def _dupes_w(self):
        groups, extras, wasted = find_duplicates()
        t = L("👯  Дубликаты: групп {n}, освободить ~{size}").format(n=len(groups), size=human(wasted)) + "\n\n"
        for s, same in groups[:20]:
            t += f"  {human(s)} ×{len(same)}:\n" + "".join(f"      {p.replace(HOME,'~')}\n" for p in same) + "\n"
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
        self.q.put(("broken", "".join(lines), files))

    def _broken_clean(self, files):
        if not files or not messagebox.askyesno("KRYLAN", L("Переместить {n} битых/пустых файлов в Корзину?").format(n=len(files))): return
        ok = 0
        for p in files:
            if safe_trash(p): ok += 1
        messagebox.showinfo("KRYLAN", L("В Корзину: {n} файлов.").format(n=ok)); self.t_broken()

    def t_smart(self):
        self._out(L("🩺 Читаю состояние диска…"))
        threading.Thread(target=lambda: self.q.put(("tout", disk_health_report(), None)), daemon=True).start()

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
                    self.tgt.update({"cpu":a["cpu"],"ram":a["ram"],"disk":a["disk"],"batt":a["batt"] or 0})
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
                elif kind == "broken":
                    if self.page == "tools":
                        self._out(a)
                        if b:
                            self._btn(self.t_action, L("🧩 Удалить битые/пустые ({n})").format(n=len(b)), RED,
                                      lambda fs=b: self._broken_clean(fs)).pack(side="left", pady=4)
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
