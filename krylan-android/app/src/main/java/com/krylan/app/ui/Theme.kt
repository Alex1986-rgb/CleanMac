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

    // HUD-«рубка» CleanMac: navy-база, glass-карточки, неон-акценты.
    val bg0 = Color(0xFF091327)     // navy фон
    val glowIn = Color(0xFF173D72)  // центр радиального свечения
    val glowOut = Color(0xFF060D1E) // края радиального свечения
    val glass = Color(0xFF102444)   // стекло
    val track = Color(0xFF22436F)   // дорожка гейджа
    val text = Color(0xFFE4EEFB)
    val muted = Color(0xFF7088B2)
    val green = Color(0xFF2FE5A0)
    val blue = Color(0xFF2F8FFF)
    val yellow = Color(0xFFFFD60A)
    val red = Color(0xFFFF5A52)
    val purple = Color(0xFFBF5AF2)  // оставлен для совместимости (карточки)
    val cyan = Color(0xFF36D6FF)

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
