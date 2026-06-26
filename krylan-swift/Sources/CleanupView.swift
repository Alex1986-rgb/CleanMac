// Очистка собственного кэша приложения (разрешено на iOS и macOS).
import SwiftUI
#if os(iOS)
import UIKit
#endif

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

/// Запись о подкаталоге кэша: имя и размер в байтах.
struct CacheEntry: Identifiable {
    let id = UUID()
    let name: String
    let bytes: Int64
}

/// Считает размеры подпапок/файлов внутри собственного .cachesDirectory.
/// Только наш sandbox-контейнер — чужие данные недоступны и не сканируются.
@MainActor
final class CacheBreakdown: ObservableObject {
    @Published var entries: [CacheEntry] = []

    private var cachesURL: URL? {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
    }

    func scan() {
        guard let url = cachesURL else { entries = []; return }
        let fm = FileManager.default
        let items = (try? fm.contentsOfDirectory(
            at: url,
            includingPropertiesForKeys: [.isDirectoryKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        )) ?? []

        var result: [CacheEntry] = []
        for item in items {
            let isDir = (try? item.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) ?? false
            let bytes: Int64
            if isDir {
                bytes = CacheCleaner.dirSize(item)
            } else {
                bytes = Int64((try? item.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)
            }
            if bytes > 0 {
                result.append(CacheEntry(name: item.lastPathComponent, bytes: bytes))
            }
        }
        entries = Array(result.sorted { $0.bytes > $1.bytes }.prefix(8))
    }

    /// Человекочитаемый размер: Б/КБ/МБ/ГБ.
    static func human(_ bytes: Int64) -> String {
        let units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
        var value = Double(bytes)
        var idx = 0
        while value >= 1024 && idx < units.count - 1 {
            value /= 1024
            idx += 1
        }
        if idx == 0 {
            return "\(Int(value)) \(units[idx])"
        }
        return String(format: "%.1f %@", value, units[idx])
    }
}

struct CleanupView: View {
    @StateObject private var cleaner = CacheCleaner()
    @StateObject private var breakdown = CacheBreakdown()

    var body: some View {
        ScrollView {
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

                breakdownCard

                Button { cleaner.clean(); breakdown.scan() } label: {
                    Text("Очистить кэш").bold()
                        .padding(.horizontal, 20).padding(.vertical, 11)
                        .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                }.buttonStyle(.plain)

                if !cleaner.status.isEmpty {
                    Text(cleaner.status).foregroundStyle(Brand.green)
                }

                recentlyDeletedCard

                Spacer(minLength: 0)
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(StarfieldView())
        .onAppear { cleaner.refresh(); breakdown.scan() }
    }

    // MARK: - Разбивка кэша по подпапкам

    @ViewBuilder
    private var breakdownCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Что внутри кэша")
                .font(.headline).foregroundStyle(Brand.text)
            Text("Крупнейшие папки и файлы кэша этого приложения. Очистка удалит именно их.")
                .font(.caption).foregroundStyle(Brand.muted)

            if breakdown.entries.isEmpty {
                Text("Кэш пуст.")
                    .font(.callout).foregroundStyle(Brand.muted)
                    .padding(.top, 4)
            } else {
                let maxBytes = breakdown.entries.first?.bytes ?? 1
                ForEach(breakdown.entries) { entry in
                    VStack(alignment: .leading, spacing: 5) {
                        HStack {
                            Text(entry.name)
                                .font(.callout).foregroundStyle(Brand.text)
                                .lineLimit(1).truncationMode(.middle)
                            Spacer(minLength: 8)
                            Text(CacheBreakdown.human(entry.bytes))
                                .font(.callout.monospacedDigit())
                                .foregroundStyle(Brand.muted)
                        }
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Brand.track)
                                Capsule().fill(Brand.green)
                                    .frame(width: max(4, geo.size.width *
                                        CGFloat(Double(entry.bytes) / Double(max(maxBytes, 1)))))
                            }
                        }
                        .frame(height: 6)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    // MARK: - Недавно удалённые (awareness)

    @ViewBuilder
    private var recentlyDeletedCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: "trash")
                    .foregroundStyle(Brand.yellow)
                Text("Недавно удалённые")
                    .font(.headline).foregroundStyle(Brand.text)
            }
            Text("Удалённые фото и видео хранятся в системном альбоме «Недавно удалённые» до 30 дней и всё это время занимают место. Очистить их можно только в приложении Фото — мы не имеем доступа к чужим данным.")
                .font(.caption).foregroundStyle(Brand.muted)

            Button { openPhotos() } label: {
                Text("Открыть Фото").bold()
                    .padding(.horizontal, 20).padding(.vertical, 11)
                    .frame(maxWidth: .infinity)
                    .background(Brand.glass)
                    .overlay(Capsule().stroke(Brand.yellow, lineWidth: 1))
                    .foregroundStyle(Brand.yellow)
                    .clipShape(Capsule())
            }.buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }

    private func openPhotos() {
        #if os(iOS)
        if let url = URL(string: "photos-redirect://") {
            UIApplication.shared.open(url)
        }
        #elseif os(macOS)
        if let url = URL(string: "/System/Applications/Photos.app") {
            NSWorkspace.shared.open(url)
        }
        #endif
    }
}
