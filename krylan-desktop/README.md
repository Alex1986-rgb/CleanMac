# 🪽 KRYLAN Desktop — Windows · macOS · Linux

Кросс-платформенный оптимизатор: мониторинг CPU/ОЗУ/диск/батарея и безопасная
очистка кэшей (всё в Корзину). Один код для всех компьютеров.
Создатель: **Кырлан Александр Сергеевич**.

## Запуск (любая ОС)
```bash
pip install -r requirements.txt
python krylan.py
```
Нужен **Python 3.9+** (на Windows — с python.org, «Add to PATH»).

## Сборка standalone

### Windows (.exe)
```bat
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name KRYLAN --icon krylan.ico krylan.py
:: результат: dist\KRYLAN.exe — запускается на любом Windows без Python
```
> Иконка `krylan.ico` уже в комплекте.
> Без подписи Windows SmartScreen покажет «Запустить всё равно» (Подробнее → Выполнить).

### macOS (.app/.dmg)
```bash
pyinstaller --onefile --windowed --name KRYLAN --icon ../CleanMac.icns krylan.py
```

### Linux
```bash
pyinstaller --onefile --name krylan krylan.py   # ./dist/krylan
```

## Что внутри
- **Дашборд** — кольца CPU/ОЗУ/Диск/Батарея (psutil), инфо об ОС/диске/памяти.
- **Процессы** — диспетчер задач: топ по памяти/CPU + завершение процесса.
- **Сеть** — скорость ↓/↑ на дашборде.
- **Очистка** — временные файлы и кэши, **зависят от ОС**:
  - Windows: `%TEMP%`, кэш Chrome/Edge/Explorer
  - macOS: `~/Library/Caches`, `~/Library/Logs`
  - Linux: `~/.cache`, эскизы
  - Удаление через **send2trash** (системная Корзина).
- **О программе** — бренд, автор, версия.

## Полная версия для macOS
На macOS богаче нативный **CleanMac** (../README.md): автопилот, защита,
деинсталлятор, карта диска и т.д. KRYLAN Desktop — лёгкий кросс-платформенный вариант.
