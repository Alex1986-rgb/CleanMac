#!/bin/bash
# Генерация Sparkle appcast.xml из релизов GitHub → docs/appcast.xml.
# Для нативной (подписанной) версии: Sparkle проверяет этот файл.
# ВНИМАНИЕ: для боевого Sparkle нужна EdDSA-подпись (sparkle:edSignature) —
# добавляется утилитой `sign_update` из Sparkle после подписи DMG.
set -e
REPO="Alex1986-rgb/CleanMac"
OUT="$(dirname "$0")/docs/appcast.xml"
URL="https://alex1986-rgb.github.io/CleanMac/appcast.xml"

{
echo '<?xml version="1.0" encoding="utf-8"?>'
echo '<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" xmlns:dc="http://purl.org/dc/elements/1.1/">'
echo '  <channel>'
echo '    <title>KRYLAN CleanMac</title>'
echo "    <link>$URL</link>"
echo '    <description>«Дай устройству крылья» — обновления KRYLAN CleanMac.</description>'
echo '    <language>ru</language>'
gh api "repos/$REPO/releases" --jq '.[] | select(.draft==false) |
  "    <item>\n      <title>\(.tag_name)</title>\n      <sparkle:version>\(.tag_name|ltrimstr("v"))</sparkle:version>\n      <sparkle:shortVersionString>\(.tag_name|ltrimstr("v"))</sparkle:shortVersionString>\n      <pubDate>\(.published_at)</pubDate>\n      <enclosure url=\"\(.assets[] | select(.name|endswith(".dmg")) | .browser_download_url)\" sparkle:version=\"\(.tag_name|ltrimstr("v"))\" type=\"application/octet-stream\" length=\"\(.assets[] | select(.name|endswith(".dmg")) | .size)\"/>\n    </item>"' 2>/dev/null
echo '  </channel>'
echo '</rss>'
} > "$OUT"
echo "✓ $OUT собран ($(grep -c '<item>' "$OUT") версий)"
