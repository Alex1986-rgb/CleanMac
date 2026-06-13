// Скриншоты (PhotoKit): сетка с выбором и удалением в «Недавно удалённые».
import SwiftUI
import Photos

@MainActor
final class ScreenshotScanner: ObservableObject {
    @Published var assets: [PHAsset] = []
    @Published var selected = Set<String>()
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
        let opts = PHFetchOptions()
        opts.predicate = NSPredicate(format: "(mediaSubtypes & %d) != 0",
                                     PHAssetMediaSubtype.photoScreenshot.rawValue)
        opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
        let fetch = PHAsset.fetchAssets(with: .image, options: opts)
        var arr: [PHAsset] = []
        fetch.enumerateObjects { a, _, _ in arr.append(a) }
        assets = arr; selected = []
        scanning = false
        status = arr.isEmpty ? "Скриншотов не найдено" : "Скриншотов: \(arr.count)"
    }

    func toggle(_ a: PHAsset) {
        if selected.contains(a.localIdentifier) { selected.remove(a.localIdentifier) }
        else { selected.insert(a.localIdentifier) }
    }

    func selectAll() { selected = Set(assets.map(\.localIdentifier)) }

    func deleteSelected() {
        let del = assets.filter { selected.contains($0.localIdentifier) }
        guard !del.isEmpty else { return }
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(del as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self, ok else { return }
                self.assets.removeAll { self.selected.contains($0.localIdentifier) }
                self.selected = []
                self.status = "Перенесено в «Недавно удалённые» (хранится 30 дней)"
            }
        }
    }
}

struct ScreenshotsView: View {
    @StateObject private var scanner = ScreenshotScanner()
    private let cols = [GridItem(.adaptive(minimum: 76), spacing: 8)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                PageHeader(title: "Скриншоты")
                Text("Скриншоты копятся незаметно и редко нужны спустя время. Выберите лишние — удаление обратимо 30 дней.")
                    .font(.callout).foregroundStyle(Brand.muted)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                }

                if !scanner.assets.isEmpty {
                    HStack {
                        Button("Выбрать все") { scanner.selectAll() }
                            .font(.caption.bold()).foregroundStyle(Brand.blue).buttonStyle(.plain)
                        Spacer()
                        Button { scanner.deleteSelected() } label: {
                            Text("Удалить (\(scanner.selected.count))")
                                .font(.caption.bold())
                                .foregroundStyle(scanner.selected.isEmpty ? Brand.muted : Brand.red)
                        }.buttonStyle(.plain).disabled(scanner.selected.isEmpty)
                    }

                    LazyVGrid(columns: cols, spacing: 8) {
                        ForEach(scanner.assets, id: \.localIdentifier) { asset in
                            ZStack(alignment: .topTrailing) {
                                AssetThumb(asset: asset)
                                if scanner.selected.contains(asset.localIdentifier) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(Brand.green)
                                        .background(Circle().fill(.black.opacity(0.6)))
                                        .padding(4)
                                }
                            }
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
    }
}
