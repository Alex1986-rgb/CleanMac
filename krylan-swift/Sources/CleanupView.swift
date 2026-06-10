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
        let fmt = ByteCountFormatter()
        fmt.countStyle = .file
        fmt.allowsNonnumericFormatting = false   // «0 КБ» вместо «Zero KB»
        sizeText = fmt.string(fromByteCount: Self.dirSize(url))
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
            PageHeader(title: "Очистка")
            Text("Кэш этого приложения. На iOS доступна очистка только собственных данных.")
                .font(.callout).foregroundStyle(Brand.muted)
            VStack(spacing: 4) {
                Text(cleaner.sizeText)
                    .font(.system(size: 40, weight: .bold)).foregroundStyle(Brand.green)
                Text("кэш приложения").font(.caption).foregroundStyle(Brand.muted)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 24)
            .background(Brand.glass)
            .clipShape(RoundedRectangle(cornerRadius: 16))
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
        .background(Brand.bg0)
        .onAppear { cleaner.refresh() }
    }
}
