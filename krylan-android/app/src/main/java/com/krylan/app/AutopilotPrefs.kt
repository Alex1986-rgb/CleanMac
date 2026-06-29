// Настройки Автопилота через SharedPreferences (без новых зависимостей) + планирование WorkManager.
package com.krylan.app

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/** Обёртка над SharedPreferences для состояния Автопилота. */
class AutopilotPrefs(ctx: Context) {
    private val sp = ctx.applicationContext.getSharedPreferences("krylan_autopilot", Context.MODE_PRIVATE)

    var enabled: Boolean
        get() = sp.getBoolean(KEY_ENABLED, false)
        set(v) = sp.edit().putBoolean(KEY_ENABLED, v).apply()

    var lastRunMs: Long
        get() = sp.getLong(KEY_LAST_RUN, 0L)
        set(v) = sp.edit().putLong(KEY_LAST_RUN, v).apply()

    var lastFreedBytes: Long
        get() = sp.getLong(KEY_LAST_FREED, 0L)
        set(v) = sp.edit().putLong(KEY_LAST_FREED, v).apply()

    var lastToReview: Int
        get() = sp.getInt(KEY_LAST_REVIEW, 0)
        set(v) = sp.edit().putInt(KEY_LAST_REVIEW, v).apply()

    companion object {
        private const val KEY_ENABLED = "enabled"
        private const val KEY_LAST_RUN = "last_run_ms"
        private const val KEY_LAST_FREED = "last_freed_bytes"
        private const val KEY_LAST_REVIEW = "last_to_review"
    }
}

object Autopilot {

    /** Включает Автопилот: сохраняет флаг и ставит периодическую задачу (мин. 15 мин + flex). */
    fun enable(ctx: Context) {
        AutopilotPrefs(ctx).enabled = true
        val request = PeriodicWorkRequestBuilder<AutopilotWorker>(
            6, TimeUnit.HOURS,            // основной интервал
            1, TimeUnit.HOURS             // flex-окно
        ).build()
        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
            AutopilotWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }

    /** Выключает Автопилот: снимает флаг и отменяет периодическую задачу. */
    fun disable(ctx: Context) {
        AutopilotPrefs(ctx).enabled = false
        WorkManager.getInstance(ctx).cancelUniqueWork(AutopilotWorker.WORK_NAME)
    }
}
