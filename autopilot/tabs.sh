#!/bin/bash
# Сохранение и возврат открытых вкладок браузера.
#
# Зачем. Автопилот освобождает память единственным доступным непривилегированному
# агенту способом — закрывает фоновые браузеры. Если у браузера не включено
# восстановление сессии, человек возвращается к маку и обнаруживает пустое окно:
# для него это не «освободилась память», а «пропала работа». Настройка
# восстановления живёт под HMAC-подписью и правится только в самом браузере,
# то есть агент на неё повлиять не может. Зато может сохранить список вкладок
# сам — и вернуть по первому требованию.
#
#   tabs.sh save "Microsoft Edge"    — запомнить открытые вкладки
#   tabs.sh restore "Microsoft Edge" — открыть их заново
#   tabs.sh list                     — что сохранено и когда
#   tabs.sh count "Microsoft Edge"   — сколько вкладок в снимке
#
# Снимки: ~/mac-optimizer/tabs/<браузер>.txt — по одному URL на строку,
# первая строка «# <дата> <время>». Формат нарочно простой: его должен уметь
# прочитать и человек, и приложение, и следующий скрипт.
set -uo pipefail

DIR="${MAC_OPT_DIR:-$HOME/mac-optimizer}"
TABS_DIR="$DIR/tabs"

snapshot_path() { echo "$TABS_DIR/$(echo "$1" | tr ' /' '__').txt"; }

save_tabs() {
  local app="$1"
  # pgrep, а НЕ `ps | grep -q`: с `set -o pipefail` такой конвейер всегда
  # «падает». grep -q закрывает канал на первом же совпадении, ps получает
  # SIGPIPE и возвращает ненулевой код — pipefail считает упавшим весь
  # конвейер. Проверка «браузер запущен» из-за этого давала ложное «нет»
  # при 24 живых процессах Edge, и снимок не делался никогда.
  #
  # Самого себя pgrep здесь не найдёт, хотя имя браузера и лежит в argv
  # скрипта: macOS-pgrep по умолчанию исключает свой процесс и всех предков
  # (`man pgrep`, ключ -a включает их обратно). На Linux это была бы ловушка.
  pgrep -f "$app" >/dev/null 2>&1 || return 1          # не запущен — нечего снимать
  # Диалект один и тот же для Edge/Chrome/Safari: windows -> tabs -> URL.
  # Проверено на живых Edge и Safari.
  #
  # `if ... is running` внутри — страховка от автозапуска: `tell application`
  # по правилам Apple events САМ поднимает приложение, если оно закрыто.
  # Оптимизатор, открывающий браузер, которого пользователь закрыл, —
  # худшее, что он может сделать.
  local urls
  urls=$(osascript -e "if application \"$app\" is running then
    tell application \"$app\"
      set out to \"\"
      repeat with w in windows
        repeat with t in tabs of w
          set u to URL of t
          if u is not missing value then set out to out & u & linefeed
        end repeat
      end repeat
      return out
    end tell
  end if" 2>/dev/null)
  # Пустой снимок не пишем: он бы затёр предыдущий полезный.
  # Фильтр `^[a-z]+://` сам отсекает about:blank (в нём нет //), так что
  # отдельный `grep -v '^about:'` был мёртвым кодом — убран.
  urls=$(printf '%s\n' "$urls" | grep -E '^[a-z]+://' || true)
  [ -z "$urls" ] && return 1
  mkdir -p "$TABS_DIR"
  {
    echo "# $(date '+%Y-%m-%d %H:%M:%S')"
    printf '%s\n' "$urls"
  } > "$(snapshot_path "$app")"
  printf '%s\n' "$urls" | wc -l | tr -d ' '
}

restore_tabs() {
  local app="$1" f n=0
  f=$(snapshot_path "$app")
  [ -f "$f" ] || { echo "снимок не найден: $f" >&2; return 1; }
  # open -a с пачкой URL: браузер сам разложит их по вкладкам одного окна.
  local urls=()
  while IFS= read -r u; do
    # Файл могли править руками: снимаем BOM и хвостовой \r. Без этого BOM
    # превращал строку-заголовок в «URL», а open спотыкался на ней и ронял
    # весь возврат — при задавленном stderr это выглядело как «не сработало».
    u=${u#$'\xEF\xBB\xBF'}
    u=${u%$'\r'}
    case "$u" in ''|'#'*) continue;; esac
    urls+=("$u"); n=$((n+1))
  done < "$f"
  [ "$n" -eq 0 ] && { echo "снимок пуст" >&2; return 1; }
  # Один битый URL не должен отменять остальные: open вернёт ненулевой код,
  # но вкладки, которые открылись, уже открыты — сообщаем и не считаем сбоем.
  if ! open -a "$app" "${urls[@]}" 2>/dev/null; then
    echo "часть URL не открылась" >&2
  fi
  echo "$n"
}

# Снимок «по необходимости»: только если прошлый устарел. Нужен для регулярных
# снимков в фоне — снимок пригодится и когда браузер закрыл не автопилот, а сам
# пользователь или падение. Без проверки свежести агент дёргал бы AppleScript
# у каждого браузера каждую минуту без всякой пользы.
STALE_SEC="${TABS_STALE_SEC:-300}"

maybe_save() {
  local app="$1" f
  f=$(snapshot_path "$app")
  if [ -f "$f" ]; then
    local age=$(( $(date +%s) - $(stat -f %m "$f" 2>/dev/null || echo 0) ))
    [ "$age" -lt "$STALE_SEC" ] && return 2      # свежий — ничего не делаем
  fi
  save_tabs "$app"
}

case "${1:-}" in
  save)    save_tabs "${2:?нужно имя браузера}";;
  maybe-save)
    # Без аргумента — по всем известным браузерам. Выходим нулём всегда: это
    # фоновая операция «сделай, если надо», и незапущенный браузер — норма,
    # а не ошибка. Иначе вызывающий скрипт получал ложный сигнал о сбое.
    if [ -n "${2:-}" ]; then maybe_save "$2" || true
    else
      for a in "Microsoft Edge" "Google Chrome" "Safari" "Yandex"; do
        n=$(maybe_save "$a") && [ -n "$n" ] && echo "$a: $n"
      done
    fi
    exit 0
    ;;
  restore) restore_tabs "${2:?нужно имя браузера}";;
  count)
    # grep -c печатает «0» и при этом выходит с кодом 1, поэтому наивное
    # `grep -c … || echo 0` выдавало «0» дважды. Считаем через переменную.
    f=$(snapshot_path "${2:?нужно имя браузера}")
    if [ -f "$f" ]; then n=$(grep -cE '^[a-z]+://' "$f" || true); echo "${n:-0}"
    else echo 0; fi
    ;;
  list)
    [ -d "$TABS_DIR" ] || { echo "снимков нет"; exit 0; }
    for f in "$TABS_DIR"/*.txt; do
      [ -f "$f" ] || continue
      name=$(basename "$f" .txt | tr '_' ' ')
      printf '%-18s %s вкладок, снято %s\n' "$name" \
        "$(grep -cE '^[a-z]+://' "$f")" "$(head -1 "$f" | sed 's/^# //')"
    done
    ;;
  *) echo "Использование: tabs.sh {save|restore|count|list} [браузер]"; exit 2;;
esac
