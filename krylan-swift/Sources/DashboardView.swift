// Дашборд KRYLAN — модернизированный дизайн (надёжная раскладка).
import SwiftUI

struct DashboardView: View {
    @ObservedObject var monitor: SystemMonitor
    @EnvironmentObject private var coord: AppCoordinator
    @StateObject private var engine = OptimizeEngine()

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {

                // Подзаголовок (титул показывает нав-бар)
                HStack {
                    Text("Состояние в реальном времени")
                        .font(.subheadline).foregroundStyle(Brand.muted)
                    Spacer(minLength: 0)
                }

                // ✨ Главная кнопка: один тап делает всё безопасное (sandbox iOS).
                Button(action: { engine.run() }) {
                    HStack(spacing: 10) {
                        if engine.phase == .running {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .tint(Color(red: 0.04, green: 0.08, blue: 0.06))
                        } else if engine.phase == .done {
                            Image(systemName: "checkmark.circle.fill").font(.title3.bold())
                        }
                        Text(engine.phase == .running ? "Оптимизирую…"
                             : (engine.phase == .done ? "Оптимизировано" : "✨ Оптимизировать"))
                            .font(.headline)
                    }
                    .foregroundStyle(Color(red: 0.04, green: 0.08, blue: 0.06))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 15)
                    .background(
                        LinearGradient(colors: [Brand.green, Brand.cyan],
                                       startPoint: .leading, endPoint: .trailing)
                    )
                    .clipShape(Capsule())
                    .shadow(color: Brand.green.opacity(0.35), radius: 12, y: 4)
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

                // Фирменный анимированный глобус KRYLAN
                GlobeView()
                    .frame(maxWidth: .infinity)

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
