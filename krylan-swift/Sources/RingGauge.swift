// HUD-кольцо KRYLAN в стиле «рубки» (эталон macOS CleanMac).
// Canvas: след-круг + 28 насечек (горят до значения, каждая 6-я длиннее)
// + светящаяся дуга прогресса + белая точка-конец + центр value + подпись.
import SwiftUI

/// Большое HUD-кольцо (для блока ЗДОРОВЬЕ/героя).
struct RingGauge: View {
    var value: Double          // 0...100
    var label: String
    var invert: Bool = false   // invert=true: больше=лучше (заряд батареи)
    var size: CGFloat = 92
    var unit: String = "%"
    var bigCenter: String? = nil   // если задан — показать вместо value (напр. «Отлично»)

    var body: some View {
        let frac = max(0, min(1, value / 100))
        let color = invert ? Brand.load(100 - value) : Brand.load(value)
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            Canvas { ctx, sz in
                HUDRing.draw(ctx: &ctx, size: sz, frac: frac, color: color, t: t,
                             ticks: 28, lineWidth: max(3, size * 0.07))
            }
            .overlay(centerLabel(color: color))
            .frame(width: size, height: size)
        }
    }

    @ViewBuilder
    private func centerLabel(color: Color) -> some View {
        VStack(spacing: size * 0.02) {
            if let big = bigCenter {
                Text("\(Int(value))")
                    .font(.system(size: size * 0.34, weight: .bold, design: .rounded))
                    .foregroundStyle(Brand.text)
                Text(big)
                    .font(.system(size: size * 0.12, weight: .bold))
                    .foregroundStyle(color)
            } else {
                Text("\(Int(value))")
                    .font(.system(size: size * 0.30, weight: .bold, design: .rounded))
                    .foregroundStyle(Brand.text) +
                Text(unit)
                    .font(.system(size: size * 0.15, weight: .semibold))
                    .foregroundStyle(Brand.muted)
            }
            Text(label)
                .font(.system(size: size * 0.105, weight: .bold))
                .tracking(0.5)
                .foregroundStyle(Brand.muted)
        }
    }
}

/// Компактное HUD-кольцо для орбитальных гейджей дашборда.
struct MiniGauge: View {
    var value: Double
    var label: String
    var invert: Bool = false
    var size: CGFloat = 64

    var body: some View {
        let frac = max(0, min(1, value / 100))
        let color = invert ? Brand.load(100 - value) : Brand.load(value)
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            Canvas { ctx, sz in
                HUDRing.draw(ctx: &ctx, size: sz, frac: frac, color: color, t: t,
                             ticks: 28, lineWidth: max(2, size * 0.06))
            }
            .overlay(
                VStack(spacing: 0) {
                    Text("\(Int(value))")
                        .font(.system(size: size * 0.30, weight: .bold, design: .rounded))
                        .foregroundStyle(Brand.text)
                    Text(label)
                        .font(.system(size: size * 0.135, weight: .bold))
                        .tracking(0.3)
                        .foregroundStyle(color)
                }
            )
            .frame(width: size, height: size)
        }
    }
}

/// Общий рисователь HUD-кольца (используют RingGauge и MiniGauge).
enum HUDRing {
    static func draw(ctx: inout GraphicsContext, size: CGSize, frac: Double,
                     color: Color, t: TimeInterval, ticks: Int, lineWidth: CGFloat) {
        let cx = size.width / 2, cy = size.height / 2
        let R = min(size.width, size.height) / 2 - lineWidth * 0.8
        let center = CGPoint(x: cx, y: cy)
        let start = -Double.pi / 2          // сверху
        let total = 2 * Double.pi

        // 1) Тонкий след-круг.
        let trackRect = CGRect(x: cx - R, y: cy - R, width: R * 2, height: R * 2)
        ctx.stroke(Path(ellipseIn: trackRect), with: .color(Brand.track.opacity(0.55)),
                   lineWidth: max(1, lineWidth * 0.35))

        // 2) Насечки (28): горят до frac, каждая 6-я длиннее.
        let litCount = Int((Double(ticks) * frac).rounded())
        for i in 0..<ticks {
            let a = start + total * Double(i) / Double(ticks)
            let long = (i % 6 == 0)
            let inner = R - (long ? lineWidth * 1.9 : lineWidth * 1.2)
            let outer = R - lineWidth * 0.2
            let lit = i < litCount
            let p1 = CGPoint(x: cx + cos(a) * inner, y: cy + sin(a) * inner)
            let p2 = CGPoint(x: cx + cos(a) * outer, y: cy + sin(a) * outer)
            var path = Path(); path.move(to: p1); path.addLine(to: p2)
            let col = lit ? color.opacity(0.95) : Brand.track.opacity(0.45)
            ctx.stroke(path, with: .color(col), lineWidth: long ? max(2, lineWidth * 0.5) : max(1.2, lineWidth * 0.35))
        }

        // 3) Светящаяся дуга прогресса (несколько проходов для glow).
        if frac > 0.001 {
            let end = start + total * frac
            let arcR = R - lineWidth * 0.2
            func arc() -> Path {
                var p = Path()
                p.addArc(center: center, radius: arcR,
                         startAngle: .radians(start), endAngle: .radians(end), clockwise: false)
                return p
            }
            // glow слои
            ctx.stroke(arc(), with: .color(color.opacity(0.22)), style: StrokeStyle(lineWidth: lineWidth * 2.6, lineCap: .round))
            ctx.stroke(arc(), with: .color(color.opacity(0.35)), style: StrokeStyle(lineWidth: lineWidth * 1.6, lineCap: .round))
            ctx.stroke(arc(), with: .color(color), style: StrokeStyle(lineWidth: lineWidth * 0.85, lineCap: .round))

            // 4) Белая точка-конец с пульсом.
            let pulse = 0.85 + 0.15 * sin(t * 3.0)
            let ex = cx + cos(end) * arcR
            let ey = cy + sin(end) * arcR
            let dotR = lineWidth * 0.7 * pulse
            let halo = CGRect(x: ex - dotR * 2.2, y: ey - dotR * 2.2, width: dotR * 4.4, height: dotR * 4.4)
            ctx.fill(Path(ellipseIn: halo), with: .color(color.opacity(0.30)))
            let dot = CGRect(x: ex - dotR, y: ey - dotR, width: dotR * 2, height: dotR * 2)
            ctx.fill(Path(ellipseIn: dot), with: .color(.white))
        }
    }
}
