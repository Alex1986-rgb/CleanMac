// Умные подсказки (в духе Files by Google): карточки с реальными счётчиками и переходом к действию.
// Счётчики считаются лениво и безопасно (Dispatchers.IO + try/catch); при ошибке/без разрешения — «—».
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Photo
import androidx.compose.material.icons.filled.PhotoSizeSelectLarge
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

// Индексы вкладок должны совпадать с порядком enum Tab в MainActivity:
// 0 Dashboard, 1 Storage, 2 Cleanup, 3 Media, 4 Apps.
private const val TAB_CLEANUP = 2
private const val TAB_MEDIA = 3

/**
 * Колонка карточек-подсказок с живыми счётчиками.
 * @param onNavigate переключение вкладки по её индексу (ordinal enum Tab).
 */
@Composable
fun SmartSuggestions(ctx: Context, onNavigate: (Int) -> Unit) {
    // null = ещё считаем или ошибка/нет разрешения -> покажем «—».
    var cacheLabel by remember { mutableStateOf<String?>(null) }
    var screenshots by remember { mutableStateOf<Int?>(null) }
    var largeFiles by remember { mutableStateOf<Int?>(null) }
    var duplicates by remember { mutableStateOf<Int?>(null) }

    LaunchedEffect(Unit) {
        cacheLabel = runCatchingIo { SystemInfo.fmtSize(SystemInfo.cacheBytes(ctx)) }
        screenshots = runCatchingIo { MediaStoreUtils.screenshots(ctx).size }
        largeFiles = runCatchingIo { MediaStoreUtils.largeFiles(ctx).size }
        duplicates = runCatchingIo { MediaStoreUtils.duplicateGroups(ctx).size }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Подсказки", color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)

        SuggestionCard(
            icon = Icons.Filled.CleaningServices,
            tint = Brand.green,
            title = "Кэш приложения",
            value = "~ ${cacheLabel ?: "—"}",
            onClick = { onNavigate(TAB_CLEANUP) },
        )
        SuggestionCard(
            icon = Icons.Filled.Photo,
            tint = Brand.cyan,
            title = "Скриншоты",
            value = screenshots?.toString() ?: "—",
            onClick = { onNavigate(TAB_MEDIA) },
        )
        SuggestionCard(
            icon = Icons.Filled.PhotoSizeSelectLarge,
            tint = Brand.blue,
            title = "Крупные файлы",
            value = largeFiles?.toString() ?: "—",
            onClick = { onNavigate(TAB_MEDIA) },
        )
        SuggestionCard(
            icon = Icons.Filled.ContentCopy,
            tint = Brand.purple,
            title = "Дубли",
            value = duplicates?.toString() ?: "—",
            onClick = { onNavigate(TAB_MEDIA) },
        )
    }
}

/** Запускает блокирующую работу на IO-потоке; любая ошибка/отсутствие разрешения -> null. */
private suspend fun <T> runCatchingIo(block: () -> T): T? =
    try {
        withContext(Dispatchers.IO) { block() }
    } catch (_: Throwable) {
        null
    }

@Composable
private fun SuggestionCard(
    icon: ImageVector,
    tint: Color,
    title: String,
    value: String,
    onClick: () -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Row(
            Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Box(
                Modifier.size(42.dp).background(tint.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) { Icon(icon, contentDescription = null, tint = tint) }
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, color = Brand.muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Text(value, color = Brand.text, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.weight(1f))
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = Brand.muted,
            )
        }
    }
}
