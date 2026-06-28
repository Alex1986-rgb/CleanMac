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
    @Published var cpuUsedPercent: Double = 0
    @Published var swapUsedPercent: Double = 0
    @Published var netDownBps: Double = 0   // скорость загрузки, байт/с
    @Published var netUpBps: Double = 0     // скорость отдачи, байт/с
    @Published var netDownHist: [Double] = Array(repeating: 0, count: 40)
    @Published var netUpHist: [Double] = Array(repeating: 0, count: 40)

    private var timer: Timer?
    private var prevRecv: UInt64 = 0
    private var prevSent: UInt64 = 0
    private var prevNetTime: TimeInterval = 0
    private var prevCPUTicks: (user: Double, sys: Double, idle: Double, nice: Double)?

    /// Человекочитаемая скорость, напр. «1.2 МБ/с».
    var netDownLabel: String { Self.humanRate(netDownBps) }
    var netUpLabel: String { Self.humanRate(netUpBps) }

    static func humanRate(_ bps: Double) -> String {
        let u = ["Б", "КБ", "МБ", "ГБ"]; var v = bps; var i = 0
        while v >= 1024 && i < u.count - 1 { v /= 1024; i += 1 }
        return String(format: i == 0 ? "%.0f %@/с" : "%.1f %@/с", v, u[i])
    }

    /// Общая оценка состояния 0…100 (больше — лучше).
    var healthScore: Double {
        let ramOk = 100 - memoryUsedPercent
        let diskOk = 100 - diskUsedPercent
        let cpuOk = 100 - cpuUsedPercent
        let battOk = Double(batteryPercent)
        return max(0, min(100, 0.3 * ramOk + 0.3 * diskOk + 0.2 * cpuOk + 0.2 * battOk))
    }

    /// Имя устройства для подписи под планетой.
    var deviceName: String {
        #if os(iOS)
        return UIDevice.current.name
        #else
        return Host.current().localizedName ?? "Mac"
        #endif
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
        // --- CPU (дельта тиков) ---
        cpuUsedPercent = cpuUsedPercentTick()
        // --- SWAP ---
        swapUsedPercent = Self.swapUsedPercent()
        // --- Батарея ---
        #if os(iOS)
        let lvl = UIDevice.current.batteryLevel
        batteryPercent = lvl < 0 ? 100 : Int(lvl * 100)
        #endif
        // --- Сеть (интернет) ---
        let (recv, sent) = Self.interfaceBytes()
        let now = Date().timeIntervalSince1970
        if prevNetTime > 0 {
            let dt = max(0.5, now - prevNetTime)
            // счётчики 32-битные — защищаемся от переполнения через wrapping
            netDownBps = max(0, Double(recv &- prevRecv)) / dt
            netUpBps   = max(0, Double(sent &- prevSent)) / dt
        }
        prevRecv = recv; prevSent = sent; prevNetTime = now
        netDownHist = Array((netDownHist + [netDownBps]).suffix(40))
        netUpHist = Array((netUpHist + [netUpBps]).suffix(40))
    }

    /// Суммарные байты recv/sent по всем активным интерфейсам (кроме loopback).
    /// getifaddrs + if_data работает и на macOS, и в песочнице iOS.
    static func interfaceBytes() -> (recv: UInt64, sent: UInt64) {
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0 else { return (0, 0) }
        defer { freeifaddrs(ifaddr) }
        var recv: UInt64 = 0, sent: UInt64 = 0
        var ptr = ifaddr
        while let p = ptr {
            defer { ptr = p.pointee.ifa_next }
            let name = String(cString: p.pointee.ifa_name)
            let flags = Int32(p.pointee.ifa_flags)
            guard let addr = p.pointee.ifa_addr,
                  addr.pointee.sa_family == UInt8(AF_LINK),
                  (flags & IFF_UP) == IFF_UP, name != "lo0",
                  let data = p.pointee.ifa_data?.assumingMemoryBound(to: if_data.self)
            else { continue }
            recv += UInt64(data.pointee.ifi_ibytes)
            sent += UInt64(data.pointee.ifi_obytes)
        }
        return (recv, sent)
    }

    /// % загрузки CPU по дельте host тиков (user+sys+nice / total). Работает на macOS и iOS.
    private func cpuUsedPercentTick() -> Double {
        var count = mach_msg_type_number_t(MemoryLayout<host_cpu_load_info_data_t>.size / MemoryLayout<integer_t>.size)
        var info = host_cpu_load_info_data_t()
        let kr = withUnsafeMutablePointer(to: &info) { p in
            p.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, $0, &count)
            }
        }
        guard kr == KERN_SUCCESS else { return cpuUsedPercent }
        let user = Double(info.cpu_ticks.0)
        let sys  = Double(info.cpu_ticks.1)
        let idle = Double(info.cpu_ticks.2)
        let nice = Double(info.cpu_ticks.3)
        defer { prevCPUTicks = (user, sys, idle, nice) }
        guard let prev = prevCPUTicks else { return 0 }
        let du = user - prev.user, ds = sys - prev.sys, di = idle - prev.idle, dn = nice - prev.nice
        let total = du + ds + di + dn
        guard total > 0 else { return cpuUsedPercent }
        return max(0, min(100, (du + ds + dn) / total * 100))
    }

    /// % использования swap через sysctl vm.swapusage (доступно и в песочнице iOS).
    static func swapUsedPercent() -> Double {
        var usage = xsw_usage()
        var size = MemoryLayout<xsw_usage>.size
        guard sysctlbyname("vm.swapusage", &usage, &size, nil, 0) == 0, usage.xsu_total > 0 else { return 0 }
        return min(100, Double(usage.xsu_used) / Double(usage.xsu_total) * 100)
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
