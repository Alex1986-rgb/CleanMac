// Дашборд KRYLAN — модернизированный дизайн (надёжная раскладка).
import SwiftUI

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {

                // Подзаголовок (титул показывает нав-бар)
                HStack {
                    Text("Состояние в реальном времени")
                        .font(.subheadline).foregroundStyle(Brand.muted)
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

                // Рекомендации
                VStack(alignment: .leading, spacing: 10) {
                    Text("РЕКОМЕНДАЦИИ").font(.caption.bold()).foregroundStyle(Brand.muted)
                    ForEach(Array(advice.enumerated()), id: \.offset) { _, a in
                        HStack(alignment: .top, spacing: 10) {
                            Circle().fill(a.0).frame(width: 10, height: 10).padding(.top, 5)
                            Text(a.1).font(.subheadline).foregroundStyle(Brand.text)
                            Spacer(minLength: 0)
                        }
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(Brand.bg0)
    }

    /// Безопасные советы по метрикам устройства (семафор по DESIGN.md).
    private var advice: [(Color, String)] {
        var out: [(Color, String)] = []
        let disk = monitor.diskUsedPercent, ram = monitor.memoryUsedPercent, batt = monitor.batteryPercent
        if disk >= 90 {
            out.append((Brand.red, "Хранилище заполнено на \(Int(disk))% — удалите дубли фото, крупные видео и скриншоты."))
        } else if disk >= 80 {
            out.append((Brand.yellow, "Хранилище на \(Int(disk))% — проверьте «Видео» и «Скриншоты»."))
        }
        if ram >= 85 {
            out.append((Brand.red, "Память на \(Int(ram))% — закройте фоновые приложения."))
        }
        if batt > 0 && batt <= 20 {
            out.append((Brand.yellow, "Низкий заряд (\(batt)%) — подключите зарядку."))
        }
        if out.isEmpty {
            out.append((Brand.green, "Всё в порядке — устройство работает оптимально."))
        }
        return out
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
