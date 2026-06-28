// Дашборд KRYLAN — модернизированный дизайн (надёжная раскладка).
import SwiftUI

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor
    @EnvironmentObject private var coord: AppCoordinator
    @StateObject private var engine = OptimizeEngine()

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {

                // ✨ Главная кнопка: один тап делает всё безопасное (sandbox iOS).
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
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 15)
                    .background(
                        LinearGradient(colors: [Brand.green, Brand.cyan],
                                       startPoint: .leading, endPoint: .trailing)
                    )
                    .clipShape(Capsule())
                    .shadow(color: Brand.green.opacity(0.45), radius: 16, y: 4)
                }
                .buttonStyle(.plain)
                .disabled(engine.phase == .running)

                // Прогресс/статус во время работы.
                if engine.phase == .running {
                    VStack(spacing: 8) {
                        ProgressView(value: engine.progress)
                            .tint(Brand.green)
                        Text(engine.statusLine)
                            .font(.caption).foregroundStyle(Brand.muted)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(14)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                    .transition(.opacity)
                }

                // Карточка результата one-tap: что очищено + что найдено к разбору.
                if engine.phase == .done {
                    resultCard
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }

                // ★ HUD-«рубка»: радиальная компоновка (планета + 6 гейджей).
                hudCockpit
                    .frame(maxWidth: .infinity)

                // Карточки
                infoCard("internaldrive.fill", "Хранилище",
                         "\(monitor.diskFreeGB) ГБ свободно", "из \(monitor.diskTotalGB) ГБ", Brand.blue)
                infoCard("memorychip.fill", "Оперативная память",
                         "\(Int(monitor.memoryUsedPercent))% занято", "всего \(monitor.ramTotalGB) ГБ", Brand.purple)
                // Карточка «Интернет» с живым спарклайном ↓/↑
                HStack(spacing: 14) {
                    Image(systemName: "network").font(.title2).foregroundStyle(Brand.green)
                        .frame(width: 46, height: 46)
                        .background(RoundedRectangle(cornerRadius: 12).fill(Brand.green.opacity(0.15)))
                    VStack(alignment: .leading, spacing: 2) {
                        Text("ИНТЕРНЕТ").font(.caption.bold()).foregroundStyle(Brand.muted)
                        Text("↓ \(monitor.netDownLabel)   ↑ \(monitor.netUpLabel)")
                            .font(.subheadline.bold()).foregroundStyle(Brand.text)
                    }
                    Spacer(minLength: 8)
                    ZStack {
                        Sparkline(values: monitor.netUpHist, color: Brand.blue)
                        Sparkline(values: monitor.netDownHist, color: Brand.green)
                    }.frame(width: 90, height: 34)
                }
                .padding(16)
                .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))

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
        .background(StarfieldView())
    }

    // MARK: - HUD «рубка» (радиальная компоновка)

    /// 6 метрик по углам орбиты: ЗДОРОВЬЕ −120, CPU −60, ОЗУ 0, ДИСК 60, SWAP 120, БАТАРЕЯ 180.
    private var gauges: [(value: Double, label: String, invert: Bool, angle: Double)] {
        [
            (monitor.healthScore,             "ЗДОР", false, -120),
            (monitor.cpuUsedPercent,          "CPU",  false,  -60),
            (monitor.memoryUsedPercent,       "ОЗУ",  false,    0),
            (monitor.diskUsedPercent,         "ДИСК", false,   60),
            (monitor.swapUsedPercent,         "SWAP", false,  120),
            (Double(monitor.batteryPercent),  "БАТ",  true,   180),
        ]
    }

    private var hudCockpit: some View {
        GeometryReader { geo in
            let W = geo.size.width
            let H = geo.size.height
            let topInset: CGFloat = 34          // место под часы/интернет/ЭКГ
            let cx = W / 2
            let cy = topInset + (H - topInset) / 2
            let gaugeSize: CGFloat = 64
            // Орбита: не выходим за края (учитываем половину гейджа + поля).
            let orbit = min(W / 2, (H - topInset) / 2) - gaugeSize / 2 - 6
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
                        // узелок у центра
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

                // 6 орбитальных гейджей.
                ForEach(Array(gauges.enumerated()), id: \.offset) { _, g in
                    let a = g.angle * .pi / 180
                    MiniGauge(value: g.value, label: g.label, invert: g.invert, size: gaugeSize)
                        .position(x: cx + cos(a) * orbit, y: cy + sin(a) * orbit)
                }

                // Часы HH:MM сверху.
                TimelineView(.periodic(from: .now, by: 1)) { _ in
                    Text(Self.clock.string(from: Date()))
                        .font(.system(size: 15, weight: .bold, design: .monospaced))
                        .foregroundStyle(Brand.cyan)
                }
                .position(x: cx, y: 12)

                // Интернет ↓/↑ справа.
                VStack(alignment: .trailing, spacing: 2) {
                    Text("↓ \(monitor.netDownLabel)")
                        .foregroundStyle(Brand.green)
                    Text("↑ \(monitor.netUpLabel)")
                        .foregroundStyle(Brand.blue)
                }
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .position(x: W - 44, y: 14)

                // Мини-ЭКГ слева.
                ECGView(color: Brand.green, level: monitor.cpuUsedPercent / 100)
                    .frame(width: 72, height: 26)
                    .position(x: 44, y: 14)
            }
        }
        .frame(height: 340)
    }

    private static let clock: DateFormatter = {
        let f = DateFormatter(); f.dateFormat = "HH:mm"; return f
    }()

    // MARK: - Карточка результата one-tap

    @ViewBuilder
    private var resultCard: some View {
        let r = engine.result
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                Image(systemName: "checkmark.seal.fill").foregroundStyle(Brand.green)
                Text("Оптимизация завершена").font(.headline).foregroundStyle(Brand.text)
                Spacer(minLength: 0)
                Button { engine.reset() } label: {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
                }.buttonStyle(.plain)
            }

            // Очищено кэша — реально освобождено.
            HStack(spacing: 10) {
                Image(systemName: "trash.fill").foregroundStyle(Brand.green)
                    .frame(width: 22)
                Text("Очищено кэша: \(OptimizeEngine.human(r.cacheFreedBytes))")
                    .font(.subheadline.bold()).foregroundStyle(Brand.text)
                Spacer(minLength: 0)
            }

            // Найдено к разбору (медиа/контакты НЕ удаляем — только переход).
            Text("Найдено к разбору").font(.caption.bold()).foregroundStyle(Brand.muted)

            if r.photosDenied {
                Text("Нет доступа к медиатеке — разрешите его, чтобы найти дубли и крупные файлы.")
                    .font(.caption).foregroundStyle(Brand.yellow)
            } else {
                reviewRow("photo.on.rectangle.angled", "Дубли фото",
                          "\(r.photoDupExtras) лишних", Brand.purple, r.photoDupExtras > 0, .photos)
                reviewRow("camera.viewfinder", "Скриншоты",
                          "\(r.screenshots)", Brand.blue, r.screenshots > 0, .shots)
                reviewRow("film", "Крупные видео",
                          "\(r.largeVideos)", Brand.cyan, r.largeVideos > 0, .videos)
                reviewRow("livephoto", "Live Photos",
                          "\(r.livePhotos)", Brand.green, r.livePhotos > 0, .photos)
            }

            if r.contactsDenied {
                Text("Нет доступа к контактам — разрешите, чтобы найти дубли и неполные записи.")
                    .font(.caption).foregroundStyle(Brand.yellow)
            } else {
                reviewRow("person.2.fill", "Контакты-дубли",
                          "\(r.contactDuplicates)", Brand.blue, r.contactDuplicates > 0, .contacts)
                reviewRow("person.crop.circle.badge.exclamationmark", "Неполные контакты",
                          "\(r.contactsIncomplete)", Brand.yellow, r.contactsIncomplete > 0, .contacts)
            }

            // Честная оценка потенциала + дисклеймер (без «ускорим телефон»).
            if r.estReclaimBytes > 0 && !r.photosDenied {
                Divider().overlay(Brand.track)
                Text("Можно освободить ещё ~\(OptimizeEngine.human(r.estReclaimBytes)), разобрав найденное вручную.")
                    .font(.caption).foregroundStyle(Brand.muted)
            }
            Text("Медиа и контакты KRYLAN не удаляет автоматически — только с вашим подтверждением в системном диалоге.")
                .font(.caption2).foregroundStyle(Brand.muted)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 18).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 18).stroke(Brand.green.opacity(0.35), lineWidth: 1))
    }

    /// Строка-переход на вкладку разбора. Активна, если есть что разбирать.
    private func reviewRow(_ icon: String, _ title: String, _ value: String,
                           _ tint: Color, _ enabled: Bool, _ section: Section) -> some View {
        Button { if enabled { coord.go(to: section) } } label: {
            HStack(spacing: 12) {
                Image(systemName: icon).foregroundStyle(enabled ? tint : Brand.muted)
                    .frame(width: 24)
                Text(title).font(.subheadline).foregroundStyle(enabled ? Brand.text : Brand.muted)
                Spacer(minLength: 8)
                Text(value).font(.subheadline.bold().monospacedDigit())
                    .foregroundStyle(enabled ? tint : Brand.muted)
                if enabled {
                    Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(Brand.muted)
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
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
