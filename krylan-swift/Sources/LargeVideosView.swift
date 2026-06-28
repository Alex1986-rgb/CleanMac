// Видео (PhotoKit): два режима.
//  • «Крупные»  — топ по длительности, удаление по одному.
//  • «Похожие»  — группировка роликов по близкой длительности (±2 c) и близкой
//                 оценке размера; удаление лишних (кроме одного) через системный диалог.
// Точный размер файла PhotoKit публично не отдаёт — используем честную оценку
// «вес ≈ длительность × площадь кадра» (прокси битрейта), без приватных API.
import SwiftUI
import Photos

enum VideoScanMode: String, CaseIterable, Identifiable {
    case large   = "Крупные"
    case similar = "Похожие"
    var id: String { rawValue }
}

/// Группа похожих видео (для режима «Похожие»).
struct VideoGroup: Identifiable {
    let id = UUID()
    var assets: [PHAsset]
}

@MainActor
final class VideoScanner: ObservableObject {
    @Published var videos: [PHAsset] = []       // режим «Крупные»
    @Published var groups: [VideoGroup] = []    // режим «Похожие»
    @Published var selected = Set<String>()     // выбранные ролики (по localIdentifier)
    @Published var status = "Готово к сканированию"
    @Published var scanning = false
    @Published var mode: VideoScanMode = .large
    @Published var bannerMoved = 0              // >0 — показать баннер «Недавно удалённые»
    @Published var didScan = false             // уже сканировали хотя бы раз (для авто-скана)

    /// Авто-скан при открытии: только если доступ уже выдан и ещё не сканировали.
    func autoScanIfPossible() {
        guard !didScan, !scanning, PhotoAccess.isAuthorized else { return }
        switch mode {
        case .large:   runLarge()
        case .similar: runSimilar()
        }
    }

    /// Сколько роликов можно убрать (по одному лишнему в каждой группе).
    var extraCount: Int { groups.reduce(0) { $0 + $1.assets.count - 1 } }

    /// Суммарная оценка «веса» выбранных роликов (прокси, без точных байт).
    var selectedSizeEstimate: Double {
        videos.filter { selected.contains($0.localIdentifier) }
            .reduce(0) { $0 + Self.sizeEstimate($1) }
    }

    func toggle(_ a: PHAsset) {
        if selected.contains(a.localIdentifier) { selected.remove(a.localIdentifier) }
        else { selected.insert(a.localIdentifier) }
    }

    func selectAll() { selected = Set(videos.map(\.localIdentifier)) }
    func clearSelection() { selected.removeAll() }

    /// Удаляет ВСЕ выбранные ролики одним системным подтверждением.
    func deleteSelected() {
        let del = videos.filter { selected.contains($0.localIdentifier) }
        guard !del.isEmpty else { return }
        let count = del.count
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(del as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.videos.removeAll { self.selected.contains($0.localIdentifier) }
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
                switch self.mode {
                case .large:   self.runLarge()
                case .similar: self.runSimilar()
                }
            }
        }
    }

    private func runLarge() {
        scanning = true
        status = "Сканирую медиатеку…"
        groups = []
        selected.removeAll()
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
                self.didScan = true
                self.status = arr.isEmpty ? "Видео не найдено" : "Самых длинных видео: \(arr.count)"
            }
        }
    }

    /// Похожие видео: кластеры роликов с близкой длительностью (±2 c) и близкой
    /// оценкой размера (вес = длительность × площадь кадра, разница ≤ 15%), от 2 штук.
    private func runSimilar() {
        scanning = true
        status = "Ищу похожие видео…"
        videos = []
        selected.removeAll()
        // Тяжёлый перебор всей медиатеки — вне главного потока.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            // Сортируем по длительности — тогда похожие по длине окажутся рядом.
            opts.sortDescriptors = [NSSortDescriptor(key: "duration", ascending: true)]
            let fetch = PHAsset.fetchAssets(with: .video, options: opts)
            var all: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in if a.duration > 0 { all.append(a) } }

            let found = Self.clusterSimilar(all)
            await MainActor.run {
                self.groups = found
                self.scanning = false
                self.didScan = true
                self.status = found.isEmpty ? "Похожих видео не найдено"
                    : "Похожих групп: \(found.count), лишних роликов: \(self.extraCount)"
            }
        }
    }

    /// Кластеризация: список уже отсортирован по длительности.
    /// Склеиваем соседей с разницей длительности ≤ 2 c и относительной
    /// разницей оценки размера ≤ 15%. Группы от 2 роликов.
    nonisolated static func clusterSimilar(_ sorted: [PHAsset]) -> [VideoGroup] {
        guard sorted.count > 1 else { return [] }
        var result: [[PHAsset]] = []
        var cur: [PHAsset] = [sorted[0]]
        for i in 1..<sorted.count {
            let prev = sorted[i-1], a = sorted[i]
            let dDur = abs(a.duration - prev.duration)
            let sizeA = sizeEstimate(a), sizeP = sizeEstimate(prev)
            let rel = max(sizeA, sizeP) > 0 ? abs(sizeA - sizeP) / max(sizeA, sizeP) : 1
            if dDur <= 2 && rel <= 0.15 {
                cur.append(a)
            } else {
                if cur.count >= 2 { result.append(cur) }
                cur = [a]
            }
        }
        if cur.count >= 2 { result.append(cur) }
        return result.map { VideoGroup(assets: $0) }
            .sorted { $0.assets.count > $1.assets.count }
    }

    /// Честная оценка «веса» ролика без приватных API:
    /// длительность × площадь кадра ≈ объём данных (прокси битрейта).
    nonisolated static func sizeEstimate(_ a: PHAsset) -> Double {
        Double(a.pixelWidth) * Double(a.pixelHeight) * a.duration
    }

    /// Удаляет все ролики группы кроме первого — через системное подтверждение.
    func deleteExtras(in group: VideoGroup) {
        let extras = Array(group.assets.dropFirst())
        guard !extras.isEmpty else { return }
        let count = extras.count
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(extras as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    self.groups.removeAll { $0.id == group.id }
                    self.bannerMoved = count
                    Haptics.success()
                    self.status = "Перенесено в «Недавно удалённые»: \(count)"
                }
            }
        }
    }
}

struct LargeVideosView: View {
    @StateObject private var scanner = VideoScanner()
    @State private var confirmDeleteSelected = false
    @State private var confirmGroup: VideoGroup?
    @State private var previewAsset: PHAsset?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Видео")
                Text(scanner.mode == .large
                     ? "Длинные видео — главные потребители места. Топ-50 по длительности. Отметьте лишние галочкой и удалите все разом."
                     : "Похожие ролики: близкая длительность (±2 c) и близкий размер. Размер — оценка по битрейту, без точных байт.")
                    .font(.callout).foregroundStyle(Brand.muted)

                Picker("Режим", selection: $scanner.mode) {
                    ForEach(VideoScanMode.allCases) { m in Text(m.rawValue).tag(m) }
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

                if scanner.mode == .large {
                    largeMode
                } else {
                    similarMode
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(StarfieldView())
        .task { scanner.autoScanIfPossible() }
        .fullScreenCoverCompat(item: $previewAsset) { asset in
            FullScreenAssetPreview(asset: asset)
        }
        .confirmationDialog("Удалить выбранные видео?",
                            isPresented: $confirmDeleteSelected, titleVisibility: .visible) {
            Button("Удалить (\(scanner.selected.count))", role: .destructive) { scanner.deleteSelected() }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("Дальше появится системный запрос подтверждения. Видео перенесутся в «Недавно удалённые», место освободится только после очистки этого альбома.")
        }
        .confirmationDialog("Удалить лишние ролики группы?",
                            isPresented: Binding(get: { confirmGroup != nil },
                                                 set: { if !$0 { confirmGroup = nil } }),
                            titleVisibility: .visible) {
            Button("Удалить", role: .destructive) {
                if let g = confirmGroup { scanner.deleteExtras(in: g) }
                confirmGroup = nil
            }
            Button("Отмена", role: .cancel) { confirmGroup = nil }
        } message: {
            Text("Останется первый ролик, остальные перейдут в «Недавно удалённые».")
        }
    }

    // MARK: режим «Крупные» — мультивыбор

    @ViewBuilder private var largeMode: some View {
        if scanner.videos.isEmpty {
            if !scanner.scanning {
                if PhotoAccess.isAuthorized {
                    EmptyStateView(icon: "film.stack",
                                   title: "Список пуст",
                                   subtitle: "Нажмите «Сканировать», чтобы найти самые длинные видео.")
                } else {
                    PhotoPermissionGate { scanner.scan() }
                }
            }
        } else {
            SelectionActionBar(
                selectedCount: scanner.selected.count,
                totalCount: scanner.videos.count,
                subtitle: scanner.selected.isEmpty ? "" : "освободит ≈ \(Self.fmtSize(scanner.selectedSizeEstimate))",
                onSelectAll: { scanner.selectAll() },
                onClear: { scanner.clearSelection() },
                onDelete: { confirmDeleteSelected = true }
            )
            ForEach(scanner.videos, id: \.localIdentifier) { v in
                videoRow(v)
            }
        }
    }

    private func videoRow(_ v: PHAsset) -> some View {
        let isSel = scanner.selected.contains(v.localIdentifier)
        return HStack(spacing: 12) {
            AssetThumb(asset: v, selected: isSel)
            VStack(alignment: .leading, spacing: 3) {
                Text(Self.fmtDuration(v.duration))
                    .font(.headline).foregroundStyle(Brand.text)
                Text("\(v.pixelWidth)×\(v.pixelHeight) · ≈ \(Self.fmtSize(VideoScanner.sizeEstimate(v)))")
                    .font(.caption).foregroundStyle(Brand.muted)
                if let d = v.creationDate {
                    Text(d.formatted(date: .abbreviated, time: .omitted))
                        .font(.caption2).foregroundStyle(Brand.muted)
                }
            }
            Spacer(minLength: 0)
            Image(systemName: isSel ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(isSel ? Brand.green : Brand.muted)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16)
            .fill(isSel ? Brand.green.opacity(0.12) : Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 16)
            .strokeBorder(isSel ? Brand.green.opacity(0.5) : .clear, lineWidth: 1))
        .contentShape(Rectangle())
        .onTapGesture {
            Haptics.selection()
            scanner.toggle(v)
        }
        .onLongPressGesture { previewAsset = v }
    }

    // MARK: режим «Похожие» — групповое удаление лишних

    @ViewBuilder private var similarMode: some View {
        if scanner.groups.isEmpty {
            if !scanner.scanning {
                if PhotoAccess.isAuthorized {
                    EmptyStateView(icon: "square.stack.3d.up",
                                   title: "Похожих не найдено",
                                   subtitle: "Запустите сканирование — соберём группы роликов близкой длины и размера.")
                } else {
                    PhotoPermissionGate { scanner.scan() }
                }
            }
        } else {
            ForEach(scanner.groups) { group in
                VStack(alignment: .leading, spacing: 10) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(Array(group.assets.prefix(8).enumerated()), id: \.offset) { _, asset in
                                VStack(spacing: 4) {
                                    AssetThumb(asset: asset)
                                        .onLongPressGesture { previewAsset = asset }
                                    Text(Self.fmtDuration(asset.duration))
                                        .font(.caption2.bold()).foregroundStyle(Brand.muted)
                                }
                            }
                        }
                    }
                    HStack {
                        Text("\(group.assets.count) похожих ролика · ~\(Self.fmtDuration(group.assets.first?.duration ?? 0))")
                            .font(.caption.bold()).foregroundStyle(Brand.muted)
                        Spacer()
                        Button { confirmGroup = group } label: {
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
    }

    static func fmtDuration(_ s: TimeInterval) -> String {
        let t = Int(s)
        return t >= 3600 ? String(format: "%d:%02d:%02d", t/3600, t%3600/60, t%60)
                         : String(format: "%d:%02d", t/60, t%60)
    }

    /// Перевод прокси-оценки «вес = пиксели × длительность» в читаемые байты.
    /// Коэффициент ≈ 0.07 байта на (пиксель·сек) — грубая, честная оценка H.264, без точных байт.
    static func fmtSize(_ estimate: Double) -> String {
        let bytes = estimate * 0.07
        let u = ["Б", "КБ", "МБ", "ГБ"]; var v = bytes; var i = 0
        while v >= 1024 && i < u.count - 1 { v /= 1024; i += 1 }
        return i == 0 ? "\(Int(v)) \(u[i])" : String(format: "%.1f %@", v, u[i])
    }
}
