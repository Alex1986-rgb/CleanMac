cask "cleanmac" do
  version "2.40.0"
  sha256 "c311126145165eeae9ce7a05ff856cff6789afb3e7dbd8ac4fbb197f1bffb335"

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
