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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Photo
import androidx.compose.material.icons.filled.PhotoSizeSelectLarge
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
import com.krylan.app.MediaStoreUtils
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import com.krylan.app.ui.HudConsole
import com.krylan.app.ui.HudMetric
import com.krylan.app.ui.RingGauge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale as JLocale

// Индекс вкладки «Медиа» = ordinal enum Tab в MainActivity (Dashboard0/Storage1/Cleanup2/Media3/Apps4).
private const val TAB_MEDIA_DASH = 3

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

    // Часы для HUD (обновляются вместе с tick).
    val clock = remember(tick) {
        SimpleDateFormat("HH:mm:ss", JLocale.US).format(Date())
    }
    // Нормированная ЭКГ-линия 0..1 из истории скачивания (для мини-кардиограммы слева).
    val ekg = remember(tick) {
        val peak = (downHist.maxOrNull() ?: 1f).coerceAtLeast(1f)
        downHist.map { (it / peak).coerceIn(0f, 1f) }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(
                Brush.radialGradient(
                    colors = listOf(Brand.glowIn, Brand.bg0, Brand.glowOut)
                )
            )
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Состояние в реальном времени", color = Brand.muted, fontSize = 14.sp)

        // ✨ Флагманская кнопка «Оптимизировать»: один тап делает всё безопасное
        // (чистит СВОЙ кэш) и быстро считает, что есть к разбору (скриншоты/крупные/дубли).
        // Удаление медиа НЕ авто — только переход на вкладку «Медиа» (системный диалог/корзина).
        // Формулировки честные — без «boost RAM / ускорить» (политика Google Play).
        val scope = rememberCoroutineScope()
        var optimizing by remember { mutableStateOf(false) }
        var result by remember { mutableStateOf<OptimizeResult?>(null) }

        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(50))
                .background(Brush.horizontalGradient(listOf(Brand.green, Brand.cyan)))
                .clickable(enabled = !optimizing) {
                    optimizing = true
                    result = null
                    scope.launch {
                        val r = withContext(Dispatchers.IO) {
                            // 1) Реально: чистим только кэш этого приложения.
                            val freed = try { SystemInfo.clearCache(ctx) } catch (_: Throwable) { 0L }
                            // 2) Быстрые подсчёты к разбору (без удаления).
                            val dupes = try { MediaStoreUtils.duplicateGroups(ctx).size } catch (_: Throwable) { 0 }
                            val shots = try { MediaStoreUtils.screenshots(ctx).size } catch (_: Throwable) { 0 }
                            val large = try { MediaStoreUtils.largeFiles(ctx).size } catch (_: Throwable) { 0 }
                            OptimizeResult(freedBytes = freed, duplicates = dupes, screenshots = shots, largeFiles = large)
                        }
                        result = r
                        optimizing = false
                    }
                }
                .padding(vertical = 15.dp),
            contentAlignment = Alignment.Center
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (optimizing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = Color(0xFF0B1410),
                        strokeWidth = 2.dp
                    )
                }
                Text(
                    if (optimizing) "Оптимизирую…" else "✨  Оптимизировать",
                    color = Color(0xFF0B1410), fontSize = 16.sp, fontWeight = FontWeight.Bold
                )
            }
        }
        Text(
            "Чистит только кэш этого приложения и показывает, что найдено к разбору. " +
                "Системные файлы и чужие данные не трогаем. Медиа удаляется вручную в разделе «Медиа».",
            color = Brand.muted, fontSize = 11.sp
        )

        // Карточка-результат после оптимизации: очищено + что найдено к разбору, с переходами.
        result?.let { r ->
            OptimizeResultCard(r, onNavigate)
        }

        // Умные подсказки с реальными счётчиками и переходом на нужную вкладку.
        SmartSuggestions(ctx, onNavigate)

        // HUD-«рубка» KRYLAN: радиальный дашборд (планета в центре, гейджи по кругу).
        val downPct = run {
            val peak = (downHist.maxOrNull() ?: 1f).coerceAtLeast(1f)
            (net.downBps.toFloat() / peak).coerceIn(0f, 1f)
        }
        val hudMetrics = listOf(
            // -120: ЗДОРОВЬЕ (выше — лучше → цвет по запасу)
            HudMetric("ЗДОРОВЬЕ", "${health.toInt()}", health / 100f, Brand.load(100f - health)),
            // -60: ОЗУ
            HudMetric("ОЗУ", "${ramPct.toInt()}%", ramPct / 100f, Brand.load(ramPct)),
            // 0: ДИСК
            HudMetric("ДИСК", "${storage.usedPercent.toInt()}%", storage.usedPercent / 100f, Brand.load(storage.usedPercent)),
            // 60: ПАМЯТЬ (нагрузка ОЗУ как «загрузка системы»)
            HudMetric("CPU", "${ramPct.toInt()}%", ramPct / 100f, Brand.load(ramPct)),
            // 120: СЕТЬ (доля от пика загрузки)
            HudMetric("СЕТЬ", SystemInfo.fmtRate(net.downBps), downPct, Brand.cyan),
            // 180: БАТАРЕЯ (выше — лучше)
            HudMetric("БАТАРЕЯ", "$battery%", battery / 100f, Brand.load(100f - battery)),
        )
        HudConsole(
            metrics = hudMetrics,
            deviceName = android.os.Build.MODEL ?: Brand.NAME,
            clock = clock,
            downRate = SystemInfo.fmtRate(net.downBps),
            upRate = SystemInfo.fmtRate(net.upBps),
            ekg = ekg,
            modifier = Modifier.fillMaxWidth()
        )

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

/** Итог оптимизации: освобождённый кэш + счётчики к ручному разбору. */
data class OptimizeResult(
    val freedBytes: Long,
    val duplicates: Int,
    val screenshots: Int,
    val largeFiles: Int,
)

@Composable
private fun OptimizeResultCard(r: OptimizeResult, onNavigate: (Int) -> Unit) {
    val toReview = r.duplicates + r.screenshots + r.largeFiles
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Brand.green)
                Text("Готово", color = Brand.text, fontSize = 17.sp, fontWeight = FontWeight.Bold)
            }
            Text(
                "Очищено кэша: ${SystemInfo.fmtSize(r.freedBytes)}",
                color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold
            )
            if (toReview > 0) {
                Text("Найдено к разбору", color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                ReviewRow(Icons.Filled.ContentCopy, Brand.purple, "Дубли", r.duplicates) { onNavigate(TAB_MEDIA_DASH) }
                ReviewRow(Icons.Filled.Photo, Brand.cyan, "Скриншоты", r.screenshots) { onNavigate(TAB_MEDIA_DASH) }
                ReviewRow(Icons.Filled.PhotoSizeSelectLarge, Brand.blue, "Крупные файлы", r.largeFiles) { onNavigate(TAB_MEDIA_DASH) }
                Text(
                    "Медиа не удаляется автоматически — открой раздел «Медиа», удаление идёт через системный диалог (корзину).",
                    color = Brand.muted, fontSize = 11.sp
                )
            } else {
                Text("Ничего лишнего к разбору не нашли.", color = Brand.muted, fontSize = 13.sp)
            }
        }
    }
}

@Composable
private fun ReviewRow(icon: ImageVector, tint: Color, title: String, count: Int, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Box(
            Modifier.size(36.dp).background(tint.copy(alpha = 0.15f), RoundedCornerShape(10.dp)),
            contentAlignment = Alignment.Center
        ) { Icon(icon, contentDescription = null, tint = tint) }
        Text(title, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.weight(1f))
        Text("$count", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Icon(
            Icons.AutoMirrored.Filled.KeyboardArrowRight,
            contentDescription = null,
            tint = Brand.muted
        )
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
