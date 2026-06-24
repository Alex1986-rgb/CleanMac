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

    // Системные цвета iOS (Apple HIG): чёрная база, карточки systemGray6.
    val bg0 = Color(0xFF000000)
    val glass = Color(0xFF1C1C1E)   // systemGray6
    val track = Color(0xFF3A3A3C)   // systemGray4
    val text = Color(0xFFFFFFFF)
    val muted = Color(0xFF98989F)
    val green = Color(0xFF30D158)   // systemGreen
    val blue = Color(0xFF0A84FF)    // systemBlue
    val yellow = Color(0xFFFFD60A)  // systemYellow
    val red = Color(0xFFFF453A)     // systemRed
    val purple = Color(0xFFBF5AF2)  // systemPurple
    val cyan = Color(0xFF64D2FF)    // systemTeal

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
