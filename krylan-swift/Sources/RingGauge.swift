// Анимированное кольцо-индикатор.
import SwiftUI

struct RingGauge: View {
    var value: Double          // 0...100
    var label: String
    var invert: Bool = false   // invert=true: больше=лучше (например, заряд батареи)

    var body: some View {
        let frac = max(0, min(1, value / 100))
        let color = invert ? Brand.load(100 - value) : Brand.load(value)
        VStack(spacing: 8) {
            ZStack {
                Circle().stroke(Brand.track, lineWidth: 12)
                Circle()
                    .trim(from: 0, to: frac)
                    .stroke(color, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.4), value: frac)
                Text("\(Int(value))%")
                    .font(.title3.bold())
                    .foregroundStyle(Brand.text)
            }
            .frame(width: 92, height: 92)
            Text(label).font(.caption).foregroundStyle(Brand.muted)
        }
    }
}
