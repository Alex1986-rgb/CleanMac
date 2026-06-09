# 🪽 KRYLAN — SwiftUI каркас (Mac + iPhone)

Кросс-платформенный каркас приложения KRYLAN на SwiftUI.
Создатель: **Кырлан Александр Сергеевич**. Слоган: «Дай устройству крылья».

> Это **стартовый каркас**, а не готовый продукт. iOS не даёт чистить чужие
> данные — мобильная версия про **хранилище, батарею, фото-дубли, контакты**.

## Как открыть и собрать
1. Установи **Xcode** (App Store) — нужен полный Xcode, не Command Line Tools.
2. `File → New → Project… → Multiplatform → App`, имя **KRYLAN**.
3. Удали стандартные `ContentView.swift`/`*App.swift` и **перетащи сюда файлы из `Sources/`**.
4. Выбери таргет (My Mac / iPhone) и запусти ⌘R.

## Что внутри (готово)
- Бренд, палитра, навигация (NavigationSplitView)
- Дашборд с анимированными кольцами (память/диск/батарея)
- `SystemMonitor` — кросс-платформенный сбор метрик (Mach + FileManager + UIDevice)
- Экраны: Хранилище, Батарея, О программе

## Что доработать (см. ../ROADMAP.md, раздел 2)
- iOS: фото-дубликаты (PhotoKit), дубли контактов (Contacts)
- Иконки KRYLAN в Assets.xcassets
- Apple Developer Program → TestFlight/App Store
