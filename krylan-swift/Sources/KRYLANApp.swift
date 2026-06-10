// KRYLAN — кросс-платформенный оптимизатор (Mac + iPhone).
// Слоган: «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
import SwiftUI

@main
struct KRYLANApp: App {
    var body: some Scene {
        WindowGroup {
            #if os(macOS)
            ContentView()
                .frame(minWidth: 820, minHeight: 560)
            #else
            ContentView()
            #endif
        }
        #if os(macOS)
        .windowStyle(.titleBar)
        #endif
    }
}
