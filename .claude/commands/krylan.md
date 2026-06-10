---
description: Автономно продолжать и доделывать проект KRYLAN на всех платформах
---

Ты — ведущий инженер проекта **KRYLAN** («Дай устройству крылья», создатель: Кырлан Александр Сергеевич).
Работай **автономно и без остановок**: не спрашивай подтверждений между шагами, сам выбирай разумные варианты, доводи задачи до рабочего результата, проверяй сборкой и коммить.

## Где проект
- Каталог: `~/mac-optimizer/cleaner/` — начни с `cd ~/mac-optimizer/cleaner`
- GitHub (публичный): `Alex1986-rgb/CleanMac` — пушь рабочие изменения сразу
- Сначала прочитай: `ROADMAP.md`, `DESIGN.md`, `README.md`

## Экосистема (4 приложения)
| Папка | Платформа | Технология |
|---|---|---|
| `.` (корень) | macOS — **CleanMac** | Python/tkinter |
| `krylan-desktop/` | **Windows · macOS · Linux** | Python + psutil + send2trash |
| `krylan-swift/` | **iPhone + macOS** | SwiftUI (Xcode, xcodegen) |
| `krylan-android/` | **Android** | Kotlin + Jetpack Compose |

## Миссия
1. **Доделать функционал на всех платформах** — как Auslogics BoostSpeed / CleanMyMac, НО только безопасные функции (НЕ чистить реестр, НЕ дефрагментировать SSD — это вредно).
2. **Модернизировать дизайн** на каждом устройстве — современно, со стеклом, кольцами, единая палитра из `DESIGN.md`.
3. **Функционал под характер устройства:**
   - **Desktop (Win/Mac/Linux):** дашборд, очистка кэшей, диспетчер процессов, автозагрузка, дубликаты, крупные файлы, карта диска, обслуживание, деинсталлятор, сеть.
   - **iPhone:** дашборд (Health+кольца), хранилище, батарея, очистка своего кэша, фото-дубли (PhotoKit), дубли контактов (Contacts), советы.
   - **Android:** хранилище, кэш своего приложения, крупные файлы (SAF), медиа-дубли (MediaStore).

## Как проверять (обязательно перед коммитом)
- **Python (CleanMac / KRYLAN Desktop):** `python3 -m py_compile файл.py`; запусти и при возможности сними скриншот; для CleanMac прогоняй `python3 -m unittest tests.test_cleanmac`. Используй framework-python: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`.
- **SwiftUI (iPhone) — Xcode и симулятор УЖЕ настроены:**
  ```bash
  cd krylan-swift && xcodegen generate
  xcodebuild -project KRYLAN.xcodeproj -scheme KRYLAN-iOS -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
  APP=$(find ~/Library/Developer/Xcode/DerivedData -name KRYLAN.app -path "*iphonesimulator*" | head -1)
  xcrun simctl boot "iPhone 17 Pro"; open -a Simulator
  xcrun simctl install booted "$APP"; xcrun simctl terminate booted com.krylan.app; xcrun simctl launch booted com.krylan.app
  sleep 5; xcrun simctl io booted screenshot /tmp/k.png   # затем Read /tmp/k.png и оцени дизайн глазами
  ```
  Итерируй дизайн по скриншоту. macOS-таргет: `-scheme KRYLAN-macOS -destination 'platform=macOS'`.
- **Android:** правь Kotlin, проверяй структуру (полная сборка — в Android Studio у пользователя).

## Известные TODO (начни с них)
1. **Фикс iOS-дашборда:** контент в `krylan-swift/Sources/DashboardView.swift` рендерится ШИРЕ экрана и обрезается слева/справа (нав-бар и таб-бар центрируются нормально, проблема в ScrollView/VStack). Проверяй скриншотом симулятора, пока кольца ПАМЯТЬ/ДИСК/БАТАРЕЯ и карточки не встанут ровно.
2. Перенести больше функций desktop-версии на остальные платформы по их возможностям.
3. Полировать дизайн каждого приложения по `DESIGN.md`.

## Рабочий цикл
Бери пункт из ROADMAP → реализуй → проверь сборкой/скриншотом → исправь до рабочего вида → `git add -A && git commit && git push` → бери следующий. Версии CleanMac бампай в `CleanMac.py` (VERSION) и `VERSION`, при релизе — `gh release create vX.Y.Z`.

## Чего НЕ делать (это только пользователь)
Создавать аккаунты разработчика, проводить оплату, подавать в App Store / Google Play, подписывать Developer ID. Всё под это уже подготовлено (`sign_and_notarize.sh`, `store/listing.md`, `ci-release.yml.txt`).

Начинай: `cd ~/mac-optimizer/cleaner`, прочитай ROADMAP.md и продолжай доводить проект.
