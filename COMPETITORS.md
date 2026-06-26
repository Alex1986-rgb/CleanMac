# 🪽 KRYLAN — конкурентный анализ и план «быть лучше»

Цель — сделать KRYLAN сильнее лидеров на каждой платформе, **только безопасными методами**
(без чистки реестра «для скорости», без дефрага SSD, без fake-booster, без обмана в формулировках).
Сложность помечена: `easy / medium / hard`. Сделанное отмечается `[x]`.

> Анализ от 2026-06. macOS-раздел — с живыми источниками вендоров; мобильные/desktop —
> по знаниям рынка и официальной документации (Apple sandbox, Google Play policy, Material 3).

---

## macOS — CleanMac

**Лидеры:** CleanMyMac (MacPaw), DaisyDisk, Sensei (Cindori), MacKeeper, Parallels Toolbox, OnyX, AppCleaner.

**Их killer-фичи:** Smart Care (всё одним проходом), sunburst-карта диска (DaisyDisk),
термо/железо-монитор + бенчмарк диска (Sensei), меню-бар присутствие, мессенджинг доверия
«системное под защитой».

**Что добавить, чтобы быть лучше:**
- [x] **Smart Care — один клик** — уже есть как «Ускорить» (`_boost_worker`: кэши+логи → Корзина, снимки APFS, кэш Quick Look, разгрузка памяти). Осталось: превью «что будет сделано» + добавить в проход проверку апдейтов/приватность. `easy`
- [ ] **Sunburst-карта диска** с drill-down (превратить текущую карту в интерактивное кольцо). `medium`
- [ ] **«Scan as admin»** — показ скрытого системного места (реальные десятки ГБ). `medium`
- [ ] **Меню-бар спутник** (`menubar.py`/rumps): живые CPU/RAM/SWAP/температура + кнопка Smart Care. `medium`
- [ ] **Термо-дашборд + бенчмарк диска** (powermetrics/SMC, read/write тест). `easy→medium`
- [ ] **Лёгкий adware-скан** по известным путям LaunchAgents (не полноценный AV). `medium`
- [ ] **SmartDelete** — фоновый перехват удаления приложения → добить «хвосты». `medium`
- [ ] Чистка локальных дублей облака (iCloud/Dropbox). `medium`

**Дизайн 2026:** Liquid Glass (Tahoe), bento-grid карточек, one-hero-action, живые кольца/гейджи.

---

## Desktop — KRYLAN Desktop (Windows · macOS · Linux)

**Лидеры:** CCleaner, Auslogics BoostSpeed, Wise Care 365, Glary Utilities, IObit ASC;
Linux — BleachBit, Stacer, Czkawka.

**Что добавить, чтобы быть лучше:**
- [x] **Software Updater** через нативные менеджеры (`brew outdated` / `winget upgrade` / `apt list --upgradable`) — killer-фича рынка №1, read-only, без bundleware. `medium` ✅ v1.11
- [ ] **Health Report** — итог одним экраном после сканирования + экспорт HTML/PDF. `easy`
- [ ] **Похожие изображения** (perceptual hash, не только MD5). `medium`
- [ ] **Битые/нулевые файлы, broken symlinks**. `easy→medium`
- [ ] **Обратимый «Focus Mode»** — пауза фоновых процессов с авто-восстановлением (безопаснее kill). `medium`
- [ ] **Менеджер расширений браузеров** + улучшенная приватность по профилям. `medium`
- [ ] **Реестр Windows — только бэкап/снапшот веток** перед изменениями (НЕ «чистка»). `medium`
- [ ] **Защита от over-cleaning**: whitelist рискованных кэшей + dry-run превью. `easy`

**Anti-фичи (НЕ делаем — это вред):** registry-clean «для скорости», дефраг SSD, отключение системных служб.
Это наше УТП против агрессивных конкурентов.

**Дизайн:** единые токены через `ttk`/`sv-ttk`/`ttkbootstrap`, анимированные кольца, sidebar,
крупный «Health Score».

---

## iOS — KRYLAN (iPhone/iPad)

**Реальность sandbox:** только свой кэш + фото/видео (PhotoKit) + контакты + storage-цифры.
Чужие кэши/«system junk»/«RAM boost» — НЕЛЬЗЯ (и за это режут в ревью).

**Лидеры:** Gemini Photos (MacPaw), Smart Cleaner, Cleanup (свайп), Boost Cleaner, Cleaner Kit.
Все берут **качеством разбора фото** (similar, не только exact) + скоростью (свайп/batch).

**Что добавить, чтобы быть лучше:**
- [x] Похожие/серии/размытые фото (Vision) — уже есть в Фото-интеллекте.
- [x] **Неполные контакты** (без имени/без номера) + дубли по имени. ✅ v1.0
- [ ] **Swipe-разбор фото** («one-by-one», undo, счётчик «освобождено N МБ»). `medium`
- [ ] **Точный прогноз освобождаемого места** до системного диалога удаления. `easy`
- [ ] **Honest-onboarding** (реальный скан → мягкий paywall после первой пользы). `medium`
- [ ] **Smart-категории медиа** (GIF/мемы, Live Photos, «давно не открывал»). `easy→medium`
- [ ] **Старые события календаря** (EventKit). `easy`
- [ ] **Виджеты + честные локальные уведомления** (без «storage full» страшилок). `medium`

**Дизайн 2026:** Liquid Glass-слой, «жидкая» анимация освобождения места, parallax звёздного неба,
result-экран «До/После» как трофей (share-asset).

---

## Android — KRYLAN

**Реальность scoped storage (11+):** только свой кэш + медиа через MediaStore (удаление = системный диалог).
Google Play **банит fake-booster** и misleading-формулировки.

**Лидеры:** SD Maid 2/SE (CorpseFinder), Files by Google (smart suggestions + корзина),
CCleaner, AVG Cleaner (similar/blurry), 1Tap Cleaner.

**Что добавить, чтобы быть лучше:**
- [x] **Честные формулировки** — «Освободить кэш» вместо «Ускорить — как новый», trust-note. ✅ v0.8
- [ ] **Smart-подсказки на дашборде** (Files-style карточки: кэш, похожие фото, осиротевшие, давно не открывал). `medium`
- [ ] **Корзина / undo** через `createTrashRequest` (Android 11+). `easy→medium`
- [ ] **Похожие/размытые фото** (ML Kit / perceptual hash). `hard` (это moat)
- [ ] **CorpseFinder-lite** — осиротевшие файлы удалённых приложений (MediaStore × список пакетов). `medium`
- [ ] **«Неиспользуемые приложения»** (UsageStatsManager). `medium`
- [ ] **Планировщик авто-сканов** + честные нотификации (WorkManager). `medium`

**Дизайн 2026:** Material 3 Expressive — dynamic color (Monet), крупный storage-donut как герой,
spring-анимации + haptics, новые формы кнопок, адаптивный layout + Glance-виджет.

---

## Сквозной принцип бренда
**«Ты решаешь — системное под защитой».** Везде: обратимость (Корзина/Недавно удалённые),
dry-run/превью, честные цифры в МБ/ГБ, никаких страшилок и фейк-ускорений.
Это и этика, и защита от ревью сторов, и отличие от агрессивных конкурентов.
