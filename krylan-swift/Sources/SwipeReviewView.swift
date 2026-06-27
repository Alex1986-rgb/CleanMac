// Swipe-разбор фото: один кадр за раз, влево — в корзину, вправо — оставить.
// Удаление батчем через системное подтверждение (→ «Недавно удалённые», 30 дней).
// Главный UX-паттерн категории (Gemini Photos / Cleanup). Только PhotoKit, sandbox-safe.
import SwiftUI
import Photos

#if canImport(UIKit)
import UIKit
#endif

@MainActor
final class SwipeReviewModel: ObservableObject {
    @Published var assets: [PHAsset] = []
    @Published var index = 0
    @Published var marked: [PHAsset] = []
    @Published var status = "Готово к разбору"
    @Published var loading = false
    @Published var finished = false

    /// Грубая, честная оценка размера снимка (без приватных API): ~0.3 байта на пиксель (JPEG).
    static func estBytes(_ a: PHAsset) -> Int64 {
        Int64(Double(a.pixelWidth) * Double(a.pixelHeight) * 0.3)
    }

    var freedEstimate: Int64 { marked.reduce(0) { $0 + Self.estBytes($1) } }
    var current: PHAsset? { index < assets.count ? assets[index] : nil }
    var progress: Double { assets.isEmpty ? 0 : Double(index) / Double(assets.count) }

    static func fmt(_ b: Int64) -> String {
        let u = ["Б", "КБ", "МБ", "ГБ"]; var v = Double(b); var i = 0
        while v >= 1024 && i < u.count - 1 { v /= 1024; i += 1 }
        return i == 0 ? "\(Int(v)) \(u[i])" : String(format: "%.1f %@", v, u[i])
    }

    func load() {
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
        loading = true; status = "Загружаю медиатеку…"
        // Перебор медиатеки — вне главного потока, чтобы не блокировать UI.
        Task.detached(priority: .userInitiated) {
            let opts = PHFetchOptions()
            opts.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: false)]
            opts.fetchLimit = 300
            let fetch = PHAsset.fetchAssets(with: .image, options: opts)
            var collected: [PHAsset] = []
            fetch.enumerateObjects { a, _, _ in collected.append(a) }
            let arr = collected
            await MainActor.run {
                self.assets = arr; self.index = 0; self.marked = []; self.finished = false
                self.loading = false
                self.status = arr.isEmpty ? "Нет фото для разбора"
                    : "Свайпай: влево — удалить, вправо — оставить"
            }
        }
    }

    func keep() { advance() }

    func remove() {
        if let a = current { marked.append(a) }
        advance()
    }

    private func advance() {
        if index < assets.count { index += 1 }
        if index >= assets.count { finished = true }
    }

    /// Удаляет все помеченные кадры одним системным подтверждением.
    func commit() {
        guard !marked.isEmpty else { finished = true; return }
        let toDelete = marked
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.deleteAssets(toDelete as NSArray)
        }) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                if ok {
                    self.status = "Освобождено ≈ \(Self.fmt(self.freedEstimate)) — в «Недавно удалённые»"
                    self.marked = []
                } else {
                    self.status = "Удаление отменено"
                }
                self.finished = true
            }
        }
    }
}

struct SwipeReviewView: View {
    @StateObject private var m = SwipeReviewModel()
    @State private var drag: CGSize = .zero

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                Text("Быстрый разбор недавних фото по одному. Помеченные удаляются одним подтверждением — попадают в «Недавно удалённые» (30 дней).")
                    .font(.callout).foregroundStyle(Brand.muted)
                    .frame(maxWidth: .infinity, alignment: .leading)

                if m.assets.isEmpty {
                    Button { m.load() } label: {
                        Text(m.loading ? "Загружаю…" : "Начать разбор").bold()
                            .padding(.horizontal, 22).padding(.vertical, 12)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(m.loading)
                    Text(m.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                } else if let a = m.current, !m.finished {
                    // Счётчики
                    HStack {
                        Label("\(m.index)/\(m.assets.count)", systemImage: "rectangle.stack")
                            .font(.caption.bold()).foregroundStyle(Brand.muted)
                        Spacer()
                        Label("к удалению: \(m.marked.count) ≈ \(SwipeReviewModel.fmt(m.freedEstimate))",
                              systemImage: "trash")
                            .font(.caption.bold()).foregroundStyle(Brand.red)
                    }
                    ProgressView(value: m.progress).tint(Brand.green)

                    // Карточка с жестом свайпа
                    BigAssetImage(asset: a)
                        .frame(height: 380)
                        .clipShape(RoundedRectangle(cornerRadius: 22))
                        .overlay(alignment: .topLeading) { tag("ОСТАВИТЬ", Brand.green, drag.width > 40) }
                        .overlay(alignment: .topTrailing) { tag("УДАЛИТЬ", Brand.red, drag.width < -40) }
                        .offset(x: drag.width, y: 0)
                        .rotationEffect(.degrees(Double(drag.width) / 22))
                        .gesture(
                            DragGesture()
                                .onChanged { drag = $0.translation }
                                .onEnded { v in
                                    if v.translation.width < -90 { m.remove() }
                                    else if v.translation.width > 90 { m.keep() }
                                    drag = .zero
                                }
                        )
                        .animation(.spring(response: 0.3), value: drag)

                    HStack(spacing: 16) {
                        circleButton("trash", Brand.red) { m.remove() }
                        circleButton("checkmark", Brand.green) { m.keep() }
                    }
                } else {
                    // Финал разбора
                    VStack(spacing: 12) {
                        Image(systemName: m.marked.isEmpty ? "checkmark.seal.fill" : "trash.circle.fill")
                            .font(.system(size: 54)).foregroundStyle(m.marked.isEmpty ? Brand.green : Brand.red)
                        Text(m.marked.isEmpty ? "Разбор завершён" : "К удалению: \(m.marked.count) ≈ \(SwipeReviewModel.fmt(m.freedEstimate))")
                            .font(.headline).foregroundStyle(Brand.text)
                        Text(m.status).font(.subheadline).foregroundStyle(Brand.muted)
                        if !m.marked.isEmpty {
                            Button { m.commit() } label: {
                                Text("Удалить помеченные").bold()
                                    .padding(.horizontal, 22).padding(.vertical, 12)
                                    .background(Brand.red).foregroundStyle(.white).clipShape(Capsule())
                            }.buttonStyle(.plain)
                        }
                        Button { m.load() } label: {
                            Text("Разобрать ещё раз").font(.subheadline.bold()).foregroundStyle(Brand.green)
                        }.buttonStyle(.plain)
                    }
                    .padding(.top, 20)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(StarfieldView())
    }

    private func tag(_ text: String, _ color: Color, _ show: Bool) -> some View {
        Text(text).font(.caption.bold()).foregroundStyle(.white)
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(color).clipShape(Capsule())
            .padding(14).opacity(show ? 1 : 0)
    }

    private func circleButton(_ icon: String, _ color: Color, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon).font(.title2.bold()).foregroundStyle(color)
                .frame(width: 62, height: 62)
                .background(color.opacity(0.15)).clipShape(Circle())
                .overlay(Circle().stroke(color.opacity(0.5), lineWidth: 1.5))
        }.buttonStyle(.plain)
    }
}

/// Крупное изображение PHAsset для карточки разбора.
struct BigAssetImage: View {
    let asset: PHAsset
    @State private var image: Image?

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 22).fill(Brand.track)
            if let image {
                image.resizable().scaledToFill()
            } else {
                ProgressView().tint(Brand.muted)
            }
        }
        .frame(maxWidth: .infinity)
        .clipped()
        .id(asset.localIdentifier)
        .onAppear(perform: load)
    }

    private func load() {
        let opts = PHImageRequestOptions()
        opts.isNetworkAccessAllowed = true
        opts.deliveryMode = .opportunistic
        PHImageManager.default().requestImage(
            for: asset, targetSize: CGSize(width: 800, height: 800),
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
