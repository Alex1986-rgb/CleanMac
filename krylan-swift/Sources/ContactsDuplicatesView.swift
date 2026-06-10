// Дубли контактов (Contacts framework): список групп с именами и телефонами.
import SwiftUI
import Contacts

struct ContactGroup: Identifiable {
    let id = UUID()
    let name: String
    let count: Int
    let phones: [String]
}

@MainActor
final class ContactScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var groups: [ContactGroup] = []
    @Published var scanning = false

    func scan() {
        status = "Запрос доступа к контактам…"
        let store = CNContactStore()
        store.requestAccess(for: .contacts) { [weak self] ok, _ in
            Task { @MainActor in
                guard let self else { return }
                guard ok else { self.status = "Нет доступа к контактам"; return }
                self.run(store)
            }
        }
    }

    private func run(_ store: CNContactStore) {
        scanning = true
        status = "Сканирую контакты…"
        let keys = [CNContactGivenNameKey, CNContactFamilyNameKey,
                    CNContactPhoneNumbersKey] as [CNKeyDescriptor]
        let req = CNContactFetchRequest(keysToFetch: keys)
        var byName: [String: (count: Int, phones: Set<String>)] = [:]
        do {
            try store.enumerateContacts(with: req) { c, _ in
                let name = (c.givenName + " " + c.familyName)
                    .trimmingCharacters(in: .whitespaces)
                guard !name.isEmpty else { return }
                let key = name.lowercased()
                var entry = byName[key] ?? (0, [])
                entry.count += 1
                c.phoneNumbers.forEach { entry.phones.insert($0.value.stringValue) }
                byName[key] = entry
            }
            groups = byName
                .filter { $0.value.count > 1 }
                .map { ContactGroup(name: $0.key.capitalized, count: $0.value.count,
                                    phones: Array($0.value.phones).sorted()) }
                .sorted { $0.count > $1.count }
            status = groups.isEmpty ? "Дубликатов не найдено"
                                    : "Групп дублей по имени: \(groups.count)"
        } catch {
            status = "Не удалось прочитать контакты"
        }
        scanning = false
    }
}

struct ContactsDuplicatesView: View {
    @StateObject private var scanner = ContactScanner()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Поиск контактов с одинаковыми именами. Объединение — в приложении «Контакты» (KRYLAN не меняет вашу книгу).")
                    .font(.callout).foregroundStyle(Brand.muted)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                }

                ForEach(scanner.groups) { g in
                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "person.2.fill")
                            .font(.title3).foregroundStyle(Brand.blue)
                            .frame(width: 40, height: 40)
                            .background(Brand.blue.opacity(0.15))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                        VStack(alignment: .leading, spacing: 3) {
                            Text(g.name).font(.headline).foregroundStyle(Brand.text)
                            Text("\(g.count) записи с этим именем")
                                .font(.caption).foregroundStyle(Brand.muted)
                            if !g.phones.isEmpty {
                                Text(g.phones.prefix(3).joined(separator: " · "))
                                    .font(.caption2).foregroundStyle(Brand.muted)
                            }
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Brand.glass))
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
        }
        .background(Brand.bg0)
    }
}
