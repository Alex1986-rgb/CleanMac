// Фирменный анимированный «глобус» KRYLAN — вращающаяся каркасная планета в неон-циан.
// Canvas + TimelineView(.animation): плавно ~60fps, без таймеров. Работает на iOS и macOS.
import SwiftUI

struct GlobeView: View {
    var height: CGFloat = 220
    // Неон-циан эталона (ярче, чем системный Brand.cyan).
    private let neon = Color(red: 0.13, green: 0.83, blue: 0.93)
    // Узлы-«города» — розовый.
    private let pink = Color(red: 1.0, green: 0.40, blue: 0.83)   // #FF66D4
    // Фиксированный набор широт для узлов.
    private let cityLat: [Double] = [0.52, -0.20, 0.10, -0.45, 0.34, -0.08, 0.62]

    var body: some View {
        TimelineView(.animation) { tl in
            let t = tl.date.timeIntervalSinceReferenceDate
            Canvas { ctx, size in
                let cx = size.width / 2
                let cy = size.height / 2
                let r = min(size.width, size.height) * 0.34

                // Пульс-сердцебиение.
                let ph = (t * 1.8).truncatingRemainder(dividingBy: 1.0)
                let beat = exp(-pow(ph - 0.16, 2) / 0.004) + 0.6 * exp(-pow(ph - 0.34, 2) / 0.004)
                let puls = min(1.0, beat)

                // Ореол: 4 убывающие окружности.
                for k in 0..<4 {
                    let rr = r + Double(k) * 4 + puls * 7
                    let rect = CGRect(x: cx - rr, y: cy - rr, width: rr * 2, height: rr * 2)
                    let op = 0.22 * (1.0 - Double(k) / 4.0)
                    ctx.stroke(Path(ellipseIn: rect), with: .color(neon.opacity(op)), lineWidth: 1.5)
                }

                // Кольцо-импульс на ударе.
                if puls > 0.15 {
                    let rr = r + 8 + puls * 16
                    let rect = CGRect(x: cx - rr, y: cy - rr, width: rr * 2, height: rr * 2)
                    ctx.stroke(Path(ellipseIn: rect), with: .color(neon.opacity(0.35 * puls)), lineWidth: 2)
                }

                // Тёмная сфера + яркий лимб.
                let sphere = CGRect(x: cx - r, y: cy - r, width: r * 2, height: r * 2)
                ctx.fill(Path(ellipseIn: sphere), with: .color(neon.opacity(0.06)))
                ctx.stroke(Path(ellipseIn: sphere), with: .color(neon.opacity(0.55 + 0.45 * puls)), lineWidth: 2)

                // Параллели.
                for lat in [-0.66, -0.33, 0.0, 0.33, 0.66] {
                    let rx = r * (1 - lat * lat).squareRoot()
                    let ry = rx * 0.18
                    let ey = cy - r * lat
                    let rect = CGRect(x: cx - rx, y: ey - ry, width: rx * 2, height: ry * 2)
                    ctx.stroke(Path(ellipseIn: rect), with: .color(neon.opacity(0.5)), lineWidth: 1)
                }

                // Меридианы (вращаются).
                let phase = t * 2.4
                for k in 0..<6 {
                    let ang = phase + Double(k) * .pi / 6
                    let rx = abs(r * cos(ang))
                    let rect = CGRect(x: cx - rx, y: cy - r, width: rx * 2, height: r * 2)
                    ctx.stroke(Path(ellipseIn: rect), with: .color(neon.opacity(0.5)), lineWidth: 1)
                }

                // Узлы-«города» на передней полусфере.
                for (n, la) in cityLat.enumerated() {
                    let na = phase + Double(n) * 0.9
                    guard sin(na) > -0.1 else { continue }
                    let rx = r * (1 - la * la).squareRoot()
                    let px = cx + rx * cos(na)
                    let py = cy - r * la
                    let dot = CGRect(x: px - 3, y: py - 3, width: 6, height: 6)
                    ctx.fill(Path(ellipseIn: dot), with: .color(pink))
                    let halo = CGRect(x: px - 6, y: py - 6, width: 12, height: 12)
                    ctx.stroke(Path(ellipseIn: halo), with: .color(pink.opacity(0.4)), lineWidth: 1)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .frame(height: height)
    }
}
