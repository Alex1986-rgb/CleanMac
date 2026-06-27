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
    /// Индекс «лучшего» кадра (кэш). nil пока не вычислен.
    var bestIndex: Int? = nil
}

enum PhotoScanMode: String, CaseIterable, Identifiable {
    case exact  = "Дубли"
    case series = "Серии"
    case blurry = "Размытые"
    case live   = "Live Photos"
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
                switch self.mode {
                case .exact:  self.runExact()
                case .series: self.runSeries()
                case .blurry: self.runBlurry()
                case .live:   self.runLive()
                }
            }
        }
    }

    private func runExact() {
        scanning = true
        status = "Сканирую медиатеку…"
        // Тяжёлый перебор всей медиатеки — вне главного потока, чтобы не блокировать UI.
        Task.detached(priority: .userInitiated) {
            let assets = PHAsset.fetchAssets(with: .image, options: nil)
            // Кандидаты в дубликаты: совпадают размеры и дата съёмки (упрощённая эвристика).
            var buckets: [String: [PHAsset]] = [:]
            assets.enumerateObjects { a, _, _ in
                let key = "\(a.pixelWidth)x\(a.pixelHeight)-\(Int(a.creationDate?.timeIntervalSince1970 ?? 0))"
                buckets[key, default: []].append(a)
            }
            let groups = buckets.values.filter { $0.count > 1 }
                .map { DupGroup(assets: $0) }
                .sorted { $0.assets.count > $1.assets.count }
            await MainActor.run {
                self.groups = groups
                self.scanning = false
                self.status = groups.isEmpty ? "Дубликатов не найдено"
                    : "Похожих групп: \(groups.count), лишних снимков: \(self.extraCount)"
            }
        }
    }

    /// Серии: кадры подряд с паузой ≤10 с и одинаковым разрешением, от 3 штук.
    private func runSeries() {
        scanning = true
        status = "Ищу серии снимков…"
        // Тяжёлый перебор всей медиатеки — вне главного потока.
        Task.detached(priority: .userInitiated) {
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
            let groups = found.map { DupGroup(assets: $0) }
                .sorted { $0.assets.count > $1.assets.count }
            await MainActor.run {
                self.groups = groups
                self.scanning = false
                self.status = groups.isEmpty ? "Серий не найдено"
                    : "Серий: \(groups.count), лишних кадров: \(self.extraCount)"
            }
        }
    }

    /// Размытые: оценка резкости по вариации Лапласиана миниатюры (меньше — размытее).
    /// Кандидаты ниже порога, по 1 кадру в группе. Не удаляем автоматически.
    private func runBlurry() {
        scanning = true
        status = "Анализирую резкость…"
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            opts.fetchLimit = 800   // ограничиваем, чтобы не нагружать устройство
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var assets: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in assets.append(a) }

            let req = PHImageRequestOptions()
            req.isSynchronous = true
            req.deliveryMode = .fastFormat
            req.isNetworkAccessAllowed = false
            req.resizeMode = .fast

            var scored: [(PHAsset, Double)] = []
            for a in assets {
                var cg: CGImage?
                PHImageManager.default().requestImage(
                    for: a, targetSize: CGSize(width: 120, height: 120),
                    contentMode: .aspectFit, options: req
                ) { img, _ in
                    #if canImport(UIKit)
                    cg = img?.cgImage
                    #else
                    if let img { var r = CGRect(origin: .zero, size: img.size)
                        cg = img.cgImage(forProposedRect: &r, context: nil, hints: nil) }
                    #endif
                }
                if let cg, let v = Self.laplacianVariance(cg), v < 55 {
                    scored.append((a, v))
                }
            }
            scored.sort { $0.1 < $1.1 }                 // блюр-кандидаты сначала
            let top = scored.prefix(60).map { DupGroup(assets: [$0.0]) }
            await MainActor.run {
                self.groups = Array(top)
                self.scanning = false
                self.status = top.isEmpty ? "Размытых не найдено"
                                          : "Размытых кадров: \(top.count) (проверьте перед удалением)"
            }
        }
    }

    /// Live Photos: фото со связанным видеотреком — занимают ~2× места (кадр + видео).
    /// Отбираем по mediaSubtypes.photoLive, показываем по 1 кадру (как .blurry).
    private func runLive() {
        scanning = true
        status = "Ищу Live Photos…"
        // Перебор медиатеки — вне главного потока.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            opts.fetchLimit = 1000   // ограничиваем для производительности
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var liveAssets: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in
                if a.mediaSubtypes.contains(.photoLive) { liveAssets.append(a) }
            }
            let groups = liveAssets.prefix(200).map { DupGroup(assets: [$0]) }
            await MainActor.run {
                self.groups = Array(groups)
                self.scanning = false
                self.status = groups.isEmpty ? "Live Photos не найдено"
                    : "Live Photos: \(groups.count) (занимают ~2× места)"
            }
        }
    }

    /// Вариация Лапласиана grayscale-миниатюры (классический показатель резкости).
    nonisolated static func laplacianVariance(_ cg: CGImage) -> Double? {
        let w = 96, h = 96
        var px = [UInt8](repeating: 0, count: w * h * 4)
        let cs = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8,
                                  bytesPerRow: w * 4, space: cs,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
        var gray = [Double](repeating: 0, count: w * h)
        for i in 0..<(w * h) {
            gray[i] = 0.299 * Double(px[i*4]) + 0.587 * Double(px[i*4+1]) + 0.114 * Double(px[i*4+2])
        }
        var lap: [Double] = []; lap.reserveCapacity((w-2) * (h-2))
        for y in 1..<(h-1) {
            for x in 1..<(w-1) {
                let c = gray[y*w+x]
                lap.append(gray[(y-1)*w+x] + gray[(y+1)*w+x] + gray[y*w+x-1] + gray[y*w+x+1] - 4*c)
            }
        }
        guard !lap.isEmpty else { return nil }
        let mean = lap.reduce(0, +) / Double(lap.count)
        return lap.reduce(0) { $0 + ($1 - mean) * ($1 - mean) } / Double(lap.count)
    }

    /// Выбор индекса «лучшего» кадра в группе.
    /// Критерий: наибольшее разрешение (pixelWidth*pixelHeight),
    /// при равенстве — наибольшая резкость (вариация Лапласиана миниатюры).
    /// `sharpness[i]` — заранее посчитанная резкость для asset[i] (nil если не считали).
    /// Резкость загружается только для кандидатов с максимальным разрешением.
    nonisolated static func bestAssetIndex(in assets: [PHAsset],
                                           sharpness: [Double?]) -> Int? {
        guard !assets.isEmpty else { return nil }
        // 1) Максимальное разрешение в группе.
        let resolutions = assets.map { $0.pixelWidth * $0.pixelHeight }
        let maxRes = resolutions.max() ?? 0
        let candidates = resolutions.indices.filter { resolutions[$0] == maxRes }
        if candidates.count == 1 { return candidates[0] }
        // 2) При равенстве разрешения — наибольшая резкость среди кандидатов.
        var bestIdx = candidates[0]
        var bestSharp = sharpness.indices.contains(bestIdx) ? (sharpness[bestIdx] ?? -1) : -1
        for i in candidates.dropFirst() {
            let s = sharpness.indices.contains(i) ? (sharpness[i] ?? -1) : -1
            if s > bestSharp { bestSharp = s; bestIdx = i }
        }
        return bestIdx
    }

    /// Синхронно загружает миниатюру и считает её резкость (вне главного потока).
    nonisolated static func sharpness(of asset: PHAsset) -> Double? {
        let req = PHImageRequestOptions()
        req.isSynchronous = true
        req.deliveryMode = .fastFormat
        req.isNetworkAccessAllowed = false
        req.resizeMode = .fast
        var cg: CGImage?
        PHImageManager.default().requestImage(
            for: asset, targetSize: CGSize(width: 120, height: 120),
            contentMode: .aspectFit, options: req
        ) { img, _ in
            #if canImport(UIKit)
            cg = img?.cgImage
            #else
            if let img { var r = CGRect(origin: .zero, size: img.size)
                cg = img.cgImage(forProposedRect: &r, context: nil, hints: nil) }
            #endif
        }
        guard let cg else { return nil }
        return laplacianVariance(cg)
    }

    /// Вычисляет «лучший» кадр для группы вне главного потока и кэширует индекс.
    /// Резкость грузим только когда есть несколько кадров с одинаковым макс. разрешением.
    func computeBest(for group: DupGroup) {
        guard group.bestIndex == nil else { return }
        let id = group.id
        let assets = group.assets
        Task.detached(priority: .utility) {
            // Нужна ли резкость? Только если ≥2 кандидатов с максимальным разрешением.
            let resolutions = assets.map { $0.pixelWidth * $0.pixelHeight }
            let maxRes = resolutions.max() ?? 0
            let tiedCandidates = resolutions.indices.filter { resolutions[$0] == maxRes }
            var sharpness = [Double?](repeating: nil, count: assets.count)
            if tiedCandidates.count > 1 {
                for i in tiedCandidates {
                    sharpness[i] = Self.sharpness(of: assets[i])
                }
            }
            let idx = Self.bestAssetIndex(in: assets, sharpness: sharpness)
            await MainActor.run {
                guard let gi = self.groups.firstIndex(where: { $0.id == id }) else { return }
                self.groups[gi].bestIndex = idx
            }
        }
    }

    /// Оставляет «лучший» кадр, удаляет ВСЕ остальные — через системное подтверждение.
    func keepBest(in group: DupGroup) {
        let best = group.bestIndex ?? Self.bestAssetIndex(in: group.assets, sharpness: []) ?? 0
        let toDelete = group.assets.enumerated()
            .filter { $0.offset != best }
            .map { $0.element }
        guard !toDelete.isEmpty else { return }
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(toDelete as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    self.groups.removeAll { $0.id == group.id }
                    self.status = "Оставлен лучший кадр, остальные — в «Недавно удалённые» (30 дней)"
                }
            }
        }
    }

    /// Удаляет один снимок (для режима «Размытые»).
    func deleteOne(_ group: DupGroup) {
        guard let asset = group.assets.first else { return }
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets([asset] as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.groups.removeAll { $0.id == group.id }
                self.status = "Перенесено в «Недавно удалённые»"
            }
        }
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

                if scanner.mode == .blurry || scanner.mode == .live {
                    ForEach(scanner.groups) { group in
                        HStack(spacing: 12) {
                            if let asset = group.assets.first { AssetThumb(asset: asset) }
                            VStack(alignment: .leading, spacing: 3) {
                                Text(scanner.mode == .live ? "Live Photo" : "Размытый кадр")
                                    .font(.subheadline.bold()).foregroundStyle(Brand.text)
                                if let d = group.assets.first?.creationDate {
                                    Text(d.formatted(date: .abbreviated, time: .shortened))
                                        .font(.caption2).foregroundStyle(Brand.muted)
                                }
                            }
                            Spacer(minLength: 0)
                            Button { scanner.deleteOne(group) } label: {
                                Text("Удалить").font(.caption.bold()).foregroundStyle(Brand.red)
                            }.buttonStyle(.plain)
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                    }
                } else {
                    ForEach(scanner.groups) { group in
                        VStack(alignment: .leading, spacing: 10) {
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 8) {
                                    ForEach(Array(group.assets.prefix(8).enumerated()), id: \.offset) { idx, asset in
                                        AssetThumb(asset: asset, isBest: group.bestIndex == idx)
                                    }
                                }
                            }
                            HStack {
                                Text("\(group.assets.count) похожих снимка")
                                    .font(.caption.bold()).foregroundStyle(Brand.muted)
                                Spacer()
                                Button { scanner.keepBest(in: group) } label: {
                                    Text("Оставить лучший (удалить \(group.assets.count - 1))")
                                        .font(.caption.bold()).foregroundStyle(Brand.green)
                                }.buttonStyle(.plain)
                            }
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                        .onAppear { scanner.computeBest(for: group) }
                    }
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(StarfieldView())
    }
}

/// Миниатюра PHAsset (общая для iOS/macOS).
struct AssetThumb: View {
    let asset: PHAsset
    var isBest: Bool = false
    @State private var image: Image?

    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 10).fill(Brand.track)
            if let image {
                image.resizable().scaledToFill()
            }
            if isBest {
                Text("★ лучший")
                    .font(.system(size: 9, weight: .heavy))
                    .foregroundStyle(.black)
                    .padding(.horizontal, 5).padding(.vertical, 2)
                    .background(Brand.green, in: Capsule())
                    .padding(4)
            }
        }
        .frame(width: 72, height: 72)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(isBest ? Brand.green : .clear, lineWidth: 2)
        )
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
