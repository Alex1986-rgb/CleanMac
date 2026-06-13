#!/bin/bash
# Управление авто-оптимизатором: ./ctl.sh start|stop|status|log|dashboard
PLIST="$HOME/Library/LaunchAgents/com.macbook.optimizer.plist"
LABEL="com.macbook.optimizer"
DIR="$HOME/mac-optimizer"
UID_=$(id -u)

case "$1" in
  start)
    launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null
    launchctl bootstrap "gui/$UID_" "$PLIST" && echo "✅ Авто-оптимизатор запущен (проверка каждую минуту)"
    ;;
  stop)
    launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null && echo "⏹  Авто-оптимизатор остановлен"
    ;;
  status)
    if launchctl list | grep -q "$LABEL"; then echo "🟢 Работает"; else echo "🔴 Остановлен"; fi
    echo "--- текущие метрики ---"; cat "$DIR/state.json" 2>/dev/null
    ;;
  log)
    tail -20 "$DIR/optimize.log" 2>/dev/null || echo "(лог пуст — пиков не было)";;
  dashboard)
    bash "$DIR/dashboard.sh";;
  test)   # принудительно прогнать оптимизатор сейчас
    bash "$DIR/optimize.sh"; echo "Прогон выполнен. Лог:"; tail -5 "$DIR/optimize.log" 2>/dev/null;;
  *)
    echo "Использование: ctl.sh {start|stop|status|log|dashboard|test}";;
esac
