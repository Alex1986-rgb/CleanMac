# 🧪 Тесты KRYLAN CleanMac

Юнит-тесты безопасных функций (без GUI).

## Запуск
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m unittest -v tests.test_cleanmac
```

## Покрытие
- `human()` — форматирование размеров (Б/КБ/МБ/ГБ)
- `is_protected()` / `to_trash()` — **защита системных и корневых папок** от удаления
- `TR` — словарь локализации (RU/EN)

CI (`ci-release.yml.txt`) запускает эти тесты на каждый тег.
