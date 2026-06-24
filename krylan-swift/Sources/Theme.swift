// Бренд и палитра KRYLAN.
import SwiftUI

enum Brand {
    static let name   = "KRYLAN"
    static let slogan = "Дай устройству крылья"
    static let author = "Кырлан Александр Сергеевич"
    static let version = "0.6.0"

    // Системные цвета iOS (Apple HIG): чёрная база, карточки systemGray6.
    static let bg0    = Color(red: 0.0,   green: 0.0,   blue: 0.0)     // #000000
    static let bg1    = Color(red: 0.110, green: 0.110, blue: 0.118)   // #1C1C1E
    static let glass  = Color(red: 0.110, green: 0.110, blue: 0.118)   // systemGray6
    static let track  = Color(red: 0.227, green: 0.227, blue: 0.235)   // #3A3A3C systemGray4
    static let text   = Color(red: 1.0,   green: 1.0,   blue: 1.0)     // #FFFFFF
    static let muted  = Color(red: 0.596, green: 0.596, blue: 0.624)   // #98989F
    static let green  = Color(red: 0.188, green: 0.820, blue: 0.345)   // systemGreen #30D158
    static let blue   = Color(red: 0.039, green: 0.518, blue: 1.0)     // systemBlue #0A84FF
    static let cyan   = Color(red: 0.392, green: 0.824, blue: 1.0)     // systemTeal #64D2FF
    static let purple = Color(red: 0.749, green: 0.353, blue: 0.949)   // systemPurple #BF5AF2
    static let yellow = Color(red: 1.0,   green: 0.839, blue: 0.039)   // systemYellow #FFD60A
    static let red    = Color(red: 1.0,   green: 0.271, blue: 0.227)   // systemRed #FF453A

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
