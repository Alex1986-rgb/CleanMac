#!/bin/bash
# Установка автопилота KRYLAN CleanMac.
# Копирует скрипты стража в ~/mac-optimizer и ставит LaunchAgent
# com.macbook.optimizer (прогон раз в минуту, действует только на пике).
# Идемпотентно: можно запускать повторно.
#
#   bash autopilot/install.sh          — установить и запустить
#   bash autopilot/install.sh --no-start — только разложить файлы
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="$HOME/mac-optimizer"
LA="$HOME/Library/LaunchAgents"
LABEL="com.macbook.optimizer"
PLIST="$LA/$LABEL.plist"
UID_=$(id -u)

mkdir -p "$DIR" "$LA"

for f in optimize.sh ctl.sh dashboard.sh; do
  install -m 755 "$SRC/$f" "$DIR/$f"
  echo "  ✓ $DIR/$f"
done

# __HOME__ подставляем реальным путём: launchd не раскрывает ~ и $HOME
sed "s|__HOME__|$HOME|g" "$SRC/$LABEL.plist" > "$PLIST"
echo "  ✓ $PLIST"

if [ "${1:-}" = "--no-start" ]; then
  echo "Файлы разложены. Запуск: bash $DIR/ctl.sh start"
  exit 0
fi

launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID_" "$PLIST"

if launchctl list | grep -q "$LABEL"; then
  echo "✅ Автопилот установлен и запущен (проверка раз в минуту)"
else
  echo "⚠️  Агент не поднялся — проверьте: launchctl print gui/$UID_/$LABEL"
  exit 1
fi
