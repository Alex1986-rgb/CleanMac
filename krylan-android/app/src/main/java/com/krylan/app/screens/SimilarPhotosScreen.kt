// Похожие и размытые фото: сканирование perceptual-hash + резкости, мультивыбор, удаление в корзину.
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.MediaFile
import com.krylan.app.MediaStoreUtils
import com.krylan.app.PhotoAnalysis
import com.krylan.app.PhotoSignature
import com.krylan.app.SimilarGroup
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import kotlin.coroutines.coroutineContext

/** Состояние фонового скана: прогресс + результат. */
private sealed interface ScanState {
    data object Idle : ScanState
    data class Scanning(val done: Int, val total: Int) : ScanState
    data class Ready(val signatures: List<PhotoSignature>, val scanned: Int) : ScanState
}

/** Сколько последних фото анализируем максимум (честная подпись в UI). */
private const val MAX_PHOTOS = 2000

@Composable
fun SimilarPhotosScreen(ctx: Context) {
    MediaPermissionGate(ctx) {
        var mode by remember { mutableIntStateOf(0) } // 0 = Похожие, 1 = Размытые
        var reload by remember { mutableIntStateOf(0) }
        var scan by remember { mutableStateOf<ScanState>(ScanState.Idle) }
        var selected by remember { mutableStateOf<Set<Long>>(emptySet()) }
        val actions = rememberMediaActions(ctx) { reload++ }
        val haptics = LocalHapticFeedback.current

        // Скан: читаем последние фото, считаем подписи пачками, обновляя прогресс. Всё в IO.
        LaunchedEffect(reload) {
            selected = emptySet()
            scan = ScanState.Scanning(0, 0)
            val result = withContext(Dispatchers.IO) {
                val photos = try { MediaStoreUtils.recentImages(ctx, MAX_PHOTOS) } catch (e: Exception) { emptyList() }
                val total = photos.size
                scan = ScanState.Scanning(0, total)
                val sigs = ArrayList<PhotoSignature>(total)
                photos.forEachIndexed { i, f ->
                    coroutineContext.ensureActive()
                    sigs.add(PhotoAnalysis.signatureOf(ctx, f))
                    // Обновляем прогресс не на каждом кадре, чтобы не спамить рекомпозициями.
                    if (i % 15 == 0 || i == total - 1) scan = ScanState.Scanning(i + 1, total)
                }
                ScanState.Ready(sigs, total)
            }
            scan = result
        }

        val state = scan
        val groups: List<SimilarGroup> = remember(state) {
            (state as? ScanState.Ready)?.let { PhotoAnalysis.groupSimilar(it.signatures) } ?: emptyList()
        }
        val blurry: List<PhotoSignature> = remember(state) {
            (state as? ScanState.Ready)?.let { PhotoAnalysis.blurry(it.signatures) } ?: emptyList()
        }

        // Файлы по выбранным id (для оценки места и удаления).
        val allFilesById = remember(state) {
            (state as? ScanState.Ready)?.signatures?.associate { it.file.id to it.file } ?: emptyMap()
        }
        val selectedFiles: List<MediaFile> = remember(selected, allFilesById) {
            selected.mapNotNull { allFilesById[it] }
        }
        val selectedBytes = selectedFiles.sumOf { it.size }

        Column(Modifier.fillMaxSize().background(Brand.bg0)) {
            TrashBanner(actions)
            // Переключатель режима.
            Row(
                Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp)
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf("Похожие", "Размытые").forEachIndexed { i, t ->
                    val sel = mode == i
                    Text(
                        t,
                        color = if (sel) Color(0xFF0B1410) else Brand.text,
                        fontSize = 13.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .background(if (sel) Brand.green else Brand.glass, RoundedCornerShape(50))
                            .clickable { mode = i; selected = emptySet() }
                            .padding(horizontal = 13.dp, vertical = 8.dp)
                    )
                }
            }

            when (state) {
                is ScanState.Scanning -> ScanProgress(state.done, state.total)
                ScanState.Idle -> Box(Modifier.fillMaxWidth().padding(20.dp)) {
                    Text("Подготовка…", color = Brand.muted, fontSize = 14.sp)
                }
                is ScanState.Ready -> {
                    if (mode == 0) {
                        SimilarList(
                            groups = groups,
                            scanned = state.scanned,
                            selected = selected,
                            onToggle = { id ->
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                selected = if (id in selected) selected - id else selected + id
                            },
                            modifier = Modifier.weight(1f)
                        )
                        // Кандидаты к удалению = все, кроме лучшего в каждой группе.
                        val deletable = remember(groups) {
                            groups.flatMap { g -> g.photos.drop(1).map { it.file.id } }.toSet()
                        }
                        if (groups.isNotEmpty()) {
                            val allSel = deletable.isNotEmpty() && selected.containsAll(deletable)
                            DuplicatesSelectionBarLike(
                                toggleLabel = if (allSel) "Снять выбор" else "Выбрать все, кроме лучшего",
                                selectedCount = selectedFiles.size,
                                selectedBytes = selectedBytes,
                                supportsTrash = actions.supportsTrash,
                                onToggleAll = { selected = if (allSel) emptySet() else deletable },
                                onDelete = {
                                    if (selectedFiles.isNotEmpty()) {
                                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                        actions.remove(selectedFiles)
                                    }
                                }
                            )
                        }
                    } else {
                        BlurryList(
                            blurry = blurry,
                            scanned = state.scanned,
                            selected = selected,
                            onToggle = { id ->
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                selected = if (id in selected) selected - id else selected + id
                            },
                            modifier = Modifier.weight(1f)
                        )
                        if (blurry.isNotEmpty()) {
                            val allIds = remember(blurry) { blurry.map { it.file.id }.toSet() }
                            val allSel = selected.containsAll(allIds)
                            DuplicatesSelectionBarLike(
                                toggleLabel = if (allSel) "Снять выбор" else "Выбрать все",
                                selectedCount = selectedFiles.size,
                                selectedBytes = selectedBytes,
                                supportsTrash = actions.supportsTrash,
                                onToggleAll = { selected = if (allSel) emptySet() else allIds },
                                onDelete = {
                                    if (selectedFiles.isNotEmpty()) {
                                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                        actions.remove(selectedFiles)
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ScanProgress(done: Int, total: Int) {
    Column(Modifier.fillMaxWidth().padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            if (total > 0) "Анализируем фото… $done / $total" else "Читаем медиатеку…",
            color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold
        )
        if (total > 0) {
            LinearProgressIndicator(
                progress = { done.toFloat() / total.coerceAtLeast(1) },
                modifier = Modifier.fillMaxWidth(),
                color = Brand.green,
                trackColor = Brand.track,
            )
        }
        Text(
            "Считаем «отпечаток» и резкость каждого кадра локально. Ничего не отправляется в сеть.",
            color = Brand.muted, fontSize = 12.sp
        )
    }
}

@Composable
private fun SimilarList(
    groups: List<SimilarGroup>,
    scanned: Int,
    selected: Set<Long>,
    onToggle: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    val reclaimable = groups.sumOf { g -> g.photos.drop(1).sumOf { it.file.size } }
    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = Brand.glass),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp)
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Групп похожих: ${groups.size}", color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    Text("Проверено фото: $scanned (последние)", color = Brand.muted, fontSize = 12.sp)
                    if (groups.isNotEmpty())
                        Text("Можно освободить до ${SystemInfo.fmtSize(reclaimable)}", color = Brand.green, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        if (groups.isEmpty()) {
            item { Text("Похожих кадров не найдено — отлично!", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold) }
        }
        items(groups.size) { gi ->
            val g = groups[gi]
            Card(
                colors = CardDefaults.cardColors(containerColor = Brand.glass),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("${g.photos.size} похожих кадра", color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    g.photos.forEachIndexed { idx, p ->
                        val isBest = idx == 0
                        val checked = p.file.id in selected
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(10.dp))
                                .clickable(enabled = !isBest) { onToggle(p.file.id) }
                                .padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Icon(
                                imageVector = if (checked) Icons.Filled.CheckCircle else Icons.Filled.RadioButtonUnchecked,
                                contentDescription = null,
                                tint = when { isBest -> Brand.muted.copy(alpha = 0.4f); checked -> Brand.green; else -> Brand.muted },
                                modifier = Modifier.size(20.dp)
                            )
                            Column(Modifier.weight(1f)) {
                                Text(
                                    p.file.name + if (isBest) " · оставить (самое чёткое)" else "",
                                    color = if (isBest) Brand.green else Brand.text,
                                    fontSize = 12.sp,
                                    fontWeight = if (isBest) FontWeight.Bold else FontWeight.Normal,
                                    maxLines = 1
                                )
                                Text(SystemInfo.fmtSize(p.file.size), color = Brand.muted, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BlurryList(
    blurry: List<PhotoSignature>,
    scanned: Int,
    selected: Set<Long>,
    onToggle: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier.fillMaxWidth(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Text(
                "Размытые · ${blurry.size} · проверено $scanned",
                color = Brand.muted, fontSize = 13.sp, modifier = Modifier.padding(bottom = 4.dp)
            )
        }
        if (blurry.isEmpty()) {
            item { Text("Размытых фото не найдено.", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold) }
        }
        items(blurry, key = { it.file.id }) { p ->
            SelectableFileRow(
                f = p.file,
                checked = p.file.id in selected,
                onToggle = { onToggle(p.file.id) }
            )
        }
    }
}

/**
 * Локальная панель массового действия для этого экрана (нужны нестандартные подписи
 * «Выбрать все, кроме лучшего» / «Выбрать все»). Визуально совпадает с SelectionBar/Дубли.
 */
@Composable
private fun DuplicatesSelectionBarLike(
    toggleLabel: String,
    selectedCount: Int,
    selectedBytes: Long,
    supportsTrash: Boolean,
    onToggleAll: () -> Unit,
    onDelete: () -> Unit,
) {
    val deleteVerb = if (supportsTrash) "В корзину" else "Удалить"
    Column(
        Modifier.fillMaxWidth().background(Brand.glass).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.TextButton(onClick = onToggleAll) {
                Text(toggleLabel, color = Brand.cyan, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
            Spacer(Modifier.weight(1f))
            if (selectedCount > 0) {
                Text("освободит ≈ ${SystemInfo.fmtSize(selectedBytes)}", color = Brand.muted, fontSize = 12.sp)
            }
        }
        Box(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp))
                .background(if (selectedCount > 0) Brand.red else Brand.red.copy(alpha = 0.4f))
                .clickable(enabled = selectedCount > 0, onClick = onDelete)
                .padding(vertical = 13.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                if (selectedCount > 0) "$deleteVerb выбранные ($selectedCount)" else "Ничего не выбрано",
                color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold
            )
        }
    }
}
