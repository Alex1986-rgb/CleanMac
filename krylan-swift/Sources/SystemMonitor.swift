// Кросс-платформенный сбор системных метрик.
import Foundation
import Combine
#if os(iOS)
import UIKit
#endif

@MainActor
final class SystemMonitor: ObservableObject {
    @Published var diskFreeGB = 0
    @Published var diskTotalGB = 0
    @Published var ramTotalGB = 0
    @Published var batteryPercent = 100
    @Published var diskUsedPercent: Double = 0
    @Published var memoryUsedPercent: Double = 0

    private var timer: Timer?

    /// Общая оценка состояния 0…100 (больше — лучше).
    var healthScore: Double {
        let ramOk = 100 - memoryUsedPercent
        let diskOk = 100 - diskUsedPercent
        let battOk = Double(batteryPercent)
        return max(0, min(100, 0.4 * ramOk + 0.4 * diskOk + 0.2 * battOk))
    }

    var healthLabel: String {
        healthScore >= 75 ? "Отлично" : (healthScore >= 50 ? "Хорошо" : "Внимание")
    }

    func start() {
        #if os(iOS)
        UIDevice.current.isBatteryMonitoringEnabled = true
        #endif
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }

    func refresh() {
        // --- Диск ---
        if let a = try? FileManager.default.attributesOfFileSystem(forPath: NSHomeDirectory()),
           let total = (a[.systemSize] as? NSNumber)?.doubleValue,
           let free = (a[.systemFreeSize] as? NSNumber)?.doubleValue, total > 0 {
            diskTotalGB = Int(total / 1_073_741_824)
            diskFreeGB  = Int(free  / 1_073_741_824)
            diskUsedPercent = (total - free) / total * 100
        }
        // --- ОЗУ ---
        ramTotalGB = Int(Double(ProcessInfo.processInfo.physicalMemory) / 1_073_741_824)
        memoryUsedPercent = Self.memoryUsedPercent()
        // --- Батарея ---
        #if os(iOS)
        let lvl = UIDevice.current.batteryLevel
        batteryPercent = lvl < 0 ? 100 : Int(lvl * 100)
        #endif
    }

    /// % занятой физической памяти через Mach (работает на macOS и iOS).
    static func memoryUsedPercent() -> Double {
        var stats = vm_statistics64()
        var count = mach_msg_type_number_t(MemoryLayout<vm_statistics64>.size / MemoryLayout<integer_t>.size)
        let kr = withUnsafeMutablePointer(to: &stats) { p in
            p.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics64(mach_host_self(), HOST_VM_INFO64, $0, &count)
            }
        }
        guard kr == KERN_SUCCESS else { return 0 }
        var pageSize: vm_size_t = 0
        host_page_size(mach_host_self(), &pageSize)
        let ps = Double(pageSize)
        let used = (Double(stats.active_count) + Double(stats.wire_count)
                    + Double(stats.compressor_page_count)) * ps
        let total = Double(ProcessInfo.processInfo.physicalMemory)
        return total > 0 ? min(100, used / total * 100) : 0
    }
}
