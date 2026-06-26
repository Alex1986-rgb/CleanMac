cask "cleanmac" do
  # Версия = последний ОПУБЛИКОВАННЫЙ релиз с .dmg (а не версия исходников).
  # Обновляется при каждом релизе: bump version + sha256 от собранного DMG.
  version "2.39.0"
  sha256 "61b6761943e818bbfac3579bc101fc7c2696f54bd3ac0c0ba8feb8005872faa7"

  url "https://github.com/Alex1986-rgb/CleanMac/releases/download/v#{version}/CleanMac.dmg"
  name "CleanMac"
  desc "Mac optimizer: dashboard, smart cleanup, autopilot, privacy and protection"
  homepage "https://github.com/Alex1986-rgb/CleanMac"

  depends_on macos: ">= :big_sur"

  app "CleanMac.app"

  zap trash: [
    "~/.config/cleanmac",
  ]
end
