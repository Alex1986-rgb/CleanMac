// Онбординг KRYLAN — честное знакомство при первом запуске (до основного интерфейса).
// Фирменный стиль: тёмный фон + звёздное небо StarfieldView + glass-карточки.
// Слоган: «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
import SwiftUI

/// Один пункт «что умеет» KRYLAN.
private struct Feature: Identifiable {
    let id = UUID()
    let icon: String
    let tint: Color
    let title: String
    let subtitle: String
}

struct OnboardingView: View {
    /// Вызывается по нажатию «Начать» — поднимает флаг krylan.onboarded.
    var onDone: () -> Void

    private let features: [Feature] = [
        Feature(icon: "rectangle.stack.badge.minus", tint: Brand.green,
                title: "Разбор фото и Live Photos",
                subtitle: "Просматривайте снимки по одному и решайте, что оставить."),
        Feature(icon: "photo.on.rectangle.angled", tint: Brand.cyan,
                title: "Дубли, серии и размытые",
                subtitle: "KRYLAN находит похожие кадры и неудачные снимки."),
        Feature(icon: "person.2", tint: Brand.purple,
                title: "Дубликаты контактов",
                subtitle: "Объединяйте повторяющиеся карточки в адресной книге."),
        Feature(icon: "internaldrive", tint: Brand.blue,
                title: "Хранилище под контролем",
                subtitle: "Видно, что занимает место, и где можно освободить."),
    ]

    var body: some View {
        ZStack {
            StarfieldView()

            VStack(spacing: 0) {
                ScrollView {
                    VStack(spacing: 22) {
                        header
                        VStack(spacing: 12) {
                            ForEach(features) { f in featureCard(f) }
                        }
                        privacyCard
                    }
                    .padding(.horizontal, 22)
                    .padding(.top, 48)
                    .padding(.bottom, 24)
                }

                startButton
            }
        }
        .preferredColorScheme(.dark)
        #if os(iOS)
        .statusBarHidden(false)
        #endif
    }

    // MARK: - Шапка

    private var header: some View {
        VStack(spacing: 8) {
            Text("🪽 \(Brand.name)")
                .font(.system(size: 40, weight: .bold))
                .foregroundStyle(Brand.text)
            Text("«\(Brand.slogan)»")
                .font(.title3.weight(.semibold))
                .foregroundStyle(Brand.green)
            Text("Наведём порядок в фото, контактах и хранилище.")
                .font(.subheadline)
                .foregroundStyle(Brand.muted)
                .multilineTextAlignment(.center)
                .padding(.top, 2)
        }
        .padding(.bottom, 4)
    }

    // MARK: - Карточка фичи

    private func featureCard(_ f: Feature) -> some View {
        HStack(spacing: 14) {
            Image(systemName: f.icon)
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(f.tint)
                .frame(width: 44, height: 44)
                .background(f.tint.opacity(0.15), in: RoundedRectangle(cornerRadius: 12, style: .continuous))

            VStack(alignment: .leading, spacing: 3) {
                Text(f.title)
                    .font(.headline)
                    .foregroundStyle(Brand.text)
                Text(f.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(Brand.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Brand.glass.opacity(0.7), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.white.opacity(0.06), lineWidth: 1)
        )
    }

    // MARK: - Честный посыл о приватности

    private var privacyCard: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "lock.shield")
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(Brand.green)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 6) {
                Text("Честно о приватности")
                    .font(.subheadline.bold())
                    .foregroundStyle(Brand.text)
                Text("KRYLAN работает локально и ничего не отправляет в сеть. Удаление всегда проходит через системное подтверждение — файлы попадают в «Недавно удалённые», откуда их можно вернуть.")
                    .font(.footnote)
                    .foregroundStyle(Brand.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Brand.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Brand.green.opacity(0.25), lineWidth: 1)
        )
    }

    // MARK: - Кнопка «Начать»

    private var startButton: some View {
        VStack(spacing: 6) {
            Button(action: onDone) {
                Text("Начать")
                    .font(.headline)
                    .foregroundStyle(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Brand.green, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            }
            .buttonStyle(.plain)

            Text(Brand.author)
                .font(.caption2)
                .foregroundStyle(Brand.muted)
        }
        .padding(.horizontal, 22)
        .padding(.top, 12)
        .padding(.bottom, 16)
        .background(.ultraThinMaterial)
    }
}

#Preview {
    OnboardingView(onDone: {})
}
