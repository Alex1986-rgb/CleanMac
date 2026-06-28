// Звёздное небо + порхающие крылья — фирменный фон KRYLAN («Дай устройству крылья»).
// Canvas + TimelineView: плавная анимация мерцания и парения без таймеров.
import SwiftUI

struct StarfieldView: View {
    // Звёзды генерируются один раз (детерминированно), чтобы не «прыгали».
    private struct Star { let x: Double; let y: Double; let r: Double; let phase: Double; let tint: Double }
    private let stars: [Star] = {
        var g = SystemRandomNumberGenerator()
        var seed: UInt64 = 0x9E3779B97F4A7C15
        func rnd() -> Double { seed = seed &* 6364136223846793005 &+ 1442695040888963407; return Double(seed >> 11) / Double(1 << 53) }
        return (0..<90).map { _ in Star(x: rnd(), y: rnd(), r: 0.6 + rnd()*1.8, phase: rnd()*6.28, tint: rnd()) }
    }()

    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                // База navy.
                ctx.fill(Path(CGRect(origin: .zero, size: size)), with: .color(Brand.bg0))
                // Радиальное свечение «рубки»: ярче центр-верх, гаснет к краям.
                let gc = CGPoint(x: size.width * 0.5, y: size.height * 0.38)
                let gr = max(size.width, size.height) * 0.85
                ctx.fill(Path(CGRect(origin: .zero, size: size)),
                         with: .radialGradient(
                            Gradient(colors: [Brand.glow.opacity(0.85), Brand.bg0, Brand.bg1]),
                            center: gc, startRadius: 0, endRadius: gr))
                // звёзды
                for s in stars {
                    let tw = 0.45 + 0.55 * (0.5 + 0.5 * sin(t * 1.6 + s.phase))
                    let r = s.r * (0.7 + 0.6 * tw)
                    let col = (s.tint < 0.5 ? Brand.cyan : Color.white)
                    let rect = CGRect(x: s.x*size.width - r, y: s.y*size.height - r, width: r*2, height: r*2)
                    ctx.fill(Path(ellipseIn: rect), with: .color(col.opacity(0.18 + 0.55*tw)))
                }
                // порхающие крылья 🪽
                for (i, base) in [(0.12, 0.16), (0.88, 0.22), (0.5, 0.10)].enumerated() {
                    let bob = sin(t * (0.8 + Double(i)*0.15) + Double(i)) * 10
                    let p = CGPoint(x: base.0 * size.width, y: base.1 * size.height + bob)
                    var txt = Text("🪽").font(.system(size: 26))
                    txt = txt.foregroundColor(Brand.blue.opacity(0.30))
                    ctx.draw(txt, at: p)
                }
            }
            .ignoresSafeArea()
        }
    }
}
