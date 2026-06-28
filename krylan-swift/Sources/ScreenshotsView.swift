// Скриншоты (PhotoKit): сетка с выбором и удалением в «Недавно удалённые».
import SwiftUI
import Photos

@MainActor
final class ScreenshotScanner: ObservableObject {
    @Published var assets: [PHAsset] = []
    @Published var selected = Set<String>()
    @Published var status = "Готово к сканированию"
    @Published var scanning = false
    @Published var bannerMoved = 0              // >0 — показать баннер «Недавно удалённые»

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
        // Тяжёлый перебор всей медиатеки — вне главного потока, чтобы не блокировать UI.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.predicate = NSPredicate(format: "(mediaSubtypes & %d) != 0",
                                         PHAssetMediaSubtype.photoScreenshot.rawValue)
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var arr: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in arr.append(a) }
            await MainActor.run {
                self.assets = arr
                self.selected = []
                self.scanning = false
                self.status = arr.isEmpty ? "Скриншотов не найдено" : "Скриншотов: \(arr.count)"
            }
        }
    }

    func toggle(_ a: PHAsset) {
        if selected.contains(a.localIdentifier) { selected.remove(a.localIdentifier) }
        else { selected.insert(a.localIdentifier) }
    }

    func selectAll() { selected = Set(assets.map(\.localIdentifier)) }
    func clearSelection() { selected.removeAll() }

    func deleteSelected() {
        let del = assets.filter { selected.contains($0.localIdentifier) }
        guard !del.isEmpty else { return }
        let count = del.count
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(del as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.assets.removeAll { self.selected.contains($0.localIdentifier) }
                self.selected = []
                self.bannerMoved = count
                self.status = "Перенесено в «Недавно удалённые»: \(count)"
            }
        }
    }
}

struct ScreenshotsView: View {
    @StateObject private var scanner = ScreenshotScanner()
    @State private var confirmDelete = false
    private let cols = [GridItem(.adaptive(minimum: 76), spacing: 8)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Скриншоты")
                Text("Скриншоты копятся незаметно и редко нужны спустя время. Отметьте лишние галочкой и удалите все разом — обратимо 30 дней.")
                    .font(.callout).foregroundStyle(Brand.muted)

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

                if scanner.assets.isEmpty {
                    if !scanner.scanning {
                        EmptyStateView(icon: "camera.viewfinder",
                                       title: "Скриншотов нет",
                                       subtitle: "Нажмите «Сканировать», чтобы собрать все скриншоты из медиатеки.")
                    }
                } else {
                    SelectionActionBar(
                        selectedCount: scanner.selected.count,
                        totalCount: scanner.assets.count,
                        onSelectAll: { scanner.selectAll() },
                        onClear: { scanner.clearSelection() },
                        onDelete: { confirmDelete = true }
                    )

                    LazyVGrid(columns: cols, spacing: 8) {
                        ForEach(scanner.assets, id: \.localIdentifier) { asset in
                            AssetThumb(asset: asset,
                                       selected: scanner.selected.contains(asset.localIdentifier))
                                .contentShape(Rectangle())
                                .onTapGesture { scanner.toggle(asset) }
                        }
                    }
                    .padding(14)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(StarfieldView())
        .confirmationDialog("Удалить выбранные скриншоты?",
                            isPresented: $confirmDelete, titleVisibility: .visible) {
            Button("Удалить (\(scanner.selected.count))", role: .destructive) { scanner.deleteSelected() }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("Дальше появится системный запрос. Скриншоты перенесутся в «Недавно удалённые»; место освободится только после очистки этого альбома.")
        }
    }
}
