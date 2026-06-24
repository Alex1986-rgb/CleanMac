cask "cleanmac" do
  version "2.37.0"
  sha256 "b8a27458c9c7fb500129e4d48adc4cd0ed63b67dce96bca26c08a45943d2e320"

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
