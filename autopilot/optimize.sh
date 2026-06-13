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

# --- пороги пика ---
FREE_PCT_PEAK=20                  # свободной памяти меньше 20%
SWAP_PEAK_MB=5000                 # ИЛИ swap больше 5 ГБ при нехватке памяти

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" >> "$LOG"; }
notify() {
  osascript -e "display notification \"$2\" with title \"🧹 Mac Optimizer\" subtitle \"$1\"" 2>/dev/null
}

# ---------- сбор метрик ----------
free_pct=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub(/%/,"",$2); print $2}')
[ -z "$free_pct" ] && free_pct=100
swap_used=$(sysctl -n vm.swapusage 2>/dev/null | awk '{print $6}' | tr -d 'M')
swap_used=${swap_used%.*}; [ -z "$swap_used" ] && swap_used=0
load1=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
ncpu=$(sysctl -n hw.ncpu)

# топ-3 процесса по памяти (для уведомления и дашборда)
top_mem=$(/bin/ps -axo rss,comm | sort -rn | head -3 | awk '{printf "%s (%.0fM); ", $2, $1/1024}' | sed 's/.*\///g' 2>/dev/null)

# записать состояние для дашборда (простой JSON)
cat > "$STATE" <<EOF
{"ts":"$(date '+%H:%M:%S')","free_pct":$free_pct,"swap_mb":$swap_used,"load1":"$load1","ncpu":$ncpu}
EOF

# ---------- детектор пика ----------
peak=0
reason=""
if [ "$free_pct" -lt "$FREE_PCT_PEAK" ] 2>/dev/null; then peak=1; reason="мало памяти (${free_pct}% свободно)"; fi
if [ "$swap_used" -gt "$SWAP_PEAK_MB" ] 2>/dev/null && [ "$free_pct" -lt 35 ] 2>/dev/null; then peak=1; reason="swap ${swap_used}M, память ${free_pct}%"; fi

[ "$peak" -eq 0 ] && exit 0

# ---------- cooldown ----------
now=$(date +%s)
if [ -f "$COOLDOWN_FILE" ]; then
  last=$(cat "$COOLDOWN_FILE" 2>/dev/null); last=${last:-0}
  if [ $((now - last)) -lt "$COOLDOWN" ]; then exit 0; fi
fi
echo "$now" > "$COOLDOWN_FILE"

log "⚠️ ПИК: $reason. Топ: $top_mem"
freed_note=""

# ---------- ДЕЙСТВИЕ 1: безопасные кэши ----------
cleared=0
for sub in "Microsoft Edge" "Google/Chrome" "Yandex" "com.apple.Safari" "Homebrew"; do
  p="$HOME/Library/Caches/$sub"
  if [ -d "$p" ]; then
    sz=$(/usr/bin/du -sm "$p" 2>/dev/null | awk '{print $1}')
    # чистим кэш браузера только если он НЕ запущен
    appname=$(echo "$sub" | sed 's#.*/##')
    if /bin/ps -axo comm | grep -qi "$appname" && [ "$sub" != "Homebrew" ]; then continue; fi
    rm -rf "$p"/* 2>/dev/null && cleared=$((cleared + ${sz:-0}))
  fi
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
sleep 2
free_after=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub(/%/,"",$2); print $2}')
log "✅ После оптимизации: память ${free_after}% свободно"
notify "$reason" "Освобождено: ${freed_note}${closed:+браузеры:$closed} Память: ${free_pct}% → ${free_after}%"
exit 0
