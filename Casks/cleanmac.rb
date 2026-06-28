cask "cleanmac" do
  # Версия = последний ОПУБЛИКОВАННЫЙ релиз с .dmg (а не версия исходников).
  # Обновляется при каждом релизе: bump version + sha256 от собранного DMG.
  version "2.45.0"
  sha256 "aadfd7c47623f0c37a5dadef0f750f71e4139a6999af92df4b3d29c41235657f"

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
