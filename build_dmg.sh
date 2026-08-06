#!/bin/bash
# Сборка CleanMac.dmg для раздачи.
#  - если установлен PyInstaller → собирает самодостаточный .app (с Python внутри);
#  - иначе пакует существующий ~/Applications/CleanMac.app (нужен framework-python у пользователя).
set -e
cd "$(dirname "$0")"
NAME="CleanMac"
VER="$(cat VERSION 2>/dev/null | tr -d '[:space:]')"; VER="${VER:-0.0.0}"

# Питон ищем, а не прибиваем гвоздями. Раньше путь был жёстко задан как
# /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 — стоило снести
# или обновить Python, и сборка молча уходила в ветку «PyInstaller не найден»
# и падала на копировании несуществующего ~/Applications/CleanMac.app.
find_python() {
  for c in "$PYTHON" \
           /Library/Frameworks/Python.framework/Versions/3.1[3-9]/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
           /opt/homebrew/bin/python3 "$(command -v python3 || true)" /usr/bin/python3; do
    [ -n "$c" ] && [ -x "$c" ] || continue
    "$c" -c "import PyInstaller" 2>/dev/null && { echo "$c"; return 0; }
  done
  for c in "$PYTHON" /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
           /opt/homebrew/bin/python3 "$(command -v python3 || true)" /usr/bin/python3; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return 1; }
  done
  return 1
}
PY="$(find_python)" && HAVE_PI=1 || HAVE_PI=0
echo "▶ Python: ${PY:-не найден}$([ "$HAVE_PI" = 1 ] && echo ' (PyInstaller есть)' || echo ' (PyInstaller НЕТ)')"

STAGE="$(mktemp -d)/dmg"
mkdir -p "$STAGE"

if [ "$HAVE_PI" = 1 ]; then
  echo "▶ Сборка самодостаточного .app через PyInstaller…"
  # psutil исключаем намеренно: его .so одной архитектуры ломает universal2.
  # В CleanMac.py psutil нужен ТОЛЬКО для скорости сети, а там есть резерв
  # через `netstat -ib` — поэтому в бандле сеть работает и без psutil.
  "$PY" -m PyInstaller --windowed --name "$NAME" --icon CleanMac.icns \
        --target-arch universal2 --exclude-module psutil \
        --osx-bundle-identifier com.macbook.cleanmac --noconfirm CleanMac.py

  # PyInstaller не знает про наш VERSION и ставит в Info.plist 0.0.0 —
  # из-за этого в «О программе» и в Finder висела версия 0.0.0.
  PLIST="dist/$NAME.app/Contents/Info.plist"
  plutil -replace CFBundleShortVersionString -string "$VER" "$PLIST"
  plutil -replace CFBundleVersion            -string "$VER" "$PLIST"
  echo "▶ Версия в бандле: $VER"

  # Ad-hoc подпись: без неё ядро может прибить процесс сигналом 9 при запуске.
  # Полноценная подпись Developer ID + нотаризация — в sign_and_notarize.sh.
  codesign --force --sign - --timestamp=none "dist/$NAME.app" 2>/dev/null \
    && echo "▶ Ad-hoc подпись поставлена" \
    || echo "⚠️  Ad-hoc подпись не встала — проверьте вручную"

  cp -R "dist/$NAME.app" "$STAGE/"
else
  SRC=""
  for c in "$HOME/Applications/$NAME.app" "/Applications/$NAME.app" "dist/$NAME.app"; do
    [ -d "$c" ] && { SRC="$c"; break; }
  done
  if [ -z "$SRC" ]; then
    echo "❌ PyInstaller не установлен и готового $NAME.app не найдено."
    echo "   Поставьте сборщик:  ${PY:-python3} -m pip install pyinstaller"
    exit 1
  fi
  echo "▶ PyInstaller не найден — пакую $SRC"
  cp -R "$SRC" "$STAGE/"
fi

ln -s /Applications "$STAGE/Applications"
rm -f "$NAME.dmg"
hdiutil create -volname "$NAME" -srcfolder "$STAGE" -ov -format UDZO "$NAME.dmg" >/dev/null
echo "✅ Готово: $(pwd)/$NAME.dmg"
echo
echo "   Сборка НЕ нотаризована. У того, кто скачает её из интернета, macOS покажет"
echo "   «Apple не удалось подтвердить, что файл не содержит вредоносного ПО» и не даст"
echo "   запустить: файл помечен карантином. Лечится одной командой после установки:"
echo "       xattr -dr com.apple.quarantine /Applications/$NAME.app"
echo "   Чтобы диалога не было вовсе — нужен Apple Developer ID: см. sign_and_notarize.sh"
