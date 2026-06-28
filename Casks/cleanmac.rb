cask "cleanmac" do
  # Версия = последний ОПУБЛИКОВАННЫЙ релиз с .dmg (а не версия исходников).
  # Обновляется при каждом релизе: bump version + sha256 от собранного DMG.
  version "2.47.0"
  sha256 "498997dea3f1c17113c159b5764c6654e0d22d69eb306220779343fd447a61f1"

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
