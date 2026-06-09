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
