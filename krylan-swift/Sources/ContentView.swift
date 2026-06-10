// Навигация и экраны KRYLAN.
import SwiftUI

enum Section: String, CaseIterable, Identifiable {
    case dashboard = "Дашборд"
    case storage   = "Хранилище"
    case battery   = "Батарея"
    case cleanup   = "Очистка"
    case photos    = "Фото-дубли"
    case contacts  = "Контакты"
    case tips      = "Советы"
    case about     = "О программе"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .dashboard: return "gauge.with.dots.needle.67percent"
        case .storage:   return "internaldrive"
        case .battery:   return "battery.100"
        case .cleanup:   return "trash"
        case .photos:    return "photo.on.rectangle.angled"
        case .contacts:  return "person.2"
        case .tips:      return "lightbulb"
        case .about:     return "info.circle"
        }
    }
}

struct ContentView: View {
    @State private var selection: Section? = .dashboard
    @StateObject private var monitor = SystemMonitor()

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 2) {
                Text("🪽 \(Brand.name)").font(.title2.bold()).foregroundStyle(Brand.text)
                Text(Brand.slogan).font(.caption.bold()).foregroundStyle(Brand.green)
            }
            .padding(.horizontal).padding(.top, 10).padding(.bottom, 6)
            .frame(maxWidth: .infinity, alignment: .leading)

            List(Section.allCases, selection: $selection) { s in
                Label(s.rawValue, systemImage: s.icon).tag(s as Section?)
            }
        } detail: {
            Group {
                switch selection ?? .dashboard {
                case .dashboard: DashboardView(monitor: monitor)
                case .storage:   StorageView(monitor: monitor)
                case .battery:   InfoScreen(title: "Батарея",
                                            lines: ["Заряд: \(monitor.batteryPercent)%",
                                                    "Память: \(Int(monitor.memoryUsedPercent))% занято",
                                                    "ОЗУ: \(monitor.ramTotalGB) ГБ"])
                case .cleanup:   CleanupView()
                case .photos:    PhotoDuplicatesView()
                case .contacts:  ContactsDuplicatesView()
                case .tips:      TipsView(monitor: monitor)
                case .about:     AboutScreen()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Brand.bg0)
        }
        .onAppear { monitor.start() }
    }
}

struct InfoScreen: View {
    let title: String
    let lines: [String]
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title).font(.largeTitle.bold()).foregroundStyle(Brand.text)
            ForEach(lines, id: \.self) { l in
                Text(l).foregroundStyle(Brand.muted)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16).background(Brand.glass)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            Spacer()
        }
        .padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

struct AboutScreen: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("🪽 \(Brand.name)").font(.system(size: 34, weight: .bold)).foregroundStyle(Brand.text)
            Text("«\(Brand.slogan)»").font(.title3.bold()).foregroundStyle(Brand.green)
            Text("Создатель: \(Brand.author)").bold().foregroundStyle(Brand.text)
            Text("Версия каркаса \(Brand.version)").foregroundStyle(Brand.muted)
            Text("Экосистема KRYLAN: Mac · iPhone · Android.").foregroundStyle(Brand.muted).padding(.top, 6)
            Spacer()
        }
        .padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}
