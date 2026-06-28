// Общие элементы для экранов разбора медиа (видео, скриншоты, фото-дубли):
//  • кружок-индикатор мультивыбора поверх превью;
//  • честный баннер про «Недавно удалённые» с кнопкой «Открыть Фото»;
//  • открытие приложения «Фото» (sandbox-safe, без приватных API).
// Удаление медиа везде — только через системный диалог PHPhotoLibrary.
import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

/// Открыть системное приложение «Фото» (для перехода в «Недавно удалённые»).
/// Конкретный альбом открыть публичного API нет — открываем сами «Фото», это ок.
enum PhotosApp {
    static func open() {
        #if os(iOS)
        if let url = URL(string: "photos-redirect://") {
            UIApplication.shared.open(url)
        }
        #elseif os(macOS)
        if let url = URL(string: "photos://") {
            NSWorkspace.shared.open(url)
        }
        #endif
    }
}

/// Кружок-индикатор выбора в углу превью.
/// Пусто — не выбран; зелёная галочка (checkmark.circle.fill) — выбран.
struct SelectionCircle: View {
    let isSelected: Bool
    var body: some View {
        ZStack {
            Circle()
                .fill(.black.opacity(0.55))
                .frame(width: 22, height: 22)
            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(Brand.green)
                    .background(Circle().fill(.black.opacity(0.85)))
            } else {
                Circle()
                    .strokeBorder(.white.opacity(0.85), lineWidth: 2)
                    .frame(width: 21, height: 21)
            }
        }
        .shadow(color: .black.opacity(0.4), radius: 2, y: 1)
    }
}

/// Честное напоминание: удалённое лишь перенесено в «Недавно удалённые».
/// Реально место освобождается только после очистки этого альбома.
struct RecentlyDeletedBanner: View {
    /// Кол-во только что перенесённых объектов (для текста). 0 — не показываем счётчик.
    var movedCount: Int = 0
    /// Колбэк закрытия баннера.
    var onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(Brand.yellow)
                    .font(.headline)
                VStack(alignment: .leading, spacing: 4) {
                    Text(movedCount > 0
                         ? "Перенесено в «Недавно удалённые»: \(movedCount)"
                         : "Перенесено в «Недавно удалённые»")
                        .font(.subheadline.bold()).foregroundStyle(Brand.text)
                    Text("Место пока НЕ освобождено. Чтобы реально освободить место:\nФото → Альбомы → Недавно удалённые → Выбрать → Удалить.")
                        .font(.caption).foregroundStyle(Brand.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                Button { onClose() } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(Brand.muted)
                }.buttonStyle(.plain)
            }
            Button { PhotosApp.open() } label: {
                Label("Открыть Фото", systemImage: "photo.on.rectangle.angled")
                    .font(.caption.bold())
                    .padding(.horizontal, 14).padding(.vertical, 8)
                    .background(Brand.blue).foregroundStyle(.white)
                    .clipShape(Capsule())
            }.buttonStyle(.plain)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(Brand.yellow.opacity(0.35), lineWidth: 1))
    }
}

/// Нижняя панель действий мультивыбора: «Выбрать все/Снять выбор» + «Удалить выбранные (N)».
struct SelectionActionBar: View {
    let selectedCount: Int
    let totalCount: Int
    /// Доп. подпись (например, оценка освобождаемого размера). Пусто — не показываем.
    var subtitle: String = ""
    let onSelectAll: () -> Void
    let onClear: () -> Void
    let onDelete: () -> Void

    private var allSelected: Bool { selectedCount == totalCount && totalCount > 0 }

    var body: some View {
        VStack(spacing: 10) {
            HStack {
                Button(allSelected ? "Снять выбор" : "Выбрать все") {
                    allSelected ? onClear() : onSelectAll()
                }
                .font(.caption.bold()).foregroundStyle(Brand.blue).buttonStyle(.plain)
                Spacer()
                if !subtitle.isEmpty {
                    Text(subtitle).font(.caption.bold()).foregroundStyle(Brand.muted)
                }
            }
            Button { onDelete() } label: {
                Text("Удалить выбранные (\(selectedCount))").bold()
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(selectedCount > 0 ? Brand.red : Brand.track)
                    .foregroundStyle(selectedCount > 0 ? .white : Brand.muted)
                    .clipShape(Capsule())
            }
            .buttonStyle(.plain)
            .disabled(selectedCount == 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
    }
}

/// Аккуратное пустое состояние со значком и текстом.
struct EmptyStateView: View {
    let icon: String
    let title: String
    var subtitle: String = ""
    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 42)).foregroundStyle(Brand.muted)
            Text(title).font(.headline).foregroundStyle(Brand.text)
            if !subtitle.isEmpty {
                Text(subtitle).font(.subheadline).foregroundStyle(Brand.muted)
                    .multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }
}
