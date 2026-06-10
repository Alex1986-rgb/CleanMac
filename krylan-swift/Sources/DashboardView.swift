// Дашборд KRYLAN — модернизированный дизайн (надёжная раскладка).
import SwiftUI

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {

                // Заголовок
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Дашборд").font(.system(size: 28, weight: .bold)).foregroundStyle(Brand.text)
                        Text("Состояние в реальном времени")
                            .font(.subheadline).foregroundStyle(Brand.muted)
                    }
                    Spacer(minLength: 0)
                }

                // Health-герой
                VStack(spacing: 0) {
                    ZStack {
                        Circle().stroke(Brand.track, lineWidth: 16)
                        Circle().trim(from: 0, to: monitor.healthScore / 100)
                            .stroke(Brand.load(100 - monitor.healthScore),
                                    style: StrokeStyle(lineWidth: 16, lineCap: .round))
                            .rotationEffect(.degrees(-90))
                            .animation(.easeOut(duration: 0.5), value: monitor.healthScore)
                        VStack(spacing: 0) {
                            Text("\(Int(monitor.healthScore))")
                                .font(.system(size: 46, weight: .bold)).foregroundStyle(Brand.text)
                            Text(monitor.healthLabel)
                                .font(.subheadline.bold()).foregroundStyle(Brand.load(100 - monitor.healthScore))
                        }
                    }
                    .frame(width: 160, height: 160)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 22)
                .background(RoundedRectangle(cornerRadius: 20).fill(Brand.glass))

                // Кольца метрик
                HStack(spacing: 0) {
                    Spacer(minLength: 0)
                    ring(monitor.memoryUsedPercent, "ПАМЯТЬ")
                    Spacer(minLength: 0)
                    ring(monitor.diskUsedPercent, "ДИСК")
                    Spacer(minLength: 0)
                    ring(Double(monitor.batteryPercent), "БАТАРЕЯ", invert: true)
                    Spacer(minLength: 0)
                }
                .padding(.vertical, 18)
                .frame(maxWidth: .infinity)
                .background(RoundedRectangle(cornerRadius: 20).fill(Brand.glass))

                // Карточки
                infoCard("internaldrive.fill", "Хранилище",
                         "\(monitor.diskFreeGB) ГБ свободно", "из \(monitor.diskTotalGB) ГБ", Brand.blue)
                infoCard("memorychip.fill", "Оперативная память",
                         "\(Int(monitor.memoryUsedPercent))% занято", "всего \(monitor.ramTotalGB) ГБ", Brand.purple)
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(Brand.bg0)
    }

    private func ring(_ value: Double, _ label: String, invert: Bool = false) -> some View {
        let color = invert ? Brand.load(100 - value) : Brand.load(value)
        return VStack(spacing: 8) {
            ZStack {
                Circle().stroke(Brand.track, lineWidth: 9)
                Circle().trim(from: 0, to: min(1, value / 100))
                    .stroke(color, style: StrokeStyle(lineWidth: 9, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.4), value: value)
                Text("\(Int(value))%").font(.callout.bold()).foregroundStyle(Brand.text)
            }
            .frame(width: 70, height: 70)
            Text(label).font(.caption2).foregroundStyle(Brand.muted)
        }
    }

    private func infoCard(_ icon: String, _ title: String, _ value: String, _ sub: String, _ tint: Color) -> some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.title2).foregroundStyle(tint)
                .frame(width: 46, height: 46)
                .background(tint.opacity(0.15)).clipShape(RoundedRectangle(cornerRadius: 12))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.caption.bold()).foregroundStyle(Brand.muted)
                Text(value).font(.title3.bold()).foregroundStyle(Brand.text)
                Text(sub).font(.caption).foregroundStyle(Brand.muted)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }
}
