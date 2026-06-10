// Дашборд KRYLAN.
import SwiftUI

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Дашборд").font(.largeTitle.bold()).foregroundStyle(Brand.text)
                    Text("Состояние устройства в реальном времени")
                        .font(.callout).foregroundStyle(Brand.muted)
                }

                // Health-кольцо (общая оценка)
                ZStack {
                    Circle().stroke(Brand.track, lineWidth: 16)
                    Circle().trim(from: 0, to: monitor.healthScore / 100)
                        .stroke(Brand.load(100 - monitor.healthScore),
                                style: StrokeStyle(lineWidth: 16, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                        .animation(.easeOut(duration: 0.5), value: monitor.healthScore)
                    VStack(spacing: 2) {
                        Text("\(Int(monitor.healthScore))")
                            .font(.system(size: 42, weight: .bold)).foregroundStyle(Brand.text)
                        Text(monitor.healthLabel)
                            .font(.caption.bold()).foregroundStyle(Brand.load(100 - monitor.healthScore))
                    }
                }
                .frame(width: 152, height: 152)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 22)
                .background(Brand.glass)
                .clipShape(RoundedRectangle(cornerRadius: 18))

                HStack(spacing: 22) {
                    RingGauge(value: monitor.memoryUsedPercent, label: "ПАМЯТЬ")
                    RingGauge(value: monitor.diskUsedPercent, label: "ДИСК")
                    RingGauge(value: Double(monitor.batteryPercent), label: "БАТАРЕЯ", invert: true)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 18)
                .background(Brand.glass)
                .clipShape(RoundedRectangle(cornerRadius: 18))

                card(title: "Хранилище",
                     value: "\(monitor.diskFreeGB) ГБ свободно",
                     sub: "из \(monitor.diskTotalGB) ГБ")
                card(title: "Оперативная память",
                     value: "\(Int(monitor.memoryUsedPercent))% занято",
                     sub: "установлено \(monitor.ramTotalGB) ГБ")
            }
            .padding(24)
        }
        .background(Brand.bg0)
    }

    func card(title: String, value: String, sub: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption.bold()).foregroundStyle(Brand.muted)
            Text(value).font(.title2.bold()).foregroundStyle(Brand.text)
            Text(sub).font(.callout).foregroundStyle(Brand.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(Brand.glass)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
