// Контакты (Contacts framework): дубли по имени + неполные записи (без имени/без номера).
// Объединение/правка — в системном приложении «Контакты»; KRYLAN не меняет книгу сам.
import SwiftUI
import Contacts

struct ContactGroup: Identifiable {
    let id = UUID()
    let name: String
    let count: Int
    let phones: [String]
    var subtitle: String = ""
}

@MainActor
final class ContactScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var groups: [ContactGroup] = []        // дубли по имени
    @Published var incomplete: [ContactGroup] = []     // без имени или без номера
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
        var incompleteList: [ContactGroup] = []
        do {
            try store.enumerateContacts(with: req) { c, _ in
                let name = (c.givenName + " " + c.familyName)
                    .trimmingCharacters(in: .whitespaces)
                let phones = c.phoneNumbers.map { $0.value.stringValue }
                if name.isEmpty && !phones.isEmpty {
                    incompleteList.append(ContactGroup(name: "Без имени", count: 1,
                                                       phones: phones, subtitle: "нет имени"))
                } else if !name.isEmpty && phones.isEmpty {
                    incompleteList.append(ContactGroup(name: name, count: 1,
                                                       phones: [], subtitle: "нет номера"))
                }
                guard !name.isEmpty else { return }
                let key = name.lowercased()
                var entry = byName[key] ?? (0, [])
                entry.count += 1
                phones.forEach { entry.phones.insert($0) }
                byName[key] = entry
            }
            groups = byName
                .filter { $0.value.count > 1 }
                .map { ContactGroup(name: $0.key.capitalized, count: $0.value.count,
                                    phones: Array($0.value.phones).sorted()) }
                .sorted { $0.count > $1.count }
            incomplete = incompleteList.sorted { $0.name < $1.name }
            let parts = [groups.isEmpty ? nil : "дублей: \(groups.count)",
                         incomplete.isEmpty ? nil : "неполных: \(incomplete.count)"].compactMap { $0 }
            status = parts.isEmpty ? "Всё в порядке" : "Найдено — " + parts.joined(separator: ", ")
        } catch {
            status = "Не удалось прочитать контакты"
        }
        scanning = false
    }
}

struct ContactsDuplicatesView: View {
    @StateObject private var scanner = ContactScanner()
    @State private var mode = 0   // 0 — дубли, 1 — неполные

    private var items: [ContactGroup] { mode == 0 ? scanner.groups : scanner.incomplete }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Дубли по имени и неполные записи. Правки — в приложении «Контакты» (KRYLAN не меняет вашу книгу).")
                    .font(.callout).foregroundStyle(Brand.muted)

                HStack(spacing: 12) {
                    Button { scanner.scan() } label: {
                        Text(scanner.scanning ? "Сканирую…" : "Сканировать").bold()
                            .padding(.horizontal, 20).padding(.vertical, 11)
                            .background(Brand.green).foregroundStyle(.black).clipShape(Capsule())
                    }.buttonStyle(.plain).disabled(scanner.scanning)
                    Text(scanner.status).font(.subheadline.bold()).foregroundStyle(Brand.green)
                }

                Picker("", selection: $mode) {
                    Text("Дубли (\(scanner.groups.count))").tag(0)
                    Text("Неполные (\(scanner.incomplete.count))").tag(1)
                }
                .pickerStyle(.segmented)

                if items.isEmpty {
                    Text(mode == 0 ? "Дубликатов нет." : "Неполных контактов нет.")
                        .font(.callout).foregroundStyle(Brand.muted).padding(.top, 8)
                }

                ForEach(items) { g in
                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: mode == 0 ? "person.2.fill" : "person.crop.circle.badge.exclamationmark")
                            .font(.title3).foregroundStyle(mode == 0 ? Brand.blue : Brand.yellow)
                            .frame(width: 40, height: 40)
                            .background((mode == 0 ? Brand.blue : Brand.yellow).opacity(0.15))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                        VStack(alignment: .leading, spacing: 3) {
                            Text(g.name).font(.headline).foregroundStyle(Brand.text)
                            Text(mode == 0 ? "\(g.count) записи с этим именем" : g.subtitle)
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
        .background(StarfieldView())
    }
}
