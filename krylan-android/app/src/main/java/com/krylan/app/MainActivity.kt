// KRYLAN — Android дашборд (Jetpack Compose). Создатель: Кырлан Александр Сергеевич.
package com.krylan.app

import android.app.ActivityManager
import android.content.Context
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.os.StatFs
import android.os.Environment
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.ui.Brand
import com.krylan.app.ui.KrylanTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { KrylanTheme { Dashboard(this) } }
    }
}

private fun gb(bytes: Long) = (bytes / 1_073_741_824.0)

@Composable
fun Dashboard(ctx: Context) {
    // --- Хранилище ---
    val stat = StatFs(Environment.getDataDirectory().path)
    val total = stat.blockCountLong * stat.blockSizeLong
    val free = stat.availableBlocksLong * stat.blockSizeLong
    val diskUsedPct = if (total > 0) ((total - free) * 100f / total) else 0f

    // --- Память ---
    val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    val mem = ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
    val ramUsedPct = if (mem.totalMem > 0) ((mem.totalMem - mem.availMem) * 100f / mem.totalMem) else 0f

    // --- Батарея ---
    val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
    val battery = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("🪽 ${Brand.NAME}", color = Brand.text, fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text("«${Brand.SLOGAN}»", color = Brand.green, fontWeight = FontWeight.Bold)

        Metric("Хранилище", "${"%.1f".format(gb(free))} ГБ свободно из ${"%.0f".format(gb(total))} ГБ", diskUsedPct)
        Metric("Память", "${ramUsedPct.toInt()}% занято · всего ${"%.1f".format(gb(mem.totalMem))} ГБ", ramUsedPct)
        Metric("Батарея", "$battery%", (100 - battery).toFloat())

        Text("Создатель: ${Brand.AUTHOR}", color = Brand.muted, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
    }
}

@Composable
fun Metric(title: String, value: String, loadPct: Float) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Text(value, color = Brand.text, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            LinearProgressIndicator(
                progress = { (loadPct / 100f).coerceIn(0f, 1f) },
                color = Brand.load(loadPct),
                trackColor = Brand.track,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}
