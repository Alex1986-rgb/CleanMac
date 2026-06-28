// Общие элементы для экранов разбора медиа (видео, скриншоты, фото-дубли):
//  • кружок-индикатор мультивыбора поверх превью;
//  • честный баннер про «Недавно удалённые» с кнопкой «Открыть Фото»;
//  • открытие приложения «Фото» (sandbox-safe, без приватных API).
// Удаление медиа везде — только через системный диалог PHPhotoLibrary.
import SwiftUI
import Photos
#if canImport(AVKit)
import AVKit
#endif

#if canImport(UIKit)
import UIKit
#endif

// MARK: - Тактильная отдача (только iOS, мягко деградирует на macOS)

/// Лёгкие тактильные сигналы для подтверждения действий.
/// На macOS — no-op (оборачиваем вызовы в #if внутри, чтобы таргет собирался).
enum Haptics {
    /// Лёгкий «тик» при выборе элемента.
    static func selection() {
        #if os(iOS)
        let g = UIImpactFeedbackGenerator(style: .light)
        g.prepare(); g.impactOccurred()
        #endif
    }
    /// Успех — после успешного переноса в «Недавно удалённые».
    static func success() {
        #if os(iOS)
        let g = UINotificationFeedbackGenerator()
        g.prepare(); g.notificationOccurred(.success)
        #endif
    }
}

// MARK: - Честная оценка размера медиа (публичные API, без приватных fileSize)

/// Оценка веса ассетов по публичным метаданным PhotoKit.
/// ВСЁ здесь — ОЦЕНКА (приблизительно), точные байты PhotoKit публично не отдаёт.
enum MediaEstimate {
    /// Байт на пиксель для фото (сжатый JPEG/HEIC, грубая честная оценка).
    static let bytesPerPhotoPixel: Double = 0.25
    /// Множитель для Live Photo (кадр + короткое видео ≈ 2×).
    static let livePhotoMultiplier: Double = 2.0
    /// Коэффициент видео: байт на (пиксель·сек), грубый прокси битрейта H.264.
    static let bytesPerVideoPixelSecond: Double = 0.07

    /// Оценка байт одного фото по площади кадра (Live Photo — ~2×).
    static func photoBytes(_ a: PHAsset) -> Double {
        let pixels = Double(a.pixelWidth) * Double(a.pixelHeight)
        let mult = a.mediaSubtypes.contains(.photoLive) ? livePhotoMultiplier : 1.0
        return pixels * bytesPerPhotoPixel * mult
    }

    /// Оценка байт одного видео (длительность × площадь кадра × коэффициент).
    static func videoBytes(_ a: PHAsset) -> Double {
        Double(a.pixelWidth) * Double(a.pixelHeight) * a.duration * bytesPerVideoPixelSecond
    }

    /// Авто-оценка байт по типу ассета.
    static func bytes(_ a: PHAsset) -> Double {
        a.mediaType == .video ? videoBytes(a) : photoBytes(a)
    }

    /// Читаемый размер из байт: «≈ 1.2 ГБ» / «≈ 340 МБ».
    static func fmtBytes(_ bytes: Double) -> String {
        let u = ["Б", "КБ", "МБ", "ГБ", "ТБ"]; var v = max(0, bytes); var i = 0
        while v >= 1024 && i < u.count - 1 { v /= 1024; i += 1 }
        return i <= 1 ? "\(Int(v)) \(u[i])" : String(format: "%.1f %@", v, u[i])
    }

    /// Сумма оценки байт для набора ассетов.
    static func totalBytes(_ assets: [PHAsset]) -> Double {
        assets.reduce(0) { $0 + bytes($1) }
    }
}

// MARK: - Доступ к Фото (для авто-скана при открытии)

/// Статус доступа к медиатеке + удобные флаги для авто-скана.
enum PhotoAccess {
    /// Текущий статус (readWrite).
    static var status: PHAuthorizationStatus {
        PHPhotoLibrary.authorizationStatus(for: .readWrite)
    }
    /// Доступ уже выдан (полный или ограниченный) — можно сканировать без запроса.
    static var isAuthorized: Bool {
        let s = status
        return s == .authorized || s == .limited
    }
    /// Решение по доступу ещё не принято — покажем кнопку запроса.
    static var isUndetermined: Bool { status == .notDetermined }
    /// Доступ запрещён/ограничен системно — ведём в Настройки.
    static var isDenied: Bool {
        let s = status
        return s == .denied || s == .restricted
    }
}

/// Понятный экран-заглушка, когда доступа к Фото нет.
/// Кнопка «Разрешить доступ к фото» — запрос авторизации либо переход в Настройки.
struct PhotoPermissionGate: View {
    /// Колбэк после успешной выдачи доступа (запускаем скан).
    var onGranted: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "lock.shield")
                .font(.system(size: 42)).foregroundStyle(Brand.yellow)
            Text("Нужен доступ к Фото")
                .font(.headline).foregroundStyle(Brand.text)
            Text("Чтобы найти, что занимает место, разрешите доступ к медиатеке. KRYLAN ничего не удаляет без вашего подтверждения в системном диалоге.")
                .font(.subheadline).foregroundStyle(Brand.muted)
                .multilineTextAlignment(.center)
            Button {
                if PhotoAccess.isUndetermined {
                    PHPhotoLibrary.requestAuthorization(for: .readWrite) { _ in
                        Task { @MainActor in
                            if PhotoAccess.isAuthorized { onGranted() }
                        }
                    }
                } else {
                    #if os(iOS)
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                    #endif
                }
            } label: {
                Label(PhotoAccess.isUndetermined ? "Разрешить доступ к фото" : "Открыть настройки",
                      systemImage: "photo.badge.plus")
                    .font(.subheadline.bold())
                    .padding(.horizontal, 18).padding(.vertical, 11)
                    .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
            }.buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
        .padding(.horizontal, 16)
    }
}

// PHAsset уже имеет стабильный localIdentifier — используем его как Identifiable,
// чтобы биндить полноэкранный просмотр через `item:`.
extension PHAsset: @retroactive Identifiable {
    public var id: String { localIdentifier }
}

extension View {
    /// Полноэкранный просмотр: на iOS — `.fullScreenCover`, на macOS — `.sheet`
    /// (fullScreenCover на macOS недоступен). Единый вызов для обоих таргетов.
    @ViewBuilder
    func fullScreenCoverCompat<Item: Identifiable, Content: View>(
        item: Binding<Item?>,
        @ViewBuilder content: @escaping (Item) -> Content
    ) -> some View {
        #if os(iOS)
        self.fullScreenCover(item: item, content: content)
        #else
        self.sheet(item: item, content: content)
        #endif
    }
}

// MARK: - Полноэкранный просмотр ассета (по долгому нажатию)

/// Полноэкранный просмотр фото/видео — чтобы не удалить нужное по ошибке.
/// Фото — крупное изображение; видео — AVPlayer (через requestPlayerItem),
/// с фолбэком на крупный кадр + длительность, если плеер недоступен.
struct FullScreenAssetPreview: View {
    let asset: PHAsset
    @Environment(\.dismiss) private var dismiss

    @State private var image: Image?
    #if canImport(AVKit)
    @State private var player: AVPlayer?
    #endif

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            Group {
                if asset.mediaType == .video {
                    videoBody
                } else {
                    photoBody
                }
            }

            VStack {
                HStack {
                    Spacer()
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 30))
                            .foregroundStyle(.white.opacity(0.9))
                            .shadow(radius: 4)
                    }.buttonStyle(.plain).padding(16)
                }
                Spacer()
                caption
            }
        }
        .onAppear(perform: load)
        .onDisappear {
            #if canImport(AVKit)
            // Останавливаем и полностью отпускаем плеер, иначе AVPlayer + item утекают.
            player?.pause()
            player?.replaceCurrentItem(with: nil)
            player = nil
            #endif
        }
    }

    @ViewBuilder private var photoBody: some View {
        if let image {
            image.resizable().scaledToFit().ignoresSafeArea()
        } else {
            ProgressView().tint(.white)
        }
    }

    @ViewBuilder private var videoBody: some View {
        #if canImport(AVKit)
        if let player {
            VideoPlayer(player: player).ignoresSafeArea()
        } else {
            ZStack {
                if let image { image.resizable().scaledToFit() }
                ProgressView().tint(.white)
            }
        }
        #else
        if let image { image.resizable().scaledToFit() }
        #endif
    }

    private var caption: some View {
        VStack(spacing: 4) {
            if asset.mediaType == .video {
                Text("\(asset.pixelWidth)×\(asset.pixelHeight) · \(Self.fmtDuration(asset.duration)) · ≈ \(MediaEstimate.fmtBytes(MediaEstimate.videoBytes(asset)))")
            } else {
                Text("\(asset.pixelWidth)×\(asset.pixelHeight) · ≈ \(MediaEstimate.fmtBytes(MediaEstimate.photoBytes(asset)))")
            }
            if let d = asset.creationDate {
                Text(d.formatted(date: .abbreviated, time: .shortened))
            }
            Text("Оценка размера — приблизительная")
                .foregroundStyle(.white.opacity(0.5))
        }
        .font(.caption.bold())
        .foregroundStyle(.white.opacity(0.85))
        .padding(.vertical, 12).padding(.horizontal, 16)
        .background(.black.opacity(0.35), in: Capsule())
        .padding(.bottom, 28)
    }

    private func load() {
        // Крупное изображение (для фото и как фолбэк-кадр для видео).
        let opts = PHImageRequestOptions()
        opts.isNetworkAccessAllowed = true
        opts.deliveryMode = .highQualityFormat
        let target = CGSize(width: 1600, height: 1600)
        PHImageManager.default().requestImage(for: asset, targetSize: target,
                                              contentMode: .aspectFit, options: opts) { img, _ in
            #if canImport(UIKit)
            if let img { Task { @MainActor in self.image = Image(uiImage: img) } }
            #else
            if let img { Task { @MainActor in self.image = Image(nsImage: img) } }
            #endif
        }

        #if canImport(AVKit)
        if asset.mediaType == .video {
            let vopts = PHVideoRequestOptions()
            vopts.isNetworkAccessAllowed = true
            vopts.deliveryMode = .automatic
            PHImageManager.default().requestPlayerItem(forVideo: asset, options: vopts) { item, _ in
                guard let item else { return }
                Task { @MainActor in self.player = AVPlayer(playerItem: item) }
            }
        }
        #endif
    }

    static func fmtDuration(_ s: TimeInterval) -> String {
        let t = Int(s)
        return t >= 3600 ? String(format: "%d:%02d:%02d", t/3600, t%3600/60, t%60)
                         : String(format: "%d:%02d", t/60, t%60)
    }
}

/// Открыть системное приложение «Фото» (для перехода в «Недавно удалённые»).
/// Конкретный альбом открыть публичного API нет — открываем сами «Фото», это ок.
enum PhotosApp {
    static func open() {
        #if os(iOS)
        if let url = URL(string: "photos-redirect://") {
            UIApplication.shared.open(url)
        }
        #elseif os(macOS)
        if let url = URL(string: "photos://") {
            NSWorkspace.shared.open(url)
        }
        #endif
    }
}

/// Кружок-индикатор выбора в углу превью.
/// Пусто — не выбран; зелёная галочка (checkmark.circle.fill) — выбран.
struct SelectionCircle: View {
    let isSelected: Bool
    var body: some View {
        ZStack {
            Circle()
                .fill(.black.opacity(0.55))
                .frame(width: 22, height: 22)
            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(Brand.green)
                    .background(Circle().fill(.black.opacity(0.85)))
            } else {
                Circle()
                    .strokeBorder(.white.opacity(0.85), lineWidth: 2)
                    .frame(width: 21, height: 21)
            }
        }
        .shadow(color: .black.opacity(0.4), radius: 2, y: 1)
    }
}

/// Честное напоминание: удалённое лишь перенесено в «Недавно удалённые».
/// Реально место освобождается только после очистки этого альбома.
struct RecentlyDeletedBanner: View {
    /// Кол-во только что перенесённых объектов (для текста). 0 — не показываем счётчик.
    var movedCount: Int = 0
    /// Колбэк закрытия баннера.
    var onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(Brand.yellow)
                    .font(.headline)
                VStack(alignment: .leading, spacing: 4) {
                    Text(movedCount > 0
                         ? "Перенесено в «Недавно удалённые»: \(movedCount)"
                         : "Перенесено в «Недавно удалённые»")
                        .font(.subheadline.bold()).foregroundStyle(Brand.text)
                    Text("Место пока НЕ освобождено. Чтобы реально освободить место:\nФото → Альбомы → Недавно удалённые → Выбрать → Удалить.")
                        .font(.caption).foregroundStyle(Brand.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                Button { onClose() } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(Brand.muted)
                }.buttonStyle(.plain)
            }
            Button { PhotosApp.open() } label: {
                Label("Открыть Фото", systemImage: "photo.on.rectangle.angled")
                    .font(.caption.bold())
                    .padding(.horizontal, 14).padding(.vertical, 8)
                    .background(Brand.blue).foregroundStyle(.white)
                    .clipShape(Capsule())
            }.buttonStyle(.plain)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(Brand.yellow.opacity(0.35), lineWidth: 1))
    }
}

/// Нижняя панель действий мультивыбора: «Выбрать все/Снять выбор» + «Удалить выбранные (N)».
struct SelectionActionBar: View {
    let selectedCount: Int
    let totalCount: Int
    /// Доп. подпись (например, оценка освобождаемого размера). Пусто — не показываем.
    var subtitle: String = ""
    let onSelectAll: () -> Void
    let onClear: () -> Void
    let onDelete: () -> Void

    private var allSelected: Bool { selectedCount == totalCount && totalCount > 0 }

    var body: some View {
        VStack(spacing: 10) {
            HStack {
                Button(allSelected ? "Снять выбор" : "Выбрать все") {
                    allSelected ? onClear() : onSelectAll()
                }
                .font(.caption.bold()).foregroundStyle(Brand.blue).buttonStyle(.plain)
                Spacer()
                if !subtitle.isEmpty {
                    Text(subtitle).font(.caption.bold()).foregroundStyle(Brand.muted)
                }
            }
            Button { onDelete() } label: {
                Text("Удалить выбранные (\(selectedCount))").bold()
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(selectedCount > 0 ? Brand.red : Brand.track)
                    .foregroundStyle(selectedCount > 0 ? .white : Brand.muted)
                    .clipShape(Capsule())
            }
            .buttonStyle(.plain)
            .disabled(selectedCount == 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }
}

// MARK: - Оценка разбивки хранилища по категориям (для листа ДИСК)

/// Грубая ОЦЕНКА, сколько занимают Видео / Фото / Скриншоты в медиатеке.
/// Только публичные метаданные PhotoKit (пиксели, длительность) — без точных байт.
/// Считается вне главного потока.
@MainActor
final class StorageBreakdownScanner: ObservableObject {
    @Published var videoBytes: Double = 0
    @Published var photoBytes: Double = 0
    @Published var screenshotBytes: Double = 0
    @Published var videoCount = 0
    @Published var photoCount = 0
    @Published var screenshotCount = 0
    @Published var ready = false
    @Published var running = false

    func loadIfNeeded() {
        guard !ready, !running, PhotoAccess.isAuthorized else { return }
        running = true
        Task.detached(priority: .utility) {
            var vBytes = 0.0, pBytes = 0.0, sBytes = 0.0
            var vCount = 0, pCount = 0, sCount = 0

            // Видео.
            let videos = PHAsset.fetchAssets(with: .video, options: nil)
            videos.enumerateObjects { a, _, _ in
                vBytes += MediaEstimate.videoBytes(a); vCount += 1
            }
            // Фото (скриншоты считаем отдельно, чтобы не дублировать в «Фото»).
            let images = PHAsset.fetchAssets(with: .image, options: nil)
            images.enumerateObjects { a, _, _ in
                let b = MediaEstimate.photoBytes(a)
                if a.mediaSubtypes.contains(.photoScreenshot) {
                    sBytes += b; sCount += 1
                } else {
                    pBytes += b; pCount += 1
                }
            }

            await MainActor.run {
                self.videoBytes = vBytes; self.photoBytes = pBytes; self.screenshotBytes = sBytes
                self.videoCount = vCount; self.photoCount = pCount; self.screenshotCount = sCount
                self.ready = true; self.running = false
            }
        }
    }
}

/// Постоянная мини-подсказка про «Недавно удалённые» + кнопка «Открыть Фото».
struct RecentlyDeletedHint: View {
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "clock.arrow.circlepath")
                .foregroundStyle(Brand.yellow).font(.subheadline)
            VStack(alignment: .leading, spacing: 6) {
                Text("Удалённое лежит в «Недавно удалённые» 30 дней — очистите их, чтобы освободить место.")
                    .font(.caption).foregroundStyle(Brand.muted)
                    .fixedSize(horizontal: false, vertical: true)
                Button { PhotosApp.open() } label: {
                    Label("Открыть Фото", systemImage: "photo.on.rectangle.angled")
                        .font(.caption.bold())
                        .padding(.horizontal, 12).padding(.vertical, 6)
                        .background(Brand.blue).foregroundStyle(.white).clipShape(Capsule())
                }.buttonStyle(.plain)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Brand.yellow.opacity(0.3), lineWidth: 1))
    }
}

/// Аккуратное пустое состояние со значком и текстом.
struct EmptyStateView: View {
    let icon: String
    let title: String
    var subtitle: String = ""
    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 42)).foregroundStyle(Brand.muted)
            Text(title).font(.headline).foregroundStyle(Brand.text)
            if !subtitle.isEmpty {
                Text(subtitle).font(.subheadline).foregroundStyle(Brand.muted)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }
}
