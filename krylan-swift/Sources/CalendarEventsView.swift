// Календарь (EventKit): находит СТАРЫЕ события (старше выбранного порога) и
// предлагает удалить ВЫБРАННЫЕ пользователем. KRYLAN ничего не удаляет сам —
// только по явному действию (кнопка «Удалить выбранные» + подтверждение).
import SwiftUI
import EventKit

struct OldEvent: Identifiable {
    let id: String           // EKEvent.eventIdentifier
    let title: String
    let date: Date
    let calendar: String
}

@MainActor
final class CalendarScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var events: [OldEvent] = []
    @Published var selected: Set<String> = []
    @Published var scanning = false
    @Published var access: EKAuthorizationStatus = EKEventStore.authorizationStatus(for: .event)

    /// Порог «старости» в днях (по умолчанию 1 год).
    var olderThanDays = 365

    private let store = EKEventStore()

    func scan() {
        status = "Запрос доступа к календарю…"
        Task {
            let granted = await requestAccess()
            self.access = EKEventStore.authorizationStatus(for: .event)
            guard granted else {
                self.status = "Нет доступа к календарю. Разрешите его в Настройках → Конфиденциальность."
                return
            }
            await self.run()
        }
    }

    private func requestAccess() async -> Bool {
        if #available(iOS 17.0, macOS 14.0, *) {
            return (try? await store.requestFullAccessToEvents()) ?? false
        } else {
            return await withCheckedContinuation { cont in
                store.requestAccess(to: .event) { ok, _ in cont.resume(returning: ok) }
            }
        }
    }

    private func run() async {
        scanning = true
        status = "Ищу старые события…"
        let cutoff = Calendar.current.date(byAdding: .day, value: -olderThanDays, to: Date()) ?? Date()
        let store = self.store
        // Перебор событий — вне главного потока.
        let found: [OldEvent] = await Task.detached(priority: .userInitiated) {
            // EventKit ограничивает диапазон одного запроса ~4 годами — идём окнами назад.
            let cal = Calendar.current
            var results: [OldEvent] = []
            var windowEnd = cutoff
            // Самая ранняя разумная граница — 10 лет назад от порога.
            let hardStart = cal.date(byAdding: .year, value: -10, to: cutoff) ?? cutoff
            while windowEnd > hardStart {
                let windowStart = cal.date(byAdding: .year, value: -3, to: windowEnd) ?? hardStart
                let lo = max(windowStart, hardStart)
                let predicate = store.predicateForEvents(withStart: lo, end: windowEnd, calendars: nil)
                let chunk = store.events(matching: predicate)
                for e in chunk where e.startDate != nil && e.startDate < cutoff {
                    guard let id = e.eventIdentifier else { continue }
                    results.append(OldEvent(id: id,
                                            title: e.title?.isEmpty == false ? e.title : "Без названия",
                                            date: e.startDate,
                                            calendar: e.calendar?.title ?? ""))
                }
                windowEnd = lo
            }
            // Уникализируем (повторяющиеся события могут попасть из соседних окон).
            var seen = Set<String>()
            let unique = results.filter { seen.insert($0.id).inserted }
            return unique.sorted { $0.date > $1.date }
        }.value

        self.events = found
        self.selected = []
        self.status = found.isEmpty
            ? "Старых событий не найдено"
            : "Найдено старых событий: \(found.count)"
        self.scanning = false
    }

    func toggle(_ id: String) {
        if selected.contains(id) { selected.remove(id) } else { selected.insert(id) }
    }

    func selectAll() { selected = Set(events.map { $0.id }) }
    func clearSelection() { selected = [] }

    /// Удаление ВЫБРАННЫХ событий — вызывается только по явному действию пользователя.
    func deleteSelected() {
        guard !selected.isEmpty else { return }
        let ids = selected
        let store = self.store
        status = "Удаляю выбранные события…"
        Task.detached(priority: .userInitiated) {
            var removed = 0
            var failed = 0
            for id in ids {
                guard let event = store.event(withIdentifier: id) else { failed += 1; continue }
                do {
                    try store.remove(event, span: .thisEvent, commit: false)
                    removed += 1
                } catch {
                    failed += 1
                }
            }
            do { try store.commit() } catch { /* commit-ошибка отразится в статусе ниже */ }
            await MainActor.run {
                self.events.removeAll { ids.contains($0.id) }
                self.selected = []
                self.status = failed == 0
                    ? "Удалено событий: \(removed)"
                    : "Удалено: \(removed), не удалось: \(failed)"
            }
        }
    }
}

struct CalendarEventsView: View {
    @StateObject private var scanner = CalendarScanner()
    @State private var confirmDelete = false

    private static let df: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ru_RU")
        f.dateFormat = "d MMM yyyy"
        return f
    }()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Старые события (старше 1 года). KRYLAN ничего не удаляет сам — выберите события вручную и подтвердите удаление.")
                    .font(.callout).foregroundStyle(Brand.muted)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if !scanner.events.isEmpty {
                    HStack(spacing: 12) {
                        Button("Выбрать все") { scanner.selectAll() }
                            .buttonStyle(.plain).foregroundStyle(Brand.blue).font(.subheadline.bold())
                        Button("Снять выбор") { scanner.clearSelection() }
                            .buttonStyle(.plain).foregroundStyle(Brand.muted).font(.subheadline.bold())
                        Spacer(minLength: 0)
                        Button { confirmDelete = true } label: {
                            Text("Удалить выбранные (\(scanner.selected.count))").bold()
                                .padding(.horizontal, 16).padding(.vertical, 9)
                                .background(scanner.selected.isEmpty ? Brand.track : Brand.red)
                                .foregroundStyle(scanner.selected.isEmpty ? Brand.muted : .white)
                                .clipShape(Capsule())
                        }.buttonStyle(.plain).disabled(scanner.selected.isEmpty)
                    }
                }

                if scanner.events.isEmpty && !scanner.scanning {
                    Text("Нажмите «Сканировать», чтобы найти старые события.")
                        .font(.callout).foregroundStyle(Brand.muted).padding(.top, 8)
                }

                ForEach(scanner.events) { ev in
                    let isOn = scanner.selected.contains(ev.id)
                    Button { scanner.toggle(ev.id) } label: {
                        HStack(alignment: .top, spacing: 12) {
                            Image(systemName: isOn ? "checkmark.circle.fill" : "circle")
                                .font(.title3).foregroundStyle(isOn ? Brand.green : Brand.muted)
                                .frame(width: 28)
                            Image(systemName: "calendar")
                                .font(.title3).foregroundStyle(Brand.purple)
                                .frame(width: 40, height: 40)
                                .background(Brand.purple.opacity(0.15))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                            VStack(alignment: .leading, spacing: 3) {
                                Text(ev.title).font(.headline).foregroundStyle(Brand.text)
                                    .multilineTextAlignment(.leading)
                                Text(Self.df.string(from: ev.date))
                                    .font(.caption).foregroundStyle(Brand.muted)
                                if !ev.calendar.isEmpty {
                                    Text(ev.calendar).font(.caption2).foregroundStyle(Brand.muted)
                                }
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 16)
                            .fill(isOn ? Brand.green.opacity(0.10) : Brand.glass))
                    }.buttonStyle(.plain)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(StarfieldView())
        .alert("Удалить выбранные события?", isPresented: $confirmDelete) {
            Button("Отмена", role: .cancel) {}
            Button("Удалить", role: .destructive) { scanner.deleteSelected() }
        } message: {
            Text("Будет удалено событий: \(scanner.selected.count). Действие нельзя отменить.")
        }
    }
}
