// Фирменный анимированный каркасный глобус KRYLAN: вращающаяся неон-циан планета.
package com.krylan.app.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Анимированный каркасный глобус в неон-циан палитре KRYLAN.
 * Бесконечное вращение меридианов + пульс-сердцебиение ореола.
 */
@Composable
fun GlobeView(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "globe")
    // t — секунды, монотонно растёт (период 60с, чтобы хватало для %1f и фаз).
    val t by transition.animateFloat(
        initialValue = 0f,
        targetValue = 60f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 60_000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "globe-time"
    )

    Canvas(modifier = modifier) {
        val cx = size.width / 2f
        val cy = size.height / 2f
        val r = (minOf(size.width, size.height) / 2f) * 0.62f

        val cyan = Brand.cyan
        val node = Color(0xFFFF66D4)

        // Пульс-сердцебиение.
        val ph = (t * 1.8f) % 1f
        val rawPuls = exp(-((ph - 0.16f) * (ph - 0.16f)) / 0.004f) +
            0.6f * exp(-((ph - 0.34f) * (ph - 0.34f)) / 0.004f)
        val puls = rawPuls.coerceAtMost(1f)

        // Ореол: 4 окружности с убыванием alpha.
        for (k in 0 until 4) {
            val rad = r + k * 4f + puls * 7f
            val alpha = (0.30f - k * 0.06f).coerceAtLeast(0.04f)
            drawCircle(
                color = cyan.copy(alpha = alpha),
                radius = rad,
                center = Offset(cx, cy),
                style = Stroke(width = 1.5f)
            )
        }

        // Кольцо-импульс на ударе.
        if (puls > 0.15f) {
            drawCircle(
                color = cyan.copy(alpha = 0.35f * puls),
                radius = r + 8f + puls * 16f,
                center = Offset(cx, cy),
                style = Stroke(width = 2f)
            )
        }

        // Тёмная сфера + лимб.
        drawCircle(
            color = cyan.copy(alpha = 0.10f),
            radius = r,
            center = Offset(cx, cy)
        )
        drawCircle(
            color = cyan.copy(alpha = (0.55f + 0.4f * puls).coerceAtMost(1f)),
            radius = r,
            center = Offset(cx, cy),
            style = Stroke(width = 2f)
        )

        // Параллели.
        for (lat in listOf(-0.66f, -0.33f, 0f, 0.33f, 0.66f)) {
            val rx = r * sqrt(1f - lat * lat)
            drawOval(
                color = cyan.copy(alpha = 0.45f),
                topLeft = Offset(cx - rx, cy - r * lat - rx * 0.18f),
                size = Size(2f * rx, 2f * rx * 0.18f),
                style = Stroke(width = 1f)
            )
        }

        // Меридианы (вращаются).
        val phase = t * 2.4f
        for (k in 0..5) {
            val ang = phase + k * (PI.toFloat() / 6f)
            val rx = abs(r * cos(ang))
            drawOval(
                color = cyan.copy(alpha = 0.40f),
                topLeft = Offset(cx - rx, cy - r),
                size = Size(2f * rx, 2f * r),
                style = Stroke(width = 1f)
            )
        }

        // Узлы-«города» на передней полусфере.
        val lats = listOf(0.55f, 0.20f, -0.10f, 0.40f, -0.35f, 0.05f, -0.50f)
        for (n in 0 until 7) {
            val na = phase + n * 0.9f
            if (sin(na) > -0.1f) {
                val la = lats[n]
                val rx = r * sqrt(1f - la * la)
                val px = cx + rx * cos(na)
                val py = cy - r * la
                drawCircle(
                    color = node,
                    radius = 3f,
                    center = Offset(px, py)
                )
            }
        }
    }
}
