// Дашборд: Health-кольцо + кольца метрик + карточки (дизайн как в iOS-версии).
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.Canvas
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import com.krylan.app.ui.GlobeView
import com.krylan.app.ui.RingGauge
import kotlinx.coroutines.delay

@Composable
fun DashboardScreen(ctx: Context, onNavigate: (Int) -> Unit = {}) {
    var tick by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { while (true) { delay(3000); tick++ } }

    val storage = remember(tick) { SystemInfo.storage() }
    val ramPct = remember(tick) { SystemInfo.ramUsedPercent(ctx) }
    val battery = remember(tick) { SystemInfo.batteryPercent(ctx) }
    val health = remember(tick) { SystemInfo.healthScore(ctx) }
    val healthLabel = if (health >= 70) "Отлично" else if (health >= 40) "Внимание" else "Критично"
    val net = remember(tick) { SystemInfo.netSpeed() }
    val downHist = remember { mutableStateListOf<Float>() }
    val upHist = remember { mutableStateListOf<Float>() }
    LaunchedEffect(tick) {
        downHist.add(net.downBps.toFloat()); if (downHist.size > 40) downHist.removeAt(0)
        upHist.add(net.upBps.toFloat()); if (upHist.size > 40) upHist.removeAt(0)
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Состояние в реальном времени", color = Brand.muted, fontSize = 14.sp)

        // Флагманская кнопка очистки кэша (единственное безопасное на Android 11+).
        // Формулировки честные — без «boost RAM / ускорить в N раз» (политика Google Play).
        var boosting by remember { mutableStateOf(false) }
        var boostFreed by remember { mutableLongStateOf(-1L) }
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(50))
                .background(Brush.horizontalGradient(listOf(Brand.green, Brand.cyan)))
                .clickable(enabled = !boosting) {
                    boosting = true
                    boostFreed = SystemInfo.clearCache(ctx)
                    boosting = false
                }
                .padding(vertical = 15.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                when {
                    boostFreed >= 0 -> "✓ Готово — освобождено ${SystemInfo.fmtSize(boostFreed)}"
                    boosting -> "Очищаю…"
                    else -> "🧹  Освободить кэш"
                },
                color = Color(0xFF0B1410), fontSize = 16.sp, fontWeight = FontWeight.Bold
            )
        }
        Text(
            "Очищает только кэш этого приложения. Системные файлы и данные не трогаем.",
            color = Brand.muted, fontSize = 11.sp
        )

        // Умные подсказки с реальными счётчиками и переходом на нужную вкладку.
        SmartSuggestions(ctx, onNavigate)

        // Фирменный анимированный глобус KRYLAN
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(
                Modifier.fillMaxWidth().height(220.dp),
                contentAlignment = Alignment.Center
            ) {
                GlobeView(Modifier.fillMaxSize())
            }
        }

        // Health-герой
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(Modifier.fillMaxWidth().padding(vertical = 22.dp), contentAlignment = Alignment.Center) {
                RingGauge(progress = health / 100f, color = Brand.load(100f - health), size = 160.dp, stroke = 16.dp) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("${health.toInt()}", color = Brand.text, fontSize = 44.sp, fontWeight = FontWeight.Bold)
                        Text(healthLabel, color = Brand.load(100f - health), fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Кольца метрик
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                Modifier.fillMaxWidth().padding(vertical = 18.dp),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                MetricRing(ramPct, "ПАМЯТЬ")
                MetricRing(storage.usedPercent, "ДИСК")
                MetricRing(battery.toFloat(), "БАТАРЕЯ", invert = true)
            }
        }

        InfoCard(Icons.Filled.Storage, "Хранилище",
            "${"%.0f".format(SystemInfo.gb(storage.freeBytes))} ГБ свободно",
            "из ${"%.0f".format(SystemInfo.gb(storage.totalBytes))} ГБ", Brand.blue)
        InfoCard(Icons.Filled.Memory, "Оперативная память",
            "${ramPct.toInt()}% занято",
            "всего ${"%.1f".format(SystemInfo.gb(SystemInfo.ramTotalBytes(ctx)))} ГБ", Brand.purple)
        // Карточка «Интернет» с живым спарклайном ↓/↑
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Box(
                    Modifier.size(46.dp).background(Brand.green.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                    contentAlignment = Alignment.Center
                ) { Icon(Icons.Filled.Wifi, contentDescription = null, tint = Brand.green) }
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("ИНТЕРНЕТ", color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Text("↓ ${SystemInfo.fmtRate(net.downBps)}   ↑ ${SystemInfo.fmtRate(net.upBps)}",
                        color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.weight(1f))
                Box(Modifier.size(width = 90.dp, height = 34.dp)) {
                    Sparkline(upHist, Brand.blue, Modifier.fillMaxSize())
                    Sparkline(downHist, Brand.green, Modifier.fillMaxSize())
                }
            }
        }

        Text("Создатель: ${Brand.AUTHOR}", color = Brand.muted, fontSize = 11.sp)
    }
}

@Composable
private fun MetricRing(value: Float, label: String, invert: Boolean = false) {
    val color = if (invert) Brand.load(100f - value) else Brand.load(value)
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        RingGauge(progress = value / 100f, color = color, size = 72.dp, stroke = 9.dp) {
            Text("${value.toInt()}%", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        }
        Text(label, color = Brand.muted, fontSize = 10.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun Sparkline(values: List<Float>, color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier) {
        if (values.size < 2) return@Canvas
        val peak = (values.maxOrNull() ?: 1f).coerceAtLeast(1f)
        val n = values.size - 1
        val path = Path()
        values.forEachIndexed { i, v ->
            val x = size.width * i / n
            val y = size.height - size.height * (v / peak)
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, color, style = Stroke(width = 4f, cap = StrokeCap.Round))
    }
}

@Composable
fun InfoCard(icon: ImageVector, title: String, value: String, sub: String, tint: Color) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Box(
                Modifier.size(46.dp).background(tint.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) { Icon(icon, contentDescription = null, tint = tint) }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Text(value, color = Brand.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                Text(sub, color = Brand.muted, fontSize = 12.sp)
            }
        }
    }
}
