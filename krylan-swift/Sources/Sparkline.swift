// Лёгкий спарклайн (мини-график) для живой скорости сети на дашборде.
import SwiftUI

struct Sparkline: View {
    let values: [Double]
    let color: Color

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let peak = max(values.max() ?? 1, 1)
            let n = max(values.count - 1, 1)
            Path { p in
                for (i, v) in values.enumerated() {
                    let x = w * CGFloat(i) / CGFloat(n)
                    let y = h - h * CGFloat(v / peak)
                    if i == 0 { p.move(to: CGPoint(x: x, y: y)) }
                    else { p.addLine(to: CGPoint(x: x, y: y)) }
                }
            }
            .stroke(color, style: StrokeStyle(lineWidth: 2, lineJoin: .round))
        }
    }
}

/// Бегущая ЭКГ-линия (кардиограмма системы) для левого HUD-блока.
/// Амплитуда пика растёт с нагрузкой `level` (0…1).
struct ECGView: View {
    var color: Color = Brand.green
    var level: Double = 0.4   // 0…1 — пульс/нагрузка
    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                let w = size.width, h = size.height, mid = h / 2
                let amp = (0.18 + 0.55 * max(0, min(1, level))) * h
                // фаза бега
                let speed = 1.6
                var path = Path()
                let steps = Int(w)
                for i in 0...steps {
                    let x = Double(i)
                    // нормированная позиция вдоль одного «удара»
                    let beatLen = 60.0
                    let ph = ((x / beatLen) + t * speed).truncatingRemainder(dividingBy: 1.0)
                    // спайк QRS: узкий резкий пик + маленькая обратная волна
                    let spike = exp(-pow(ph - 0.5, 2) / 0.0008) - 0.35 * exp(-pow(ph - 0.56, 2) / 0.0015)
                    let pwave = 0.12 * exp(-pow(ph - 0.30, 2) / 0.003)
                    let y = mid - (spike + pwave) * amp
                    if i == 0 { path.move(to: CGPoint(x: x, y: y)) }
                    else { path.addLine(to: CGPoint(x: x, y: y)) }
                }
                // glow + основная линия
                ctx.stroke(path, with: .color(color.opacity(0.30)), style: StrokeStyle(lineWidth: 5, lineJoin: .round))
                ctx.stroke(path, with: .color(color), style: StrokeStyle(lineWidth: 1.8, lineJoin: .round))
            }
        }
    }
}
