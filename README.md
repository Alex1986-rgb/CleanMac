<div align="center">

<img src="docs/icon.png" width="128" alt="KRYLAN CleanMac"/>

# 🪽 KRYLAN · CleanMac

### «Дай устройству крылья»

**Красивый оптимизатор со «стеклянным» интерфейсом.**
Дашборд с диаграммами, автопилот, безопасная очистка — мощнее CCleaner, бесплатно и с открытым кодом.

**Экосистема KRYLAN:** macOS · **Windows · Linux** (доступно) · iPhone · Android (в разработке).
**Создатель:** Кырлан Александр Сергеевич.

![version](https://img.shields.io/badge/version-2.41.0-37d39a)
![platform](https://img.shields.io/badge/macOS-11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-purple)

</div>

---

## Возможности

### 📊 Дашборд (реальное время, анимация)
- Кольца **Health / CPU / ОЗУ / SWAP / Диск**
- Пончик **состава памяти** (активная/связанная/сжатая/неактивная/свободная)
- Пончик **диска** (занято/свободно)
- График **нагрузки CPU и ОЗУ** за минуту
- Виджет **батареи**: заряд, время, циклы, ёмкость, состояние
- Живой список **процессов** с барами CPU и расходом ОЗУ

### 🚀 Автопилот
Фоновый страж следит за памятью и при пике сам чистит кэши и закрывает
фоновые браузеры. Управление из приложения: вкл/выкл, журнал, ручной запуск.

### 🧽 Очистка
Категории кэшей и логов → **Анализ** (объём) → **Очистить** (в Корзину, обратимо).
Кэш браузера чистится только когда он закрыт.

### 🛠 Инструменты
Менеджер автозагрузки · крупные файлы (>100 МБ) · поиск дубликатов (size+MD5) ·
закрытие фоновых браузеров · очистка Корзины.

---

## Структура проекта (экосистема KRYLAN)
| Папка | Что это | README |
|---|---|---|
| `.` (корень) | **CleanMac** — оптимизатор macOS (Python/tkinter) | этот файл |
| `menubar.py` | мини-монитор в строке меню (rumps) | — |
| `krylan-desktop/` | **Windows · macOS · Linux** (Python/psutil) | [README](krylan-desktop/README.md) |
| `krylan-swift/` | каркас **iOS + macOS** (SwiftUI) | [README](krylan-swift/README.md) |
| `krylan-android/` | каркас **Android** (Kotlin + Compose) | [README](krylan-android/README.md) |
| `tests/` | юнит-тесты | [README](tests/README.md) |
| `design/` | дизайн-токены для Figma | [DESIGN.md](DESIGN.md) |
| `docs/` | лендинг (GitHub Pages) + промо + appcast | — |

Документы: [ROADMAP](ROADMAP.md) · [DISTRIBUTION](DISTRIBUTION.md) · [PRIVACY](PRIVACY.md) · [TERMS](TERMS.md)

## Установка

**Homebrew** (после публичного релиза):
```bash
brew install --cask Alex1986-rgb/tap/cleanmac
```

**Готовый `.dmg`** — на странице [Releases](https://github.com/Alex1986-rgb/CleanMac/releases).
Перетащите CleanMac в «Программы». Первый запуск: ПКМ → «Открыть» (приложение
распространяется вне App Store, как все чистильщики).

> Сборка **universal2** (Intel + Apple Silicon) — работает на всех маках с macOS 11+.

**Из исходников:**
```bash
git clone https://github.com/Alex1986-rgb/CleanMac.git
cd CleanMac
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 CleanMac.py
```
> Нужен python.org Python 3.12 (с tkinter). Внешних зависимостей у приложения нет;
> Pillow требуется только для пересборки иконки (`make_icon.py`).

---

## Сборка

```bash
./make_icon.py        # пересобрать иконку (нужен Pillow)
./build_dmg.sh        # собрать CleanMac.dmg из .app
```

---

## Почему не в App Store?

Системные чистильщики **не проходят** в Mac App Store: песочница MAS запрещает
доступ к кэшам других приложений, `pmset`/`system_profiler` и завершение чужих
процессов. Поэтому CleanMac, как CCleaner и CleanMyMac, распространяется
**нотаризованным .dmg** напрямую.

---

## Безопасность

- Любое удаление = перемещение в **Корзину** (можно вернуть).
- Кэш браузера не трогается, пока браузер запущен.
- Никаких сетевых отправок данных; единственный сетевой запрос — проверка
  версии на GitHub.

## Дорожная карта (экосистема KRYLAN)
- ✅ **macOS** — CleanMac (это приложение), universal Intel + Apple Silicon
- 🔜 **iPhone** — KRYLAN для iOS (в рамках ограничений: фото-дубли, контакты, хранилище)
- 🔜 **Android** — KRYLAN для Android (кэши приложений, крупные файлы)

> Мобильные версии — отдельные приложения с функциями, допустимыми политиками App Store / Google Play.

## Лицензия
[MIT](LICENSE) © 2026 **Кырлан Александр Сергеевич**
