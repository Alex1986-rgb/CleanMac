// Крупные видео (PhotoKit): топ по длительности/разрешению, удаление по одному.
// Точный размер файла PhotoKit публично не отдаёт — сортируем по длительности (честный прокси).
import SwiftUI
import Photos

@MainActor
final class VideoScanner: ObservableObject {
    @Published var videos: [PHAsset] = []
    @Published var status = "Готово к сканированию"
    @Published var scanning = false

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
        status = "Сканирую медиатеку…"
        // Сортировка всей медиатеки по длительности — вне главного потока, чтобы не блокировать UI.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "duration", ascending: false)]
            opts.fetchLimit = 50
            let fetch = PHAsset.fetchAssets(with: .video, options: opts)
            var arr: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in arr.append(a) }
            await MainActor.run {
                self.videos = arr
                self.scanning = false
                self.status = arr.isEmpty ? "Видео не найдено" : "Самых длинных видео: \(arr.count)"
            }
        }
    }

    func delete(_ a: PHAsset) {
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets([a] as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.videos.removeAll { $0.localIdentifier == a.localIdentifier }
                self.status = "Перенесено в «Недавно удалённые»"
            }
        }
    }
}

struct LargeVideosView: View {
    @StateObject private var scanner = VideoScanner()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Видео")
                Text("Длинные видео — главные потребители места. Топ-50 по длительности.")
                    .font(.callout).foregroundStyle(Brand.muted)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                }

                ForEach(scanner.videos, id: \.localIdentifier) { v in
                    HStack(spacing: 12) {
                        AssetThumb(asset: v)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(Self.fmtDuration(v.duration))
                                .font(.headline).foregroundStyle(Brand.text)
                            Text("\(v.pixelWidth)×\(v.pixelHeight)")
                                .font(.caption).foregroundStyle(Brand.muted)
                            if let d = v.creationDate {
                                Text(d.formatted(date: .abbreviated, time: .omitted))
                                    .font(.caption2).foregroundStyle(Brand.muted)
                            }
                        }
                        Spacer(minLength: 0)
                        Button { scanner.delete(v) } label: {
                            Text("Удалить").font(.caption.bold()).foregroundStyle(Brand.red)
                        }.buttonStyle(.plain)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(StarfieldView())
    }

    static func fmtDuration(_ s: TimeInterval) -> String {
        let t = Int(s)
        return t >= 3600 ? String(format: "%d:%02d:%02d", t/3600, t%3600/60, t%60)
                         : String(format: "%d:%02d", t/60, t%60)
    }
}
