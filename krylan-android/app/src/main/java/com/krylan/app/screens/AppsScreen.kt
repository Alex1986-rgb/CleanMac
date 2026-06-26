// Менеджер приложений: список по размеру APK, удаление через системный диалог.
// Размер APK — честный ориентир без спец-разрешений (полный размер требует Usage Access).
// Вкладка «Неиспользуемые» — давно не открывавшиеся приложения по данным UsageStatsManager
// (требует особого доступа Usage Access, не runtime-permission).
package com.krylan.app.screens

import android.app.AppOpsManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.Uri
import android.os.Process
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class AppEntry(val label: String, val pkg: String, val apkBytes: Long)

// Приложение с данными о простое. idleDays = -1 → нет записи об использовании (никогда/очень давно).
data class IdleApp(val label: String, val pkg: String, val apkBytes: Long, val idleDays: Long)

private fun installedApps(ctx: Context): List<AppEntry> {
    val pm = ctx.packageManager
    return pm.getInstalledApplications(0)
        .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 && it.packageName != ctx.packageName }
        .map { AppEntry(pm.getApplicationLabel(it).toString(), it.packageName, File(it.sourceDir).length()) }
        .sortedByDescending { it.apkBytes }
}

// Есть ли особый доступ Usage Access. checkOpNoThrow доступен с API 19 (minSdk=26 — безопасно).
private fun hasUsageAccess(ctx: Context): Boolean = try {
    val appOps = ctx.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
    @Suppress("DEPRECATION")
    val mode = appOps.checkOpNoThrow(
        AppOpsManager.OPSTR_GET_USAGE_STATS,
        Process.myUid(),
        ctx.packageName
    )
    mode == AppOpsManager.MODE_ALLOWED
} catch (e: Exception) {
    false
}

// Порог «давно не использовано» — 30 дней.
private const val IDLE_THRESHOLD_DAYS = 30L
private const val DAY_MILLIS = 24L * 60L * 60L * 1000L

// Считает простой по UsageStatsManager. Возвращает null при ошибке/отсутствии доступа.
private fun idleApps(ctx: Context): List<IdleApp>? {
    return try {
        val usm = ctx.getSystemService(Context.USAGE_STATS_SERVICE) as? UsageStatsManager ?: return null
        val now = System.currentTimeMillis()
        val begin = now - 365L * DAY_MILLIS
        val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_YEARLY, begin, now)
        if (stats == null || stats.isEmpty()) return null

        // Максимальное lastTimeUsed по пакету (на пакет может быть несколько записей).
        val lastUsed = HashMap<String, Long>()
        for (s in stats) {
            val prev = lastUsed[s.packageName] ?: 0L
            if (s.lastTimeUsed > prev) lastUsed[s.packageName] = s.lastTimeUsed
        }

        val installed = installedApps(ctx)
        installed.mapNotNull { app ->
            val last = lastUsed[app.pkg]
            val idleDays = if (last == null || last <= 0L) -1L else (now - last) / DAY_MILLIS
            // Берём только давно не использованные: нет записи ИЛИ простой больше порога.
            when {
                idleDays < 0L -> IdleApp(app.label, app.pkg, app.apkBytes, -1L)
                idleDays >= IDLE_THRESHOLD_DAYS -> IdleApp(app.label, app.pkg, app.apkBytes, idleDays)
                else -> null
            }
        // Сначала «нет данных об открытии» (idleDays < 0), затем по убыванию дней простоя.
        }.sortedWith(compareByDescending<IdleApp> { it.idleDays < 0L }.thenByDescending { it.idleDays })
    } catch (e: Exception) {
        null
    }
}

private fun idleLabel(idleDays: Long): String =
    if (idleDays < 0L) "нет данных об открытии" else "простой $idleDays дн."

@Composable
fun AppsScreen(ctx: Context) {
    var reload by remember { mutableIntStateOf(0) }
    var showIdle by remember { mutableStateOf(false) }

    val apps = remember(reload) { installedApps(ctx) }

    // Доступ перечитываем на каждый reload (юзер мог выдать его в Настройках и вернуться).
    var access by remember { mutableStateOf(false) }
    // null = ещё считаем; иначе результат (возможно пустой).
    var idle by remember { mutableStateOf<List<IdleApp>?>(null) }

    LaunchedEffect(reload, showIdle) {
        if (showIdle) {
            access = hasUsageAccess(ctx)
            idle = null
            if (access) {
                val result = withContext(Dispatchers.IO) { idleApps(ctx) }
                idle = result ?: emptyList()
                // Пустой ответ при «есть доступ» иногда значит, что доступ только что выдан
                // и статистика не успела собраться — оставляем пусто, текст ниже честно поясняет.
            } else {
                idle = emptyList()
            }
        }
    }

    LazyColumn(
        Modifier.fillMaxSize().background(Brand.bg0),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        // Переключатель вкладок.
        item {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = { showIdle = false }) {
                    Text("Все",
                        color = if (!showIdle) Brand.blue else Brand.muted,
                        fontSize = 14.sp,
                        fontWeight = if (!showIdle) FontWeight.Bold else FontWeight.Normal)
                }
                TextButton(onClick = { showIdle = true }) {
                    Text("Неиспользуемые",
                        color = if (showIdle) Brand.blue else Brand.muted,
                        fontSize = 14.sp,
                        fontWeight = if (showIdle) FontWeight.Bold else FontWeight.Normal)
                }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = { reload++ }) {
                    Text("Обновить", color = Brand.blue, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        if (!showIdle) {
            // ── Вкладка «Все»: список по размеру APK ──
            item {
                Text("Приложений: ${apps.size} · сортировка по размеру APK",
                    color = Brand.muted, fontSize = 13.sp)
            }
            items(apps, key = { it.pkg }) { a ->
                AppCard(
                    title = a.label,
                    subtitle = "${a.pkg} · APK ${SystemInfo.fmtSize(a.apkBytes)}",
                    onDelete = { ctx.startActivity(Intent(Intent.ACTION_DELETE, Uri.parse("package:${a.pkg}"))) }
                )
            }
            if (apps.isEmpty()) item {
                Text("Список приложений недоступен.", color = Brand.muted, fontSize = 14.sp)
            }
        } else {
            // ── Вкладка «Неиспользуемые» ──
            if (!access) {
                item { UsageAccessCard(ctx) }
            } else {
                val list = idle
                when {
                    list == null -> item {
                        Text("Считаем простой приложений…", color = Brand.muted, fontSize = 14.sp)
                    }
                    list.isEmpty() -> item {
                        Text(
                            "Давно не открывавшихся приложений не найдено " +
                                "(порог $IDLE_THRESHOLD_DAYS дн.). Если доступ выдан только что — " +
                                "статистике нужно время, чтобы накопиться.",
                            color = Brand.muted, fontSize = 13.sp
                        )
                    }
                    else -> {
                        item {
                            Text("Не открывались ≥ $IDLE_THRESHOLD_DAYS дн.: ${list.size}",
                                color = Brand.muted, fontSize = 13.sp)
                        }
                        items(list, key = { it.pkg }) { a ->
                            AppCard(
                                title = a.label,
                                subtitle = "${idleLabel(a.idleDays)} · APK ${SystemInfo.fmtSize(a.apkBytes)}",
                                onDelete = { ctx.startActivity(Intent(Intent.ACTION_DELETE, Uri.parse("package:${a.pkg}"))) }
                            )
                        }
                    }
                }
            }
        }
    }
}

// Карточка приложения (общая для обеих вкладок).
@Composable
private fun AppCard(title: String, subtitle: String, onDelete: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Text(subtitle, color = Brand.muted, fontSize = 11.sp, maxLines = 1)
            }
            TextButton(onClick = onDelete) {
                Text("Удалить", color = Brand.red, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

// Карточка-приглашение выдать особый доступ Usage Access.
@Composable
private fun UsageAccessCard(ctx: Context) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Нужен доступ к статистике использования",
                color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Text(
                "Чтобы показать давно не открывавшиеся приложения, KRYLAN нужен особый доступ " +
                    "«Доступ к данным об использовании». Это не обычное разрешение — его выдают " +
                    "вручную в системных настройках. Данные не покидают устройство.",
                color = Brand.muted, fontSize = 13.sp
            )
            TextButton(onClick = {
                try {
                    ctx.startActivity(
                        Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    )
                } catch (e: Exception) {
                    // Некоторые прошивки не имеют экрана — открываем общие настройки.
                    try {
                        ctx.startActivity(
                            Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        )
                    } catch (_: Exception) { }
                }
            }) {
                Text("Открыть настройки доступа", color = Brand.blue, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
