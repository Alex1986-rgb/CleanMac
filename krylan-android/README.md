# 🪽 KRYLAN — Android каркас (Kotlin + Jetpack Compose)

Стартовый каркас Android-версии KRYLAN. Создатель: **Кырлан Александр Сергеевич**.

> Android 11+ закрыл доступ к чужим кэшам, а Google Play банит «бустеры».
> Поэтому версия про **хранилище, память, батарею, крупные файлы и медиа-дубли**
> в доступном пользователю хранилище.

## Как открыть
1. Установи **Android Studio**.
2. `Open` → выбери папку `krylan-android/`.
3. Gradle Sync (Android Studio сам докачает `gradle-wrapper.jar` и SDK),
   выбери эмулятор/устройство, ▶ Run.

> Конфигурация готова: корневой `build.gradle.kts`, `settings.gradle.kts`,
> `app/build.gradle.kts`, `gradle.properties` и `gradle/wrapper/`.

## Что внутри
- `MainActivity.kt` — Compose-дашборд: хранилище, память, батарея
- `ui/Theme.kt` — палитра и бренд KRYLAN
- Манифест, Gradle-файлы

## Что доработать (см. ../ROADMAP.md, раздел 3)
- Крупные файлы через Storage Access Framework
- Медиа-дубликаты (MediaStore + хеш)
- Очистка кэша своего приложения
- Иконки KRYLAN, локализация, Play Console
