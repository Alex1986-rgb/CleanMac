// Экран хранилища с кольцом и разбивкой.
import SwiftUI

struct StorageView: View {
    @ObservedObject var monitor: SystemMonitor

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            PageHeader(title: "Хранилище")

            ZStack {
                Circle().stroke(Brand.track, lineWidth: 18)
                Circle().trim(from: 0, to: monitor.diskUsedPercent / 100)
                    .stroke(Brand.load(monitor.diskUsedPercent),
                            style: StrokeStyle(lineWidth: 18, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.easeOut(duration: 0.5), value: monitor.diskUsedPercent)
                VStack(spacing: 2) {
                    Text("\(Int(monitor.diskUsedPercent))%")
                        .font(.system(size: 40, weight: .bold)).foregroundStyle(Brand.text)
                    Text("занято").font(.caption).foregroundStyle(Brand.muted)
                }
            }
            .frame(width: 172, height: 172)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)

            row("Свободно", "\(monitor.diskFreeGB) ГБ", Brand.green)
            row("Занято", "\(max(0, monitor.diskTotalGB - monitor.diskFreeGB)) ГБ", Brand.blue)
            row("Всего", "\(monitor.diskTotalGB) ГБ", Brand.muted)
            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(StarfieldView())
    }

    func row(_ title: String, _ value: String, _ color: Color) -> some View {
        HStack(spacing: 10) {
            Circle().fill(color).frame(width: 10, height: 10)
            Text(title).foregroundStyle(Brand.muted)
            Spacer()
            Text(value).bold().foregroundStyle(Brand.text)
        }
        .padding(14)
        .background(Brand.glass)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
