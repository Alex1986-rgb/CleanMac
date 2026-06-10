// Фирменные кольца KRYLAN (DESIGN.md: толщина 10-16, скруглённые концы).
package com.krylan.app.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun RingGauge(
    progress: Float,                 // 0..1
    color: Color,
    size: Dp = 80.dp,
    stroke: Dp = 10.dp,
    content: @Composable () -> Unit = {}
) {
    val animated by animateFloatAsState(
        targetValue = progress.coerceIn(0f, 1f),
        animationSpec = tween(500), label = "ring"
    )
    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(size)) {
        Canvas(Modifier.size(size)) {
            val sw = stroke.toPx()
            val arcSize = Size(this.size.width - sw, this.size.height - sw)
            val topLeft = Offset(sw / 2f, sw / 2f)
            drawArc(
                color = Brand.track, startAngle = -90f, sweepAngle = 360f,
                useCenter = false, topLeft = topLeft, size = arcSize,
                style = Stroke(sw, cap = StrokeCap.Round)
            )
            drawArc(
                color = color, startAngle = -90f, sweepAngle = 360f * animated,
                useCenter = false, topLeft = topLeft, size = arcSize,
                style = Stroke(sw, cap = StrokeCap.Round)
            )
        }
        content()
    }
}
