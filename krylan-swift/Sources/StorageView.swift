// Экран хранилища: кольцо свободно/занято + разбор медиатеки по типам (PhotoKit).
import SwiftUI
import Photos
#if os(iOS)
import UIKit
#else
import AppKit
#endif

/// Категория медиа для карточек «Что занимает место».
struct MediaCategory: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
    let color: Color
    var count: Int          // -1 = ещё считаем
    let hint: String
}

/// Быстрый подсчёт медиатеки через PhotoKit: только .count, без загрузки картинок.
@MainActor
final class MediaInventory: ObservableObject {
    enum Access { case unknown, granted, limited, denied }

    @Published var access: Access = .unknown
    @Published var loading = false
    @Published var photos = -1
    @Published var videos = -1
    @Published var screenshots = -1
    @Published var live = -1

    var categories: [MediaCategory] {
        [
            MediaCategory(title: "Фото",        icon: "photo.on.rectangle.angled",
                          color: Brand.green,  count: photos,      hint: "Все изображения медиатеки"),
            MediaCategory(title: "Видео",       icon: "video.fill",
                          color: Brand.blue,   count: videos,      hint: "Ролики занимают больше всего места"),
            MediaCategory(title: "Скриншоты",   icon: "camera.viewfinder",
                          color: Brand.cyan,   count: screenshots, hint: "Часто можно удалять смело"),
            MediaCategory(title: "Live Photos", icon: "livephoto",
                          color: Brand.purple, count: live,        hint: "Кадр + видеотрек, ~2× места")
        ]
    }

    /// Запрос доступа и подсчёт (count считается в фоне, @Published обновляется на главном).
    func load() {
        guard access != .granted, access != .limited else { return }
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] st in
            Task { @MainActor in
                guard let self else { return }
                switch st {
                case .authorized: self.access = .granted
                case .limited:    self.access = .limited
                default:          self.access = .denied; return
                }
                self.count()
            }
        }
    }

    private func count() {
        loading = true
        Task.detached(priority: .utility) {
            let images = PHAsset.fetchAssets(with: .image, options: nil).count
            let vids   = PHAsset.fetchAssets(with: .video, options: nil).count

            let shotOpts = PHFetchOptions()
            shotOpts.predicate = NSPredicate(format: "(mediaSubtype & %d) != 0",
                                             PHAssetMediaSubtype.photoScreenshot.rawValue)
            let shots = PHAsset.fetchAssets(with: .image, options: shotOpts).count

            let liveOpts = PHFetchOptions()
            liveOpts.predicate = NSPredicate(format: "(mediaSubtype & %d) != 0",
                                             PHAssetMediaSubtype.photoLive.rawValue)
            let lives = PHAsset.fetchAssets(with: .image, options: liveOpts).count

            await MainActor.run {
                self.photos = images
                self.videos = vids
                self.screenshots = shots
                self.live = lives
                self.loading = false
            }
        }
    }
}

struct StorageView: View {
    @ObservedObject var monitor: SystemMonitor
    @StateObject private var inventory = MediaInventory()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Хранилище")

                ZStack {
                    Circle().stroke(Brand.track, lineWidth: 18)
                    Circle().trim(from: 0, to: monitor.diskUsedPercent / 100)
                        .stroke(Brand.load(monitor.diskUsedPercent),
                                style: StrokeStyle(lineWidth: 18, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                        .animation(.easeOut(duration: 0.5), value: monitor.diskUsedPercent)
                    VStack(spacing: 2) {
                        Text("\(Int(monitor.diskUsedPercent))%")
                            .font(.system(size: 40, weight: .bold)).foregroundStyle(Brand.text)
                        Text("занято").font(.caption).foregroundStyle(Brand.muted)
                    }
                }
                .frame(width: 172, height: 172)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)

                row("Свободно", "\(monitor.diskFreeGB) ГБ", Brand.green)
                row("Занято", "\(max(0, monitor.diskTotalGB - monitor.diskFreeGB)) ГБ", Brand.blue)
                row("Всего", "\(monitor.diskTotalGB) ГБ", Brand.muted)

                mediaSection
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .background(StarfieldView())
        .onAppear { inventory.load() }
    }

    // MARK: «Что занимает место»

    @ViewBuilder
    private var mediaSection: some View {
        Text("Что занимает место")
            .font(.headline).foregroundStyle(Brand.text)
            .padding(.top, 8)

        switch inventory.access {
        case .denied:
            accessCard
        default:
            ForEach(inventory.categories) { cat in
                categoryCard(cat)
            }
            Text(inventory.loading
                 ? "Считаю медиатеку…"
                 : "Подсчёт по медиатеке (PhotoKit). KRYLAN работает в песочнице iOS и видит только фото/видео — системные файлы недоступны.")
                .font(.caption).foregroundStyle(Brand.muted)
                .padding(.top, 2)
        }
    }

    private func categoryCard(_ cat: MediaCategory) -> some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10).fill(cat.color.opacity(0.18))
                    .frame(width: 40, height: 40)
                Image(systemName: cat.icon).foregroundStyle(cat.color).font(.system(size: 18, weight: .semibold))
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(cat.title).font(.subheadline.bold()).foregroundStyle(Brand.text)
                Text(cat.count < 0 ? "считаю…" : "\(cat.count) \(plural(cat.count))")
                    .font(.caption).foregroundStyle(Brand.muted)
            }
            Spacer(minLength: 0)
            Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(Brand.muted)
        }
        .padding(14)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    private var accessCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Image(systemName: "lock.shield").foregroundStyle(Brand.yellow).font(.title2)
                Text("Нужен доступ к медиатеке, чтобы показать разбор по типам.")
                    .font(.subheadline).foregroundStyle(Brand.text)
            }
            Button {
                openSettings()
            } label: {
                Text("Разрешить доступ").bold()
                    .padding(.horizontal, 18).padding(.vertical, 10)
                    .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
            }.buttonStyle(.plain)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    private func openSettings() {
        #if os(iOS)
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
        #else
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Photos") {
            NSWorkspace.shared.open(url)
        }
        #endif
    }

    private func plural(_ n: Int) -> String {
        let n10 = n % 10, n100 = n % 100
        if n10 == 1 && n100 != 11 { return "элемент" }
        if (2...4).contains(n10) && !(12...14).contains(n100) { return "элемента" }
        return "элементов"
    }

    func row(_ title: String, _ value: String, _ color: Color) -> some View {
        HStack(spacing: 10) {
            Circle().fill(color).frame(width: 10, height: 10)
            Text(title).foregroundStyle(Brand.muted)
            Spacer()
            Text(value).bold().foregroundStyle(Brand.text)
        }
        .padding(14)
        .background(Brand.glass)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
