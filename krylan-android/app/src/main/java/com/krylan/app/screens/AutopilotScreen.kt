// Автопилот: тумблер периодической задачи (WorkManager), разрешение на уведомления,
// ручная проверка «сейчас». Честно: авто-удаление медиа невозможно — только свой кэш + напоминание.
package com.krylan.app.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.krylan.app.Autopilot
import com.krylan.app.AutopilotPrefs
import com.krylan.app.MediaStoreUtils
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private fun notifGranted(ctx: Context): Boolean =
    if (Build.VERSION.SDK_INT >= 33)
        ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.POST_NOTIFICATIONS) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED
    else true

@Composable
fun AutopilotScreen(ctx: Context) {
    val prefs = remember { AutopilotPrefs(ctx) }
    var enabled by remember { mutableStateOf(prefs.enabled) }
    var hasNotif by remember { mutableStateOf(notifGranted(ctx)) }

    // Снимок последнего прогона.
    var lastRun by remember { mutableStateOf(prefs.lastRunMs) }
    var lastFreed by remember { mutableStateOf(prefs.lastFreedBytes) }
    var lastReview by remember { mutableStateOf(prefs.lastToReview) }

    val scope = rememberCoroutineScope()
    var checking by remember { mutableStateOf(false) }
    var checkResult by remember { mutableStateOf<String?>(null) }

    // Запрос POST_NOTIFICATIONS — при подтверждении включаем Автопилот.
    val notifLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasNotif = granted
        if (granted) {
            Autopilot.enable(ctx)
            enabled = true
        }
    }

    fun turnOn() {
        if (Build.VERSION.SDK_INT >= 33 && !notifGranted(ctx)) {
            notifLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        } else {
            Autopilot.enable(ctx)
            enabled = true
            hasNotif = true
        }
    }

    fun turnOff() {
        Autopilot.disable(ctx)
        enabled = false
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Заголовок + тумблер
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        Modifier.size(44.dp).background(Brand.green.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                        contentAlignment = Alignment.Center
                    ) { Icon(Icons.Filled.Bolt, contentDescription = null, tint = Brand.green) }
                    Column(Modifier.weight(1f)) {
                        Text("Автопилот", color = Brand.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        Text(
                            if (enabled) "Включён — работает в фоне" else "Выключен",
                            color = if (enabled) Brand.green else Brand.muted, fontSize = 12.sp
                        )
                    }
                    Switch(
                        checked = enabled,
                        onCheckedChange = { if (it) turnOn() else turnOff() },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color(0xFF0B1410),
                            checkedTrackColor = Brand.green,
                            uncheckedThumbColor = Brand.muted,
                            uncheckedTrackColor = Brand.track,
                        )
                    )
                }
                Text(
                    "Android запускает фоновые задачи по своему расписанию (обычно раз в несколько часов). " +
                        "KRYLAN чистит свой кэш и шлёт напоминание о месте к освобождению. " +
                        "Авто-удаление медиа невозможно — только с вашим подтверждением.",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }

        // Блок разрешения на уведомления (Android 13+)
        if (Build.VERSION.SDK_INT >= 33 && !hasNotif) {
            Card(
                colors = CardDefaults.cardColors(containerColor = Brand.glass),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Filled.Notifications, contentDescription = null, tint = Brand.yellow)
                        Text("Нет разрешения на уведомления", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                    Text(
                        "Без уведомлений Автопилот не сможет напоминать о находках. Разрешите их в настройках приложения.",
                        color = Brand.muted, fontSize = 12.sp
                    )
                    ActionButton("Открыть настройки приложения", Brand.yellow) {
                        runCatching {
                            ctx.startActivity(
                                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                                    .setData(Uri.fromParts("package", ctx.packageName, null))
                                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            )
                        }
                    }
                }
            }
        }

        // Кнопка «Проверить и очистить сейчас»
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(50))
                .background(Brand.green)
                .clickable(enabled = !checking) {
                    if (checking) return@clickable
                    checking = true
                    checkResult = null
                    scope.launch {
                        val (freed, review) = withContext(Dispatchers.IO) {
                            val f = try { SystemInfo.clearCache(ctx) } catch (_: Throwable) { 0L }
                            val s = try { MediaStoreUtils.screenshots(ctx).size } catch (_: Throwable) { 0 }
                            val l = try { MediaStoreUtils.largeFiles(ctx).size } catch (_: Throwable) { 0 }
                            val d = try { MediaStoreUtils.duplicateGroups(ctx).size } catch (_: Throwable) { 0 }
                            f to (s + l + d)
                        }
                        prefs.lastRunMs = System.currentTimeMillis()
                        prefs.lastFreedBytes = freed
                        prefs.lastToReview = review
                        lastRun = prefs.lastRunMs; lastFreed = freed; lastReview = review
                        checkResult = "Очищено: ${SystemInfo.fmtSize(freed)} · к разбору: $review"
                        checking = false
                    }
                }
                .padding(vertical = 15.dp),
            contentAlignment = Alignment.Center
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                if (checking) CircularProgressIndicator(Modifier.size(18.dp), color = Color(0xFF0B1410), strokeWidth = 2.dp)
                Text(
                    if (checking) "Проверяю…" else "⚡  Проверить и очистить сейчас",
                    color = Color(0xFF0B1410), fontSize = 16.sp, fontWeight = FontWeight.Bold
                )
            }
        }
        checkResult?.let {
            Text(it, color = Brand.green, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        }

        // Последний прогон
        if (lastRun > 0) {
            Card(
                colors = CardDefaults.cardColors(containerColor = Brand.glass),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Brand.green)
                        Text("Последний прогон", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    }
                    Text(
                        SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.US).format(Date(lastRun)),
                        color = Brand.muted, fontSize = 12.sp
                    )
                    Text("Очищено кэша: ${SystemInfo.fmtSize(lastFreed)}", color = Brand.text, fontSize = 13.sp)
                    Text("Найдено к разбору: $lastReview", color = Brand.text, fontSize = 13.sp)
                }
            }
        }

        // Честная плашка
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Как это честно работает", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(
                    "• Реально чистится только кэш этого приложения.\n" +
                        "• Чужие и системные файлы не трогаются.\n" +
                        "• Медиа удаляется только вами — через системный диалог в разделе «Медиа».\n" +
                        "• Точное время фонового запуска решает Android (минимум раз в 15 минут, на практике реже).",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun ActionButton(label: String, color: Color, onClick: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(color)
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(label, color = Color(0xFF0B1410), fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
}
