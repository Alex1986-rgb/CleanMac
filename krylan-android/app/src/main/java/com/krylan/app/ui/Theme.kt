// Бренд и палитра KRYLAN для Android.
package com.krylan.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object Brand {
    const val NAME = "KRYLAN"
    const val SLOGAN = "Дай устройству крылья"
    const val AUTHOR = "Кырлан Александр Сергеевич"

    val bg0 = Color(0xFF12161D)
    val glass = Color(0xFF212B37)
    val track = Color(0xFF333D4E)
    val text = Color(0xFFEEF2F8)
    val muted = Color(0xFF8A94A6)
    val green = Color(0xFF37D39A)
    val blue = Color(0xFF4B8CF9)
    val yellow = Color(0xFFF6BB45)
    val red = Color(0xFFF2685F)

    fun load(p: Float): Color = if (p < 60) green else if (p < 85) yellow else red
}

private val KrylanColors = darkColorScheme(
    primary = Brand.green,
    background = Brand.bg0,
    surface = Brand.glass,
    onBackground = Brand.text,
    onSurface = Brand.text,
)

@Composable
fun KrylanTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = KrylanColors, content = content)
}
