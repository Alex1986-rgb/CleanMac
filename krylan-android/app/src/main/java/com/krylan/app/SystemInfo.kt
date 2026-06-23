// Системные метрики и безопасная очистка собственного кэша.
package com.krylan.app

import android.app.ActivityManager
import android.content.Context
import android.net.TrafficStats
import android.os.BatteryManager
import android.os.Environment
import android.os.StatFs
import android.os.SystemClock
import java.io.File
import java.util.Locale

data class StorageInfo(val totalBytes: Long, val freeBytes: Long) {
    val usedBytes get() = totalBytes - freeBytes
    val usedPercent get() = if (totalBytes > 0) usedBytes * 100f / totalBytes else 0f
}

object SystemInfo {

    fun storage(): StorageInfo {
        val s = StatFs(Environment.getDataDirectory().path)
        return StorageInfo(s.blockCountLong * s.blockSizeLong, s.availableBlocksLong * s.blockSizeLong)
    }

    fun ramTotalBytes(ctx: Context): Long = memInfo(ctx).totalMem

    fun ramUsedPercent(ctx: Context): Float {
        val m = memInfo(ctx)
        return if (m.totalMem > 0) (m.totalMem - m.availMem) * 100f / m.totalMem else 0f
    }

    fun batteryPercent(ctx: Context): Int {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        return bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }

    // --- Сеть (интернет): скорость вниз/вверх через общесистемные счётчики ---
    data class NetSpeed(val downBps: Long, val upBps: Long)

    private var prevRx = 0L
    private var prevTx = 0L
    private var prevNetMs = 0L

    /** Скорость сети с прошлого вызова (байт/с). Первый вызов вернёт 0. */
    fun netSpeed(): NetSpeed {
        val rx = TrafficStats.getTotalRxBytes()
        val tx = TrafficStats.getTotalTxBytes()
        val now = SystemClock.elapsedRealtime()
        // UNSUPPORTED (-1) на устройствах без счётчиков
        if (rx < 0 || tx < 0) return NetSpeed(0, 0)
        var down = 0L; var up = 0L
        if (prevNetMs > 0) {
            val dt = ((now - prevNetMs).coerceAtLeast(500)) / 1000.0
            down = ((rx - prevRx).coerceAtLeast(0) / dt).toLong()
            up = ((tx - prevTx).coerceAtLeast(0) / dt).toLong()
        }
        prevRx = rx; prevTx = tx; prevNetMs = now
        return NetSpeed(down, up)
    }

    fun fmtRate(bytesPerSec: Long): String = "${fmtSize(bytesPerSec)}/с"

    /** Оценка здоровья 0..100 — как в iOS-версии: среднее от запаса по памяти и диску. */
    fun healthScore(ctx: Context): Float {
        val ram = ramUsedPercent(ctx)
        val disk = storage().usedPercent
        return (100f - (ram + disk) / 2f).coerceIn(0f, 100f)
    }

    // --- Кэш СВОЕГО приложения (единственная разрешённая очистка на Android 11+) ---

    fun cacheBytes(ctx: Context): Long =
        dirSize(ctx.cacheDir) + dirSize(ctx.externalCacheDir) + dirSize(ctx.codeCacheDir)

    /** Удаляет содержимое кэш-каталогов приложения. Возвращает освобождённые байты. */
    fun clearCache(ctx: Context): Long {
        val before = cacheBytes(ctx)
        listOf(ctx.cacheDir, ctx.externalCacheDir, ctx.codeCacheDir).forEach { dir ->
            dir?.listFiles()?.forEach { it.deleteRecursively() }
        }
        return (before - cacheBytes(ctx)).coerceAtLeast(0)
    }

    private fun memInfo(ctx: Context): ActivityManager.MemoryInfo {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        return ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
    }

    private fun dirSize(dir: File?): Long =
        dir?.walkBottomUp()?.filter { it.isFile }?.sumOf { it.length() } ?: 0L

    fun fmtSize(bytes: Long): String {
        val kb = 1024.0; val mb = kb * 1024; val gbb = mb * 1024
        return when {
            bytes >= gbb -> String.format(Locale.US, "%.1f ГБ", bytes / gbb)
            bytes >= mb  -> String.format(Locale.US, "%.1f МБ", bytes / mb)
            bytes >= kb  -> String.format(Locale.US, "%.0f КБ", bytes / kb)
            else         -> "$bytes Б"
        }
    }

    fun gb(bytes: Long): Double = bytes / 1_073_741_824.0
}
