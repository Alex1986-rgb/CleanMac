cask "cleanmac" do
  # Версия = последний ОПУБЛИКОВАННЫЙ релиз с .dmg (а не версия исходников).
  # Обновляется при каждом релизе: bump version + sha256 от собранного DMG.
  version "2.43.0"
  sha256 "c73e3775b2ca439ef765bfa2e401a7370af9433bd53d2494a537f54bd3d87367"

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
