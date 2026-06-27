# 🪽 KRYLAN — Android (Kotlin + Jetpack Compose)

**Дай устройству крылья.** Android-версия KRYLAN: наведение порядка в хранилище
и медиатеке честными средствами платформы. Версия **0.8.0**.
Создатель: **Кырлан Александр Сергеевич**.

> Android 11+ закрыл доступ к чужим кэшам, а Google Play банит «бустеры».
> Поэтому KRYLAN работает в **доступном пользователю хранилище**: крупные файлы,
> медиа-дубли, скриншоты, загрузки, медиа мессенджеров — и **неиспользуемые
> приложения**. Честные формулировки, без booster-обещаний.

## Принцип «только безопасное»
Удаление медиа идёт через системную **корзину MediaStore** (`createTrashRequest`,
Android 11+): файлы не стираются сразу, есть **undo** — восстановление из корзины.
Подтверждение удаления показывает сама система.

## Возможности
- **Дашборд** — хранилище, память, батарея + анимированный глобус, smart-подсказки.
- **Хранилище** — разбор занятого места по типам (`storageBreakdown`).
- **Очистка кэша** — кэш собственного приложения.
- **Медиа-хаб** — вкладки:
  - **Крупные** файлы;
  - **Дубли** (группировка по `duplicateGroups`);
  - **Скриншоты**;
  - **Загрузки**;
  - **Медиа мессенджеров**.
  Удаление выбранного — в корзину, с кнопкой **«Восстановить»** (undo).
- **Приложения** — менеджер установленных приложений и вкладка
  **«Неиспользуемые»** — давно не открывавшиеся, по данным **UsageStatsManager**.
- **Виджет диска** на главный экран (Glance / `glance-appwidget`).
- Периодическая проверка хранилища (`StorageCheckWorker`) + уведомление.

## Сборка / запуск
1. Установите **Android Studio**.
2. `Open` → выберите папку `krylan-android/`.
3. Gradle Sync (Android Studio сам докачает `gradle-wrapper.jar` и SDK),
   выберите эмулятор/устройство, ▶ Run.

Из командной строки:
```bash
cd krylan-android
./gradlew assembleDebug      # сборка APK
./gradlew installDebug       # установка на подключённое устройство
```

**Параметры сборки:** `applicationId = com.krylan.app`,
`compileSdk = 35`, `targetSdk = 35`, `minSdk = 26`,
Compose (BOM 2024.06), Material 3, Glance 1.1. Иконки KRYLAN в комплекте
(`mipmap-*`, адаптивные `mipmap-anydpi-v26`).

## Разрешения
- `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO` — чтение медиатеки;
- `READ_EXTERNAL_STORAGE` — на старых версиях Android;
- `QUERY_ALL_PACKAGES`, `REQUEST_DELETE_PACKAGES` — список и удаление приложений;
- `PACKAGE_USAGE_STATS` — определение неиспользуемых приложений;
- `POST_NOTIFICATIONS` — уведомления проверки хранилища.

## Структура
```
app/src/main/
├── AndroidManifest.xml
├── java/com/krylan/app/
│   ├── MainActivity.kt          # навигация + точка входа
│   ├── SystemInfo.kt            # метрики устройства
│   ├── MediaStoreUtils.kt       # медиа, дубли, корзина (createTrashRequest)
│   ├── StorageCheckWorker.kt    # фоновая проверка хранилища (WorkManager)
│   ├── screens/                 # Dashboard · Storage · Cleanup · Media · Apps · SmartSuggestions
│   ├── ui/                      # Theme · GlobeView · Rings
│   └── widget/DiskWidget.kt     # виджет диска (Glance)
└── res/                         # иконки (mipmap-*), values, xml
```
