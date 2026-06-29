// One-tap «Оптимизировать»: безопасная очистка + быстрые сканы (iOS sandbox).
// Чистим только СВОЙ кэш. Медиа/контакты — НЕ удаляем, только находим к разбору.
import SwiftUI
import Photos
import Contacts

/// 5 верхнеуровневых вкладок iOS. Каждая группирует один или несколько разделов (Section).
enum Tab: String, CaseIterable, Identifiable {
    case dashboard = "Дашборд"
    case storage   = "Хранилище"
    case media     = "Фото"
    case system    = "Система"
    case more      = "Ещё"
    var id: String { rawValue }

    var icon: String {
        switch self {
        case .dashboard: return "gauge.with.dots.needle.67percent"
        case .storage:   return "internaldrive"
        case .media:     return "photo.on.rectangle.angled"
        case .system:    return "gearshape.2"
        case .more:      return "ellipsis.circle"
        }
    }
}

extension Section {
    /// К какой верхнеуровневой вкладке iOS относится раздел.
    var tab: Tab {
        switch self {
        case .dashboard:                      return .dashboard
        case .storage, .cleanup, .battery:    return .storage
        case .review, .photos, .shots, .videos: return .media
        case .autopilot, .contacts, .calendar, .geoprivacy, .tips: return .system
        case .about:                          return .more
        }
    }
}

/// Координатор навигации: позволяет любой вью переключить активную вкладку и
/// при необходимости запушить под-экран (нужно, чтобы карточка результата
/// дашборда вела на «Фото-дубли», «Скриншоты», «Контакты» и т.д.).
@MainActor
final class AppCoordinator: ObservableObject {
    // iOS: выбранная верхнеуровневая вкладка + стек навигации внутри неё.
    @Published var tab: Tab = .dashboard
    @Published var path: [Section] = []
    // macOS: выбранный раздел в NavigationSplitView (длинный список допустим).
    @Published var macSection: Section? = .dashboard

    init() {
        // Стартовый раздел из launch-аргумента -KrylanTab (тестовый хук).
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-KrylanTab"), i + 1 < args.count,
           let s = Section.allCases.first(where: { $0.key == args[i + 1] }) {
            go(to: s)
        }
    }

    /// Перейти к разделу: переключить вкладку и, если раздел — под-экран хаба,
    /// запушить его в стек этой вкладки. Работает и для iOS, и для macOS.
    func go(to section: Section) {
        macSection = section
        withAnimation {
            tab = section.tab
            // Корни вкладок (Дашборд, хаб «Хранилище», хаб «Фото», хаб «Система», «Ещё»)
            // открываются без push. Конкретные под-экраны — пушим в стек.
            if section.isSubScreen {
                path = [section]
            } else {
                path = []
            }
        }
    }
}

extension Section {
    /// Под-экран, который нужно пушить в стек вкладки (а не показывать как корень).
    var isSubScreen: Bool {
        switch self {
        case .dashboard, .about: return false   // корни своих вкладок
        default:                 return true    // всё остальное доступно через хаб → push
        }
    }
}

/// Результат одного прогона one-tap оптимизации.
struct OptimizeResult {
    var cacheFreedBytes: Int64 = 0      // реально освобождено из своего кэша
    var photoDupExtras = 0              // лишних снимков в дубль-группах
    var screenshots = 0                 // всего скриншотов
    var largeVideos = 0                 // топ длинных видео
    var livePhotos = 0                  // Live Photos (≈2× места)
    var contactDuplicates = 0           // дубли контактов по имени
    var contactsIncomplete = 0          // неполные контакты
    var estReclaimBytes: Int64 = 0      // грубая оценка освобождаемого места по медиа
    var photosDenied = false           // не дали доступ к медиатеке
    var contactsDenied = false         // не дали доступ к контактам
}

@MainActor
final class OptimizeEngine: ObservableObject {
    enum Phase: Equatable { case idle, running, done }

    @Published var phase: Phase = .idle
    @Published var statusLine = ""
    @Published var progress: Double = 0          // 0…1
    @Published var result = OptimizeResult()

    private var cachesURL: URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
    }

    /// Запуск всей оптимизации одним тапом. Безопасно, без доп.вопросов.
    func run() {
        guard phase != .running else { return }
        phase = .running
        progress = 0
        result = OptimizeResult()

        Task {
            // 1) Реальная очистка собственного кэша (.cachesDirectory).
            statusLine = "Очищаю кэш приложения…"
            progress = 0.1
            // Файловый I/O — вне главного потока, чтобы не подвешивать UI.
            result.cacheFreedBytes = await Task.detached(priority: .userInitiated) {
                Self.cleanOwnCache()
            }.value
            await tick(0.25)

            // 2) Запрашиваем доступ к фото (один раз на все фото-сканы).
            statusLine = "Проверяю доступ к медиатеке…"
            let photoOK = await requestPhotos()
            await tick(0.32)

            if photoOK {
                statusLine = "Ищу дубли фото…"
                let dup = await scanPhotoDuplicates()
                result.photoDupExtras = dup.extras
                result.estReclaimBytes += dup.bytes
                progress = 0.5

                statusLine = "Считаю скриншоты…"
                let shots = await scanScreenshots()
                result.screenshots = shots.count
                result.estReclaimBytes += shots.bytes
                progress = 0.62

                statusLine = "Ищу крупные видео…"
                let vids = await scanLargeVideos()
                result.largeVideos = vids.count
                result.estReclaimBytes += vids.bytes
                progress = 0.74

                statusLine = "Ищу Live Photos…"
                let live = await scanLivePhotos()
                result.livePhotos = live.count
                result.estReclaimBytes += live.bytes
                progress = 0.85
            } else {
                result.photosDenied = true
                progress = 0.85
            }

            // 3) Контакты.
            statusLine = "Проверяю контакты…"
            let contactsOK = await requestContacts()
            if contactsOK {
                let c = await scanContacts()
                result.contactDuplicates = c.dups
                result.contactsIncomplete = c.incomplete
            } else {
                result.contactsDenied = true
            }
            progress = 1.0

            statusLine = "Готово"
            withAnimation { phase = .done }
        }
    }

    func reset() {
        withAnimation { phase = .idle }
        progress = 0
        statusLine = ""
    }

    // MARK: - Кэш (реально, как CacheCleaner.clean)

    nonisolated private static func cleanOwnCache() -> Int64 {
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

    // MARK: - Доступы

    private func requestPhotos() async -> Bool {
        await withCheckedContinuation { cont in
            PHPhotoLibrary.requestAuthorization(for: .readWrite) { st in
                cont.resume(returning: st == .authorized || st == .limited)
            }
        }
    }

    private func requestContacts() async -> Bool {
        await withCheckedContinuation { cont in
            CNContactStore().requestAccess(for: .contacts) { ok, _ in
                cont.resume(returning: ok)
            }
        }
    }

    // MARK: - Быстрые сканы (только подсчёт, без удаления)

    /// Грубая оценка размера фото по мегапикселям (JPEG ≈ 0.3 байта/пиксель — консервативно).
    nonisolated private static func estPhotoBytes(_ a: PHAsset) -> Int64 {
        Int64(Double(a.pixelWidth * a.pixelHeight) * 0.3)
    }

    private func scanPhotoDuplicates() async -> (extras: Int, bytes: Int64) {
        await Task.detached(priority: .userInitiated) {
            let assets = PHAsset.fetchAssets(with: .image, options: nil)
            var buckets: [String: [PHAsset]] = [:]
            assets.enumerateObjects { a, _, _ in
                let key = "\(a.pixelWidth)x\(a.pixelHeight)-\(Int(a.creationDate?.timeIntervalSince1970 ?? 0))"
                buckets[key, default: []].append(a)
            }
            var extras = 0
            var bytes: Int64 = 0
            for group in buckets.values where group.count > 1 {
                extras += group.count - 1
                // место к освобождению — все кроме одного оригинала
                for a in group.dropFirst() { bytes += Self.estPhotoBytes(a) }
            }
            return (extras, bytes)
        }.value
    }

    private func scanScreenshots() async -> (count: Int, bytes: Int64) {
        await Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.predicate = NSPredicate(format: "(mediaSubtypes & %d) != 0",
                                         PHAssetMediaSubtype.photoScreenshot.rawValue)
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var count = 0
            var bytes: Int64 = 0
            fetch.enumerateObjects { a, _, _ in count += 1; bytes += Self.estPhotoBytes(a) }
            return (count, bytes)
        }.value
    }

    private func scanLargeVideos() async -> (count: Int, bytes: Int64) {
        await Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "duration", ascending: false)]
            opts.fetchLimit = 50
            let fetch = PHAsset.fetchAssets(with: .video, options: opts)
            var count = 0
            var bytes: Int64 = 0
            fetch.enumerateObjects { a, _, _ in
                count += 1
                // оценка видео: ~6 Мбит/с H.264 → 0.75 МБ/с
                bytes += Int64(a.duration * 750_000)
            }
            return (count, bytes)
        }.value
    }

    private func scanLivePhotos() async -> (count: Int, bytes: Int64) {
        await Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            opts.fetchLimit = 1000
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var count = 0
            var bytes: Int64 = 0
            fetch.enumerateObjects { a, _, _ in
                if a.mediaSubtypes.contains(.photoLive) {
                    count += 1
                    // у Live видео-трек ≈ равен фото → потенциал ≈ один кадр
                    bytes += Self.estPhotoBytes(a)
                }
            }
            return (count, bytes)
        }.value
    }

    private func scanContacts() async -> (dups: Int, incomplete: Int) {
        await Task.detached(priority: .userInitiated) {
            let store = CNContactStore()
            let keys = [CNContactGivenNameKey, CNContactFamilyNameKey,
                        CNContactPhoneNumbersKey] as [CNKeyDescriptor]
            let req = CNContactFetchRequest(keysToFetch: keys)
            var byName: [String: Int] = [:]
            var incomplete = 0
            do {
                try store.enumerateContacts(with: req) { c, _ in
                    let name = (c.givenName + " " + c.familyName)
                        .trimmingCharacters(in: .whitespaces)
                    let phones = c.phoneNumbers.map { $0.value.stringValue }
                    if (name.isEmpty && !phones.isEmpty) || (!name.isEmpty && phones.isEmpty) {
                        incomplete += 1
                    }
                    guard !name.isEmpty else { return }
                    byName[name.lowercased(), default: 0] += 1
                }
            } catch { /* нет доступа/ошибка — вернём 0 */ }
            let dups = byName.values.filter { $0 > 1 }.count
            return (dups, incomplete)
        }.value
    }

    // MARK: - Утилиты

    private func tick(_ p: Double) async {
        progress = p
        try? await Task.sleep(nanoseconds: 250_000_000)
    }

    /// Человекочитаемый размер (Б/КБ/МБ/ГБ).
    static func human(_ bytes: Int64) -> String { CacheBreakdown.human(bytes) }
}
