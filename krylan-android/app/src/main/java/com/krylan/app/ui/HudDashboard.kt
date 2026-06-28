// HUD-«рубка» KRYLAN: радиальный дашборд как в macOS CleanMac.
// Планета в центре, кольца-гейджи вокруг по углам, navy-фон со свечением и звёздами.
package com.krylan.app.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.random.Random

/**
 * Радиальное HUD-кольцо (гейдж): 28 насечек (горят до значения, каждая 6-я длиннее),
 * track-круг, светящаяся дуга прогресса, белая точка-конец, значение + подпись по центру.
 */
@Composable
fun HudGauge(
    progress: Float,        // 0..1
    color: Color,
    label: String,
    valueText: String,
    size: Dp = 84.dp,
) {
    val frac = progress.coerceIn(0f, 1f)
    val transition = rememberInfiniteTransition(label = "hud-gauge")
    val pulse by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "hud-pulse"
    )

    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(size)) {
        Canvas(Modifier.size(size)) {
            val cx = this.size.width / 2f
            val cy = this.size.height / 2f
            val center = Offset(cx, cy)
            val outer = min(cx, cy)
            val ringR = outer * 0.78f
            val sw = outer * 0.14f

            // Track-круг.
            drawCircle(
                color = Brand.track.copy(alpha = 0.55f),
                radius = ringR,
                center = center,
                style = Stroke(width = sw * 0.6f)
            )

            // 28 насечек по кругу (-90° старт). Горят до frac, каждая 6-я длиннее.
            val ticks = 28
            for (i in 0 until ticks) {
                val ang = (-90f + i * 360f / ticks) * (Math.PI.toFloat() / 180f)
                val lit = i.toFloat() / ticks <= frac
                val longTick = i % 6 == 0
                val len = if (longTick) outer * 0.20f else outer * 0.11f
                val rIn = ringR - len / 2f
                val rOut = ringR + len / 2f
                val tColor = if (lit) color else Brand.track.copy(alpha = 0.4f)
                drawLine(
                    color = tColor,
                    start = Offset(cx + rIn * cos(ang), cy + rIn * sin(ang)),
                    end = Offset(cx + rOut * cos(ang), cy + rOut * sin(ang)),
                    strokeWidth = if (longTick) 2.4f else 1.6f,
                    cap = StrokeCap.Round
                )
            }

            // Светящаяся дуга прогресса (сначала размытый ореол, потом ядро).
            val arcSize = Size((ringR) * 2f, (ringR) * 2f)
            val arcTopLeft = Offset(cx - ringR, cy - ringR)
            val sweep = 360f * frac
            drawArc(
                color = color.copy(alpha = 0.25f + 0.15f * pulse),
                startAngle = -90f,
                sweepAngle = sweep,
                useCenter = false,
                topLeft = arcTopLeft,
                size = arcSize,
                style = Stroke(width = sw * 1.8f, cap = StrokeCap.Round)
            )
            drawArc(
                color = color,
                startAngle = -90f,
                sweepAngle = sweep,
                useCenter = false,
                topLeft = arcTopLeft,
                size = arcSize,
                style = Stroke(width = sw, cap = StrokeCap.Round)
            )

            // Белая точка-конец дуги.
            if (frac > 0f) {
                val endAng = (-90f + sweep) * (Math.PI.toFloat() / 180f)
                val ex = cx + ringR * cos(endAng)
                val ey = cy + ringR * sin(endAng)
                drawCircle(color = color.copy(alpha = 0.35f), radius = sw * 0.85f, center = Offset(ex, ey))
                drawCircle(color = Color.White, radius = sw * 0.45f, center = Offset(ex, ey))
            }
        }
        // Значение + подпись по центру.
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(valueText, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(label, color = Brand.muted, fontSize = 7.sp, fontWeight = FontWeight.Bold)
        }
    }
}

/** Одна метрика для HUD-гейджа: подпись, значение, прогресс 0..1 и цвет. */
data class HudMetric(
    val label: String,
    val valueText: String,
    val progress: Float,
    val color: Color,
)

/**
 * Радиальный HUD-«рубка»: звёздный navy-фон со свечением, центральный глобус,
 * 6 гейджей по углам -120/-60/0/60/120/180 на cyan-коннекторах,
 * часы сверху, интернет ↓/↑ справа, мини-ЭКГ слева, имя устройства под планетой.
 */
@Composable
fun HudConsole(
    metrics: List<HudMetric>,        // ожидается до 6 элементов
    deviceName: String,
    clock: String,
    downRate: String,
    upRate: String,
    ekg: List<Float>,
    modifier: Modifier = Modifier,
) {
    // Стабильные звёзды на всё время жизни компонента.
    val stars = remember {
        val rnd = Random(42)
        List(60) {
            Triple(rnd.nextFloat(), rnd.nextFloat(), 0.25f + rnd.nextFloat() * 0.55f)
        }
    }

    val transition = rememberInfiniteTransition(label = "hud-console")
    val twinkle by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 3000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "twinkle"
    )

    val orbit = 130.dp
    val gaugeSize = 78.dp
    val planet = 110.dp
    val boxH = 360.dp

    // Углы гейджей (как в эталоне).
    val angles = listOf(-120f, -60f, 0f, 60f, 120f, 180f)

    Box(
        modifier
            .fillMaxWidth()
            .height(boxH),
        contentAlignment = Alignment.Center
    ) {
        // Фон: радиальный градиент (центр-верх светлее) + звёзды + коннекторы.
        Canvas(Modifier.fillMaxSize()) {
            val w = this.size.width
            val h = this.size.height
            // Радиальное свечение от центра-верха.
            drawRect(
                brush = Brush.radialGradient(
                    colors = listOf(Brand.glowIn, Brand.bg0, Brand.glowOut),
                    center = Offset(w / 2f, h * 0.42f),
                    radius = maxOf(w, h) * 0.8f
                ),
                size = this.size
            )
            // Звёзды (~60 точек) с лёгким мерцанием.
            stars.forEach { (sx, sy, base) ->
                val a = (base + 0.2f * (twinkle - 0.5f)).coerceIn(0.08f, 0.9f)
                drawCircle(
                    color = Brand.text.copy(alpha = a),
                    radius = base * 1.4f,
                    center = Offset(sx * w, sy * h)
                )
            }
            // Коннектор-линии от центра к позициям гейджей (cyan).
            val cx = w / 2f
            val cy = h / 2f
            val orbitPx = orbit.toPx()
            angles.forEachIndexed { i, deg ->
                if (i < metrics.size) {
                    val rad = deg * (Math.PI.toFloat() / 180f)
                    val gx = cx + orbitPx * cos(rad)
                    val gy = cy + orbitPx * sin(rad)
                    drawLine(
                        color = Brand.cyan.copy(alpha = 0.35f),
                        start = Offset(cx, cy),
                        end = Offset(gx, gy),
                        strokeWidth = 1.4f,
                        cap = StrokeCap.Round
                    )
                }
            }
        }

        // Центральный глобус.
        GlobeView(Modifier.size(planet))

        // Имя устройства под планетой.
        Text(
            deviceName,
            color = Brand.text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.offset(y = planet / 2f + 14.dp)
        )

        // Часы сверху.
        Text(
            clock,
            color = Brand.cyan,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.align(Alignment.TopCenter)
        )

        // Интернет ↓/↑ справа сверху.
        Column(
            horizontalAlignment = Alignment.End,
            modifier = Modifier.align(Alignment.TopEnd)
        ) {
            Text("↓ $downRate", color = Brand.green, fontSize = 10.sp, fontWeight = FontWeight.Bold)
            Text("↑ $upRate", color = Brand.blue, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        }

        // Мини-ЭКГ слева сверху.
        Box(
            Modifier
                .align(Alignment.TopStart)
                .size(width = 88.dp, height = 30.dp)
        ) {
            EkgLine(ekg, Brand.red, Modifier.fillMaxSize())
        }

        // 6 гейджей по углам на орбите.
        angles.forEachIndexed { i, deg ->
            if (i < metrics.size) {
                val m = metrics[i]
                val rad = deg * (Math.PI.toFloat() / 180f)
                val dx = orbit * cos(rad)
                val dy = orbit * sin(rad)
                Box(
                    Modifier.offset(x = dx, y = dy),
                    contentAlignment = Alignment.Center
                ) {
                    HudGauge(
                        progress = m.progress,
                        color = m.color,
                        label = m.label,
                        valueText = m.valueText,
                        size = gaugeSize
                    )
                }
            }
        }
    }
}

/** Мини-ЭКГ: линия из значений 0..1, отрисованная как пик-кардиограмма. */
@Composable
fun EkgLine(values: List<Float>, color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier) {
        if (values.size < 2) return@Canvas
        val n = values.size - 1
        val w = size.width
        val h = size.height
        var prev = Offset(0f, h - h * values[0].coerceIn(0f, 1f))
        for (i in 1..n) {
            val x = w * i / n
            val y = h - h * values[i].coerceIn(0f, 1f)
            val cur = Offset(x, y)
            drawLine(color = color, start = prev, end = cur, strokeWidth = 2f, cap = StrokeCap.Round)
            prev = cur
        }
    }
}
