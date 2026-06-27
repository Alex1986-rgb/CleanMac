// Навигация KRYLAN.
// iOS: 5 верхнеуровневых вкладок (TabView) с под-навигацией через хаб-экраны.
// macOS: NavigationSplitView со сгруппированным по секциям списком разделов.
import SwiftUI

/// Разделы приложения. На iOS сгруппированы в 5 вкладок (см. Section.tab),
/// на macOS показываются единым списком, сгруппированным заголовками.
enum Section: String, CaseIterable, Identifiable {
    case dashboard = "Дашборд"
    case storage   = "Хранилище"
    case battery   = "Батарея"
    case cleanup   = "Очистка"
    case review    = "Разбор"
    case photos    = "Фото-дубли"
    case shots     = "Скриншоты"
    case videos    = "Видео"
    case contacts  = "Контакты"
    case calendar  = "Календарь"
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
        case .review:    return "review"
        case .photos:    return "photos"
        case .shots:     return "screenshots"
        case .videos:    return "videos"
        case .contacts:  return "contacts"
        case .calendar:  return "calendar"
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
        case .review:    return "rectangle.stack.badge.minus"
        case .photos:    return "photo.on.rectangle.angled"
        case .shots:     return "camera.viewfinder"
        case .videos:    return "film"
        case .contacts:  return "person.2"
        case .calendar:  return "calendar"
        case .tips:      return "lightbulb"
        case .about:     return "info.circle"
        }
    }
    /// Короткий подзаголовок для карточек хаб-экранов.
    var subtitle: String {
        switch self {
        case .dashboard: return "Состояние устройства"
        case .storage:   return "Что занимает место"
        case .battery:   return "Здоровье аккумулятора"
        case .cleanup:   return "Очистка кэша"
        case .review:    return "Свайп-разбор фотоплёнки"
        case .photos:    return "Похожие снимки в группах"
        case .shots:     return "Найти и удалить скриншоты"
        case .videos:    return "Самые тяжёлые ролики"
        case .contacts:  return "Дубли и неполные записи"
        case .calendar:  return "Старые события"
        case .tips:      return "Советы по устройству"
        case .about:     return "О приложении KRYLAN"
        }
    }
}

struct ContentView: View {
    @StateObject private var monitor = SystemMonitor()
    @StateObject private var coord = AppCoordinator()
    #if os(iOS)
    // Онбординг показывается только при первом запуске (iOS).
    @AppStorage("krylan.onboarded") private var onboarded = false
    #endif

    var body: some View {
        #if os(iOS)
        Group {
            if onboarded {
                content
            } else {
                OnboardingView(onDone: { onboarded = true })
            }
        }
        .environmentObject(coord)
        .onAppear { monitor.start() }
        #else
        content.environmentObject(coord).onAppear { monitor.start() }
        #endif
    }

    /// Корневой экран раздела (без обёрток навигации).
    @ViewBuilder private func screen(_ s: Section) -> some View {
        switch s {
        case .dashboard: DashboardView(monitor: monitor)
        case .storage:   StorageView(monitor: monitor)
        case .battery:   BatteryView(monitor: monitor)
        case .cleanup:   CleanupView()
        case .review:    SwipeReviewView()
        case .photos:    PhotoDuplicatesView()
        case .shots:     ScreenshotsView()
        case .videos:    LargeVideosView()
        case .contacts:  ContactsDuplicatesView()
        case .calendar:  CalendarEventsView()
        case .tips:      TipsView(monitor: monitor)
        case .about:     AboutScreen()
        }
    }

    #if os(iOS)
    /// Корень верхнеуровневой вкладки: дашборд / хаб / одиночный экран.
    @ViewBuilder private func tabRoot(_ t: Tab) -> some View {
        switch t {
        case .dashboard: DashboardView(monitor: monitor)
        case .storage:   StorageHubView(monitor: monitor)
        case .media:     MediaHubView()
        case .system:    SystemHubView(monitor: monitor)
        case .more:      MoreHubView()
        }
    }

    private var content: some View {
        TabView(selection: $coord.tab) {
            ForEach(Tab.allCases) { t in
                NavigationStack(path: pathBinding(for: t)) {
                    tabRoot(t)
                        .navigationTitle(t.rawValue)
                        .navigationBarTitleDisplayMode(.large)
                        // Любой раздел, запушенный как Section, рендерится своим экраном.
                        .navigationDestination(for: Section.self) { s in
                            screen(s)
                                .navigationTitle(s.rawValue)
                                .navigationBarTitleDisplayMode(.inline)
                        }
                }
                .tabItem { Label(t.rawValue, systemImage: t.icon) }
                .tag(t)
            }
        }
        .tint(Brand.green)
        .preferredColorScheme(.dark)   // бренд KRYLAN — тёмная тема
    }

    /// Стек навигации храним только для текущей вкладки; у остальных он пуст.
    /// Этого достаточно: coord.go переключает вкладку и заполняет path для неё.
    private func pathBinding(for t: Tab) -> Binding<[Section]> {
        Binding(
            get: { coord.tab == t ? coord.path : [] },
            set: { if coord.tab == t { coord.path = $0 } }
        )
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

            // Длинный список допустим, но сгруппирован секциями по верхнеуровневым вкладкам.
            List(selection: $coord.macSection) {
                ForEach(Tab.allCases) { group in
                    SwiftUI.Section(group.rawValue) {
                        ForEach(Section.allCases.filter { $0.tab == group }) { s in
                            Label(s.rawValue, systemImage: s.icon).tag(s)
                        }
                    }
                }
            }
        } detail: {
            screen(coord.macSection ?? .dashboard)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Brand.bg0)
        }
    }
    #endif
}

// MARK: - Хаб-экраны (iOS)

#if os(iOS)
/// Переиспользуемая карточка-ссылка на под-экран внутри хаба.
private struct HubLink: View {
    let section: Section
    var body: some View {
        NavigationLink(value: section) {
            HStack(spacing: 14) {
                Image(systemName: section.icon)
                    .font(.title3)
                    .foregroundStyle(Brand.green)
                    .frame(width: 30)
                VStack(alignment: .leading, spacing: 2) {
                    Text(section.rawValue).font(.body.weight(.semibold)).foregroundStyle(Brand.text)
                    Text(section.subtitle).font(.caption).foregroundStyle(Brand.muted)
                }
                Spacer(minLength: 8)
                Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(Brand.muted)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Brand.green.opacity(0.18), lineWidth: 1))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

private struct HubScroll<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        ScrollView {
            VStack(spacing: 12) { content }
                .padding(16)
        }
        .background(Brand.bg0.ignoresSafeArea())
    }
}

/// Вкладка «Хранилище»: Хранилище + Очистка + Батарея.
struct StorageHubView: View {
    @ObservedObject var monitor: SystemMonitor
    var body: some View {
        HubScroll {
            HubLink(section: .storage)
            HubLink(section: .cleanup)
            HubLink(section: .battery)
        }
    }
}

/// Вкладка «Фото»: Разбор + Фото-дубли + Скриншоты + Видео.
struct MediaHubView: View {
    var body: some View {
        HubScroll {
            HubLink(section: .review)
            HubLink(section: .photos)
            HubLink(section: .shots)
            HubLink(section: .videos)
        }
    }
}

/// Вкладка «Система»: Контакты + Календарь + Советы.
struct SystemHubView: View {
    @ObservedObject var monitor: SystemMonitor
    var body: some View {
        HubScroll {
            HubLink(section: .contacts)
            HubLink(section: .calendar)
            HubLink(section: .tips)
        }
    }
}

/// Вкладка «Ещё»: О программе (и всё, что не влезло в основные вкладки).
struct MoreHubView: View {
    var body: some View {
        AboutScreen()
    }
}
#endif

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
