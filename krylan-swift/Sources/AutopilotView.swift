// Автопилот — честная iOS-версия фонового стража KRYLAN.
//
// Что делаем В РАМКАХ ПРАВИЛ APPLE:
//  • Фоновая задача BGTaskScheduler по расписанию iOS чистит ТОЛЬКО свой кэш
//    (.cachesDirectory нашего sandbox-контейнера) и делает лёгкий подсчёт того,
//    что пользователь может разобрать (скриншоты / крупные видео).
//  • Если есть что разбирать — присылаем локальное уведомление-напоминание.
//  • Авто-удаление фото/видео НЕ делаем — только с подтверждением пользователя.
//
// iOS не гарантирует регулярный запуск фоновых задач: система решает сама.
// Всё iOS-специфичное — под #if os(iOS). На macOS показываем упрощённый вид.
import SwiftUI
import Photos
#if os(iOS)
import BackgroundTasks
import UserNotifications
#endif

// MARK: - Менеджер Автопилота (общая логика: ключи, расписание, прогон)

@MainActor
final class AutopilotManager: ObservableObject {
    static let shared = AutopilotManager()

    /// Идентификатор фоновой задачи. Должен совпадать с
    /// BGTaskSchedulerPermittedIdentifiers в Info.plist (см. project.yml).
    static let taskID = "com.krylan.app.autopilot.refresh"

    // Ключи UserDefaults.
    private let kEnabled = "krylan.autopilot.enabled"
    private let kLastRun = "krylan.autopilot.lastRun"

    @Published var enabled: Bool {
        didSet { UserDefaults.standard.set(enabled, forKey: kEnabled) }
    }
    @Published var lastRun: Date?
    /// Разрешены ли локальные уведомления (для честного предупреждения в UI).
    @Published var notificationsAuthorized = false
    @Published var notificationsDenied = false

    private init() {
        let d = UserDefaults.standard
        enabled = d.bool(forKey: kEnabled)
        let ts = d.double(forKey: kLastRun)
        lastRun = ts > 0 ? Date(timeIntervalSince1970: ts) : nil
    }

    private func markRun() {
        let now = Date()
        lastRun = now
        UserDefaults.standard.set(now.timeIntervalSince1970, forKey: kLastRun)
    }

    // MARK: Очистка своего кэша (тот же приём, что CacheCleaner/OptimizeEngine)

    /// Чистим только .cachesDirectory нашего контейнера. Чужие файлы недоступны.
    nonisolated static func cleanOwnCache() -> Int64 {
        guard let url = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
        else { return 0 }
        let before = CacheCleaner.dirSize(url)
        let fm = FileManager.default
        if let items = try? fm.contentsOfDirectory(at: url, includingPropertiesForKeys: nil) {
            for it in items { try? fm.removeItem(at: it) }
        }
        let after = CacheCleaner.dirSize(url)
        return max(0, before - after)
    }

    // MARK: Синхронный прогон «Проверить и очистить сейчас» (для кнопки в UI)

    struct QuickResult {
        var cacheFreed: Int64 = 0
        var screenshots = 0
        var largeVideos = 0
        var estReclaim: Int64 = 0
        var photosAuthorized = false
    }

    /// Лёгкий подсчёт медиа к разбору (без удаления): скриншоты + крупные видео.
    /// Только если доступ к фото уже выдан — Автопилот не должен дёргать запросы.
    nonisolated static func lightScan(photosAuthorized: Bool) -> (shots: Int, vids: Int, bytes: Int64) {
        guard photosAuthorized else { return (0, 0, 0) }
        var shots = 0, vids = 0
        var bytes: Int64 = 0

        // Скриншоты.
        let sOpts = PHFetchOptions()
        sOpts.predicate = NSPredicate(format: "(mediaSubtypes & %d) != 0",
                                      PHAssetMediaSubtype.photoScreenshot.rawValue)
        let sFetch = PHAsset.fetchAssets(with: .image, options: sOpts)
        sFetch.enumerateObjects { a, _, _ in
            shots += 1
            bytes += Int64(Double(a.pixelWidth * a.pixelHeight) * 0.3)
        }

        // Крупные (длинные) видео — топ-30 по длительности.
        let vOpts = PHFetchOptions()
        vOpts.sortDescriptors = [NSSortDescriptor(key: "duration", ascending: false)]
        vOpts.fetchLimit = 30
        let vFetch = PHAsset.fetchAssets(with: .video, options: vOpts)
        vFetch.enumerateObjects { a, _, _ in
            vids += 1
            bytes += Int64(a.duration * 750_000)
        }
        return (shots, vids, bytes)
    }

    /// Синхронный (async) прогон для UI-кнопки.
    func runNow() async -> QuickResult {
        var r = QuickResult()
        r.cacheFreed = await Task.detached(priority: .userInitiated) {
            Self.cleanOwnCache()
        }.value

        let authorized = Self.photosAuthorizedNow()
        r.photosAuthorized = authorized
        let scan = await Task.detached(priority: .userInitiated) {
            Self.lightScan(photosAuthorized: authorized)
        }.value
        r.screenshots = scan.shots
        r.largeVideos = scan.vids
        r.estReclaim = scan.bytes

        markRun()
        return r
    }

    nonisolated static func photosAuthorizedNow() -> Bool {
        let st = PHPhotoLibrary.authorizationStatus(for: .readWrite)
        return st == .authorized || st == .limited
    }

    // MARK: Уведомления

    #if os(iOS)
    /// Запросить разрешение на уведомления (при включении Автопилота).
    func requestNotifications() async {
        let center = UNUserNotificationCenter.current()
        let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        await refreshNotificationStatus()
        if !granted { notificationsDenied = true }
    }

    func refreshNotificationStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        notificationsAuthorized = settings.authorizationStatus == .authorized
            || settings.authorizationStatus == .provisional
        notificationsDenied = settings.authorizationStatus == .denied
    }
    #else
    func requestNotifications() async {}
    func refreshNotificationStatus() async {}
    #endif

    /// Человекочитаемый размер (nonisolated — для фонового контекста).
    nonisolated static func human(_ bytes: Int64) -> String {
        let units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
        var value = Double(bytes)
        var idx = 0
        while value >= 1024 && idx < units.count - 1 { value /= 1024; idx += 1 }
        return idx == 0 ? "\(Int(value)) \(units[idx])" : String(format: "%.1f %@", value, units[idx])
    }

    #if os(iOS)
    /// Локальное напоминание «можно освободить ≈ X».
    nonisolated static func sendReminder(shots: Int, vids: Int, bytes: Int64) {
        let content = UNMutableNotificationContent()
        content.title = "KRYLAN: можно освободить ≈ \(human(bytes))"
        var parts: [String] = []
        if shots > 0 { parts.append("\(shots) скриншотов") }
        if vids > 0 { parts.append("\(vids) видео к разбору") }
        let detail = parts.isEmpty ? "Откройте, чтобы разобрать." : parts.joined(separator: ", ") + ". Откройте, чтобы разобрать."
        content.body = detail
        content.sound = .default

        // Доставить почти сразу (мы уже в фоновом окне задачи).
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        let req = UNNotificationRequest(identifier: "krylan.autopilot.reminder",
                                        content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(req, withCompletionHandler: nil)
    }

    // MARK: Планирование BGTask

    /// Зарегистрировать обработчик задачи (вызывается из @main на launch).
    func registerBackgroundTask() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: Self.taskID, using: nil) { task in
            // Обработчик вызывается системой на любом потоке; работаем как BGAppRefreshTask.
            self.handle(task: task as! BGAppRefreshTask)
        }
    }

    /// Запланировать следующий прогон (через ~4 часа). Безопасно вызывать многократно.
    func scheduleNextRefresh() {
        guard enabled else { return }
        let request = BGAppRefreshTaskRequest(identifier: Self.taskID)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 4 * 60 * 60)
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            // На симуляторе/без entitlement submit может бросить — это не критично.
            #if DEBUG
            print("[Autopilot] schedule failed: \(error)")
            #endif
        }
    }

    /// Снять запланированные задачи (при выключении Автопилота).
    func cancelScheduled() {
        BGTaskScheduler.shared.cancel(taskRequestWithIdentifier: Self.taskID)
    }

    /// Обработчик фоновой задачи: с таймбюджетом и expirationHandler.
    private func handle(task: BGAppRefreshTask) {
        // Сразу планируем следующий прогон, чтобы цепочка не прерывалась.
        scheduleNextRefresh()

        let work = Task.detached(priority: .background) {
            // 1) Реальная очистка своего кэша.
            _ = AutopilotManager.cleanOwnCache()

            // 2) Лёгкий подсчёт медиа к разбору (только если доступ уже выдан).
            let authorized = AutopilotManager.photosAuthorizedNow()
            let scan = AutopilotManager.lightScan(photosAuthorized: authorized)

            // 3) Если есть что разбирать — напоминание.
            if scan.shots > 0 || scan.vids > 0 {
                AutopilotManager.sendReminder(shots: scan.shots, vids: scan.vids, bytes: scan.bytes)
            }

            // 4) Сохранить дату последнего прогона.
            await MainActor.run { self.markRun() }
            task.setTaskCompleted(success: true)
        }

        // Таймбюджет: если система отзывает задачу — отменяем работу.
        task.expirationHandler = {
            work.cancel()
            task.setTaskCompleted(success: false)
        }
    }
    #else
    // macOS: фоновые BGTask недоступны — no-op заглушки.
    func registerBackgroundTask() {}
    func scheduleNextRefresh() {}
    func cancelScheduled() {}
    #endif
}

// MARK: - Экран «Автопилот»

struct AutopilotView: View {
    @StateObject private var ap = AutopilotManager.shared
    @State private var running = false
    @State private var lastResult: AutopilotManager.QuickResult?

    var body: some View {
        ZStack {
            StarfieldView()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    PageHeader(title: "Автопилот")

                    headerCard
                    toggleCard
                    notificationsWarning
                    runNowCard
                    if let r = lastResult { resultCard(r) }
                    honestNote
                }
                .padding(16)
                .frame(maxWidth: 620, alignment: .leading)
                .frame(maxWidth: .infinity)
            }
        }
        .background(Brand.bg0.ignoresSafeArea())
        .task { await ap.refreshNotificationStatus() }
    }

    // Шапка с иконкой и пояснением.
    private var headerCard: some View {
        HStack(spacing: 14) {
            Image(systemName: "bolt.badge.automatic")
                .font(.system(size: 34, weight: .semibold))
                .foregroundStyle(Brand.green)
            VStack(alignment: .leading, spacing: 4) {
                Text("Фоновый страж").font(.title3.bold()).foregroundStyle(Brand.text)
                Text("Чистит свой кэш и напоминает, что можно разобрать")
                    .font(.caption).foregroundStyle(Brand.muted)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(card)
    }

    // Тумблер + статус.
    private var toggleCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle(isOn: Binding(
                get: { ap.enabled },
                set: { newValue in onToggle(newValue) }
            )) {
                Text("Включить Автопилот").font(.body.weight(.semibold)).foregroundStyle(Brand.text)
            }
            .tint(Brand.green)

            HStack(spacing: 8) {
                Circle().fill(ap.enabled ? Brand.green : Brand.muted).frame(width: 8, height: 8)
                Text(ap.enabled ? "Включён" : "Выключен")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(ap.enabled ? Brand.green : Brand.muted)
            }

            Text(lastRunText)
                .font(.caption).foregroundStyle(Brand.muted)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(card)
    }

    private var lastRunText: String {
        guard let d = ap.lastRun else { return "Ещё не отрабатывал" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "ru_RU")
        f.dateFormat = "d MMM, HH:mm"
        return "Последний прогон: \(f.string(from: d))"
    }

    // Предупреждение, если уведомления запрещены.
    @ViewBuilder private var notificationsWarning: some View {
        if ap.enabled && ap.notificationsDenied {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Image(systemName: "bell.slash.fill").foregroundStyle(Brand.yellow)
                    Text("Уведомления выключены").font(.subheadline.bold()).foregroundStyle(Brand.text)
                }
                Text("Напоминания о том, что можно разобрать, не придут. Включите уведомления в настройках.")
                    .font(.caption).foregroundStyle(Brand.muted)
                Button {
                    #if os(iOS)
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                    #endif
                } label: {
                    Text("Открыть настройки")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Brand.bg0)
                        .padding(.horizontal, 14).padding(.vertical, 8)
                        .background(Capsule().fill(Brand.yellow))
                }
                .buttonStyle(.plain)
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Brand.yellow.opacity(0.4), lineWidth: 1))
        }
    }

    // Кнопка «Проверить и очистить сейчас».
    private var runNowCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                Task { await runNow() }
            } label: {
                HStack(spacing: 10) {
                    if running {
                        ProgressView().tint(Brand.bg0)
                    } else {
                        Image(systemName: "bolt.fill")
                    }
                    Text(running ? "Проверяю…" : "Проверить и очистить сейчас")
                        .font(.body.weight(.bold))
                }
                .foregroundStyle(Brand.bg0)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Capsule().fill(Brand.green))
            }
            .buttonStyle(.plain)
            .disabled(running)

            Text("Очистит свой кэш и пересчитает, что можно разобрать.")
                .font(.caption).foregroundStyle(Brand.muted)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(card)
    }

    // Карточка с результатом последнего ручного прогона.
    private func resultCard(_ r: AutopilotManager.QuickResult) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Готово").font(.headline).foregroundStyle(Brand.green)
            row("Кэш очищен", OptimizeEngine.human(r.cacheFreed), Brand.cyan)
            if r.photosAuthorized {
                row("Скриншотов", "\(r.screenshots)", Brand.text)
                row("Видео к разбору", "\(r.largeVideos)", Brand.text)
                row("Можно освободить ≈", OptimizeEngine.human(r.estReclaim), Brand.green)
            } else {
                Text("Доступ к медиатеке не выдан — медиа не считали. Откройте «Фото», чтобы разобрать.")
                    .font(.caption).foregroundStyle(Brand.muted)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(card)
    }

    private func row(_ title: String, _ value: String, _ color: Color) -> some View {
        HStack {
            Text(title).font(.subheadline).foregroundStyle(Brand.muted)
            Spacer()
            Text(value).font(.subheadline.weight(.bold)).foregroundStyle(color)
        }
    }

    // Честное пояснение.
    private var honestNote: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "info.circle").foregroundStyle(Brand.blue)
                Text("Как это работает").font(.subheadline.bold()).foregroundStyle(Brand.text)
            }
            Text("iOS запускает фоновые задачи по своему расписанию (не гарантированно регулярно). KRYLAN в фоне чистит свой кэш и пришлёт напоминание, что можно разобрать. Авто-удаление фото/видео невозможно — только с вашим подтверждением.")
                .font(.caption).foregroundStyle(Brand.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass.opacity(0.6)))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Brand.blue.opacity(0.18), lineWidth: 1))
    }

    private var card: some View {
        RoundedRectangle(cornerRadius: 16).fill(Brand.glass)
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(Brand.green.opacity(0.18), lineWidth: 1))
    }

    // MARK: Действия

    private func onToggle(_ newValue: Bool) {
        ap.enabled = newValue
        #if os(iOS)
        if newValue {
            Task {
                await ap.requestNotifications()
                ap.scheduleNextRefresh()
            }
        } else {
            ap.cancelScheduled()
        }
        #endif
    }

    private func runNow() async {
        running = true
        let r = await ap.runNow()
        lastResult = r
        running = false
    }
}
