#!/bin/bash
# Сборка CleanMac.dmg для раздачи.
#  - если установлен PyInstaller → собирает самодостаточный .app (с Python внутри);
#  - иначе пакует существующий ~/Applications/CleanMac.app (нужен framework-python у пользователя).
set -e
cd "$(dirname "$0")"
PY="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
NAME="CleanMac"
STAGE="$(mktemp -d)/dmg"
mkdir -p "$STAGE"

if "$PY" -c "import PyInstaller" 2>/dev/null; then
  echo "▶ Сборка самодостаточного .app через PyInstaller…"
  # psutil исключаем намеренно: его .so одной архитектуры ломает universal2.
  # В CleanMac.py psutil нужен ТОЛЬКО для скорости сети, а там есть резерв
  # через `netstat -ib` — поэтому в бандле сеть работает и без psutil.
  "$PY" -m PyInstaller --windowed --name "$NAME" --icon CleanMac.icns \
        --target-arch universal2 --exclude-module psutil \
        --osx-bundle-identifier com.macbook.cleanmac --noconfirm CleanMac.py
  cp -R "dist/$NAME.app" "$STAGE/"
else
  echo "▶ PyInstaller не найден — пакую ~/Applications/$NAME.app"
  echo "  (для самодостаточной сборки: $PY -m pip install pyinstaller)"
  cp -R "$HOME/Applications/$NAME.app" "$STAGE/"
fi

ln -s /Applications "$STAGE/Applications"
rm -f "$NAME.dmg"
hdiutil create -volname "$NAME" -srcfolder "$STAGE" -ov -format UDZO "$NAME.dmg" >/dev/null
echo "✅ Готово: $(pwd)/$NAME.dmg"
echo "   Подпись/нотаризация требуют Apple Developer ID (codesign + notarytool)."
