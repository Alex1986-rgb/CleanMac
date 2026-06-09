// KRYLAN — кросс-платформенный оптимизатор (Mac + iPhone).
// Слоган: «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
import SwiftUI

@main
struct KRYLANApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 820, minHeight: 560)
        }
        #if os(macOS)
        .windowStyle(.titleBar)
        #endif
    }
}
