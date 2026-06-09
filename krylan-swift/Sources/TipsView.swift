// Рекомендации по оптимизации на основе текущих метрик.
import SwiftUI

struct TipsView: View {
    @ObservedObject var monitor: SystemMonitor

    private var tips: [(String, String, Color)] {
        var t: [(String, String, Color)] = []
        if monitor.diskUsedPercent >= 85 {
            t.append(("internaldrive.fill", "Диск заполнен на \(Int(monitor.diskUsedPercent))% — очистите кэш и крупные файлы.", Brand.red))
        }
        if monitor.memoryUsedPercent >= 80 {
            t.append(("memorychip.fill", "Память загружена на \(Int(monitor.memoryUsedPercent))% — закройте лишние приложения.", Brand.yellow))
        }
        if (1...20).contains(monitor.batteryPercent) {
            t.append(("battery.25", "Низкий заряд (\(monitor.batteryPercent)%) — подключите зарядку.", Brand.yellow))
        }
        if t.isEmpty {
            t.append(("checkmark.seal.fill", "Всё в порядке — система работает оптимально.", Brand.green))
        }
        return t
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Советы").font(.largeTitle.bold()).foregroundStyle(Brand.text)
            ForEach(Array(tips.enumerated()), id: \.offset) { _, tip in
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: tip.0).foregroundStyle(tip.2).font(.title3)
                    Text(tip.1).foregroundStyle(Brand.text)
                    Spacer()
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Brand.glass)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            Spacer()
        }
        .padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}
