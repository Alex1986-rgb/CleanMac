// Фото-дубликаты (PhotoKit): группы с миниатюрами + удаление лишних
// в системный альбом «Недавно удалённые» (восстановимо 30 дней).
import SwiftUI
import Photos

#if canImport(UIKit)
import UIKit
#else
import AppKit
#endif

struct DupGroup: Identifiable {
    let id = UUID()
    var assets: [PHAsset]
}

enum PhotoScanMode: String, CaseIterable, Identifiable {
    case exact  = "Дубли"
    case series = "Серии"
    var id: String { rawValue }
}

@MainActor
final class PhotoScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var groups: [DupGroup] = []
    @Published var scanning = false
    @Published var mode: PhotoScanMode = .exact

    var extraCount: Int { groups.reduce(0) { $0 + $1.assets.count - 1 } }

    func scan() {
        status = "Запрос доступа к фото…"
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] st in
            Task { @MainActor in
                guard let self else { return }
                guard st == .authorized || st == .limited else {
                    self.status = "Нет доступа к медиатеке"; return
                }
                self.mode == .exact ? self.runExact() : self.runSeries()
            }
        }
    }

    private func runExact() {
        scanning = true
        status = "Сканирую медиатеку…"
        let assets = PHAsset.fetchAssets(with: .image, options: nil)
        // Кандидаты в дубликаты: совпадают размеры и дата съёмки (упрощённая эвристика).
        var buckets: [String: [PHAsset]] = [:]
        assets.enumerateObjects { a, _, _ in
            let key = "\(a.pixelWidth)x\(a.pixelHeight)-\(Int(a.creationDate?.timeIntervalSince1970 ?? 0))"
            buckets[key, default: []].append(a)
        }
        groups = buckets.values.filter { $0.count > 1 }
            .map { DupGroup(assets: $0) }
            .sorted { $0.assets.count > $1.assets.count }
        scanning = false
        status = groups.isEmpty ? "Дубликатов не найдено"
                                : "Похожих групп: \(groups.count), лишних снимков: \(extraCount)"
    }

    /// Серии: кадры подряд с паузой ≤10 с и одинаковым разрешением, от 3 штук.
    private func runSeries() {
        scanning = true
        status = "Ищу серии снимков…"
        let opts = PHFetchOptions()
        opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: true)]
        let assets = PHAsset.fetchAssets(with: .image, options: opts)
        var all: [PHAsset] = []
        assets.enumerateObjects { a, _, _ in all.append(a) }
        var found: [[PHAsset]] = []
        var cur: [PHAsset] = []
        for a in all {
            if let last = cur.last, let d1 = last.creationDate, let d2 = a.creationDate,
               d2.timeIntervalSince(d1) <= 10,
               a.pixelWidth == last.pixelWidth, a.pixelHeight == last.pixelHeight {
                cur.append(a)
            } else {
                if cur.count >= 3 { found.append(cur) }
                cur = [a]
            }
        }
        if cur.count >= 3 { found.append(cur) }
        groups = found.map { DupGroup(assets: $0) }
            .sorted { $0.assets.count > $1.assets.count }
        scanning = false
        status = groups.isEmpty ? "Серий не найдено"
                                : "Серий: \(groups.count), лишних кадров: \(extraCount)"
    }

    /// Удаляет все снимки группы кроме первого — через системное подтверждение.
    func deleteExtras(in group: DupGroup) {
        let extras = Array(group.assets.dropFirst())
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(extras as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    self.groups.removeAll { $0.id == group.id }
                    self.status = "Перенесено в «Недавно удалённые» (хранится 30 дней)"
                }
            }
        }
    }
}

struct PhotoDuplicatesView: View {
    @StateObject private var scanner = PhotoScanner()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Поиск похожих фото по размеру и дате (PhotoKit). Удалённое попадает в «Недавно удалённые».")
                    .font(.callout).foregroundStyle(Brand.muted)

                Picker("Режим", selection: $scanner.mode) {
                    ForEach(PhotoScanMode.allCases) { m in Text(m.rawValue).tag(m) }
                }
                .pickerStyle(.segmented)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                }

                ForEach(scanner.groups) { group in
                    VStack(alignment: .leading, spacing: 10) {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(Array(group.assets.prefix(8).enumerated()), id: \.offset) { _, asset in
                                    AssetThumb(asset: asset)
                                }
                            }
                        }
                        HStack {
                            Text("\(group.assets.count) похожих снимка")
                                .font(.caption.bold()).foregroundStyle(Brand.muted)
                            Spacer()
                            Button { scanner.deleteExtras(in: group) } label: {
                                Text("Удалить лишние (\(group.assets.count - 1))")
                                    .font(.caption.bold()).foregroundStyle(Brand.red)
                            }.buttonStyle(.plain)
                        }
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(Brand.bg0)
    }
}

/// Миниатюра PHAsset (общая для iOS/macOS).
struct AssetThumb: View {
    let asset: PHAsset
    @State private var image: Image?

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10).fill(Brand.track)
            if let image {
                image.resizable().scaledToFill()
            }
        }
        .frame(width: 72, height: 72)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .onAppear(perform: load)
    }

    private func load() {
        let opts = PHImageRequestOptions()
        opts.isNetworkAccessAllowed = true
        opts.deliveryMode = .opportunistic
        PHImageManager.default().requestImage(
            for: asset, targetSize: CGSize(width: 144, height: 144),
            contentMode: .aspectFill, options: opts
        ) { img, _ in
            #if canImport(UIKit)
            if let img { image = Image(uiImage: img) }
            #else
            if let img { image = Image(nsImage: img) }
            #endif
        }
    }
}
