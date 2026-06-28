// Бренд и палитра KRYLAN.
import SwiftUI

enum Brand {
    static let name   = "KRYLAN"
    static let slogan = "Дай устройству крылья"
    static let author = "Кырлан Александр Сергеевич"
    static let version = "0.6.0"

    // Палитра navy «рубка» KRYLAN (эталон HUD macOS CleanMac).
    static let bg0    = Color(red: 0.035, green: 0.075, blue: 0.153)   // #091327
    static let bg1    = Color(red: 0.024, green: 0.051, blue: 0.118)   // #060d1e — край свечения
    static let glow   = Color(red: 0.090, green: 0.239, blue: 0.447)   // #173d72 — центр свечения
    static let glass  = Color(red: 0.063, green: 0.141, blue: 0.267)   // #102444
    static let track  = Color(red: 0.133, green: 0.263, blue: 0.435)   // #22436f
    static let text   = Color(red: 0.894, green: 0.933, blue: 0.984)   // #e4eefb
    static let muted  = Color(red: 0.439, green: 0.533, blue: 0.698)   // #7088b2
    static let green  = Color(red: 0.184, green: 0.898, blue: 0.627)   // #2fe5a0
    static let blue   = Color(red: 0.184, green: 0.561, blue: 1.0)     // #2f8fff
    static let cyan   = Color(red: 0.212, green: 0.839, blue: 1.0)     // #36d6ff
    static let purple = Color(red: 0.749, green: 0.353, blue: 0.949)   // #BF5AF2 (запас)
    static let yellow = Color(red: 1.0,   green: 0.839, blue: 0.039)   // #ffd60a
    static let red    = Color(red: 1.0,   green: 0.353, blue: 0.322)   // #ff5a52

    /// Цвет по нагрузке: 0 — хорошо (зелёный), 100 — плохо (красный).
    static func load(_ p: Double) -> Color {
        p < 60 ? green : (p < 85 ? yellow : red)
    }
}

/// Заголовок страницы: на iOS его показывает нав-бар, поэтому рендерим только на macOS.
struct PageHeader: View {
    let title: String
    var body: some View {
        #if os(macOS)
        Text(title).font(.largeTitle.bold()).foregroundStyle(Brand.text)
        #else
        EmptyView()
        #endif
    }
}
