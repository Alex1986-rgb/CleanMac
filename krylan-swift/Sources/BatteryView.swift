// Экран батареи с кольцом заряда.
import SwiftUI

struct BatteryView: View {
    @ObservedObject var monitor: SystemMonitor

    private var batteryColor: Color {
        monitor.batteryPercent > 40 ? Brand.green
            : (monitor.batteryPercent > 20 ? Brand.yellow : Brand.red)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Батарея").font(.largeTitle.bold()).foregroundStyle(Brand.text)

            ZStack {
                Circle().stroke(Brand.track, lineWidth: 18)
                Circle().trim(from: 0, to: Double(monitor.batteryPercent) / 100)
                    .stroke(batteryColor, style: StrokeStyle(lineWidth: 18, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.5), value: monitor.batteryPercent)
                VStack(spacing: 2) {
                    Text("\(monitor.batteryPercent)%")
                        .font(.system(size: 40, weight: .bold)).foregroundStyle(Brand.text)
                    Text("заряд").font(.caption).foregroundStyle(Brand.muted)
                }
            }
            .frame(width: 172, height: 172)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)

            infoRow("Память занята", "\(Int(monitor.memoryUsedPercent))%")
            infoRow("ОЗУ всего", "\(monitor.ramTotalGB) ГБ")
            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    func infoRow(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title).foregroundStyle(Brand.muted)
            Spacer()
            Text(value).bold().foregroundStyle(Brand.text)
        }
        .padding(14)
        .background(Brand.glass)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
