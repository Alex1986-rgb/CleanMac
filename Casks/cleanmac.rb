cask "cleanmac" do
  version "2.29.0"
  sha256 "c5e8dbedba12f9d3f77a25c26fcc679f791566a842550dd645a1de2670256c67"

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
