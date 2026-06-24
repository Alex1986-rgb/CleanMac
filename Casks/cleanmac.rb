cask "cleanmac" do
  version "2.32.0"
  sha256 "0bae87eb2b518d0e5888562ea661140a17a1546074c4814a7664e498705eb06f"

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
