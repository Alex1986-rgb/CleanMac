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
# Этот показатель считает сжатое и вытесняемое доступным, поэтому под свопом
# почти не падает и порог «меньше 20%» не достигался.
#
# Абсолютный порог swap срабатывал, но безнадёжно поздно. Файл подкачки растёт
# сам: за одну сессию он поднялся с 2048 до 8192 МБ, и условие «>5000 МБ при
# free<35%» выполнилось только когда swap дошёл до 7959 МБ — 97% от объёма ОЗУ.
# К этому моменту мак уже давно захлёбывался. Поэтому доля swap считается
# ОТ ОБЪЁМА ОЗУ: 25% — это ~2 ГБ на 8-гигабайтной машине, вмешательство
# происходит в разы раньше.
PRESSURE_CRIT=4                   # вердикт macOS: 4 = critical, действуем сразу
PRESSURE_WARN=2                   # 2 = предупреждение; само по себе НЕ повод
SWAP_WARN_PCT=25                  # ...но вместе с четвертью ОЗУ в swap — повод
SWAP_PEAK_PCT=40                  # столько swap — трэшинг независимо от вердикта
FREE_PCT_PEAK=15                  # запасной сигнал, если sysctl недоступен

# Порог простоя для ЗАКРЫТИЯ браузеров. Чистка кэшей идёт всегда, а вот окна
# закрываются, только если человека нет за компьютером. Без этого агент
# захлопывал фоновый браузер прямо посреди работы: он пропускает лишь активное
# окно, поэтому Chrome умирал, пока пользователь печатал в Edge.
IDLE_MIN_CLOSE=900                # 15 минут без клавиатуры и мыши
GRACE_SEC=30                      # столько ждём отмены, прежде чем закрыть

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
# Топ-3 процесса по памяти. Раньше здесь стоял `| sed 's/.*\///g'` в конце
# конвейера: он применялся ко ВСЕЙ собранной строке сразу, а `.*\/` жадный,
# поэтому срезалось всё до последнего слэша в строке — три записи схлопывались
# в одну, да и та показывала хвост пути («Application»), а не имя программы.
# Путь укорачиваем внутри awk, по каждому полю отдельно.
# Имя берём как «всё после первого поля», а не $2: в путях macOS полно пробелов
# («/Applications/Google Chrome.app/…», «…/Application Support/…»), и awk резал
# их по пробелу — в журнале оседало бессмысленное «Application» вместо имени
# программы. Заголовок «RSS COMM» уходит вниз при sort -rn (нечисловое = 0),
# поэтому первая строка — это уже самый жирный процесс.
_top_fmt='{ n = substr($0, index($0, $2)); sub(/.*\//, "", n);
            printf "%s (%.0fМ); ", n, $1/1024 }'
top_mem=$(/bin/ps -axo rss,comm | sort -rn | head -3 | awk "$_top_fmt" 2>/dev/null)
# Главный едок — для уведомления: чистка кэшей освобождает диск, а не ОЗУ,
# поэтому человеку полезнее знать, кого закрыть, чем сколько кэша убрали.
top_one=$(/bin/ps -axo rss,comm | sort -rn | head -1 | awk '
  { n = substr($0, index($0, $2)); sub(/.*\//, "", n);
    printf "%s %.0f МБ", n, $1/1024 }' 2>/dev/null)

# записать состояние для дашборда (простой JSON)
cat > "$STATE" <<EOF
{"ts":"$(date '+%H:%M:%S')","free_pct":$free_pct,"swap_mb":$swap_used,"swap_pct":$swap_pct,"pressure":$pressure,"ram_mb":$ram_mb,"load1":"$load1","ncpu":$ncpu}
EOF

# ---------- детектор пика ----------
# Одного «уровня 2» мало: на 8-гигабайтном маке macOS держит его почти постоянно.
# По журналу за ночь это дало 25 «пиков», в том числе при swap 1469 МБ (18% ОЗУ) —
# никакой это не трэшинг. Требуем либо критический уровень, либо предупреждение
# ВМЕСТЕ с заметным swap, либо просто очень большой swap.
peak=0
reason=""
if [ "$pressure" -ge "$PRESSURE_CRIT" ] 2>/dev/null; then
  peak=1; reason="macOS: критическая нехватка памяти (уровень $pressure), swap ${swap_used}M"
elif [ "$pressure" -ge "$PRESSURE_WARN" ] 2>/dev/null && [ "$swap_pct" -ge "$SWAP_WARN_PCT" ] 2>/dev/null; then
  peak=1; reason="macOS предупреждает (уровень $pressure) и swap ${swap_used}M — ${swap_pct}% ОЗУ"
elif [ "$swap_pct" -ge "$SWAP_PEAK_PCT" ] 2>/dev/null; then
  peak=1; reason="swap ${swap_used}M — ${swap_pct}% от ${ram_mb}M ОЗУ"
elif [ "$free_pct" -lt "$FREE_PCT_PEAK" ] 2>/dev/null; then
  peak=1; reason="свободно всего ${free_pct}% памяти"
fi

# Регулярный снимок вкладок — ДО проверки пика, иначе при отсутствии пика скрипт
# выходит и снимок не делается никогда. Пригодится и тогда, когда браузер закрыл
# не автопилот: пользователь сам или падение. Свежий снимок не переснимается
# (см. TABS_STALE_SEC в tabs.sh), так что цена — один AppleScript раз в 5 минут.
if [ -x "$DIR/tabs.sh" ]; then
  "$DIR/tabs.sh" maybe-save >/dev/null 2>&1 || true
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
# Простой пользователя в секундах (HIDIdleTime отдаётся в наносекундах).
idle=$(ioreg -c IOHIDSystem 2>/dev/null | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
[ -z "$idle" ] && idle=0

if [ -f "$DIR/close_browsers.on" ] && [ "$idle" -lt "$IDLE_MIN_CLOSE" ] 2>/dev/null; then
  log "⏸ Браузеры не трогаю: вы за компьютером (простой ${idle}s < ${IDLE_MIN_CLOSE}s)"
elif [ -f "$DIR/close_browsers.on" ]; then
  frontmost=$(osascript -e 'tell application "System Events" to name of first process whose frontmost is true' 2>/dev/null)
  targets=""
  for app in "Microsoft Edge" "Google Chrome" "Safari" "Yandex"; do
    # не трогаем активное окно, с которым работает пользователь
    if /bin/ps -axo comm | grep -qi "$app" && [ "$app" != "$frontmost" ]; then
      targets="$targets$app;"
    fi
  done
  if [ -n "$targets" ]; then
    # Даём шанс отменить. Раньше браузер просто исчезал: человек возвращался к
    # маку и обнаруживал закрытые окна, не понимая, что произошло. Диалог с
    # таймаутом сам соглашается через GRACE секунд, если никого нет рядом, —
    # то есть в обычном сценарии «отошёл и не вернулся» поведение прежнее.
    ans=$(osascript <<OSA 2>/dev/null
with timeout of $((GRACE_SEC + 15)) seconds
  tell application "System Events"
    activate
    set r to display dialog "Не хватает памяти: $reason.

Закрыть фоновые браузеры? ${targets}
Активное окно не трогаем, вкладки восстановятся при следующем запуске." ¬
      buttons {"Отменить", "Закрыть"} default button "Закрыть" ¬
      with title "🪽 KRYLAN · Автопилот" giving up after $GRACE_SEC
    if gave up of r then return "timeout"
    return button returned of r
  end tell
end timeout
OSA
)
    case "$ans" in
      "Отменить")
        # Отдельный флаг отказа не нужен: swap не изменился, значит на следующем
        # прогоне сработает COOLDOWN_STUCK и диалог не вернётся ещё час.
        log "🚫 Пользователь отменил закрытие браузеров ($targets)"
        ;;
      *)
        [ "$ans" = "timeout" ] && log "⏱ Никто не ответил за ${GRACE_SEC}с — закрываю"
        old_ifs="$IFS"; IFS=';'
        for app in $targets; do
          [ -n "$app" ] || continue
          # Снимок вкладок ДО закрытия. Восстановление сессии в браузере может
          # быть выключено (и правится только в самом браузере, ключ под HMAC),
          # поэтому без снимка закрытие означает потерю работы, а не экономию
          # памяти. Возврат — «↩️ Вернуть вкладки» в CleanMac или
          #   bash ~/mac-optimizer/tabs.sh restore "Microsoft Edge"
          if [ -x "$DIR/tabs.sh" ]; then
            saved=$("$DIR/tabs.sh" save "$app" 2>/dev/null) \
              && log "💾 Запомнил вкладок ($app): $saved"
          fi
          osascript -e "quit app \"$app\"" 2>/dev/null && closed="$closed $app;"
        done
        IFS="$old_ifs"
        [ -n "$closed" ] && log "🔻 Закрыты фоновые браузеры:$closed"
        ;;
    esac
  fi
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
  log "ℹ️ Память не освобождалась: чистка кэшей освобождает диск, а не ОЗУ. Если нужен возврат памяти — включите закрытие фоновых браузеров в «Автопилоте»."
fi
# В уведомлении важнее подсказка, чем отчёт: чистка кэшей освобождает диск, а
# не ОЗУ, и если закрывать браузеры нельзя, вернуть память может только человек.
# Поэтому называем, кто держит больше всех.
hint=""
[ -n "$top_one" ] && hint=" Больше всех держит: $top_one."
notify "$reason" "swap ${swap_used}M → ${swap_after:-?}M${closed:+, закрыты:$closed}.${hint}"
exit 0
