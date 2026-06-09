// Поиск фото-дубликатов (PhotoKit). Работает на iOS и macOS.
// В Info.plist нужен ключ NSPhotoLibraryUsageDescription.
import SwiftUI
import Photos

@MainActor
final class PhotoScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var duplicateCount = 0
    @Published var groups = 0

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
        status = "Сканирую медиатеку…"
        let assets = PHAsset.fetchAssets(with: .image, options: nil)
        // Кандидаты в дубликаты: совпадают размеры и дата съёмки (упрощённая эвристика).
        var buckets: [String: Int] = [:]
        assets.enumerateObjects { a, _, _ in
            let key = "\(a.pixelWidth)x\(a.pixelHeight)-\(Int(a.creationDate?.timeIntervalSince1970 ?? 0))"
            buckets[key, default: 0] += 1
        }
        let dup = buckets.values.filter { $0 > 1 }
        groups = dup.count
        duplicateCount = dup.reduce(0) { $0 + ($1 - 1) }
        status = dup.isEmpty ? "Дубликатов не найдено"
                             : "Похожих групп: \(groups), лишних снимков: \(duplicateCount)"
    }
}

struct PhotoDuplicatesView: View {
    @StateObject private var scanner = PhotoScanner()
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Фото-дубликаты").font(.largeTitle.bold()).foregroundStyle(Brand.text)
            Text("Поиск похожих фото по размеру и дате (PhotoKit). Удаление идёт в системный альбом «Недавно удалённые».")
                .font(.callout).foregroundStyle(Brand.muted)
            Text(scanner.status).font(.headline).foregroundStyle(Brand.green)
            Button { scanner.scan() } label: {
                Text("Сканировать").bold()
                    .padding(.horizontal, 20).padding(.vertical, 11)
                    .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
            }.buttonStyle(.plain)
            Spacer()
        }
        .padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}
