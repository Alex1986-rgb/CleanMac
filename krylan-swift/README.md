# 🪽 KRYLAN — SwiftUI каркас (Mac + iPhone)

Кросс-платформенный каркас приложения KRYLAN на SwiftUI.
Создатель: **Кырлан Александр Сергеевич**. Слоган: «Дай устройству крылья».

> Это **стартовый каркас**, а не готовый продукт. iOS не даёт чистить чужие
> данные — мобильная версия про **хранилище, батарею, фото-дубли, контакты**.

## Как открыть и собрать
**Быстро (рекомендуется) — XcodeGen генерирует готовый проект:**
```bash
brew install xcodegen
cd krylan-swift
xcodegen generate
open KRYLAN.xcodeproj
```
Выбери таргет **KRYLAN-macOS** или **KRYLAN-iOS** и запусти ⌘R.

**Вручную:** `File → New → Project → Multiplatform → App`, перетащи файлы из `Sources/`.

> Нужен полный **Xcode** (не Command Line Tools). `project.yml` уже содержит
> bundle id, цели macOS/iOS и Info.plist с разрешениями (фото/контакты).

## Экраны (готово)
- **Дашборд** — анимированные кольца память/диск/батарея
- **Хранилище**, **Батарея** — метрики устройства
- **Очистка** — кэш приложения (`CleanupView`)
- **Фото-дубли** (PhotoKit), **Контакты** (Contacts)
- **Советы** — рекомендации по метрикам
- **О программе** — бренд и автор

`SystemMonitor` — кросс-платформенный сбор метрик (Mach + FileManager + UIDevice).

## Тестовый хук
Открыть приложение сразу на нужной вкладке (для скриншотов в симуляторе):
```bash
xcrun simctl launch booted com.krylan.app -KrylanTab photos
# ключи: dashboard · storage · battery · cleanup · photos · contacts · tips · about
```

## Что доработать (см. ../ROADMAP.md, раздел 2)
- Apple Developer Program → TestFlight/App Store
