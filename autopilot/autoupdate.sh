#!/bin/bash
# KRYLAN авто-обновление: подтягивает свежий код из GitHub.
# Приложение CleanMac.app — тонкий лаунчер, запускающий исходник,
# поэтому git pull = мгновенное обновление без пересборки.
# Запускается launchd-агентом com.krylan.autoupdate (см. рядом .plist).

REPO="$HOME/mac-optimizer/cleaner"
LOG="$REPO/autopilot/autoupdate.log"

cd "$REPO" 2>/dev/null || exit 0

before=$(git rev-parse --short HEAD 2>/dev/null)
# --autostash: не упасть, если есть локальные правки; --ff-only: только безопасное продвижение
git pull --ff-only --autostash >>"$LOG" 2>&1
after=$(git rev-parse --short HEAD 2>/dev/null)

ts=$(date '+%Y-%m-%d %H:%M:%S')
if [ "$before" != "$after" ]; then
  ver=$(cat VERSION 2>/dev/null)
  echo "$ts  обновлено: $before → $after (v$ver)" >>"$LOG"
  osascript -e "display notification \"Обновлено до v$ver. Перезапустите CleanMac.\" with title \"🪽 KRYLAN\" subtitle \"Авто-обновление\"" 2>/dev/null
else
  echo "$ts  актуально ($after)" >>"$LOG"
fi
exit 0
