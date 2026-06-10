// Дашборд: Health-кольцо + кольца метрик + карточки (дизайн как в iOS-версии).
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Storage
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
import com.krylan.app.ui.RingGauge
import kotlinx.coroutines.delay

@Composable
fun DashboardScreen(ctx: Context) {
    var tick by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { while (true) { delay(3000); tick++ } }

    val storage = remember(tick) { SystemInfo.storage() }
    val ramPct = remember(tick) { SystemInfo.ramUsedPercent(ctx) }
    val battery = remember(tick) { SystemInfo.batteryPercent(ctx) }
    val health = remember(tick) { SystemInfo.healthScore(ctx) }
    val healthLabel = if (health >= 70) "Отлично" else if (health >= 40) "Внимание" else "Критично"

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Состояние в реальном времени", color = Brand.muted, fontSize = 14.sp)

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
