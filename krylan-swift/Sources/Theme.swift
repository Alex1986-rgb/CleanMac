// Бренд и палитра KRYLAN.
import SwiftUI

enum Brand {
    static let name   = "KRYLAN"
    static let slogan = "Дай устройству крылья"
    static let author = "Кырлан Александр Сергеевич"
    static let version = "0.1.0"

    static let bg0    = Color(red: 0.07, green: 0.08, blue: 0.11)
    static let glass  = Color(red: 0.13, green: 0.17, blue: 0.23)
    static let track  = Color(red: 0.20, green: 0.24, blue: 0.31)
    static let text   = Color(red: 0.93, green: 0.95, blue: 0.97)
    static let muted  = Color(red: 0.54, green: 0.58, blue: 0.65)
    static let green  = Color(red: 0.21, green: 0.83, blue: 0.60)
    static let blue   = Color(red: 0.29, green: 0.55, blue: 0.97)
    static let purple = Color(red: 0.65, green: 0.54, blue: 0.98)
    static let yellow = Color(red: 0.96, green: 0.73, blue: 0.27)
    static let red    = Color(red: 0.95, green: 0.41, blue: 0.37)

    /// Цвет по нагрузке: 0 — хорошо (зелёный), 100 — плохо (красный).
    static func load(_ p: Double) -> Color {
        p < 60 ? green : (p < 85 ? yellow : red)
    }
}
