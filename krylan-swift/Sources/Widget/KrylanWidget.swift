// Виджет KRYLAN: кольцо занятости диска на рабочем столе iPhone.
import WidgetKit
import SwiftUI

struct DiskEntry: TimelineEntry {
    let date: Date
    let usedPercent: Double
    let freeGB: Int
}

struct DiskProvider: TimelineProvider {
    func placeholder(in context: Context) -> DiskEntry {
        DiskEntry(date: .now, usedPercent: 72, freeGB: 58)
    }
    func getSnapshot(in context: Context, completion: @escaping (DiskEntry) -> Void) {
        completion(current())
    }
    func getTimeline(in context: Context, completion: @escaping (Timeline<DiskEntry>) -> Void) {
        completion(Timeline(entries: [current()],
                            policy: .after(.now.addingTimeInterval(3600))))
    }

    private func current() -> DiskEntry {
        let url = URL(fileURLWithPath: NSHomeDirectory())
        let vals = try? url.resourceValues(forKeys: [.volumeTotalCapacityKey,
                                                     .volumeAvailableCapacityForImportantUsageKey])
        let total = Double(vals?.volumeTotalCapacity ?? 1)
        let free = Double(vals?.volumeAvailableCapacityForImportantUsage ?? 0)
        let used = max(0, min(100, (total - free) / max(total, 1) * 100))
        return DiskEntry(date: .now, usedPercent: used, freeGB: Int(free / 1_073_741_824))
    }
}

struct KrylanWidgetView: View {
    var entry: DiskEntry

    private var ringColor: Color {
        entry.usedPercent < 60 ? Brand.green : (entry.usedPercent < 85 ? Brand.yellow : Brand.red)
    }

    var body: some View {
        VStack(spacing: 6) {
            ZStack {
                Circle().stroke(Brand.track, lineWidth: 10)
                Circle().trim(from: 0, to: entry.usedPercent / 100)
                    .stroke(ringColor, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                VStack(spacing: 0) {
                    Text("\(Int(entry.usedPercent))%")
                        .font(.system(size: 22, weight: .bold)).foregroundStyle(Brand.text)
                    Text("диск").font(.system(size: 9)).foregroundStyle(Brand.muted)
                }
            }
            .frame(width: 84, height: 84)
            Text("\(entry.freeGB) ГБ свободно")
                .font(.system(size: 11, weight: .bold)).foregroundStyle(Brand.muted)
        }
        .containerBackground(for: .widget) { Brand.bg0 }
    }
}

struct KrylanDiskWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "KrylanDisk", provider: DiskProvider()) { entry in
            KrylanWidgetView(entry: entry)
        }
        .configurationDisplayName("KRYLAN · Диск")
        .description("Кольцо занятости хранилища. «Дай устройству крылья».")
        .supportedFamilies([.systemSmall])
    }
}

@main
struct KrylanWidgetBundle: WidgetBundle {
    var body: some Widget {
        KrylanDiskWidget()
    }
}
