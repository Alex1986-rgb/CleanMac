// KRYLAN — кросс-платформенный оптимизатор (Mac + iPhone).
// Слоган: «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
import SwiftUI

@main
struct KRYLANApp: App {
    #if os(iOS)
    @Environment(\.scenePhase) private var scenePhase

    init() {
        // Регистрируем обработчик фоновой задачи Автопилота ДО окончания launch.
        AutopilotManager.shared.registerBackgroundTask()
    }
    #endif

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
        #if os(iOS)
        .onChange(of: scenePhase) { _, phase in
            // При уходе в фон — планируем следующий прогон, но только если Автопилот включён.
            if phase == .background, AutopilotManager.shared.enabled {
                AutopilotManager.shared.scheduleNextRefresh()
            }
        }
        #endif
    }
}
