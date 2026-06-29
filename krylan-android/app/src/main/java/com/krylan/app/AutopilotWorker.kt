// Автопилот: периодически чистит СВОЙ кэш и шлёт честное напоминание о находках к разбору.
// Авто-удаление медиа невозможно — только подсчёт и уведомление; удаление вручную пользователем.
package com.krylan.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.Worker
import androidx.work.WorkerParameters

class AutopilotWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val prefs = AutopilotPrefs(applicationContext)
        if (!prefs.enabled) return Result.success()

        // 1) Чистим ТОЛЬКО свой кэш (единственное разрешённое на Android 11+).
        val freed = try { SystemInfo.clearCache(applicationContext) } catch (_: Throwable) { 0L }

        // 2) Считаем, что есть к ручному разбору (ничего не удаляем).
        val screenshots = try { MediaStoreUtils.screenshots(applicationContext).size } catch (_: Throwable) { 0 }
        val large = try { MediaStoreUtils.largeFiles(applicationContext).size } catch (_: Throwable) { 0 }
        val dupes = try { MediaStoreUtils.duplicateGroups(applicationContext).size } catch (_: Throwable) { 0 }
        val toReview = screenshots + large + dupes

        // 3) Сохраняем итог последнего прогона (для экрана Автопилота).
        prefs.lastRunMs = System.currentTimeMillis()
        prefs.lastFreedBytes = freed
        prefs.lastToReview = toReview

        // 4) Уведомление — только если реально есть что показать.
        if (freed > 0 || toReview > 0) notify(freed, screenshots, large, dupes)

        return Result.success()
    }

    private fun notify(freed: Long, screenshots: Int, large: Int, dupes: Int) {
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL, "KRYLAN: Автопилот", NotificationManager.IMPORTANCE_DEFAULT).apply {
                    description = "Напоминания Автопилота о месте к освобождению"
                }
            )
        }

        val parts = buildList {
            if (screenshots > 0) add("$screenshots скриншотов")
            if (large > 0) add("$large крупных")
            if (dupes > 0) add("$dupes групп дублей")
        }
        val freedText = if (freed > 0) "Очищено ≈ ${SystemInfo.fmtSize(freed)}. " else ""
        val reviewText = if (parts.isNotEmpty()) "К разбору: ${parts.joinToString(", ")}. " else ""
        val text = "${freedText}${reviewText}Откройте, чтобы разобрать."

        val openIntent = applicationContext.packageManager
            .getLaunchIntentForPackage(applicationContext.packageName)
            ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
            (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)
        val pi = if (openIntent != null)
            PendingIntent.getActivity(applicationContext, 0, openIntent, flags) else null

        val n = NotificationCompat.Builder(applicationContext, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_notify_sdcard)
            .setContentTitle("KRYLAN: можно освободить место")
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .apply { if (pi != null) setContentIntent(pi) }
            .build()
        try { nm.notify(2002, n) } catch (_: SecurityException) { /* нет разрешения — молча */ }
    }

    companion object {
        const val CHANNEL = "krylan_autopilot"
        const val WORK_NAME = "krylan_autopilot_periodic"
    }
}
