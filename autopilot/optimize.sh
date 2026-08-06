#!/bin/bash
# mac-optimizer: автономный страж памяти.
# Запускается раз в минуту через LaunchAgent. При "пике" нагрузки
# чистит безопасные кэши и закрывает фоновые браузеры. Логирует всё.
# Ничего из пользовательских файлов не трогает.

DIR="$HOME/mac-optimizer"
LOG="$DIR/optimize.log"
STATE="$DIR/state.json"          # сюда дашборд читает текущие метрики
COOLDOWN_FILE="$DIR/.last_action"
COOLDOWN=300                      # не действовать чаще раза в 5 минут
COOLDOWN_STUCK=3600               # если прошлое вмешательство не помогло — ждать час

# --- пороги пика ---
# Главный сигнал — вердикт самой macOS: kern.memorystatus_vm_pressure_level
# (1 = норма, 2 = предупреждение, 4 = критично). Именно по нему система решает
# сжимать и выгружать страницы.
#
# Почему не «процент свободной памяти», как было раньше. Замер на живом маке
# 8 ГБ: swap занял 4953 МБ (60% от ОЗУ), компрессор держал 3200 МБ, macOS
# рапортовала pressure_level = 2 — а `memory_pressure` показывала 39% свободно.
# Порог «меньше 20%» не срабатывал никогда, потому что этот показатель считает
# сжатое и вытесняемое доступным и под свопом почти не падает. Второй порог был
# ещё хуже: фиксированные 5000 МБ swap на машине, где весь файл подкачки
# начинается с 2048 МБ, — условие, недостижимое в принципе.
#
# Поэтому: доля swap считается ОТ ОБЪЁМА ОЗУ, а не в абсолютных мегабайтах.
PRESSURE_PEAK=2                   # вердикт macOS: 2 = warn, 4 = critical
SWAP_PEAK_PCT=25                  # swap занял четверть ОЗУ — это уже трэшинг
FREE_PCT_PEAK=15                  # запасной сигнал, если sysctl недоступен

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" >> "$LOG"; }
notify() {
  osascript -e "display notification \"$2\" with title \"🧹 Mac Optimizer\" subtitle \"$1\"" 2>/dev/null
}

# ---------- сбор метрик ----------
free_pct=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub(/%/,"",$2); print $2}')
[ -z "$free_pct" ] && free_pct=100
swap_used=$(sysctl -n vm.swapusage 2>/dev/null | awk '{print $6}' | tr -d 'M')
swap_used=${swap_used%.*}; [ -z "$swap_used" ] && swap_used=0
ram_mb=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 8589934592) / 1048576 ))
swap_pct=$(( swap_used * 100 / (ram_mb > 0 ? ram_mb : 8192) ))
pressure=$(sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null); [ -z "$pressure" ] && pressure=1
load1=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
ncpu=$(sysctl -n hw.ncpu)

# топ-3 процесса по памяти (для уведомления и дашборда)
top_mem=$(/bin/ps -axo rss,comm | sort -rn | head -3 | awk '{printf "%s (%.0fM); ", $2, $1/1024}' | sed 's/.*\///g' 2>/dev/null)

# записать состояние для дашборда (простой JSON)
cat > "$STATE" <<EOF
{"ts":"$(date '+%H:%M:%S')","free_pct":$free_pct,"swap_mb":$swap_used,"swap_pct":$swap_pct,"pressure":$pressure,"ram_mb":$ram_mb,"load1":"$load1","ncpu":$ncpu}
EOF

# ---------- детектор пика ----------
peak=0
reason=""
if [ "$pressure" -ge "$PRESSURE_PEAK" ] 2>/dev/null; then
  peak=1; reason="macOS сообщает о нехватке памяти (уровень $pressure), swap ${swap_used}M"
fi
if [ "$swap_pct" -ge "$SWAP_PEAK_PCT" ] 2>/dev/null; then
  peak=1; reason="swap ${swap_used}M — ${swap_pct}% от ${ram_mb}M ОЗУ"
fi
if [ "$free_pct" -lt "$FREE_PCT_PEAK" ] 2>/dev/null; then
  peak=1; reason="свободно всего ${free_pct}% памяти"
fi

[ "$peak" -eq 0 ] && exit 0

# ---------- cooldown с отступлением ----------
# Пик бывает затяжным: swap на 60% от ОЗУ не уходит от того, что мы закрыли один
# браузер. С фиксированным окном в 5 минут агент долбил бы одно и то же действие
# круглые сутки и закрывал пользователю окна каждые пять минут. Поэтому: если
# прошлое вмешательство не сбило swap заметно, следующее откладываем надолго.
now=$(date +%s)
last=0; last_swap=0
if [ -f "$COOLDOWN_FILE" ]; then
  read -r last last_swap < "$COOLDOWN_FILE" 2>/dev/null
  last=${last:-0}; last_swap=${last_swap:-0}
fi
wait_for="$COOLDOWN"
if [ "$last_swap" -gt 0 ] 2>/dev/null; then
  # помогло, если swap упал хотя бы на 10% от прежнего значения
  improved=$(( last_swap - swap_used ))
  if [ "$improved" -lt $(( last_swap / 10 )) ]; then
    wait_for="$COOLDOWN_STUCK"
  fi
fi
if [ $((now - last)) -lt "$wait_for" ]; then exit 0; fi
echo "$now $swap_used" > "$COOLDOWN_FILE"

log "⚠️ ПИК: $reason. Топ: $top_mem"
freed_note=""

# ---------- ДЕЙСТВИЕ 1: безопасные кэши ----------
# Формат записи: "имя процесса-сторожа|путь". Пустой сторож = чистить всегда.
# Имя сторожа задаётся явно: раньше оно выводилось из пути (basename), и для
# "com.apple.Safari" получалось "com.apple.Safari" — такой строки в `ps -axo comm`
# нет никогда (там /Applications/Safari.app/.../Safari), поэтому проверка
# «браузер запущен» для Safari не срабатывала и кэш сносился под работающим Safari.
CACHE_TARGETS=(
  "Microsoft Edge|$HOME/Library/Caches/Microsoft Edge"
  "Microsoft Edge|$HOME/Library/Application Support/Microsoft Edge/Default/Service Worker/CacheStorage"
  "Microsoft Edge|$HOME/Library/Application Support/Microsoft Edge/Default/Code Cache"
  "Google Chrome|$HOME/Library/Caches/Google/Chrome"
  "Google Chrome|$HOME/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage"
  "Google Chrome|$HOME/Library/Application Support/Google/Chrome/Default/Code Cache"
  "Yandex|$HOME/Library/Caches/Yandex"
  "Safari|$HOME/Library/Caches/com.apple.Safari"
  "|$HOME/Library/Caches/Homebrew"
  "|$HOME/Library/Application Support/Google/GoogleUpdater/crx_cache"
)
cleared=0
for entry in "${CACHE_TARGETS[@]}"; do
  guard="${entry%%|*}"; p="${entry#*|}"
  [ -d "$p" ] || continue
  # кэш браузера трогаем только когда он закрыт
  if [ -n "$guard" ] && /bin/ps -axo comm | grep -qF "$guard"; then continue; fi
  sz=$(/usr/bin/du -smP "$p" 2>/dev/null | awk '{print $1}')
  if rm -rf "${p:?}"/* 2>/dev/null; then cleared=$((cleared + ${sz:-0})); fi
done
# старые логи
find "$HOME/Library/Logs" -type f -mtime +14 -delete 2>/dev/null
[ "$cleared" -gt 0 ] && { log "🧹 Очищено кэшей: ~${cleared}M"; freed_note="кэш ~${cleared}M; "; }

# ---------- ДЕЙСТВИЕ 2: закрыть ФОНОВЫЕ браузеры (ОПЦИОНАЛЬНО) ----------
# По умолчанию ВЫКЛЮЧЕНО — автопилот НЕ трогает браузеры.
# Включается только если пользователь создал флаг-файл (через настройку в CleanMac):
#   touch ~/mac-optimizer/close_browsers.on
closed=""
if [ -f "$DIR/close_browsers.on" ]; then
  frontmost=$(osascript -e 'tell application "System Events" to name of first process whose frontmost is true' 2>/dev/null)
  for app in "Microsoft Edge" "Google Chrome" "Safari" "Yandex"; do
    if /bin/ps -axo comm | grep -qi "$app" ; then
      # не трогаем активное окно, с которым работает пользователь
      if [ "$app" != "$frontmost" ]; then
        osascript -e "quit app \"$app\"" 2>/dev/null && closed="$closed $app;"
      fi
    fi
  done
  [ -n "$closed" ] && log "🔻 Закрыты фоновые браузеры:$closed"
else
  log "ℹ️ Закрытие браузеров отключено (нет close_browsers.on) — браузеры не тронуты"
fi

# ---------- итог ----------
# Отчитываемся по swap и вердикту macOS, а не по «проценту свободной памяти»:
# именно этот процент почти не двигается под свопом и создавал ложное
# впечатление, будто всё в порядке.
sleep 3
swap_after=$(sysctl -n vm.swapusage 2>/dev/null | awk '{print $6}' | tr -d 'M'); swap_after=${swap_after%.*}
press_after=$(sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null); [ -z "$press_after" ] && press_after=1
log "✅ Итог: swap ${swap_used}M → ${swap_after:-?}M, давление $pressure → $press_after${closed:+, закрыты:$closed}"
if [ -z "$closed" ] && [ ! -f "$DIR/close_browsers.on" ]; then
  # Честно: чистка кэшей освобождает ДИСК, а не ОЗУ. Без закрытия тяжёлых
  # процессов непривилегированный агент память вернуть не может.
  log "ℹ️ Память не освобождалась: чистка кэшей releases диск, не ОЗУ. Включите закрытие фоновых браузеров в «Автопилоте», если нужен возврат памяти."
fi
notify "$reason" "Кэш: ${freed_note:-—} swap ${swap_used}M → ${swap_after:-?}M${closed:+, закрыты:$closed}"
exit 0
