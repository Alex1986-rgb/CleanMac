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

[ -d "$APP" ] || { echo "Нет $APP — сначала ./build_dmg.sh"; exit 1; }

echo "▶ Подписываю .app (hardened runtime)…"
codesign --deep --force --options runtime --timestamp --sign "$IDENTITY" "$APP"
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
