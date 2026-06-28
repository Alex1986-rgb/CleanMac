// Крупные файлы и медиа-дубликаты: список через MediaStore, удаление через системный диалог.
package com.krylan.app.screens

import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.IntentSender
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.core.content.ContextCompat
import com.krylan.app.MediaFile
import com.krylan.app.MediaStoreUtils
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Запрашивает доступ к медиа; показывает content только после разрешения. */
@Composable
private fun MediaPermissionGate(ctx: Context, content: @Composable () -> Unit) {
    val perms = remember { MediaStoreUtils.readPermissions() }
    var granted by remember {
        mutableStateOf(perms.all {
            ContextCompat.checkSelfPermission(ctx, it) == PackageManager.PERMISSION_GRANTED
        })
    }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result -> granted = result.values.any { it } }

    if (granted) { content(); return }

    Column(
        Modifier.fillMaxSize().background(Brand.bg0).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("Нужен доступ к медиатеке", color = Brand.text, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(
            "KRYLAN сканирует фото, видео и аудио, чтобы найти крупные файлы и дубликаты. Ничего не отправляется в сеть.",
            color = Brand.muted, fontSize = 13.sp,
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp)
        )
        Button(
            onClick = { launcher.launch(perms) },
            colors = ButtonDefaults.buttonColors(containerColor = Brand.green, contentColor = Color(0xFF0B1410)),
            shape = RoundedCornerShape(50)
        ) { Text("Разрешить доступ", fontWeight = FontWeight.Bold) }
    }
}

/**
 * Контроллер действий над медиа: безопасное удаление «в корзину» (Android 11+, обратимо)
 * с возможностью «Отменить», плюс fallback на необратимое удаление до API 30.
 * Держит [statusText] для текстового баннера и [canUndo] для кнопки отмены.
 */
private class MediaActions(
    /** Запуск системного запроса корзины: trashTo=true — в корзину, false — восстановить. */
    private val launchTrash: (uris: List<Uri>, trashTo: Boolean) -> Unit,
    /** Необратимое удаление media-uri через createDeleteRequest (fallback / API < 30). */
    private val launchDelete: (List<MediaFile>) -> Unit,
    /** Прямое удаление не-медиа (APK/документы): возвращает кол-во удалённых. */
    private val deleteNonMedia: (List<MediaFile>) -> Int,
    /** Перезагрузка списка после операции без системного диалога. */
    private val reload: () -> Unit,
    val supportsTrash: Boolean,
) {
    var statusText by mutableStateOf<String?>(null)
    var canUndo by mutableStateOf(false)
        private set

    // Последняя партия uri, перемещённая в корзину — для «Отменить».
    private var lastTrashed: List<Uri> = emptyList()

    /**
     * Основное действие кнопки «Удалить».
     * Делим файлы на медиа и не-медиа: для медиа — системная корзина/delete-request
     * (валидный media-uri); для не-медиа (APK/документы/архивы) — прямой contentResolver.delete,
     * т.к. trash/deleteRequest требуют media-uri и иначе падают.
     */
    fun remove(files: List<MediaFile>) {
        if (files.isEmpty()) return
        val media = files.filter { it.isMedia }
        val nonMedia = files.filter { !it.isMedia }

        // Не-медиа удаляем напрямую (подтверждение пользователь уже дал в UI).
        var directDeleted = 0
        if (nonMedia.isNotEmpty()) {
            directDeleted = deleteNonMedia(nonMedia)
        }

        if (media.isNotEmpty()) {
            // Системный диалог; баннер для не-медиа дополним после возврата, если он был.
            pendingDirectDeleted = directDeleted
            if (supportsTrash) {
                lastTrashed = media.map { it.uri }
                launchTrash(lastTrashed, true)
            } else {
                launchDelete(media)
            }
        } else {
            // Только не-медиа — системного диалога не будет: показываем итог и перечитываем список.
            pendingDirectDeleted = 0
            statusText = "Удалено файлов: $directDeleted"
            canUndo = false
            reload()
        }
    }

    /** Кол-во не-медиа, удалённых напрямую в текущей операции (для честного баннера). */
    private var pendingDirectDeleted: Int = 0

    /** Отмена последнего перемещения в корзину — восстановление тех же uri. */
    fun undo() {
        if (canUndo && lastTrashed.isNotEmpty()) launchTrash(lastTrashed, false)
    }

    /**
     * Вызывается после успешного системного запроса.
     * [count] — число медиа-uri в запросе (фактический исход системе известен лишь как
     * RESULT_OK; список перечитывается через reload, поэтому формулируем честно — без обещаний
     * освобождённого места: оно освобождается только после очистки корзины).
     */
    fun onTrashed(count: Int) {
        val extra = pendingDirectDeleted
        pendingDirectDeleted = 0
        statusText = if (supportsTrash) {
            val base = "Запрошено в корзину: $count. Место освободится после очистки корзины " +
                "(через 30 дней автоматически либо вручную в Google Фото / Файлах)."
            if (extra > 0) "$base Удалено других файлов: $extra." else base
        } else {
            val base = "Запрошено удаление: $count."
            if (extra > 0) "$base Удалено других файлов: $extra." else base
        }
        canUndo = supportsTrash
    }

    /** Вызывается после успешного восстановления из корзины. */
    fun onRestored() {
        statusText = "Восстановлено из корзины"
        canUndo = false
        lastTrashed = emptyList()
    }

    /** Сброс баннера. */
    fun clearStatus() {
        statusText = null
    }
}

/**
 * Готовит контроллер действий: один StartIntentSenderForResult обслуживает удаление,
 * перемещение в корзину и восстановление. На API < 30 системной корзины нет —
 * удаляем напрямую (необратимо). [onDone] перезагружает список после успеха.
 */
@Composable
private fun rememberMediaActions(ctx: Context, onDone: () -> Unit): MediaActions {
    val supportsTrash = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R

    // Что именно подтверждает пользователь в системном диалоге — для верного баннера.
    var pendingOp by remember { mutableStateOf<PendingOp>(PendingOp.None) }
    val actionsRef = remember { mutableStateOf<MediaActions?>(null) }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult()
    ) { result ->
        val op = pendingOp
        pendingOp = PendingOp.None
        if (result.resultCode == Activity.RESULT_OK) {
            when (op) {
                is PendingOp.Trash -> actionsRef.value?.onTrashed(op.count)
                is PendingOp.Delete -> actionsRef.value?.onTrashed(op.count)
                PendingOp.Restore -> actionsRef.value?.onRestored()
                PendingOp.None -> { /* баннер не нужен */ }
            }
            onDone()
        }
    }

    // A7: запуск системного диалога может бросить SendIntentException/ActivityNotFoundException.
    // Оборачиваем — иначе краш; при ошибке честно сообщаем, что часть файлов не удалена.
    fun launchSender(sender: IntentSender) {
        try {
            launcher.launch(IntentSenderRequest.Builder(sender).build())
        } catch (e: IntentSender.SendIntentException) {
            pendingOp = PendingOp.None
            actionsRef.value?.statusText = "Не удалось удалить часть файлов"
        } catch (e: android.content.ActivityNotFoundException) {
            pendingOp = PendingOp.None
            actionsRef.value?.statusText = "Не удалось удалить часть файлов"
        }
    }

    val launchTrash: (List<Uri>, Boolean) -> Unit = trash@{ uris, trashTo ->
        if (uris.isEmpty() || !supportsTrash) return@trash
        val pi: PendingIntent = MediaStoreUtils.trashRequest(ctx, uris, trash = trashTo)
        pendingOp = if (trashTo) PendingOp.Trash(uris.size) else PendingOp.Restore
        launchSender(pi.intentSender)
    }

    val launchDelete: (List<MediaFile>) -> Unit = del@{ files ->
        if (files.isEmpty()) return@del
        if (supportsTrash) {
            val pi = MediaStore.createDeleteRequest(ctx.contentResolver, files.map { it.uri })
            pendingOp = PendingOp.Delete(files.size)
            launchSender(pi.intentSender)
        } else {
            // API < 30: системной корзины нет — удаляем напрямую (необратимо).
            var n = 0
            files.forEach {
                runCatching { if (ctx.contentResolver.delete(it.uri, null, null) > 0) n++ }
            }
            actionsRef.value?.statusText = "Удалено: $n"
            onDone()
        }
    }

    // Прямое удаление не-медиа (APK/документы/архивы) — без системного диалога корзины.
    val deleteNonMedia: (List<MediaFile>) -> Int = nm@{ files ->
        if (files.isEmpty()) return@nm 0
        MediaStoreUtils.deleteDirect(ctx, files.map { it.uri })
    }

    val actions = remember {
        MediaActions(launchTrash, launchDelete, deleteNonMedia, onDone, supportsTrash)
    }
    actionsRef.value = actions
    return actions
}

/**
 * Режим локальной сортировки уже загруженного списка (без новых запросов к MediaStore).
 * MediaFile содержит только id/name/size/uri — поля даты нет, поэтому сортируем
 * лишь по размеру (убыв.) и по имени (А-Я).
 */
private enum class SortMode(val label: String) {
    Size("По размеру"),
    Name("По имени"),
}

/** Какую операцию пользователь подтверждает в системном диалоге. */
private sealed interface PendingOp {
    data object None : PendingOp
    data class Delete(val count: Int) : PendingOp
    data class Trash(val count: Int) : PendingOp
    data object Restore : PendingOp
}

/** Хаб «Медиа»: Крупные · Дубли · Скриншоты · Загрузки. */
@Composable
fun MediaHubScreen(ctx: Context) {
    var tab by remember { mutableIntStateOf(0) }
    val titles = listOf("Крупные", "Видео", "Дубли", "Скриншоты", "Загрузки", "Мессенджеры", "APK")
    Column(Modifier.fillMaxSize().background(Brand.bg0)) {
        Row(
            Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp)
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            titles.forEachIndexed { i, t ->
                val sel = tab == i
                Text(
                    t,
                    color = if (sel) Color(0xFF0B1410) else Brand.text,
                    fontSize = 13.sp, fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .background(if (sel) Brand.green else Brand.glass, RoundedCornerShape(50))
                        .clickable { tab = i }
                        .padding(horizontal = 13.dp, vertical = 8.dp)
                )
            }
        }
        when (tab) {
            0 -> GenericMediaScreen(ctx, "Крупные медиа-файлы") { MediaStoreUtils.largeFiles(it) }
            1 -> GenericMediaScreen(ctx, "Видео") { MediaStoreUtils.videos(it) }
            2 -> DuplicatesScreen(ctx)
            3 -> GenericMediaScreen(ctx, "Скриншоты") { MediaStoreUtils.screenshots(it) }
            4 -> GenericMediaScreen(ctx, "Загрузки") { MediaStoreUtils.downloads(it) }
            5 -> GenericMediaScreen(ctx, "Медиа мессенджеров") { MediaStoreUtils.messengerMedia(it) }
            else -> GenericMediaScreen(ctx, "APK") { MediaStoreUtils.apkFiles(it) }
        }
    }
}

@Composable
private fun GenericMediaScreen(ctx: Context, title: String, loader: (Context) -> List<MediaFile>) {
    MediaPermissionGate(ctx) {
        var reload by remember { mutableIntStateOf(0) }
        // null = идёт загрузка; иначе результат (возможно пустой).
        var files by remember { mutableStateOf<List<MediaFile>?>(null) }
        // Сброс выбора после успешного удаления/перезагрузки списка.
        var selected by remember { mutableStateOf<Set<Long>>(emptySet()) }
        val actions = rememberMediaActions(ctx) { reload++ }
        val haptics = LocalHapticFeedback.current

        // Авто-скан при открытии экрана (разрешения уже выданы — мы внутри гейта).
        // Тяжёлый запрос MediaStore — в IO, чтобы не блокировать главный поток.
        LaunchedEffect(reload, title) {
            files = null
            selected = emptySet()
            files = withContext(Dispatchers.IO) {
                try { loader(ctx) } catch (e: Exception) { emptyList() }
            }
        }

        val list = files
        val total = list?.sumOf { it.size } ?: 0L

        var sortMode by remember { mutableStateOf(SortMode.Size) }
        // Только сортировка отображения: пересчитываем при смене режима или перезагрузке списка.
        val sorted = remember(sortMode, list) {
            when (sortMode) {
                SortMode.Size -> list?.sortedByDescending { it.size }
                SortMode.Name -> list?.sortedBy { it.name.lowercase() }
            }
        }

        // Выбранные файлы и их суммарный размер (оценка освобождаемого места).
        val selectedFiles = remember(sorted, selected) {
            sorted?.filter { it.id in selected }.orEmpty()
        }
        val selectedBytes = selectedFiles.sumOf { it.size }

        Column(Modifier.fillMaxSize().background(Brand.bg0)) {
            TrashBanner(actions)
            if (sorted != null && sorted.isNotEmpty()) {
                SortChips(sortMode) { sortMode = it }
            }
            LazyColumn(
                Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(20.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                if (sorted == null) {
                    item {
                        Text("Загрузка…", color = Brand.muted, fontSize = 14.sp)
                    }
                } else {
                    item {
                        Text("$title · ${sorted.size} · ${SystemInfo.fmtSize(total)}",
                            color = Brand.muted, fontSize = 13.sp,
                            modifier = Modifier.padding(bottom = 4.dp))
                    }
                    items(sorted, key = { it.id }) { f ->
                        SelectableFileRow(
                            f = f,
                            checked = f.id in selected,
                            onToggle = {
                                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                selected = if (f.id in selected) selected - f.id else selected + f.id
                            }
                        )
                    }
                    if (sorted.isEmpty()) item {
                        Text("Ничего не найдено.", color = Brand.muted, fontSize = 14.sp)
                    }
                }
            }
            // Панель массового действия: видна, когда список загружен и непустой.
            if (sorted != null && sorted.isNotEmpty()) {
                val allSelected = selected.size == sorted.size
                SelectionBar(
                    allSelected = allSelected,
                    selectedCount = selectedFiles.size,
                    selectedBytes = selectedBytes,
                    supportsTrash = actions.supportsTrash,
                    onToggleAll = {
                        selected = if (allSelected) emptySet() else sorted.map { it.id }.toSet()
                    },
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

/**
 * Нижняя панель массового выбора: «Выбрать все»/«Снять» + «Удалить выбранные (N)»
 * с честной оценкой «освободит ≈ X». На Android 11+ удаление идёт в корзину.
 */
@Composable
private fun SelectionBar(
    allSelected: Boolean,
    selectedCount: Int,
    selectedBytes: Long,
    supportsTrash: Boolean,
    onToggleAll: () -> Unit,
    onDelete: () -> Unit,
) {
    val deleteVerb = if (supportsTrash) "В корзину" else "Удалить"
    Column(
        Modifier
            .fillMaxWidth()
            .background(Brand.glass)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onToggleAll) {
                Text(
                    if (allSelected) "Снять выбор" else "Выбрать все",
                    color = Brand.cyan, fontWeight = FontWeight.Bold, fontSize = 13.sp
                )
            }
            Spacer(Modifier.weight(1f))
            if (selectedCount > 0) {
                Text(
                    "освободит ≈ ${SystemInfo.fmtSize(selectedBytes)}",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
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

/** Сегмент-чипы выбора сортировки (визуально как табы в MediaHubScreen). */
@Composable
private fun SortChips(current: SortMode, onSelect: (SortMode) -> Unit) {
    Row(
        Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp)
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        SortMode.values().forEach { mode ->
            val sel = mode == current
            Text(
                mode.label,
                color = if (sel) Color(0xFF0B1410) else Brand.text,
                fontSize = 13.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .background(if (sel) Brand.green else Brand.glass, RoundedCornerShape(50))
                    .clickable { onSelect(mode) }
                    .padding(horizontal = 13.dp, vertical = 8.dp)
            )
        }
    }
}

/**
 * Текстовый баннер статуса последней операции с кнопкой «Отменить».
 * Material3 Scaffold/SnackbarHost в этих экранах нет — используем лёгкий текстовый статус,
 * чтобы не тащить лишнюю обвязку.
 */
@Composable
private fun TrashBanner(actions: MediaActions) {
    val status = actions.statusText ?: return
    Row(
        Modifier
            .fillMaxWidth()
            .background(Brand.glass)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(status, color = Brand.text, fontSize = 13.sp, modifier = Modifier.weight(1f))
        if (actions.canUndo) {
            TextButton(onClick = { actions.undo() }) {
                Text("Отменить", color = Brand.green, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }
        TextButton(onClick = { actions.clearStatus() }) {
            Text("Скрыть", color = Brand.muted, fontSize = 13.sp)
        }
    }
}

@Composable
fun DuplicatesScreen(ctx: Context) {
    MediaPermissionGate(ctx) {
        var reload by remember { mutableIntStateOf(0) }
        // null = идёт скан (до 5000 строк MediaStore); иначе результат (возможно пустой).
        var groups by remember { mutableStateOf<List<List<MediaFile>>?>(null) }
        // Выбранные к удалению (по id). «Лучший» в группе никогда сюда не попадает по умолчанию.
        var selected by remember { mutableStateOf<Set<Long>>(emptySet()) }
        val actions = rememberMediaActions(ctx) { reload++ }
        val haptics = LocalHapticFeedback.current

        // Авто-скан при открытии. Тяжёлый скан дубликатов — в IO.
        LaunchedEffect(reload) {
            groups = null
            selected = emptySet()
            groups = withContext(Dispatchers.IO) {
                try { MediaStoreUtils.duplicateGroups(ctx) } catch (e: Exception) { emptyList() }
            }
        }

        val list = groups
        val wastedBytes = list?.sumOf { g -> g.first().size * (g.size - 1) } ?: 0L

        // «Лучший» в каждой группе = первый (группы отсортированы, размеры внутри равны) — его оставляем.
        // Все остальные id — кандидаты на удаление.
        val allDeletableIds = remember(list) {
            list?.flatMap { g -> g.drop(1).map { it.id } }?.toSet() ?: emptySet()
        }
        val selectedFiles = remember(list, selected) {
            list?.flatten()?.filter { it.id in selected }.orEmpty()
        }
        val selectedBytes = selectedFiles.sumOf { it.size }

        Column(Modifier.fillMaxSize().background(Brand.bg0)) {
            TrashBanner(actions)
            LazyColumn(
                Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(20.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
            if (list == null) {
                item {
                    Text("Сканируем дубликаты…", color = Brand.muted, fontSize = 14.sp)
                }
            } else {
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Brand.glass),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp)
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Групп дубликатов: ${list.size}", color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        Text("Можно освободить до ${SystemInfo.fmtSize(wastedBytes)}", color = Brand.green, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
            items(list.size) { i ->
                val g = list[i]
                Card(
                    colors = CardDefaults.cardColors(containerColor = Brand.glass),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(g.first().name, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                        Text("${g.size} копии · ${SystemInfo.fmtSize(g.first().size)} каждая", color = Brand.muted, fontSize = 12.sp)
                        // Каждая копия с галочкой. Первая помечена «оставить» и не выбирается.
                        g.forEachIndexed { idx, f ->
                            val isBest = idx == 0
                            val checked = f.id in selected
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(10.dp))
                                    .clickable(enabled = !isBest) {
                                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                                        selected = if (checked) selected - f.id else selected + f.id
                                    }
                                    .padding(vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(
                                    imageVector = if (checked) Icons.Filled.CheckCircle else Icons.Filled.RadioButtonUnchecked,
                                    contentDescription = null,
                                    tint = when {
                                        isBest -> Brand.muted.copy(alpha = 0.4f)
                                        checked -> Brand.green
                                        else -> Brand.muted
                                    },
                                    modifier = Modifier.size(20.dp)
                                )
                                Text(
                                    "Копия ${idx + 1}" + if (isBest) " · оставить" else "",
                                    color = if (isBest) Brand.green else Brand.text,
                                    fontSize = 12.sp,
                                    fontWeight = if (isBest) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        }
                    }
                }
            }
            if (list.isEmpty()) item {
                Text("Дубликаты не найдены — отлично!", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            }
            }
            // Панель: «Выбрать все, кроме лучшего» / «Снять» + удалить выбранные.
            if (list != null && list.isNotEmpty()) {
                val allDeletableSelected = allDeletableIds.isNotEmpty() && selected.containsAll(allDeletableIds)
                DuplicatesSelectionBar(
                    allSelected = allDeletableSelected,
                    selectedCount = selectedFiles.size,
                    selectedBytes = selectedBytes,
                    supportsTrash = actions.supportsTrash,
                    onToggleAll = {
                        selected = if (allDeletableSelected) emptySet() else allDeletableIds
                    },
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

/**
 * Нижняя панель для дублей: «Выбрать все, кроме лучшего» (оставить по одной копии)
 * + «Удалить выбранные (N)» с оценкой освобождаемого места.
 */
@Composable
private fun DuplicatesSelectionBar(
    allSelected: Boolean,
    selectedCount: Int,
    selectedBytes: Long,
    supportsTrash: Boolean,
    onToggleAll: () -> Unit,
    onDelete: () -> Unit,
) {
    val deleteVerb = if (supportsTrash) "В корзину" else "Удалить"
    Column(
        Modifier
            .fillMaxWidth()
            .background(Brand.glass)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onToggleAll) {
                Text(
                    if (allSelected) "Снять выбор" else "Выбрать все, кроме лучшего",
                    color = Brand.cyan, fontWeight = FontWeight.Bold, fontSize = 13.sp
                )
            }
            Spacer(Modifier.weight(1f))
            if (selectedCount > 0) {
                Text(
                    "освободит ≈ ${SystemInfo.fmtSize(selectedBytes)}",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
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

/**
 * Строка файла с кружком-галочкой выбора. Тап по всей строке переключает выбор.
 * Выбранный — зелёный CheckCircle; невыбранный — серый RadioButtonUnchecked.
 */
@Composable
private fun SelectableFileRow(f: MediaFile, checked: Boolean, onToggle: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (checked) Brand.green.copy(alpha = 0.12f) else Brand.glass
        ),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier
                .clip(RoundedCornerShape(16.dp))
                .clickable(onClick = onToggle)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(
                imageVector = if (checked) Icons.Filled.CheckCircle else Icons.Filled.RadioButtonUnchecked,
                contentDescription = if (checked) "Выбрано" else "Не выбрано",
                tint = if (checked) Brand.green else Brand.muted,
                modifier = Modifier.size(24.dp).clip(CircleShape)
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(f.name, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Text(SystemInfo.fmtSize(f.size), color = Brand.muted, fontSize = 12.sp)
            }
        }
    }
}
