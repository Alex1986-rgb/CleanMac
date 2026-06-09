#!/bin/bash
# Приватная аналитика KRYLAN: статистика загрузок релизов с GitHub.
# Никакой телеметрии в приложении — только публичные счётчики GitHub.
REPO="Alex1986-rgb/CleanMac"
echo "📈 KRYLAN · статистика загрузок ($REPO)"
echo "────────────────────────────────────────────"
gh api "repos/$REPO/releases" --jq '
  reverse | .[] |
  "\(.tag_name)\t\([.assets[].download_count] | add // 0) загрузок\t\(.published_at[0:10])"
' 2>/dev/null | column -t -s $'\t'
echo "────────────────────────────────────────────"
total=$(gh api "repos/$REPO/releases" --jq '[.[].assets[].download_count] | add // 0' 2>/dev/null)
stars=$(gh api "repos/$REPO" --jq '.stargazers_count' 2>/dev/null)
echo "Всего загрузок: ${total:-0}   ⭐ Звёзд: ${stars:-0}"
