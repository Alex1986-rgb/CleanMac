// Поиск дублей контактов (Contacts framework). Работает на iOS и macOS.
// В Info.plist нужен ключ NSContactsUsageDescription.
import SwiftUI
import Contacts

@MainActor
final class ContactScanner: ObservableObject {
    @Published var status = "Готово к сканированию"
    @Published var duplicateGroups = 0

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
        status = "Сканирую контакты…"
        let keys = [CNContactGivenNameKey, CNContactFamilyNameKey,
                    CNContactPhoneNumbersKey] as [CNKeyDescriptor]
        let req = CNContactFetchRequest(keysToFetch: keys)
        var byName: [String: Int] = [:]
        do {
            try store.enumerateContacts(with: req) { c, _ in
                let name = (c.givenName + " " + c.familyName)
                    .trimmingCharacters(in: .whitespaces).lowercased()
                if !name.isEmpty { byName[name, default: 0] += 1 }
            }
            duplicateGroups = byName.values.filter { $0 > 1 }.count
            status = duplicateGroups == 0 ? "Дубликатов не найдено"
                                          : "Групп дублей по имени: \(duplicateGroups)"
        } catch {
            status = "Не удалось прочитать контакты"
        }
    }
}

struct ContactsDuplicatesView: View {
    @StateObject private var scanner = ContactScanner()
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Дубли контактов").font(.largeTitle.bold()).foregroundStyle(Brand.text)
            Text("Поиск контактов с одинаковыми именами (Contacts framework).")
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
