// «Геолокация»: главное — помочь выключить ЖИВУЮ геопозицию (где пользователь сейчас),
// плюс доп-раздел — убрать GPS-геометки из фото (чистые копии).
//
// Честно и в рамках песочницы iOS / политики App Store:
//  • iOS НЕ даёт приложению само выключить геолокацию — только открыть Настройки и подсказать;
//  • CoreLocation используем ТОЛЬКО для чтения статуса доступа (без запроса и фонового слежения);
//  • убираем GPS из фото публичными API — PhotoKit (данные/создание ассетов) + ImageIO;
//  • оригиналы iOS не даёт молча перезаписать — поэтому создаём ЧИСТЫЕ КОПИИ;
//  • ничего не авто-удаляем и не меняем без явного действия пользователя.
import SwiftUI
import Photos
import ImageIO
import CoreLocation
import UniformTypeIdentifiers

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Чтение статуса геолокации (только чтение, без запроса доступа)

/// Честное чтение текущего статуса доступа к геолокации у самого KRYLAN.
/// НИЧЕГО не запрашиваем и не отслеживаем — только читаем authorizationStatus,
/// чтобы не триггерить лишние permission и требования App Store.
enum LocationStatusReader {
    /// Текущий статус доступа к геолокации у приложения.
    static var status: CLAuthorizationStatus {
        CLLocationManager().authorizationStatus
    }

    /// Человеко-понятная подпись статуса.
    static var humanReadable: String {
        switch status {
        case .notDetermined:       return "не запрашивался"
        case .restricted:          return "ограничен системой"
        case .denied:              return "запрещён"
        case .authorizedAlways:    return "разрешён (всегда)"
        case .authorizedWhenInUse: return "разрешён (при использовании)"
        @unknown default:          return "неизвестно"
        }
    }

    /// Доступ к геолокации фактически выдан приложению.
    static var isGranted: Bool {
        switch status {
        case .authorizedAlways, .authorizedWhenInUse: return true
        default: return false
        }
    }
}

// MARK: - Очистка GPS через ImageIO (публичные API)

/// Утилита: убрать GPS-словарь из данных изображения, сохранив остальные свойства.
enum GeoStripper {
    /// Возвращает копию данных изображения без `kCGImagePropertyGPSDictionary`.
    /// Прочие метаданные (ориентация, EXIF без GPS, профиль и т.д.) переносим как есть.
    /// nil — если данные не удалось разобрать (тогда вызывающий код просто пропускает кадр).
    static func stripGPS(from data: Data) -> Data? {
        guard let src = CGImageSourceCreateWithData(data as CFData, nil),
              let uti = CGImageSourceGetType(src) else { return nil }

        let count = CGImageSourceGetCount(src)
        let dst = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(dst, uti, max(count, 1), nil) else {
            return nil
        }

        // Свойства для удаления GPS: пустой словарь -> убрать ключ из метаданных.
        let removeGPS: [CFString: Any] = [
            kCGImagePropertyGPSDictionary: kCFNull as Any
        ]

        for i in 0..<max(count, 1) {
            // Текущие свойства кадра минус GPS.
            var props = (CGImageSourceCopyPropertiesAtIndex(src, i, nil) as? [CFString: Any]) ?? [:]
            props.removeValue(forKey: kCGImagePropertyGPSDictionary)
            // EXIF/TIFF тоже могут таить геоданные — подчищаем GPS-подсловари, если есть.
            props[kCGImagePropertyGPSDictionary] = nil

            var options = props
            // kCFNull в kCGImageDestinationMetadata-стиле гарантированно выкидывает GPS-блок.
            options.merge(removeGPS) { _, new in new }

            CGImageDestinationAddImageFromSource(dest, src, i, options as CFDictionary)
        }

        guard CGImageDestinationFinalize(dest) else { return nil }
        return dst as Data
    }
}

// MARK: - Сканер фото с геометками

/// Находит фото, у которых `PHAsset.location != nil` (есть GPS-геометка),
/// и готовит из выбранных чистые копии без геоданных.
@MainActor
final class GeoPrivacyScanner: ObservableObject {
    @Published var assets: [PHAsset] = []
    @Published var selected = Set<String>()
    @Published var status = "Готово к сканированию"
    @Published var scanning = false
    @Published var didScan = false          // уже сканировали хотя бы раз (для авто-скана)
    @Published var working = false          // идёт подготовка копий (share/save)
    @Published var infoMessage = ""         // honest-сообщение об итоге сохранения

    /// Авто-скан при открытии: только если доступ уже выдан и ещё не сканировали.
    func autoScanIfPossible() {
        guard !didScan, !scanning, PhotoAccess.isAuthorized else { return }
        run()
    }

    /// Скан с запросом доступа (кнопка).
    func scan() {
        status = "Запрос доступа к фото…"
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] st in
            Task { @MainActor in
                guard let self else { return }
                guard st == .authorized || st == .limited else {
                    self.status = "Нет доступа к медиатеке"; return
                }
                self.run()
            }
        }
    }

    private func run() {
        scanning = true
        status = "Ищу фото с геометками…"
        // Тяжёлый перебор медиатеки — вне главного потока.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var arr: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in
                // Геометка хранится в PHAsset.location (публичный API).
                if a.location != nil { arr.append(a) }
            }
            await MainActor.run {
                self.assets = arr
                self.selected = []
                self.scanning = false
                self.didScan = true
                self.status = arr.isEmpty ? "Фото с геометками не найдено" : "Фото с геометками: \(arr.count)"
            }
        }
    }

    func toggle(_ a: PHAsset) {
        if selected.contains(a.localIdentifier) { selected.remove(a.localIdentifier) }
        else { selected.insert(a.localIdentifier) }
    }

    func selectAll() { selected = Set(assets.map(\.localIdentifier)) }
    func clearSelection() { selected.removeAll() }

    var selectedAssets: [PHAsset] {
        assets.filter { selected.contains($0.localIdentifier) }
    }

    // MARK: Получение чистых данных

    /// Запросить полные данные изображения для ассета (с учётом ориентации).
    private func imageData(for asset: PHAsset) async -> Data? {
        await withCheckedContinuation { (cont: CheckedContinuation<Data?, Never>) in
            let opts = PHImageRequestOptions()
            opts.isNetworkAccessAllowed = true
            opts.isSynchronous = false
            opts.deliveryMode = .highQualityFormat
            PHImageManager.default().requestImageDataAndOrientation(for: asset, options: opts) { data, _, _, _ in
                cont.resume(returning: data)
            }
        }
    }

    /// Для выбранных ассетов получить данные и вырезать GPS.
    /// Возвращает массив пар (очищенные данные, исходный ассет) — для имён файлов/UTType.
    func makeCleanData() async -> [(data: Data, asset: PHAsset)] {
        var result: [(Data, PHAsset)] = []
        for asset in selectedAssets {
            guard let raw = await imageData(for: asset) else { continue }
            // Если GPS убрать не удалось — пропускаем кадр (честно: не отдаём «как есть»).
            guard let clean = GeoStripper.stripGPS(from: raw) else { continue }
            result.append((clean, asset))
        }
        return result
    }

    // MARK: Сохранение чистых копий в медиатеку

    /// Сохранить очищенные данные новыми ассетами (PHAssetCreationRequest .photo с data).
    /// Оригиналы не трогаем — это именно копии.
    func saveCleanCopies(_ items: [(data: Data, asset: PHAsset)]) {
        guard !items.isEmpty else {
            infoMessage = "Не удалось подготовить копии."
            return
        }
        let count = items.count
        // Создаём НОВЫЕ ассеты из очищенных данных через addResource(.photo, data:).
        PHPhotoLibrary.shared().performChanges({
            for item in items {
                let creation = PHAssetCreationRequest.forAsset()
                let resOpts = PHAssetResourceCreationOptions()
                creation.addResource(with: .photo, data: item.data, options: resOpts)
            }
        }) { [weak self] ok, err in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    Haptics.success()
                    self.infoMessage = "Сохранено чистых копий: \(count). Это НОВЫЕ фото без геоданных — оригиналы остались как были."
                } else {
                    self.infoMessage = "Не удалось сохранить копии." + (err.map { " (\($0.localizedDescription))" } ?? "")
                }
            }
        }
    }

    // MARK: Запись во временные файлы (для share-листа)

    /// Записать очищенные данные во временные файлы и вернуть их URL.
    func writeTempFiles(_ items: [(data: Data, asset: PHAsset)]) -> [URL] {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("krylan-geoclean", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        var urls: [URL] = []
        for (idx, item) in items.enumerated() {
            let ext = preferredExtension(for: item.data) ?? "jpg"
            let name = "no-geo-\(idx + 1).\(ext)"
            let url = dir.appendingPathComponent(name)
            do {
                try item.data.write(to: url, options: .atomic)
                urls.append(url)
            } catch { continue }
        }
        return urls
    }

    /// Определить расширение по содержимому (HEIC/JPEG/PNG) через ImageIO.
    private func preferredExtension(for data: Data) -> String? {
        guard let src = CGImageSourceCreateWithData(data as CFData, nil),
              let uti = CGImageSourceGetType(src),
              let type = UTType(uti as String) else { return nil }
        return type.preferredFilenameExtension
    }
}

#if os(iOS)
// MARK: - Обёртка UIActivityViewController (только iOS)

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
#endif

// MARK: - Экран

struct GeoPrivacyView: View {
    @StateObject private var scanner = GeoPrivacyScanner()
    @State private var confirmSave = false
    @State private var previewAsset: PHAsset?
    @State private var shareURLs: [URL] = []
    @State private var showShare = false
    // Статус геолокации читаем при появлении и при возврате из Настроек (только чтение).
    @State private var locStatusText = LocationStatusReader.humanReadable
    @State private var locGranted = LocationStatusReader.isGranted
    private let cols = [GridItem(.adaptive(minimum: 76), spacing: 8)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Геолокация")

                // ── ГЛАВНЫЙ БЛОК: выключить живую геопозицию ──
                locationStatusCard
                openSettingsButton
                howToHideSteps
                locationHonestNote

                Divider().background(Brand.track).padding(.vertical, 4)

                // ── ДОП-РАЗДЕЛ: убрать гео из фото ──
                photoSection
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(StarfieldView())
        .task { scanner.autoScanIfPossible() }
        .onAppear { refreshLocationStatus() }
        .fullScreenCoverCompat(item: $previewAsset) { asset in
            FullScreenAssetPreview(asset: asset)
        }
        #if os(iOS)
        .sheet(isPresented: $showShare) {
            ShareSheet(items: shareURLs)
        }
        #endif
        .confirmationDialog("Сохранить копии без геоданных?",
                            isPresented: $confirmSave, titleVisibility: .visible) {
            Button("Сохранить (\(scanner.selected.count))") { runSave() }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("В медиатеку добавятся НОВЫЕ фото без GPS-меток. Оригиналы останутся без изменений — iOS не позволяет молча изменить оригинал.")
        }
    }

    // MARK: ── Главный блок: выключить живую геопозицию ──

    /// Карточка статуса доступа KRYLAN к геолокации (только чтение).
    private var locationStatusCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Image(systemName: locGranted ? "location.fill" : "location.slash.fill")
                    .font(.title2)
                    .foregroundStyle(locGranted ? Brand.yellow : Brand.green)
                    .frame(width: 30)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Службы геолокации")
                        .font(.headline).foregroundStyle(Brand.text)
                    Text("KRYLAN: доступ \(locStatusText)")
                        .font(.subheadline.bold())
                        .foregroundStyle(locGranted ? Brand.yellow : Brand.green)
                }
                Spacer(minLength: 0)
            }
            Text("Это статус геолокации для самого KRYLAN — лишь пример. Общий тумблер и доступ всех приложений — в Настройках iOS.")
                .font(.caption).foregroundStyle(Brand.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Brand.green.opacity(0.18), lineWidth: 1))
    }

    /// Большая кнопка «Открыть настройки геолокации».
    private var openSettingsButton: some View {
        Button { openLocationSettings() } label: {
            Label("Открыть настройки геолокации", systemImage: "gearshape.fill")
                .font(.subheadline.bold())
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Brand.green).foregroundStyle(.black)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }

    /// Пошаговая инструкция «как скрыть живую геопозицию».
    private var howToHideSteps: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Как скрыть геопозицию")
                .font(.headline).foregroundStyle(Brand.text)
            step("1", "location.slash",
                 "Настройки → Конфиденциальность и безопасность → Службы геолокации — выключите полностью или по приложениям.")
            step("2", "antenna.radiowaves.left.and.right",
                 "Там же «Системные службы» → отключите «Важные геопозиции» (история мест) и «Геопредложения».")
            step("3", "camera",
                 "Камера: Настройки → Конфиденциальность → Службы геолокации → Камера → «Никогда» (фото без геометок).")
            step("4", "airplane",
                 "Быстро скрыться: включите «В самолёте» или выключите Wi-Fi/сети.")
            step("5", "photo.on.rectangle.angled",
                 "Поделиться уже снятым фото без места — используйте раздел ниже «Убрать гео из фото».")
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    private func step(_ num: String, _ icon: String, _ text: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle().fill(Brand.track).frame(width: 26, height: 26)
                Text(num).font(.caption.bold()).foregroundStyle(Brand.green)
            }
            VStack(alignment: .leading, spacing: 4) {
                Image(systemName: icon).font(.caption).foregroundStyle(Brand.muted)
                Text(text).font(.caption).foregroundStyle(Brand.text)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    /// Честная плашка: iOS не даёт приложению выключить геолокацию.
    private var locationHonestNote: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(Brand.yellow).font(.subheadline)
            Text("iOS не позволяет приложению выключить геолокацию за вас — это делается в системных настройках. Кнопка открывает их.")
                .font(.caption).foregroundStyle(Brand.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Brand.yellow.opacity(0.3), lineWidth: 1))
    }

    // MARK: ── Доп-раздел: убрать гео из фото ──

    @ViewBuilder private var photoSection: some View {
        Label("Также: убрать гео из фото", systemImage: "photo.badge.checkmark")
            .font(.headline).foregroundStyle(Brand.text)

        Text("KRYLAN находит фото с GPS-геометкой (в EXIF) и делает копии БЕЗ геоданных — поделиться или сохранить в медиатеку. Оригиналы не меняются.")
            .font(.callout).foregroundStyle(Brand.muted)

        HStack(spacing: 12) {
            Button { scanner.scan() } label: {
                Text(scanner.scanning ? "Сканирую…" : "Сканировать фото").bold()
                    .padding(.horizontal, 20).padding(.vertical, 11)
                    .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
            }.buttonStyle(.plain).disabled(scanner.scanning)
            Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
        }

        if !scanner.assets.isEmpty {
            Label("\(scanner.assets.count) фото с геометками", systemImage: "location.slash")
                .font(.subheadline.bold()).foregroundStyle(Brand.text)
        }

        if !scanner.infoMessage.isEmpty {
            infoBanner(scanner.infoMessage)
        }

        if scanner.assets.isEmpty {
            if !scanner.scanning {
                if PhotoAccess.isAuthorized {
                    EmptyStateView(icon: "location.slash",
                                   title: "Фото с геометками нет",
                                   subtitle: "Нажмите «Сканировать фото», чтобы найти фото с GPS-данными в медиатеке.")
                } else {
                    PhotoPermissionGate { scanner.scan() }
                }
            }
        } else {
            actionBar

            LazyVGrid(columns: cols, spacing: 8) {
                ForEach(scanner.assets, id: \.localIdentifier) { asset in
                    AssetThumb(asset: asset,
                               selected: scanner.selected.contains(asset.localIdentifier))
                        .contentShape(Rectangle())
                        .onTapGesture {
                            Haptics.selection()
                            scanner.toggle(asset)
                        }
                        .onLongPressGesture { previewAsset = asset }
                }
            }
            .padding(14)
            .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
        }

        honestNote
    }

    // MARK: Панель действий (выбор + кнопки share/save)

    private var actionBar: some View {
        VStack(spacing: 10) {
            HStack {
                let allSelected = scanner.selected.count == scanner.assets.count && !scanner.assets.isEmpty
                Button(allSelected ? "Снять выбор" : "Выбрать все") {
                    allSelected ? scanner.clearSelection() : scanner.selectAll()
                }
                .font(.caption.bold()).foregroundStyle(Brand.blue).buttonStyle(.plain)
                Spacer()
                Text("Выбрано: \(scanner.selected.count)")
                    .font(.caption.bold()).foregroundStyle(Brand.muted)
            }

            #if os(iOS)
            Button { runShare() } label: {
                shareLabel("Поделиться без геолокации", "square.and.arrow.up")
            }
            .buttonStyle(.plain)
            .disabled(scanner.selected.isEmpty || scanner.working)
            #endif

            Button { confirmSave = true } label: {
                shareLabel("Сохранить копии без геоданных", "square.and.arrow.down",
                           filled: true)
            }
            .buttonStyle(.plain)
            .disabled(scanner.selected.isEmpty || scanner.working)

            if scanner.working {
                HStack(spacing: 8) {
                    ProgressView().controlSize(.small)
                    Text("Готовлю чистые копии…").font(.caption).foregroundStyle(Brand.muted)
                }
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    private func shareLabel(_ title: String, _ icon: String, filled: Bool = false) -> some View {
        Label(title, systemImage: icon)
            .font(.subheadline.bold())
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(enabledBg(filled))
            .foregroundStyle(scanner.selected.isEmpty ? Brand.muted : (filled ? .black : .white))
            .clipShape(Capsule())
    }

    private func enabledBg(_ filled: Bool) -> Color {
        if scanner.selected.isEmpty { return Brand.track }
        return filled ? Brand.green : Brand.blue
    }

    private func infoBanner(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "checkmark.seal.fill").foregroundStyle(Brand.green)
            Text(text).font(.caption).foregroundStyle(Brand.text)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
            Button { scanner.infoMessage = "" } label: {
                Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
            }.buttonStyle(.plain)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Brand.green.opacity(0.3), lineWidth: 1))
    }

    private var honestNote: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(Brand.yellow).font(.subheadline)
            Text("Оригиналы сохраняют геоданные — создаём чистые копии для отправки или хранения. iOS не позволяет молча изменить оригинал.")
                .font(.caption).foregroundStyle(Brand.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Brand.yellow.opacity(0.3), lineWidth: 1))
    }

    // MARK: Действия

    /// Перечитать статус геолокации (после возврата из Настроек он может смениться).
    private func refreshLocationStatus() {
        locStatusText = LocationStatusReader.humanReadable
        locGranted = LocationStatusReader.isGranted
    }

    /// Открыть настройки приложения — самый надёжный публичный путь.
    /// Приватные App-Prefs URL НЕ используем (за них бан в App Store).
    private func openLocationSettings() {
        #if os(iOS)
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
        #endif
    }

    #if os(iOS)
    private func runShare() {
        guard !scanner.selected.isEmpty else { return }
        scanner.working = true
        Task {
            let items = await scanner.makeCleanData()
            let urls = scanner.writeTempFiles(items)
            await MainActor.run {
                scanner.working = false
                guard !urls.isEmpty else {
                    scanner.infoMessage = "Не удалось подготовить файлы для отправки."
                    return
                }
                shareURLs = urls
                showShare = true
            }
        }
    }
    #endif

    private func runSave() {
        guard !scanner.selected.isEmpty else { return }
        scanner.working = true
        Task {
            let items = await scanner.makeCleanData()
            await MainActor.run {
                scanner.working = false
                scanner.saveCleanCopies(items)
            }
        }
    }
}
