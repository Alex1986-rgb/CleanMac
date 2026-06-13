// Периодическая проверка хранилища: уведомление при заполнении >90%.
package com.krylan.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.Worker
import androidx.work.WorkerParameters

class StorageCheckWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val st = SystemInfo.storage()
        if (st.usedPercent >= 90f) {
            val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                nm.createNotificationChannel(NotificationChannel(
                    CHANNEL, "KRYLAN: предупреждения", NotificationManager.IMPORTANCE_DEFAULT))
            }
            val n = NotificationCompat.Builder(applicationContext, CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sdcard)
                .setContentTitle("Хранилище почти заполнено")
                .setContentText("Занято ${st.usedPercent.toInt()}% — откройте KRYLAN и освободите место.")
                .setAutoCancel(true)
                .build()
            try { nm.notify(1001, n) } catch (_: SecurityException) { /* нет разрешения — молча */ }
        }
        return Result.success()
    }

    companion object { const val CHANNEL = "krylan_alerts" }
}
