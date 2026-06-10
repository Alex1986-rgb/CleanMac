// Навигация KRYLAN: вкладки (TabView) на iOS, NavigationSplitView на macOS.
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
    /// Латинский ключ для launch-аргумента -KrylanTab (тестовый хук).
    var key: String {
        switch self {
        case .dashboard: return "dashboard"
        case .storage:   return "storage"
        case .battery:   return "battery"
        case .cleanup:   return "cleanup"
        case .photos:    return "photos"
        case .contacts:  return "contacts"
        case .tips:      return "tips"
        case .about:     return "about"
        }
    }
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
        content.onAppear { monitor.start() }
    }

    @ViewBuilder private func screen(_ s: Section) -> some View {
        switch s {
        case .dashboard: DashboardView(monitor: monitor)
        case .storage:   StorageView(monitor: monitor)
        case .battery:   BatteryView(monitor: monitor)
        case .cleanup:   CleanupView()
        case .photos:    PhotoDuplicatesView()
        case .contacts:  ContactsDuplicatesView()
        case .tips:      TipsView(monitor: monitor)
        case .about:     AboutScreen()
        }
    }

    #if os(iOS)
    @State private var tab: Section = {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-KrylanTab"), i + 1 < args.count,
           let s = Section.allCases.first(where: { $0.key == args[i + 1] }) { return s }
        return .dashboard
    }()

    private var content: some View {
        TabView(selection: $tab) {
            ForEach(Section.allCases) { s in
                NavigationStack {
                    screen(s)
                        .navigationTitle(s.rawValue)
                        .navigationBarTitleDisplayMode(.inline)
                }
                .tabItem { Label(s.rawValue, systemImage: s.icon) }
                .tag(s)
            }
        }
        .tint(Brand.green)
        .preferredColorScheme(.dark)   // бренд KRYLAN — тёмная тема
    }
    #else
    private var content: some View {
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
            screen(selection ?? .dashboard)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Brand.bg0)
        }
    }
    #endif
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
        .background(Brand.bg0)
    }
}
