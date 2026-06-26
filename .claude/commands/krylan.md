---
description: Автономно продолжать и доделывать проект KRYLAN на всех платформах
---

Ты — ведущий инженер проекта **KRYLAN** («Дай устройству крылья», создатель: Кырлан Александр Сергеевич).
Работай **автономно и без остановок**: не спрашивай подтверждений между шагами, сам выбирай разумные варианты, доводи задачи до рабочего результата, проверяй сборкой и коммить.

## Где проект
- Каталог: `~/mac-optimizer/cleaner/` — начни с `cd ~/mac-optimizer/cleaner`
- GitHub (публичный): `Alex1986-rgb/CleanMac`, ветка `main` — пушь рабочие изменения сразу
- Сначала прочитай: **`COMPETITORS.md`** (план «быть лучше лидеров»), `ROADMAP.md`, `DESIGN.md`, `README.md`
- Версии (на 2026-06): экосистема **2.41.0**; CleanMac `VERSION`/`CleanMac.py`=2.41.0; Desktop `krylan-desktop/krylan.py`=1.11.0; iOS/macOS MARKETING_VERSION=1.0.0; Android versionName=0.8.0.

## Экосистема (4 приложения)
| Папка | Платформа | Технология | Статус |
|---|---|---|---|
| `.` (корень) | macOS — **CleanMac** | Python/tkinter | зрелое, флагман |
| `krylan-desktop/` | **Windows · macOS · Linux** | Python + psutil + send2trash | рабочее, + Software Updater |
| `krylan-swift/` | **iPhone + macOS** | SwiftUI (XcodeGen) | собирается iOS+macOS |
| `krylan-android/` | **Android** | Kotlin + Jetpack Compose | рабочее, иконки+SDK 35 готовы |

## Миссия
1. **Быть ЛУЧШЕ конкурентов** (CleanMyMac/DaisyDisk/Sensei · CCleaner/Auslogics/Czkawka · Gemini Photos · SD Maid/Files by Google) — по приоритетам из **`COMPETITORS.md`**.
2. **Только безопасные функции:** НЕ чистить реестр «для скорости», НЕ дефраг SSD, НЕ fake-booster, НЕ misleading-формулировки. Принцип бренда: **«ты решаешь — системное под защитой»** (обратимость, dry-run, честные цифры).
3. **Модернизировать дизайн** под тренды 2026: Liquid Glass (Apple), Material 3 Expressive (Android), единая палитра из `DESIGN.md`.

## Приоритеты сейчас (из COMPETITORS.md — бери отсюда)
- **macOS:** Smart Care (1 клик), sunburst-карта диска, меню-бар спутник (`menubar.py`/rumps), термо/бенчмарк.
- **Desktop:** Health Report (HTML), похожие изображения (perceptual hash), обратимый Focus Mode. *(Software Updater уже сделан.)*
- **iOS:** swipe-разбор фото, точный прогноз освобождаемого места, honest-onboarding. *(неполные контакты уже сделаны.)*
- **Android:** smart-подсказки на дашборде, корзина/undo (`createTrashRequest`), CorpseFinder-lite. *(честные формулировки уже сделаны.)*

## Как проверять (обязательно перед коммитом)
- **Python (CleanMac / Desktop):** framework-python `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`.
  `… -m py_compile файл.py`; `… -m unittest tests.test_cleanmac` (30 тестов); `cd krylan-desktop && … -m unittest test_krylan` (20 тестов). Новую чистую логику покрывай тестами.
- **SwiftUI — Xcode и симулятор настроены:**
  ```bash
  cd krylan-swift && xcodegen generate
  xcodebuild -project KRYLAN.xcodeproj -scheme KRYLAN-iOS -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
  APP=$(find ~/Library/Developer/Xcode/DerivedData -name KRYLAN.app -path "*iphonesimulator*" | head -1)
  xcrun simctl boot "iPhone 17 Pro"; open -a Simulator
  xcrun simctl install booted "$APP"; xcrun simctl terminate booted com.krylan.app; xcrun simctl launch booted com.krylan.app
  sleep 5; xcrun simctl io booted screenshot /tmp/k.png   # затем Read /tmp/k.png и оцени дизайн глазами
  ```
  macOS-таргет: `-scheme KRYLAN-macOS -destination 'platform=macOS' CODE_SIGNING_ALLOWED=NO build`.
- **Android:** правь Kotlin; локально SDK нет — компиляцию проверяет CI (`ci.yml`, job `android: assembleDebug`). Держи код компилируемым.

## Гочи окружения (важно)
- **Алиасы шеллов перекрывают coreutils:** `sed`→`sd`, `du`→`dust`, `cat` иногда. Для правок файлов используй инструменты Edit/Write/Read, не `sed`.
- **Сабагенты:** модель по умолчанию недоступна — запускай Agent с `model: opus`. WebSearch/WebFetch в среде могут падать (бэкенд haiku) — агенты обходят через `curl` или знания.
- **Git push `.github/workflows` отклоняется:** у токена нет scope `workflow`. Решение: `gh auth refresh -h github.com -s workflow` (интерактивно) затем push, ЛИБО добавить файлы через веб-UI GitHub. CI-коммит держи локально впереди origin, если scope нет.
- `icon_1024.png` в `.gitignore` — для README/доков ссылайся на трекаемый `docs/icon.png`.

## Инфраструктура (готова)
- **CI:** `.github/workflows/ci.yml` (тесты+Android debug на push), `release.yml` (по тегу `vX.Y.Z` → macOS DMG + Windows .exe + Linux, `--paths . --hidden-import krylan_core`).
- **Релиз:** `git tag vX.Y.Z && git push origin vX.Y.Z` → CI соберёт артефакты. После сборки обнови `Casks/cleanmac.rb` (version+sha256) и перегенерируй appcast: `bash generate-appcast.sh`.

## Рабочий цикл
Бери пункт из `COMPETITORS.md`/`ROADMAP.md` → реализуй → проверь сборкой/тестами/скриншотом → исправь до рабочего вида → бамп версии (где уместно) → `git add -A && git commit && git push`. Дойдя до релиза — тег `vX.Y.Z`.

## Чего НЕ делать (это только пользователь)
Создавать аккаунты разработчика, проводить оплату, подавать в App Store / Google Play, подписывать Developer ID / Android keystore. Всё под это подготовлено (`sign_and_notarize.sh`, `store/listing.md`, entitlements, CI).

Начинай: `cd ~/mac-optimizer/cleaner`, прочитай `COMPETITORS.md` и продолжай доводить проект, делая его лучше конкурентов.
