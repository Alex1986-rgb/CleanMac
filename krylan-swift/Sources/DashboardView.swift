// Дашборд KRYLAN — один экран без скролла (адаптивная HUD-«рубка»).
// Кнопка ✨ Оптимизировать + планета с 6 тапабельными кольцами.
// Прогресс/результат и метрики — компактные .sheet, экран не растягивается.
import SwiftUI
#if os(iOS)
import UIKit
#endif

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor
    @EnvironmentObject private var coord: AppCoordinator
    @StateObject private var engine = OptimizeEngine()

    /// Какая метрика открыта в листе (nil — закрыто).
    @State private var sheet: MetricSheet?
    /// Показ компактного листа прогресса/результата оптимизации.
    @State private var showOptimizeSheet = false

    enum MetricSheet: Identifiable {
        case health, cpu, ram, disk, swap, battery
        var id: Int { hashValue }
    }

    var body: some View {
        GeometryReader { geo in
            let H = geo.size.height
            // Высота кнопки фиксирована, остальное отдаём «рубке».
            let buttonH: CGFloat = 54
            let vSpacing: CGFloat = 14

            VStack(spacing: vSpacing) {
                optimizeButton
                    .frame(height: buttonH)

                // HUD-«рубка» занимает всё оставшееся место — адаптивно.
                hudCockpit
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
            .padding(.bottom, 12)
            .frame(width: geo.size.width, height: H)
        }
        .background(StarfieldView())
        // Лист метрики при тапе на кольцо.
        .sheet(item: $sheet) { which in
            metricSheet(which)
        }
        // Компактный лист прогресса/результата оптимизации.
        .sheet(isPresented: $showOptimizeSheet, onDismiss: { engine.reset() }) {
            OptimizeProgressSheet(engine: engine, coord: coord)
        }
        .onChange(of: engine.phase) { _, phase in
            if phase == .running || phase == .done { showOptimizeSheet = true }
        }
    }

    // MARK: - Кнопка ✨ Оптимизировать (запускает полный прогон, лист — компактно)

    private var optimizeButton: some View {
        Button(action: { engine.run() }) {
            HStack(spacing: 10) {
                if engine.phase == .running {
                    ProgressView()
                        .progressViewStyle(.circular)
                        .tint(Color(red: 0.02, green: 0.05, blue: 0.10))
                } else if engine.phase == .done {
                    Image(systemName: "checkmark.circle.fill").font(.title3.bold())
                }
                Text(engine.phase == .running ? "Оптимизирую…"
                     : (engine.phase == .done ? "Оптимизировано" : "✨ Оптимизировать"))
                    .font(.headline)
            }
            .foregroundStyle(Color(red: 0.02, green: 0.05, blue: 0.10))
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(
                LinearGradient(colors: [Brand.green, Brand.cyan],
                               startPoint: .leading, endPoint: .trailing)
            )
            .clipShape(Capsule())
            .shadow(color: Brand.green.opacity(0.45), radius: 16, y: 4)
        }
        .buttonStyle(.plain)
        .disabled(engine.phase == .running)
    }

    // MARK: - HUD «рубка» (радиальная компоновка, тапабельные кольца)

    /// 6 метрик по углам орбиты + какой лист открывают.
    private var gauges: [(value: Double, label: String, invert: Bool, angle: Double, sheet: MetricSheet)] {
        [
            (monitor.healthScore,             "ЗДОР", false, -120, .health),
            (monitor.cpuUsedPercent,          "CPU",  false,  -60, .cpu),
            (monitor.memoryUsedPercent,       "ОЗУ",  false,    0, .ram),
            (monitor.diskUsedPercent,         "ДИСК", false,   60, .disk),
            (monitor.swapUsedPercent,         "SWAP", false,  120, .swap),
            (Double(monitor.batteryPercent),  "БАТ",  true,   180, .battery),
        ]
    }

    private var hudCockpit: some View {
        GeometryReader { geo in
            let W = geo.size.width
            let H = geo.size.height
            let topInset: CGFloat = min(34, H * 0.10)   // место под часы/интернет/ЭКГ
            let cx = W / 2
            let cy = topInset + (H - topInset) / 2
            // Размер гейджа масштабируется к доступному месту (но в разумных пределах).
            let gaugeSize: CGFloat = max(48, min(64, min(W, H) * 0.20))
            // Орбита: не выходим за края (учитываем половину гейджа + поля).
            let orbit = max(40, min(W / 2, (H - topInset) / 2) - gaugeSize / 2 - 6)
            let planet: CGFloat = min(orbit * 1.6, 150)

            ZStack {
                // Коннекторы от центра к каждому гейджу (светящиеся cyan).
                Canvas { ctx, _ in
                    for g in gauges {
                        let a = g.angle * .pi / 180
                        let p = CGPoint(x: cx + cos(a) * orbit, y: cy + sin(a) * orbit)
                        let inner = CGPoint(x: cx + cos(a) * (planet / 2 * 0.62),
                                            y: cy + sin(a) * (planet / 2 * 0.62))
                        var path = Path(); path.move(to: inner); path.addLine(to: p)
                        ctx.stroke(path, with: .color(Brand.cyan.opacity(0.30)), lineWidth: 3)
                        ctx.stroke(path, with: .color(Brand.cyan.opacity(0.65)), lineWidth: 1)
                        let nr: CGFloat = 2.5
                        ctx.fill(Path(ellipseIn: CGRect(x: inner.x - nr, y: inner.y - nr, width: nr*2, height: nr*2)),
                                 with: .color(Brand.cyan.opacity(0.7)))
                    }
                }

                // Центральная планета + имя устройства.
                VStack(spacing: 2) {
                    GlobeView(height: planet)
                        .frame(width: planet, height: planet)
                    Text(monitor.deviceName)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(Brand.text)
                        .lineLimit(1)
                        .frame(maxWidth: planet * 1.3)
                }
                .position(x: cx, y: cy)

                // 6 орбитальных гейджей — каждое тапабельно (вся область MiniGauge).
                ForEach(Array(gauges.enumerated()), id: \.offset) { _, g in
                    let a = g.angle * .pi / 180
                    MiniGauge(value: g.value, label: g.label, invert: g.invert, size: gaugeSize)
                        .contentShape(Circle())
                        .onTapGesture { sheet = g.sheet }
                        .position(x: cx + cos(a) * orbit, y: cy + sin(a) * orbit)
                }

                // Часы HH:MM сверху.
                TimelineView(.periodic(from: .now, by: 1)) { _ in
                    Text(Self.clock.string(from: Date()))
                        .font(.system(size: 15, weight: .bold, design: .monospaced))
                        .foregroundStyle(Brand.cyan)
                }
                .position(x: cx, y: max(10, topInset * 0.35))

                // Интернет ↓/↑ справа.
                VStack(alignment: .trailing, spacing: 2) {
                    Text("↓ \(monitor.netDownLabel)")
                        .foregroundStyle(Brand.green)
                    Text("↑ \(monitor.netUpLabel)")
                        .foregroundStyle(Brand.blue)
                }
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .position(x: W - 44, y: max(12, topInset * 0.4))

                // Мини-ЭКГ слева.
                ECGView(color: Brand.green, level: monitor.cpuUsedPercent / 100)
                    .frame(width: 72, height: 26)
                    .position(x: 44, y: max(12, topInset * 0.4))
            }
        }
    }

    private static let clock: DateFormatter = {
        let f = DateFormatter(); f.dateFormat = "HH:mm"; return f
    }()

    // MARK: - Листы метрик (по тапу на кольцо)

    @ViewBuilder
    private func metricSheet(_ which: MetricSheet) -> some View {
        switch which {
        case .health:  HealthSheet(monitor: monitor, engine: engine)
        case .cpu:     CPUSheet(monitor: monitor)
        case .ram:     RAMSheet(monitor: monitor)
        case .disk:    DiskSheet(monitor: monitor, coord: coord)
        case .swap:    SwapSheet(monitor: monitor)
        case .battery: BatterySheet(monitor: monitor)
        }
    }
}

// MARK: - Общий каркас компактного navy-листа

/// Контейнер для всех метрик-листов: navy-фон, заголовок, скролл-контент,
/// автоматическая высота (medium/large detents), кнопка закрытия.
struct MetricSheetScaffold<Content: View>: View {
    let icon: String
    let title: String
    let tint: Color
    @ViewBuilder var content: Content
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    content
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Brand.bg0.ignoresSafeArea())
            .navigationTitle(title)
            #if os(iOS)
            .toolbarBackground(Brand.bg0, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Image(systemName: icon).foregroundStyle(tint)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
                    }
                }
            }
            #else
            .toolbar {
                ToolbarItem {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
                    }
                }
            }
            #endif
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .presentationBackground(Brand.bg0)
        .preferredColorScheme(.dark)
    }
}

/// Большая капсульная кнопка-действие в стиле бренда.
struct SheetActionButton: View {
    let title: String
    var icon: String? = nil
    var filled: Bool = true
    var tint: Color = Brand.green
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let icon { Image(systemName: icon).font(.headline) }
                Text(title).font(.headline)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .foregroundStyle(filled ? Color(red: 0.02, green: 0.05, blue: 0.10) : tint)
            .background {
                if filled {
                    LinearGradient(colors: [tint, Brand.cyan],
                                   startPoint: .leading, endPoint: .trailing)
                } else {
                    Brand.glass
                }
            }
            .clipShape(Capsule())
            .overlay(filled ? nil : Capsule().stroke(tint.opacity(0.5), lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

/// Строка «ключ — значение» для листов.
struct MetricRow: View {
    let label: String
    let value: String
    var tint: Color = Brand.text
    var body: some View {
        HStack {
            Text(label).font(.subheadline).foregroundStyle(Brand.muted)
            Spacer(minLength: 8)
            Text(value).font(.subheadline.bold().monospacedDigit()).foregroundStyle(tint)
        }
        .padding(.vertical, 10).padding(.horizontal, 14)
        .background(RoundedRectangle(cornerRadius: 12).fill(Brand.glass))
    }
}

/// Кольцо-герой по центру листа.
private struct SheetHeroRing: View {
    let value: Double
    let label: String
    var invert: Bool = false
    var unit: String = "%"
    var body: some View {
        RingGauge(value: value, label: label, invert: invert, size: 120, unit: unit)
            .frame(maxWidth: .infinity)
            .padding(.bottom, 4)
    }
}

// MARK: - ДИСК → «Хранилище»

struct DiskSheet: View {
    @ObservedObject var monitor: SystemMonitor
    let coord: AppCoordinator
    @StateObject private var cleaner = CacheCleaner()
    @Environment(\.dismiss) private var dismiss
    @State private var cleaned = false

    private var usedGB: Int { max(0, monitor.diskTotalGB - monitor.diskFreeGB) }

    var body: some View {
        MetricSheetScaffold(icon: "internaldrive.fill", title: "Хранилище", tint: Brand.blue) {
            SheetHeroRing(value: monitor.diskUsedPercent, label: "ДИСК")

            MetricRow(label: "Занято", value: "\(usedGB) ГБ", tint: Brand.blue)
            MetricRow(label: "Свободно", value: "\(monitor.diskFreeGB) ГБ", tint: Brand.green)
            MetricRow(label: "Всего", value: "\(monitor.diskTotalGB) ГБ")

            Text("Освобождает место — покажем, что удалить.")
                .font(.subheadline).foregroundStyle(Brand.text)

            // Реальная очистка собственного кэша приложения.
            SheetActionButton(title: cleaned ? "Кэш очищен" : "Очистить кэш приложения",
                              icon: cleaned ? "checkmark.circle.fill" : "trash.fill",
                              tint: Brand.green) {
                cleaner.clean()
                cleaned = true
            }
            if !cleaner.sizeText.isEmpty && cleaner.sizeText != "—" {
                Text("Кэш приложения: \(cleaner.sizeText)")
                    .font(.caption).foregroundStyle(Brand.muted)
            }

            Divider().overlay(Brand.track)

            Text("РАЗБОР МЕДИА — реально освобождает диск")
                .font(.caption.bold()).foregroundStyle(Brand.muted)

            reviewLink("camera.viewfinder", "Скриншоты", "Найти и удалить", Brand.blue, .shots)
            reviewLink("photo.on.rectangle.angled", "Дубли фото", "Похожие снимки", Brand.purple, .photos)
            reviewLink("film", "Крупные видео", "Самые тяжёлые ролики", Brand.cyan, .videos)
            reviewLink("livephoto", "Live Photos", "≈2× места на снимок", Brand.green, .photos)

            Text("Медиа KRYLAN не удаляет автоматически — только с вашим подтверждением в системном диалоге.")
                .font(.caption2).foregroundStyle(Brand.muted)
        }
        .onAppear { cleaner.refresh() }
    }

    private func reviewLink(_ icon: String, _ title: String, _ sub: String,
                            _ tint: Color, _ section: Section) -> some View {
        Button {
            dismiss()
            // Дать листу закрыться, затем перейти на экран разбора.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { coord.go(to: section) }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon).foregroundStyle(tint).frame(width: 26)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.subheadline.bold()).foregroundStyle(Brand.text)
                    Text(sub).font(.caption).foregroundStyle(Brand.muted)
                }
                Spacer(minLength: 8)
                Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(Brand.muted)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(tint.opacity(0.25), lineWidth: 1))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

// MARK: - ЗДОРОВЬЕ → разбор + ✨ Оптимизировать

struct HealthSheet: View {
    @ObservedObject var monitor: SystemMonitor
    @ObservedObject var engine: OptimizeEngine
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        MetricSheetScaffold(icon: "heart.fill", title: "Здоровье", tint: Brand.green) {
            SheetHeroRing(value: monitor.healthScore, label: monitor.healthLabel)

            Text("Сводная оценка состояния устройства (\(Int(monitor.healthScore))/100). Учитывает память, диск, загрузку CPU и заряд батареи.")
                .font(.subheadline).foregroundStyle(Brand.text)

            MetricRow(label: "Память занята", value: "\(Int(monitor.memoryUsedPercent))%")
            MetricRow(label: "Диск занят", value: "\(Int(monitor.diskUsedPercent))%")
            MetricRow(label: "Загрузка CPU", value: "\(Int(monitor.cpuUsedPercent))%")
            MetricRow(label: "Батарея", value: "\(monitor.batteryPercent)%")

            SheetActionButton(title: "✨ Оптимизировать", tint: Brand.green) {
                dismiss()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { engine.run() }
            }
            Text("Полный безопасный прогон: очистка кэша приложения и поиск всего, что можно разобрать (дубли, скриншоты, крупные видео, Live Photos, контакты).")
                .font(.caption).foregroundStyle(Brand.muted)
        }
    }
}

// MARK: - CPU (честно, без booster)

struct CPUSheet: View {
    @ObservedObject var monitor: SystemMonitor
    var body: some View {
        MetricSheetScaffold(icon: "cpu", title: "Процессор", tint: Brand.blue) {
            SheetHeroRing(value: monitor.cpuUsedPercent, label: "CPU")
            MetricRow(label: "Текущая загрузка", value: "\(Int(monitor.cpuUsedPercent))%", tint: Brand.blue)
            Text("Это мгновенная загрузка процессора. iOS сам распределяет процессорное время между приложениями и снижает частоту для экономии заряда.")
                .font(.subheadline).foregroundStyle(Brand.text)
            Text("Никакого «ускорения» не существует — это маркетинговый миф. Освободить CPU можно только закрыв ненужные приложения вручную.")
                .font(.caption).foregroundStyle(Brand.muted)
        }
    }
}

// MARK: - ОЗУ (честно, без фейкового освобождения)

struct RAMSheet: View {
    @ObservedObject var monitor: SystemMonitor
    private var usedGB: Double { Double(monitor.ramTotalGB) * monitor.memoryUsedPercent / 100 }
    var body: some View {
        MetricSheetScaffold(icon: "memorychip", title: "Оперативная память", tint: Brand.purple) {
            SheetHeroRing(value: monitor.memoryUsedPercent, label: "ОЗУ")
            MetricRow(label: "Занято", value: String(format: "%.1f ГБ", usedGB), tint: Brand.purple)
            MetricRow(label: "Всего", value: "\(monitor.ramTotalGB) ГБ")
            Text("iOS управляет памятью автоматически: выгружает фоновые приложения, когда память нужна активному.")
                .font(.subheadline).foregroundStyle(Brand.text)
            Text("Кнопки «очистить RAM» в App Store запрещены — они ничего полезного не делают и вредят автономности. Поэтому здесь только честные цифры.")
                .font(.caption).foregroundStyle(Brand.muted)
        }
    }
}

// MARK: - SWAP (инфо)

struct SwapSheet: View {
    @ObservedObject var monitor: SystemMonitor
    var body: some View {
        MetricSheetScaffold(icon: "arrow.left.arrow.right.circle", title: "Подкачка (Swap)", tint: Brand.cyan) {
            SheetHeroRing(value: monitor.swapUsedPercent, label: "SWAP")
            MetricRow(label: "Использовано", value: "\(Int(monitor.swapUsedPercent))%", tint: Brand.cyan)
            Text("Swap — это файл подкачки: система временно переносит часть данных из оперативной памяти на накопитель, когда ОЗУ не хватает.")
                .font(.subheadline).foregroundStyle(Brand.text)
            Text("Высокий swap означает нехватку памяти. Управлять им вручную нельзя — это делает система. Закрытие лишних приложений снижает нагрузку.")
                .font(.caption).foregroundStyle(Brand.muted)
        }
    }
}

// MARK: - БАТАРЕЯ (советы + переход в Настройки)

struct BatterySheet: View {
    @ObservedObject var monitor: SystemMonitor
    var body: some View {
        MetricSheetScaffold(icon: "battery.100", title: "Батарея", tint: Brand.green) {
            SheetHeroRing(value: Double(monitor.batteryPercent), label: "ЗАРЯД", invert: true)
            MetricRow(label: "Текущий заряд", value: "\(monitor.batteryPercent)%",
                      tint: monitor.batteryPercent <= 20 ? Brand.red : Brand.green)

            Text("СОВЕТЫ ПО АВТОНОМНОСТИ").font(.caption.bold()).foregroundStyle(Brand.muted)
            tip("Включите авто-яркость и уменьшите время до автоблокировки.")
            tip("Отключите фоновое обновление для редко используемых приложений.")
            tip("При сильном нагреве снимите чехол и избегайте зарядки на жаре.")
            tip("Режим энергосбережения продлевает работу при низком заряде.")

            #if os(iOS)
            SheetActionButton(title: "Открыть настройки батареи",
                              icon: "gearshape.fill", filled: false, tint: Brand.green) {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            #endif
        }
    }

    private func tip(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Circle().fill(Brand.green).frame(width: 8, height: 8).padding(.top, 6)
            Text(text).font(.subheadline).foregroundStyle(Brand.text)
            Spacer(minLength: 0)
        }
    }
}

// MARK: - Компактный лист прогресса/результата оптимизации

struct OptimizeProgressSheet: View {
    @ObservedObject var engine: OptimizeEngine
    let coord: AppCoordinator
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        MetricSheetScaffold(icon: "sparkles", title: "Оптимизация", tint: Brand.green) {
            if engine.phase == .running {
                VStack(alignment: .leading, spacing: 12) {
                    ProgressView(value: engine.progress).tint(Brand.green)
                    Text(engine.statusLine)
                        .font(.subheadline).foregroundStyle(Brand.muted)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
            } else {
                resultBody
            }
        }
    }

    @ViewBuilder
    private var resultBody: some View {
        let r = engine.result

        HStack(spacing: 10) {
            Image(systemName: "trash.fill").foregroundStyle(Brand.green).frame(width: 24)
            Text("Очищено кэша: \(OptimizeEngine.human(r.cacheFreedBytes))")
                .font(.subheadline.bold()).foregroundStyle(Brand.text)
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))

        Text("НАЙДЕНО К РАЗБОРУ").font(.caption.bold()).foregroundStyle(Brand.muted)

        if r.photosDenied {
            Text("Нет доступа к медиатеке — разрешите его, чтобы найти дубли и крупные файлы.")
                .font(.caption).foregroundStyle(Brand.yellow)
        } else {
            reviewRow("photo.on.rectangle.angled", "Дубли фото", "\(r.photoDupExtras) лишних", Brand.purple, r.photoDupExtras > 0, .photos)
            reviewRow("camera.viewfinder", "Скриншоты", "\(r.screenshots)", Brand.blue, r.screenshots > 0, .shots)
            reviewRow("film", "Крупные видео", "\(r.largeVideos)", Brand.cyan, r.largeVideos > 0, .videos)
            reviewRow("livephoto", "Live Photos", "\(r.livePhotos)", Brand.green, r.livePhotos > 0, .photos)
        }

        if r.contactsDenied {
            Text("Нет доступа к контактам — разрешите, чтобы найти дубли и неполные записи.")
                .font(.caption).foregroundStyle(Brand.yellow)
        } else {
            reviewRow("person.2.fill", "Контакты-дубли", "\(r.contactDuplicates)", Brand.blue, r.contactDuplicates > 0, .contacts)
            reviewRow("person.crop.circle.badge.exclamationmark", "Неполные контакты", "\(r.contactsIncomplete)", Brand.yellow, r.contactsIncomplete > 0, .contacts)
        }

        if r.estReclaimBytes > 0 && !r.photosDenied {
            Divider().overlay(Brand.track)
            Text("Можно освободить ещё ~\(OptimizeEngine.human(r.estReclaimBytes)), разобрав найденное вручную.")
                .font(.caption).foregroundStyle(Brand.muted)
        }
        Text("Медиа и контакты KRYLAN не удаляет автоматически — только с вашим подтверждением в системном диалоге.")
            .font(.caption2).foregroundStyle(Brand.muted)
    }

    private func reviewRow(_ icon: String, _ title: String, _ value: String,
                           _ tint: Color, _ enabled: Bool, _ section: Section) -> some View {
        Button {
            if enabled {
                dismiss()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { coord.go(to: section) }
            }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon).foregroundStyle(enabled ? tint : Brand.muted).frame(width: 24)
                Text(title).font(.subheadline).foregroundStyle(enabled ? Brand.text : Brand.muted)
                Spacer(minLength: 8)
                Text(value).font(.subheadline.bold().monospacedDigit())
                    .foregroundStyle(enabled ? tint : Brand.muted)
                if enabled {
                    Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(Brand.muted)
                }
            }
            .padding(.vertical, 8)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
    }
}
