# Дистрибуция CleanMac

Полный путь от исходников до подписанного `.dmg` и автообновлений.

## 1. Сборка

```bash
./make_icon.py        # пересобрать иконку (нужен Pillow)
./build_dmg.sh        # собрать CleanMac.dmg (PyInstaller → самодостаточный .app)
```
Результат: `dist/CleanMac.app` (с Python внутри) и `CleanMac.dmg`.

## 2. Подпись (нужен Apple Developer ID — $99/год)

После регистрации в Apple Developer и установки сертификата
**«Developer ID Application»** в Связку ключей:

```bash
# посмотреть доступные подписи
security find-identity -p codesigning -v

# подписать .app (hardened runtime обязателен для нотаризации)
codesign --deep --force --options runtime --timestamp \
  --sign "Developer ID Application: ИМЯ (TEAMID)" \
  dist/CleanMac.app

codesign --verify --strict --verbose=2 dist/CleanMac.app
```

## 3. Нотаризация Apple

```bash
# один раз сохранить креды (app-specific password из appleid.apple.com)
xcrun notarytool store-credentials CLEANMAC \
  --apple-id "you@example.com" --team-id "TEAMID" --password "xxxx-xxxx-xxxx-xxxx"

# пересобрать DMG из ПОДПИСАННОГО .app, затем:
xcrun notarytool submit CleanMac.dmg --keychain-profile CLEANMAC --wait
xcrun stapler staple CleanMac.dmg          # «пришить» тикет
spctl -a -t open --context context:primary-signature -v CleanMac.dmg   # проверка
```
После этого Gatekeeper открывает приложение без предупреждений.

## 4. Релиз на GitHub

```bash
# обновить версию в двух местах: VERSION и CleanMac.py (VERSION = "x.y.z")
echo "2.1.0" > VERSION
git commit -am "release 2.1.0" && git push
gh release create v2.1.0 CleanMac.dmg --title "CleanMac 2.1.0" --notes "Что нового…"
```

## 5. Автообновление

Приложение проверяет `https://raw.githubusercontent.com/Alex1986-rgb/CleanMac/main/VERSION`.

- **Публичный репо** — работает сразу.
- **Приватный репо** — raw-файл требует токен. Варианты:
  1. Сделать репозиторий публичным (`gh repo edit --visibility public`).
  2. **Appcast** (рекомендуется при закрытом коде): отдельный *публичный* Gist
     только с номером версии и ссылкой на DMG — исходники остаются приватными.
     Затем поменять URL в `_check_update()`.
  3. Встроить read-only токен (не рекомендуется — утечёт в бинарнике).

## Заметки
- Без подписи DMG тоже работает: первый запуск через ПКМ → «Открыть».
- Для CI можно автоматизировать шаги 2–4 в GitHub Actions (macOS-раннер).
