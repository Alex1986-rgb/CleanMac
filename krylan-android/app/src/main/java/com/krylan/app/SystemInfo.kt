// Системные метрики и безопасная очистка собственного кэша.
package com.krylan.app

import android.app.ActivityManager
import android.content.Context
import android.os.BatteryManager
import android.os.Environment
import android.os.StatFs
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
