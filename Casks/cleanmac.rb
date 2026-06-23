cask "cleanmac" do
  version "2.28.0"
  sha256 "ce1601842dc0d9412b5863527a0d7e7f9621f5d143360c6a4a586b4f068e5174"

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
