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
    @Published var selected = Set<String>()     // выбранные снимки (для .blurry/.live)
    @Published var scanning = false
    @Published var mode: PhotoScanMode = .exact
    @Published var bannerMoved = 0              // >0 — показать баннер «Недавно удалённые»
    @Published var didScan = false             // уже сканировали хотя бы раз (для авто-скана)

    var extraCount: Int { groups.reduce(0) { $0 + $1.assets.count - 1 } }

    /// Плоский список снимков (по 1 кадру на группу) для режимов с мультивыбором.
    var flatAssets: [PHAsset] { groups.compactMap { $0.assets.first } }

    /// Суммарная оценка размера выбранных снимков (для .blurry/.live, приблизительно).
    var selectedSizeEstimate: Double {
        MediaEstimate.totalBytes(flatAssets.filter { selected.contains($0.localIdentifier) })
    }

    /// Авто-скан при открытии: только если доступ уже выдан и ещё не сканировали.
    func autoScanIfPossible() {
        guard !didScan, !scanning, PhotoAccess.isAuthorized else { return }
        selected.removeAll()
        switch mode {
        case .exact:  runExact()
        case .series: runSeries()
        case .blurry: runBlurry()
        case .live:   runLive()
        }
    }

    func toggle(_ a: PHAsset) {
        if selected.contains(a.localIdentifier) { selected.remove(a.localIdentifier) }
        else { selected.insert(a.localIdentifier) }
    }

    func selectAll() { selected = Set(flatAssets.map(\.localIdentifier)) }
    func clearSelection() { selected.removeAll() }

    /// Удаляет ВСЕ выбранные снимки одним системным подтверждением (для .blurry/.live).
    func deleteSelected() {
        let del = flatAssets.filter { selected.contains($0.localIdentifier) }
        guard !del.isEmpty else { return }
        let count = del.count
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(del as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.groups.removeAll { g in
                    guard let a = g.assets.first else { return false }
                    return self.selected.contains(a.localIdentifier)
                }
                self.selected.removeAll()
                self.bannerMoved = count
                Haptics.success()
                self.status = "Перенесено в «Недавно удалённые»: \(count)"
            }
        }
    }

    func scan() {
        status = "Запрос доступа к фото…"
        PHPhotoLibrary.requestAuthorization(for: .readWrite) { [weak self] st in
            Task { @MainActor in
                guard let self else { return }
                guard st == .authorized || st == .limited else {
                    self.status = "Нет доступа к медиатеке"; return
                }
                self.selected.removeAll()
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
                self.didScan = true
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
                self.didScan = true
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
                self.didScan = true
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
                self.didScan = true
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

    /// Все ассеты всех групп (для пакетного удаления выбранного в режимах групп).
    var allGroupAssets: [PHAsset] { groups.flatMap { $0.assets } }

    /// Суммарная оценка размера выбранного во всех группах (.exact/.series).
    var selectedGroupSizeEstimate: Double {
        MediaEstimate.totalBytes(allGroupAssets.filter { selected.contains($0.localIdentifier) })
    }

    /// «Выбрать все, кроме лучшего»: в каждой группе оставляем один кадр
    /// (по bestIndex, иначе — наибольшего разрешения), остальные помечаем к удалению.
    func selectAllButBest() {
        var ids = Set<String>()
        for g in groups {
            guard g.assets.count > 1 else { continue }
            let best = g.bestIndex ?? Self.bestAssetIndex(in: g.assets, sharpness: []) ?? 0
            for (i, a) in g.assets.enumerated() where i != best {
                ids.insert(a.localIdentifier)
            }
        }
        selected = ids
    }

    /// Удаляет ВСЕ выбранные кадры из групп одним системным подтверждением (.exact/.series).
    func deleteSelectedInGroups() {
        let del = allGroupAssets.filter { selected.contains($0.localIdentifier) }
        guard !del.isEmpty else { return }
        let count = del.count
        let ids = selected
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(del as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                // Удаляем выбранные кадры из групп; группы, где остался ≤1 кадр, убираем.
                for i in self.groups.indices {
                    self.groups[i].assets.removeAll { ids.contains($0.localIdentifier) }
                    self.groups[i].bestIndex = nil
                }
                self.groups.removeAll { $0.assets.count < 2 }
                self.selected.removeAll()
                self.bannerMoved = count
                Haptics.success()
                self.status = "Перенесено в «Недавно удалённые»: \(count)"
            }
        }
    }

    /// Оставляет «лучший» кадр, удаляет остальные — через системное подтверждение.
    /// Если в группе есть кадры, отмеченные вручную (`selected`), удаляем ИМЕННО их
    /// (уважаем ручной выбор пользователя). Иначе — старое поведение: всё, кроме лучшего.
    func keepBest(in group: DupGroup) {
        let manual = group.assets.filter { selected.contains($0.localIdentifier) }
        let toDelete: [PHAsset]
        if manual.isEmpty {
            let best = group.bestIndex ?? Self.bestAssetIndex(in: group.assets, sharpness: []) ?? 0
            toDelete = group.assets.enumerated()
                .filter { $0.offset != best }
                .map { $0.element }
        } else {
            toDelete = manual
        }
        guard !toDelete.isEmpty else { return }
        let count = toDelete.count
        let delIds = Set(toDelete.map { $0.localIdentifier })
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(toDelete as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    // Убираем удалённые кадры из группы и из ручного выбора.
                    if let gi = self.groups.firstIndex(where: { $0.id == group.id }) {
                        self.groups[gi].assets.removeAll { delIds.contains($0.localIdentifier) }
                        self.groups[gi].bestIndex = nil
                        // Группа без смысла (≤1 кадра) — убираем целиком.
                        if self.groups[gi].assets.count < 2 {
                            self.groups.remove(at: gi)
                        }
                    }
                    self.selected.subtract(delIds)
                    self.bannerMoved = count
                    Haptics.success()
                    self.status = manual.isEmpty
                        ? "Оставлен лучший кадр, остальные — в «Недавно удалённые»: \(count)"
                        : "Удалены отмеченные кадры — в «Недавно удалённые»: \(count)"
                }
            }
        }
    }
}

struct PhotoDuplicatesView: View {
    @StateObject private var scanner = PhotoScanner()
    @State private var confirmDeleteSelected = false
    @State private var confirmDeleteGroupSelected = false
    @State private var confirmGroup: DupGroup?
    @State private var previewAsset: PHAsset?

    /// Режимы с плоским мультивыбором (по 1 кадру на «группу»).
    private var isFlatSelectMode: Bool { scanner.mode == .blurry || scanner.mode == .live }
    private let cols = [GridItem(.adaptive(minimum: 76), spacing: 8)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Фото")
                Text(modeHint)
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

                if scanner.bannerMoved > 0 {
                    RecentlyDeletedBanner(movedCount: scanner.bannerMoved) {
                        scanner.bannerMoved = 0
                    }
                }

                if scanner.groups.isEmpty {
                    if !scanner.scanning {
                        if PhotoAccess.isAuthorized {
                            EmptyStateView(icon: "photo.on.rectangle.angled",
                                           title: "Пусто",
                                           subtitle: "Нажмите «Сканировать» для выбранного режима.")
                        } else {
                            PhotoPermissionGate { scanner.scan() }
                        }
                    }
                } else if isFlatSelectMode {
                    flatSelectGrid
                } else {
                    groupList
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(StarfieldView())
        .task { scanner.autoScanIfPossible() }
        // Смена режима в Picker должна пересканировать (didScan один на все режимы).
        .onChange(of: scanner.mode) { _, _ in
            scanner.didScan = false
            scanner.autoScanIfPossible()
        }
        .fullScreenCoverCompat(item: $previewAsset) { asset in
            FullScreenAssetPreview(asset: asset)
        }
        .confirmationDialog("Удалить выбранные кадры?",
                            isPresented: $confirmDeleteGroupSelected, titleVisibility: .visible) {
            Button("Удалить (\(scanner.selected.count))", role: .destructive) { scanner.deleteSelectedInGroups() }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("В каждой группе останется один кадр. Остальные перенесутся в «Недавно удалённые»; место освободится после очистки этого альбома.")
        }
        .confirmationDialog(scanner.mode == .live ? "Удалить выбранные Live Photos?" : "Удалить выбранные снимки?",
                            isPresented: $confirmDeleteSelected, titleVisibility: .visible) {
            Button("Удалить (\(scanner.selected.count))", role: .destructive) { scanner.deleteSelected() }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("Дальше появится системный запрос. Снимки перенесутся в «Недавно удалённые»; место освободится только после очистки этого альбома.")
        }
        .confirmationDialog("Оставить лучший кадр?",
                            isPresented: Binding(get: { confirmGroup != nil },
                                                 set: { if !$0 { confirmGroup = nil } }),
                            titleVisibility: .visible) {
            Button("Оставить лучший, удалить остальные", role: .destructive) {
                if let g = confirmGroup { scanner.keepBest(in: g) }
                confirmGroup = nil
            }
            Button("Отмена", role: .cancel) { confirmGroup = nil }
        } message: {
            Text("Останется кадр с пометкой «★ лучший», остальные перейдут в «Недавно удалённые».")
        }
    }

    private var modeHint: String {
        switch scanner.mode {
        case .exact:  return "Похожие фото по размеру и дате. Оставьте лучший кадр — остальные в «Недавно удалённые»."
        case .series: return "Серии снимков подряд. Оставьте лучший кадр — остальные в «Недавно удалённые»."
        case .blurry: return "Возможно размытые кадры. Отметьте лишние галочкой и удалите все разом."
        case .live:   return "Live Photos занимают ~2× места (кадр + видео). Отметьте лишние и удалите все разом."
        }
    }

    // MARK: .blurry / .live — плоский мультивыбор

    @ViewBuilder private var flatSelectGrid: some View {
        SelectionActionBar(
            selectedCount: scanner.selected.count,
            totalCount: scanner.flatAssets.count,
            subtitle: scanner.selected.isEmpty ? "" : "освободит ≈ \(MediaEstimate.fmtBytes(scanner.selectedSizeEstimate))",
            onSelectAll: { scanner.selectAll() },
            onClear: { scanner.clearSelection() },
            onDelete: { confirmDeleteSelected = true }
        )
        LazyVGrid(columns: cols, spacing: 8) {
            ForEach(scanner.flatAssets, id: \.localIdentifier) { asset in
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

    // MARK: .exact / .series — группы «оставить лучший»

    @ViewBuilder private var groupList: some View {
        // Умный пакетный выбор: один кадр в группе остаётся, остальные — к удалению.
        VStack(spacing: 10) {
            HStack {
                Button("Выбрать все, кроме лучшего") { scanner.selectAllButBest() }
                    .font(.caption.bold()).foregroundStyle(Brand.blue).buttonStyle(.plain)
                Spacer()
                if !scanner.selected.isEmpty {
                    Button("Снять") { scanner.clearSelection() }
                        .font(.caption.bold()).foregroundStyle(Brand.muted).buttonStyle(.plain)
                }
            }
            if !scanner.selected.isEmpty {
                Button { confirmDeleteGroupSelected = true } label: {
                    HStack {
                        Text("Удалить выбранные (\(scanner.selected.count))").bold()
                        Spacer()
                        Text("≈ \(MediaEstimate.fmtBytes(scanner.selectedGroupSizeEstimate))").bold()
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12).padding(.horizontal, 14)
                    .background(Brand.red).foregroundStyle(.white).clipShape(Capsule())
                }.buttonStyle(.plain)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))

        ForEach(scanner.groups) { group in
            VStack(alignment: .leading, spacing: 10) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(Array(group.assets.prefix(8).enumerated()), id: \.offset) { idx, asset in
                            // «★ лучший» по РЕАЛЬНОМУ индексу ассета в полном массиве group.assets,
                            // а не по позиции в срезе prefix(8) (иначе при bestIndex≥8 метка съезжала).
                            AssetThumb(asset: asset,
                                       isBest: group.bestIndex == group.assets.firstIndex(where: { $0.localIdentifier == asset.localIdentifier }),
                                       selected: scanner.selected.contains(asset.localIdentifier) ? true : nil)
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    Haptics.selection()
                                    scanner.toggle(asset)
                                }
                                .onLongPressGesture { previewAsset = asset }
                        }
                    }
                }
                HStack {
                    Text("\(group.assets.count) похожих снимка")
                        .font(.caption.bold()).foregroundStyle(Brand.muted)
                    Spacer()
                    Button { confirmGroup = group } label: {
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

/// Миниатюра PHAsset (общая для iOS/macOS).
/// `selected == nil` — кружок выбора не показываем (обычный режим просмотра).
/// `selected == true/false` — режим мультивыбора с индикатором в углу.
struct AssetThumb: View {
    let asset: PHAsset
    var isBest: Bool = false
    var selected: Bool? = nil
    @State private var image: Image?

    private var isSelected: Bool { selected == true }

    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 10).fill(Brand.track)
            if let image {
                image.resizable().scaledToFill()
            }
            if isSelected {
                RoundedRectangle(cornerRadius: 10).fill(Brand.green.opacity(0.22))
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
        .overlay(alignment: .topTrailing) {
            if let selected {
                SelectionCircle(isSelected: selected).padding(4)
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(strokeColor, lineWidth: 2)
        )
        .onAppear(perform: load)
    }

    private var strokeColor: Color {
        if isSelected { return Brand.green }
        if isBest { return Brand.green }
        return .clear
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
