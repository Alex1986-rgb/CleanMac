// Хранилище: кольцо занятости + разбивка занято/свободно/кэш приложения.
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import com.krylan.app.ui.RingGauge

@Composable
fun StorageScreen(ctx: Context) {
    val storage = remember { SystemInfo.storage() }
    val cache = remember { SystemInfo.cacheBytes(ctx) }

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                Modifier.fillMaxWidth().padding(vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                RingGauge(
                    progress = storage.usedPercent / 100f,
                    color = Brand.load(storage.usedPercent),
                    size = 170.dp, stroke = 16.dp
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("${storage.usedPercent.toInt()}%", color = Brand.text, fontSize = 40.sp, fontWeight = FontWeight.Bold)
                        Text("занято", color = Brand.muted, fontSize = 13.sp)
                    }
                }
                Text(
                    "${SystemInfo.fmtSize(storage.freeBytes)} свободно из ${SystemInfo.fmtSize(storage.totalBytes)}",
                    color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold
                )
            }
        }

        BreakdownRow("Занято", SystemInfo.fmtSize(storage.usedBytes), Brand.blue)
        BreakdownRow("Свободно", SystemInfo.fmtSize(storage.freeBytes), Brand.green)
        BreakdownRow("Кэш этого приложения", SystemInfo.fmtSize(cache), Brand.yellow)

        Text(
            "Android 11+ не даёт приложениям видеть чужие кэши — это ограничение системы, а не KRYLAN. Используйте «Файлы» и «Дубли», чтобы найти, что занимает место.",
            color = Brand.muted, fontSize = 12.sp
        )
    }
}

@Composable
private fun BreakdownRow(title: String, value: String, dot: Color) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(Modifier.size(12.dp).background(dot, CircleShape))
            Text(title, color = Brand.text, fontSize = 15.sp, modifier = Modifier.weight(1f))
            Text(value, color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        }
    }
}
