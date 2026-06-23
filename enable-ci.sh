#!/bin/bash
# Включает CI (GitHub Actions) для авто-сборки Windows .exe + Linux + macOS DMG.
# Нужно один раз: у токена должен появиться scope `workflow`.
# Запуск: bash enable-ci.sh
set -e
cd "$(dirname "$0")"
REPO="Alex1986-rgb/CleanMac"

echo "▶ Шаг 1/3: добавляю scope 'workflow' к gh-токену (откроется браузер)…"
gh auth refresh -h github.com -s workflow

echo "▶ Шаг 2/3: пушу workflow-файлы…"
git add .github/workflows/ci.yml .github/workflows/release.yml
git commit -m "ci: включить сборку всех платформ по тегу" || echo "  (нечего коммитить — уже в индексе)"
git push origin HEAD

echo "▶ Шаг 3/3: запускаю сборку всех платформ для последнего релиза…"
# release.yml собирает по тегу v* и по ручному запуску
gh workflow run "release.yml" --repo "$REPO" 2>/dev/null \
  && echo "  ✓ Сборка запущена" \
  || echo "  ⚠️ Запусти вручную: gh workflow run release.yml --repo $REPO  (или перетегируй: git tag -f v2.28.0 && git push -f origin v2.28.0)"

echo
echo "✅ Готово. Следи за сборкой: gh run watch --repo $REPO"
echo "   По завершении .exe (Windows) и Linux-бинарь появятся в релизе автоматически."
