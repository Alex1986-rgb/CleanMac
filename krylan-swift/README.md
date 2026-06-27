# 🪽 KRYLAN — SwiftUI (iOS + macOS)

**Дай устройству крылья.** Нативное приложение KRYLAN на SwiftUI для iPhone и Mac:
разбор хранилища, батарея, фото-интеллект и контакты. Версия **1.0.0**
(`MARKETING_VERSION`). Создатель: **Кырлан Александр Сергеевич**.

> iOS не даёт чистить чужие данные, поэтому KRYLAN наводит порядок там, где это
> разрешено: **хранилище, фото-медиатека, контакты**. Принцип «только безопасное» —
> приложение работает в песочнице (sandbox) и просит только нужные разрешения.

## Экраны
- **Дашборд** — анимированные кольца память/диск/батарея + глобус, спарклайны.
- **Хранилище** — занятое место с разбором по типам.
- **Батарея** — состояние и метрики питания.
- **Очистка** — кэш приложения с разбивкой и разделом **«Недавно удалённые»**.
- **Разбор (swipe)** — быстрый просмотр и сортировка медиа свайпами.
- **Фото-интеллект** (PhotoKit) — **дубликаты**, **серии** снимков (burst),
  **размытые** (оценка резкости по вариации Лапласиана), **Live Photos**.
- **Скриншоты** — отдельная вкладка для быстрой чистки.
- **Видео** — крупные видеофайлы.
- **Контакты** (Contacts) — дубликаты и неполные контакты.
- **Советы** — рекомендации по метрикам устройства.
- **Виджет** (WidgetKit) — состояние на главном экране.
- **Онбординг** — первый запуск (`@AppStorage "krylan.onboarded"`).
- **О программе** — бренд и автор.

`SystemMonitor` — кросс-платформенный сбор метрик (Mach + FileManager + UIDevice).

## Сборка и запуск
**Быстро (рекомендуется) — XcodeGen генерирует проект из `project.yml`:**
```bash
brew install xcodegen
cd krylan-swift
xcodegen generate
open KRYLAN.xcodeproj
```
Выберите таргет **KRYLAN-macOS** или **KRYLAN-iOS** и запустите ⌘R.

Из командной строки (CI / без Xcode UI):
```bash
xcodegen generate
xcodebuild -project KRYLAN.xcodeproj -scheme KRYLAN-iOS \
  -destination 'platform=iOS Simulator,name=iPhone 15' build
```

> Нужен полный **Xcode** (не Command Line Tools). `project.yml` уже содержит
> bundle id (`com.krylan.app`), цели **macOS 14+ / iOS 17+**, виджет-расширение
> и Info.plist с описаниями разрешений (фото / контакты).
> Перед сборкой на устройство впишите свой **Apple Team ID** в `DEVELOPMENT_TEAM`.

## Разрешения и приватность
- **Песочница** (`com.apple.security.app-sandbox`) — обязательна для App Store;
- доступ к **фотомедиатеке** и **контактам** (поиск дубликатов);
- чтение/запись **выбранных пользователем** файлов (очистка);
- декларация в `PrivacyInfo.xcprivacy`.
Иконки приложения подготовлены для **iOS и macOS** (`Assets.xcassets`).

## Тестовый хук
Открыть приложение сразу на нужной вкладке (для скриншотов в симуляторе):
```bash
xcrun simctl launch booted com.krylan.app -KrylanTab photos
# ключи: dashboard · storage · battery · cleanup · review
#        photos · screenshots · videos · contacts · tips · about
```

## Структура
```
krylan-swift/
├── project.yml                  # XcodeGen: цели macOS/iOS + виджет, разрешения
├── KRYLAN-macOS.entitlements    # sandbox + фото/контакты
└── Sources/
    ├── KRYLANApp.swift          # точка входа
    ├── ContentView.swift        # навигация (enum Tab)
    ├── DashboardView.swift · StorageView.swift · BatteryView.swift
    ├── CleanupView.swift · SwipeReviewView.swift
    ├── PhotoDuplicatesView.swift (дубли/серии/размытые/Live)
    ├── ScreenshotsView.swift · LargeVideosView.swift
    ├── ContactsDuplicatesView.swift · TipsView.swift · OnboardingView.swift
    ├── SystemMonitor.swift      # метрики устройства
    ├── GlobeView · RingGauge · Sparkline · StarfieldView · Theme  (UI/бренд)
    └── Widget/KrylanWidget.swift # виджет (WidgetKit)
```
