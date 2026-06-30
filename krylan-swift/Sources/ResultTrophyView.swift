// Экран-трофей «До → После»: красивый честный результат прогона ✨ Оптимизировать.
// Можно поделиться (UIActivityViewController) и сохранить картинку (ImageRenderer, iOS 16+).
// Цифры честные: реально очищенный кэш, честное «было → стало» по диску
// (или «освободится после очистки Недавно удалённых»), потенциал к разбору.
// Navy-стиль KRYLAN. macOS-таргет не ломаем: share/save под #if os(iOS),
// на macOS — сохранение PNG в Загрузки.
import SwiftUI
#if os(iOS)
import UIKit
#endif
#if os(macOS)
import AppKit
#endif

struct ResultTrophyView: View {
    let result: OptimizeResult
    @Environment(\.dismiss) private var dismiss

    // Тост о результате сохранения.
    @State private var toast: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    // Карточка-трофей, которую и рендерим в картинку.
                    TrophyCard(result: result)
                        .padding(.horizontal, 4)

                    actionButtons
                        .padding(.horizontal, 4)

                    Text("Цифры честные: показываем реально очищенный кэш и фактическое изменение свободного места. KRYLAN не делает фейковых «ускорений».")
                        .font(.caption2)
                        .foregroundStyle(Brand.muted)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 12)
                }
                .padding(20)
            }
            .background(Brand.bg0.ignoresSafeArea())
            .navigationTitle("Результат")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(Brand.bg0, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
                    }
                }
            }
            #else
            .toolbar {
                ToolbarItem {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(Brand.muted)
                    }
                }
            }
            #endif
            .overlay(alignment: .bottom) { toastView }
        }
        .presentationDetents([.large])
        .presentationDragIndicator(.visible)
        .presentationBackground(Brand.bg0)
        .preferredColorScheme(.dark)
    }

    // MARK: - Кнопки действий

    @ViewBuilder
    private var actionButtons: some View {
        VStack(spacing: 12) {
            #if os(iOS)
            SheetActionButton(title: "Поделиться", icon: "square.and.arrow.up", tint: Brand.green) {
                if let img = renderTrophy() {
                    // Презентуем activity-controller императивно из топ-VC —
                    // надёжнее, чем .sheet поверх уже показанного листа.
                    SharePresenter.present(items: [img, trophyShareText])
                }
            }
            SheetActionButton(title: "Сохранить картинку", icon: "square.and.arrow.down",
                              filled: false, tint: Brand.cyan) {
                saveTrophy()
            }
            #else
            SheetActionButton(title: "Сохранить картинку в Загрузки",
                              icon: "square.and.arrow.down", tint: Brand.green) {
                saveTrophy()
            }
            #endif
        }
    }

    private var trophyShareText: String {
        var lines = ["\(Brand.name) — \(Brand.slogan)"]
        lines.append("Очищено кэша: \(OptimizeEngine.human(result.cacheFreedBytes))")
        if result.foundToReviewTotal > 0 {
            lines.append("Найдено к разбору: \(result.foundToReviewTotal)")
        }
        if result.estReclaimBytes > 0 {
            lines.append("Можно освободить ещё ≈ \(OptimizeEngine.human(result.estReclaimBytes))")
        }
        return lines.joined(separator: "\n")
    }

    // MARK: - Рендер карточки в картинку (ImageRenderer, iOS 16+/macOS 13+)

    @MainActor
    private func renderTrophy() -> PlatformImage? {
        let card = TrophyCard(result: result)
            .frame(width: 360)
            .background(Brand.bg0)
        let renderer = ImageRenderer(content: card)
        renderer.scale = 3        // ретина-качество для шеринга
        renderer.isOpaque = true
        #if os(iOS)
        return renderer.uiImage
        #else
        return renderer.nsImage
        #endif
    }

    private func saveTrophy() {
        guard let img = renderTrophy() else { return }
        #if os(iOS)
        ImageSaver.shared.save(img) { ok in
            showToast(ok ? "Сохранено в Фото" : "Не удалось сохранить — проверьте доступ к Фото")
        }
        #else
        let url = FileManager.default
            .urls(for: .downloadsDirectory, in: .userDomainMask).first?
            .appendingPathComponent("KRYLAN-результат.png")
        if let url, let tiff = img.tiffRepresentation,
           let rep = NSBitmapImageRep(data: tiff),
           let png = rep.representation(using: .png, properties: [:]) {
            try? png.write(to: url)
            showToast("Сохранено в Загрузки")
        } else {
            showToast("Не удалось сохранить")
        }
        #endif
    }

    private func showToast(_ text: String) {
        withAnimation { toast = text }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.2) {
            withAnimation { toast = nil }
        }
    }

    @ViewBuilder
    private var toastView: some View {
        if let toast {
            Text(toast)
                .font(.subheadline.bold())
                .foregroundStyle(Brand.text)
                .padding(.horizontal, 18).padding(.vertical, 12)
                .background(Capsule().fill(Brand.glass))
                .overlay(Capsule().stroke(Brand.track, lineWidth: 1))
                .padding(.bottom, 24)
                .transition(.move(edge: .bottom).combined(with: .opacity))
        }
    }
}

// MARK: - Сама карточка-трофей (она же рендерится в картинку)

struct TrophyCard: View {
    let result: OptimizeResult

    /// Освобождено по диску ≈ стало − было (если система уже отдала место).
    private var diskFreedGB: Int { max(0, result.diskFreeAfterGB - result.diskFreeBeforeGB) }
    /// Удалённое медиа уходит в «Недавно удалённые» — диск не растёт сразу,
    /// но кэш мы очистили реально. Если факт-прирост = 0, говорим про потенциал честно.
    private var diskMovedImmediately: Bool { diskFreedGB > 0 }

    var body: some View {
        VStack(spacing: 18) {
            badge

            VStack(spacing: 4) {
                Text("Оптимизировано")
                    .font(.title2.bold())
                    .foregroundStyle(Brand.text)
                Text(Brand.slogan)
                    .font(.caption)
                    .foregroundStyle(Brand.cyan)
            }

            diskBeforeAfter

            statsGrid

            if result.estReclaimBytes > 0 && !result.photosDenied {
                potentialNote
            }

            footer
        }
        .padding(22)
        .frame(maxWidth: .infinity)
        .background(cardBackground)
        .overlay(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .stroke(
                    LinearGradient(colors: [Brand.cyan.opacity(0.55), Brand.glow.opacity(0.25)],
                                   startPoint: .top, endPoint: .bottom),
                    lineWidth: 1.5)
        )
        .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
    }

    // Фон карточки: navy-градиент + центральное свечение.
    private var cardBackground: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(
                    LinearGradient(colors: [Brand.bg0, Brand.bg1],
                                   startPoint: .top, endPoint: .bottom)
                )
            RadialGradient(colors: [Brand.glow.opacity(0.45), .clear],
                           center: .top, startRadius: 0, endRadius: 260)
                .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
        }
    }

    // MARK: Бейдж-трофей (звезда + крылья KRYLAN, свечение).

    private var badge: some View {
        ZStack {
            Circle()
                .fill(RadialGradient(colors: [Brand.green.opacity(0.40), .clear],
                                     center: .center, startRadius: 0, endRadius: 80))
                .frame(width: 150, height: 150)
            Circle()
                .fill(
                    LinearGradient(colors: [Brand.green, Brand.cyan],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )
                .frame(width: 88, height: 88)
                .shadow(color: Brand.green.opacity(0.6), radius: 18)

            // Крылья по бокам звезды — фирменный знак «дай устройству крылья».
            HStack(spacing: 56) {
                WingShape()
                    .fill(Brand.cyan.opacity(0.9))
                    .frame(width: 34, height: 22)
                WingShape()
                    .fill(Brand.cyan.opacity(0.9))
                    .frame(width: 34, height: 22)
                    .scaleEffect(x: -1)
            }

            Image(systemName: "star.fill")
                .font(.system(size: 38, weight: .bold))
                .foregroundStyle(Color(red: 0.02, green: 0.05, blue: 0.10))
        }
        .frame(height: 150)
    }

    // MARK: Диск «Было → Стало»

    private var diskBeforeAfter: some View {
        VStack(spacing: 10) {
            Text("СВОБОДНО НА ДИСКЕ")
                .font(.caption2.bold())
                .foregroundStyle(Brand.muted)
                .tracking(1.2)

            HStack(spacing: 12) {
                beforeAfterPill(title: "Было", value: "\(result.diskFreeBeforeGB) ГБ", tint: Brand.muted)
                Image(systemName: "arrow.right")
                    .font(.headline.bold())
                    .foregroundStyle(Brand.cyan)
                beforeAfterPill(title: "Стало", value: "\(result.diskFreeAfterGB) ГБ", tint: Brand.green)
            }

            if diskMovedImmediately {
                Text("Освобождено ≈ \(diskFreedGB) ГБ")
                    .font(.subheadline.bold())
                    .foregroundStyle(Brand.green)
            } else {
                Text("Освобождено ≈ \(OptimizeEngine.human(result.cacheFreedBytes)). Удалённое медиа появится после очистки «Недавно удалённых».")
                    .font(.caption)
                    .foregroundStyle(Brand.muted)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(.vertical, 14).padding(.horizontal, 14)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 18).fill(Brand.glass.opacity(0.6)))
    }

    private func beforeAfterPill(title: String, value: String, tint: Color) -> some View {
        VStack(spacing: 2) {
            Text(title).font(.caption2).foregroundStyle(Brand.muted)
            Text(value)
                .font(.title3.bold().monospacedDigit())
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.bg1.opacity(0.7)))
    }

    // MARK: Статы-плитки

    private var statsGrid: some View {
        let cols = [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)]
        return LazyVGrid(columns: cols, spacing: 12) {
            stat("trash.fill", "Очищено кэша",
                 OptimizeEngine.human(result.cacheFreedBytes), Brand.green)
            stat("magnifyingglass", "Найдено к разбору",
                 "\(result.foundToReviewTotal)", Brand.cyan)
            if !result.photosDenied {
                stat("photo.on.rectangle.angled", "Дубли фото",
                     "\(result.photoDupExtras)", Brand.purple)
                stat("film", "Крупные видео",
                     "\(result.largeVideos)", Brand.blue)
            }
        }
    }

    private func stat(_ icon: String, _ title: String, _ value: String, _ tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Image(systemName: icon).font(.subheadline).foregroundStyle(tint)
            Text(value)
                .font(.title3.bold().monospacedDigit())
                .foregroundStyle(Brand.text)
                .lineLimit(1).minimumScaleFactor(0.6)
            Text(title).font(.caption2).foregroundStyle(Brand.muted)
                .lineLimit(2).fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass.opacity(0.6)))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(tint.opacity(0.25), lineWidth: 1))
    }

    private var potentialNote: some View {
        HStack(spacing: 10) {
            Image(systemName: "sparkles").foregroundStyle(Brand.yellow)
            Text("Можно освободить ещё ≈ \(OptimizeEngine.human(result.estReclaimBytes)), разобрав найденное.")
                .font(.caption)
                .foregroundStyle(Brand.text)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Brand.glass.opacity(0.5)))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Brand.yellow.opacity(0.3), lineWidth: 1))
    }

    private var footer: some View {
        HStack(spacing: 6) {
            Image(systemName: "checkmark.seal.fill").foregroundStyle(Brand.green)
            Text(Brand.name).font(.caption.bold()).foregroundStyle(Brand.text)
            Text("• \(Self.dateFmt.string(from: result.finishedAt))")
                .font(.caption2).foregroundStyle(Brand.muted)
        }
        .padding(.top, 2)
    }

    private static let dateFmt: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "d MMM yyyy, HH:mm"
        f.locale = Locale(identifier: "ru_RU")
        return f
    }()
}

// MARK: - Кросс-платформенный тип картинки + сохранение в Фото (iOS)

#if os(iOS)
typealias PlatformImage = UIImage

/// Показ UIActivityViewController из самого верхнего презентующего контроллера.
/// Так шеринг работает даже когда трофей сам открыт как лист (без конфликта .sheet).
enum SharePresenter {
    static func present(items: [Any]) {
        guard let top = topViewController() else { return }
        let vc = UIActivityViewController(activityItems: items, applicationActivities: nil)
        // iPad: activity-controller требует источник для popover.
        if let pop = vc.popoverPresentationController {
            pop.sourceView = top.view
            pop.sourceRect = CGRect(x: top.view.bounds.midX, y: top.view.bounds.maxY - 60,
                                    width: 1, height: 1)
            pop.permittedArrowDirections = []
        }
        top.present(vc, animated: true)
    }

    private static func topViewController(_ base: UIViewController? = nil) -> UIViewController? {
        let root = base ?? UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
            .first(where: { $0.isKeyWindow })?.rootViewController
        if let nav = root as? UINavigationController {
            return topViewController(nav.visibleViewController)
        }
        if let tab = root as? UITabBarController {
            return topViewController(tab.selectedViewController)
        }
        if let presented = root?.presentedViewController {
            return topViewController(presented)
        }
        return root
    }
}

/// Сохранение UIImage в фотопленку с колбэком об успехе (нужен NSPhotoLibraryAddUsageDescription
/// либо уже выданный readWrite-доступ; у KRYLAN доступ к Фото уже запрашивается).
final class ImageSaver: NSObject {
    static let shared = ImageSaver()
    private var completion: ((Bool) -> Void)?

    func save(_ image: UIImage, completion: @escaping (Bool) -> Void) {
        self.completion = completion
        UIImageWriteToSavedPhotosAlbum(image, self,
            #selector(didFinish(_:didFinishSavingWithError:contextInfo:)), nil)
    }

    @objc private func didFinish(_ image: UIImage, didFinishSavingWithError error: Error?,
                                 contextInfo: UnsafeRawPointer) {
        let ok = (error == nil)
        DispatchQueue.main.async { self.completion?(ok); self.completion = nil }
    }
}
#else
typealias PlatformImage = NSImage
#endif

// MARK: - Простое крыло (фирменный знак KRYLAN), рисуется кривыми Безье.

struct WingShape: Shape {
    func path(in rect: CGRect) -> Path {
        var p = Path()
        let w = rect.width, h = rect.height
        // База у звезды (правый край фигуры), три «пера» влево.
        p.move(to: CGPoint(x: w, y: h * 0.5))
        p.addCurve(to: CGPoint(x: 0, y: h * 0.05),
                   control1: CGPoint(x: w * 0.55, y: -h * 0.05),
                   control2: CGPoint(x: w * 0.25, y: 0))
        p.addCurve(to: CGPoint(x: w * 0.35, y: h * 0.55),
                   control1: CGPoint(x: w * 0.30, y: h * 0.25),
                   control2: CGPoint(x: w * 0.50, y: h * 0.40))
        p.addCurve(to: CGPoint(x: 0, y: h * 0.6),
                   control1: CGPoint(x: w * 0.20, y: h * 0.55),
                   control2: CGPoint(x: w * 0.10, y: h * 0.55))
        p.addCurve(to: CGPoint(x: w * 0.45, y: h * 0.85),
                   control1: CGPoint(x: w * 0.20, y: h * 0.80),
                   control2: CGPoint(x: w * 0.35, y: h * 0.80))
        p.addCurve(to: CGPoint(x: w, y: h * 0.5),
                   control1: CGPoint(x: w * 0.70, y: h * 0.95),
                   control2: CGPoint(x: w * 0.92, y: h * 0.72))
        p.closeSubpath()
        return p
    }
}
