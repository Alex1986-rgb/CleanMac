cask "cleanmac" do
  # Версия = последний ОПУБЛИКОВАННЫЙ релиз с .dmg (а не версия исходников).
  # Обновляется при каждом релизе: bump version + sha256 от собранного DMG.
  version "2.48.0"
  sha256 "3c9b2d6416437b882663ea2e909ba305e0a1ee0aae576a1dcb4f98ed5046d384"

  url "https://github.com/Alex1986-rgb/CleanMac/releases/download/v#{version}/CleanMac.dmg"
  name "CleanMac"
  desc "Mac optimizer: dashboard, smart cleanup, autopilot, privacy and protection"
  homepage "https://github.com/Alex1986-rgb/CleanMac"

  depends_on macos: ">= :big_sur"

  app "CleanMac.app"

  # Сборка не нотаризована (нужен Apple Developer ID). Homebrew сам снимает
  # метку карантина при установке каска, поэтому через brew приложение
  # запускается сразу — в отличие от .dmg, скачанного вручную.
  caveats <<~EOS
    Сборка пока не нотаризована в Apple.

    Через Homebrew всё работает сразу. Но если вы поставите CleanMac из .dmg
    вручную, macOS скажет «Apple не удалось подтвердить, что файл не содержит
    вредоносного ПО». Лечится так:

      xattr -dr com.apple.quarantine /Applications/CleanMac.app
  EOS

  # Автопилот — это LaunchAgent, живущий ОТДЕЛЬНО от .app: скрипты в
  # ~/mac-optimizer, агент в ~/Library/LaunchAgents. Раньше zap чистил только
  # ~/.config/cleanmac, и после `brew uninstall` страж оставался в системе:
  # продолжал просыпаться раз в минуту и чистить кэши у пользователя, который
  # приложение уже удалил.
  uninstall launchctl: [
    "com.macbook.optimizer",
    "com.krylan.autoupdate",
  ]

  zap trash: [
    "~/.config/cleanmac",
    "~/mac-optimizer",
    "~/Library/LaunchAgents/com.macbook.optimizer.plist",
    "~/Library/LaunchAgents/com.krylan.autoupdate.plist",
    "~/Library/Saved Application State/com.macbook.cleanmac.savedState",
  ]
end
