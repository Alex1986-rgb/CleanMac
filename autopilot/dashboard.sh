#!/bin/bash
# Живой дашборд мониторинга. Обновляется каждые 2 сек.
DIR="$HOME/mac-optimizer"
LOG="$DIR/optimize.log"
ncpu=$(sysctl -n hw.ncpu)
totalram=$(echo "$(sysctl -n hw.memsize)/1073741824" | bc)

bar() { # bar <percent> <width>
  local p=$1 w=${2:-20} filled
  filled=$(( p * w / 100 ))
  printf "["
  for ((i=0;i<w;i++)); do [ $i -lt $filled ] && printf "█" || printf "·"; done
  printf "] %3d%%" "$p"
}
color() { # color <pct> -> зелёный/жёлтый/красный
  if [ "$1" -ge 70 ]; then printf "\033[31m"; elif [ "$1" -ge 40 ]; then printf "\033[33m"; else printf "\033[32m"; fi
}

trap 'tput cnorm; exit 0' INT TERM
tput civis 2>/dev/null

while true; do
  free_pct=$(memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub(/%/,"",$2); print $2}')
  used_pct=$(( 100 - ${free_pct:-100} ))
  swap_used=$(sysctl -n vm.swapusage 2>/dev/null | awk '{print $6}' | tr -d 'M'); swap_used=${swap_used%.*}
  swap="${swap_used}M исп."
  load1=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
  load_pct=$(echo "$load1 $ncpu" | awk '{p=$1/$2*100; if(p>100)p=100; printf "%d", p}')

  clear
  printf "\033[1m\033[36m  🖥  MAC OPTIMIZER · мониторинг\033[0m   %s\n" "$(date '+%H:%M:%S')"
  printf "  ────────────────────────────────────────────\n"
  printf "  CPU  load %-4s  " "$load1"; color "$load_pct"; bar "$load_pct" 18; printf "\033[0m  (%d ядер)\n" "$ncpu"
  printf "  RAM  занято     "; color "$used_pct"; bar "$used_pct" 18; printf "\033[0m  (всего %sГБ)\n" "$totalram"
  printf "  SWAP %-10s  " "$swap"
  if [ "${swap_used:-0}" -gt 4000 ]; then printf "\033[31m⚠ высокий\033[0m\n"; elif [ "${swap_used:-0}" -gt 1500 ]; then printf "\033[33mумеренный\033[0m\n"; else printf "\033[32mв норме\033[0m\n"; fi
  printf "  ────────────────────────────────────────────\n"
  printf "  \033[1mТоп-5 по памяти:\033[0m\n"
  /bin/ps -axo rss,comm | sort -rn | head -5 | awk '{n=$2; sub(/.*\//,"",n); printf "   %6.0f МБ  %s\n", $1/1024, n}'
  printf "  \033[1mТоп-5 по CPU:\033[0m\n"
  /bin/ps -axo %cpu,comm -r | head -6 | tail -5 | awk '{n=$2; sub(/.*\//,"",n); printf "   %5.1f%%   %s\n", $1, n}'
  printf "  ────────────────────────────────────────────\n"
  printf "  \033[2mПоследнее действие оптимизатора:\033[0m\n"
  if [ -f "$LOG" ]; then tail -1 "$LOG" | awk '{printf "  \033[2m%s\033[0m\n", $0}'; else printf "  \033[2m(пока тихо — пиков не было)\033[0m\n"; fi
  printf "\n  \033[2mCtrl+C — закрыть. Авто-оптимизатор работает в фоне.\033[0m\n"
  sleep 2
done
