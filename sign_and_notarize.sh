#!/bin/bash
# Подпись + нотаризация CleanMac. Запускать ПОСЛЕ ./build_dmg.sh.
# Требуется Apple Developer ID и однажды сохранённый профиль notarytool.
#
# Подготовка (один раз):
#   security find-identity -p codesigning -v        # узнать имя Developer ID Application
#   xcrun notarytool store-credentials CLEANMAC \
#       --apple-id "you@example.com" --team-id "TEAMID" --password "app-spec-password"
#
# Запуск:  ./sign_and_notarize.sh "Developer ID Application: ИМЯ (TEAMID)"
set -e
cd "$(dirname "$0")"
IDENTITY="${1:?Передайте имя подписи: ./sign_and_notarize.sh \"Developer ID Application: ... (TEAMID)\"}"
PROFILE="${2:-CLEANMAC}"
APP="dist/CleanMac.app"
DMG="CleanMac.dmg"
ENTS="$(dirname "$0")/cleanmac.entitlements"

[ -d "$APP" ] || { echo "Нет $APP — сначала ./build_dmg.sh"; exit 1; }
[ -f "$ENTS" ] || { echo "Нет $ENTS (entitlements для Python-бандла)"; exit 1; }

echo "▶ Подписываю .app (hardened runtime + entitlements для Python)…"
# entitlements обязательны: PyInstaller/Python грузит dylib и использует JIT —
# без них нотаризованное приложение падает при запуске. Внутренние бинарники
# подписываем раньше внешнего бандла (Apple не рекомендует --deep для notarize).
find "$APP" -type f \( -name "*.dylib" -o -name "*.so" \) -exec \
    codesign --force --options runtime --timestamp --entitlements "$ENTS" --sign "$IDENTITY" {} + 2>/dev/null || true
codesign --force --options runtime --timestamp --entitlements "$ENTS" --sign "$IDENTITY" "$APP"
codesign --verify --strict --verbose=2 "$APP"

echo "▶ Пересобираю DMG из подписанного .app…"
STAGE="$(mktemp -d)/dmg"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"; ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"; hdiutil create -volname CleanMac -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
codesign --force --timestamp --sign "$IDENTITY" "$DMG"

echo "▶ Нотаризация (ждём вердикт Apple)…"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait

echo "▶ Прикрепляю тикет (staple)…"
xcrun stapler staple "$DMG"
spctl -a -t open --context context:primary-signature -v "$DMG" || true
echo "✅ Готово: подписанный и нотаризованный $DMG"
