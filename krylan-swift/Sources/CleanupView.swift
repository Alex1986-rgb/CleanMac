// Очистка собственного кэша приложения (разрешено на iOS и macOS).
import SwiftUI

@MainActor
final class CacheCleaner: ObservableObject {
    @Published var sizeText = "—"
    @Published var status = ""

    private var cachesURL: URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
    }

    func refresh() {
        guard let url = cachesURL else { sizeText = "—"; return }
        sizeText = ByteCountFormatter.string(fromByteCount: Self.dirSize(url), countStyle: .file)
    }

    func clean() {
        guard let url = cachesURL else { return }
        let fm = FileManager.default
        if let items = try? fm.contentsOfDirectory(at: url, includingPropertiesForKeys: nil) {
            for it in items { try? fm.removeItem(at: it) }
        }
        status = "Кэш приложения очищен"
        refresh()
    }

    static func dirSize(_ url: URL) -> Int64 {
        let fm = FileManager.default
        guard let en = fm.enumerator(at: url, includingPropertiesForKeys: [.fileSizeKey]) else { return 0 }
        var total: Int64 = 0
        for case let f as URL in en {
            total += Int64((try? f.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)
        }
        return total
    }
}

struct CleanupView: View {
    @StateObject private var cleaner = CacheCleaner()
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Очистка").font(.largeTitle.bold()).foregroundStyle(Brand.text)
            Text("Кэш этого приложения. На iOS доступна очистка только собственных данных.")
                .font(.callout).foregroundStyle(Brand.muted)
            HStack(spacing: 8) {
                Text("Размер кэша:").foregroundStyle(Brand.muted)
                Text(cleaner.sizeText).font(.title3.bold()).foregroundStyle(Brand.green)
            }
            Button { cleaner.clean() } label: {
                Text("Очистить кэш").bold()
                    .padding(.horizontal, 20).padding(.vertical, 11)
                    .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
            }.buttonStyle(.plain)
            if !cleaner.status.isEmpty {
                Text(cleaner.status).foregroundStyle(Brand.green)
            }
            Spacer()
        }
        .padding(24).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .onAppear { cleaner.refresh() }
    }
}
