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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.krylan.app.MediaFile
import com.krylan.app.MediaStoreUtils
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand

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
    /** Необратимое удаление (fallback на API < 30 либо явный выбор). */
    private val launchDelete: (List<MediaFile>) -> Unit,
    val supportsTrash: Boolean,
) {
    var statusText by mutableStateOf<String?>(null)
    var canUndo by mutableStateOf(false)
        private set

    // Последняя партия uri, перемещённая в корзину — для «Отменить».
    private var lastTrashed: List<Uri> = emptyList()

    /** Основное действие кнопки «Удалить»: в корзину (если поддерживается) либо удалить. */
    fun remove(files: List<MediaFile>) {
        if (files.isEmpty()) return
        if (supportsTrash) {
            lastTrashed = files.map { it.uri }
            launchTrash(lastTrashed, true)
        } else {
            launchDelete(files)
        }
    }

    /** Отмена последнего перемещения в корзину — восстановление тех же uri. */
    fun undo() {
        if (canUndo && lastTrashed.isNotEmpty()) launchTrash(lastTrashed, false)
    }

    /** Вызывается после успешного системного запроса «в корзину». */
    fun onTrashed(count: Int) {
        statusText = "Перемещено в корзину: $count"
        canUndo = true
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
                PendingOp.Restore -> actionsRef.value?.onRestored()
                PendingOp.Delete, PendingOp.None -> { /* удаление: баннер не нужен */ }
            }
            onDone()
        }
    }

    fun launchSender(sender: IntentSender) {
        launcher.launch(IntentSenderRequest.Builder(sender).build())
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
            pendingOp = PendingOp.Delete
            launchSender(pi.intentSender)
        } else {
            files.forEach { runCatching { ctx.contentResolver.delete(it.uri, null, null) } }
            onDone()
        }
    }

    val actions = remember { MediaActions(launchTrash, launchDelete, supportsTrash) }
    actionsRef.value = actions
    return actions
}

/** Какую операцию пользователь подтверждает в системном диалоге. */
private sealed interface PendingOp {
    data object None : PendingOp
    data object Delete : PendingOp
    data class Trash(val count: Int) : PendingOp
    data object Restore : PendingOp
}

/** Хаб «Медиа»: Крупные · Дубли · Скриншоты · Загрузки. */
@Composable
fun MediaHubScreen(ctx: Context) {
    var tab by remember { mutableIntStateOf(0) }
    val titles = listOf("Крупные", "Дубли", "Скриншоты", "Загрузки", "Мессенджеры")
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
            1 -> DuplicatesScreen(ctx)
            2 -> GenericMediaScreen(ctx, "Скриншоты") { MediaStoreUtils.screenshots(it) }
            3 -> GenericMediaScreen(ctx, "Загрузки") { MediaStoreUtils.downloads(it) }
            else -> GenericMediaScreen(ctx, "Медиа мессенджеров") { MediaStoreUtils.messengerMedia(it) }
        }
    }
}

@Composable
private fun GenericMediaScreen(ctx: Context, title: String, loader: (Context) -> List<MediaFile>) {
    MediaPermissionGate(ctx) {
        var reload by remember { mutableIntStateOf(0) }
        val files = remember(reload, title) { loader(ctx) }
        val actions = rememberMediaActions(ctx) { reload++ }
        val total = files.sumOf { it.size }
        // Действие на строке: безопасно — «В корзину» (API 30+), иначе «Удалить».
        val rowLabel = if (actions.supportsTrash) "В корзину" else "Удалить"

        Column(Modifier.fillMaxSize().background(Brand.bg0)) {
            TrashBanner(actions)
            LazyColumn(
                Modifier.fillMaxSize(),
                contentPadding = PaddingValues(20.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                item {
                    Text("$title · ${files.size} · ${SystemInfo.fmtSize(total)}",
                        color = Brand.muted, fontSize = 13.sp,
                        modifier = Modifier.padding(bottom = 4.dp))
                }
                items(files, key = { it.id }) { f ->
                    FileRow(f, actionLabel = rowLabel) { actions.remove(listOf(f)) }
                }
                if (files.isEmpty()) item {
                    Text("Ничего не найдено.", color = Brand.muted, fontSize = 14.sp)
                }
            }
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
        val groups = remember(reload) { MediaStoreUtils.duplicateGroups(ctx) }
        val actions = rememberMediaActions(ctx) { reload++ }
        val wastedBytes = groups.sumOf { g -> g.first().size * (g.size - 1) }
        val dupLabelPrefix = if (actions.supportsTrash) "В корзину лишние" else "Удалить лишние"

        Column(Modifier.fillMaxSize().background(Brand.bg0)) {
            TrashBanner(actions)
            LazyColumn(
                Modifier.fillMaxSize(),
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
                        Text("Групп дубликатов: ${groups.size}", color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        Text("Можно освободить до ${SystemInfo.fmtSize(wastedBytes)}", color = Brand.green, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
            items(groups.size) { i ->
                val g = groups[i]
                Card(
                    colors = CardDefaults.cardColors(containerColor = Brand.glass),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(g.first().name, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                        Text("${g.size} копии · ${SystemInfo.fmtSize(g.first().size)} каждая", color = Brand.muted, fontSize = 12.sp)
                        TextButton(onClick = { actions.remove(g.drop(1)) }) {
                            Text("$dupLabelPrefix (${g.size - 1})", color = Brand.red, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                    }
                }
            }
            if (groups.isEmpty()) item {
                Text("Дубликаты не найдены — отлично!", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            }
        }
    }
}

@Composable
private fun FileRow(f: MediaFile, actionLabel: String, onAction: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(f.name, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Text(SystemInfo.fmtSize(f.size), color = Brand.muted, fontSize = 12.sp)
            }
            TextButton(onClick = onAction) {
                Text(actionLabel, color = Brand.red, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
