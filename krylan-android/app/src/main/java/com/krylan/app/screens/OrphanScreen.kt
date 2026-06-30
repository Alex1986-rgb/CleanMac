// Осиротевшие файлы (CorpseFinder-lite): ручной разбор папок удалённых приложений и пустых папок.
package com.krylan.app.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.OrphanFinder
import com.krylan.app.OrphanItem
import com.krylan.app.OrphanScanResult
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun OrphanScreen(ctx: Context) {
    var reload by remember { mutableIntStateOf(0) }
    var result by remember { mutableStateOf<OrphanScanResult?>(null) }
    var status by remember { mutableStateOf<String?>(null) }
    // Подтверждение удаления конкретной находки.
    var confirm by remember { mutableStateOf<OrphanItem?>(null) }
    var canManage by remember { mutableStateOf(OrphanFinder.hasManageStorage()) }

    LaunchedEffect(reload) {
        result = null
        canManage = OrphanFinder.hasManageStorage()
        result = withContext(Dispatchers.IO) {
            try { OrphanFinder.scan(ctx) } catch (e: Exception) { OrphanScanResult(emptyList(), false) }
        }
    }

    val r = result
    Column(Modifier.fillMaxSize().background(Brand.bg0)) {
        status?.let { s ->
            Row(
                Modifier.fillMaxWidth().background(Brand.glass).padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(s, color = Brand.text, fontSize = 13.sp, modifier = Modifier.weight(1f))
                TextButton(onClick = { status = null }) { Text("Скрыть", color = Brand.muted, fontSize = 13.sp) }
            }
        }

        LazyColumn(
            Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Brand.glass),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Осиротевшие файлы", color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        Text(
                            "Папки удалённых приложений (имя вида com.xxx.yyy без установленного приложения) " +
                                "и пустые папки в общем хранилище. Только для ручной проверки — ничего не удаляем автоматически.",
                            color = Brand.muted, fontSize = 12.sp
                        )
                    }
                }
            }

            when {
                r == null -> item { Text("Сканируем хранилище…", color = Brand.muted, fontSize = 14.sp) }
                !r.storageReadable -> item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Brand.glass),
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("Нет доступа к общему хранилищу", color = Brand.yellow, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "Android (scoped storage) скрывает чужие папки от приложений. Чтобы KRYLAN мог " +
                                    "находить и удалять осиротевшие папки, нужен доступ «Управление всеми файлами», " +
                                    "либо разберите папки вручную в файловом менеджере.",
                                color = Brand.muted, fontSize = 12.sp
                            )
                            ActionPill("Открыть настройки доступа") { openAllFilesAccess(ctx) }
                            ActionPill("Открыть папку Download") { openDownloadFolder(ctx) { status = it } }
                        }
                    }
                }
                r.items.isEmpty() -> item {
                    Text("Осиротевших папок не найдено — чисто!", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                else -> {
                    item {
                        Text("Найдено: ${r.items.size} · ${SystemInfo.fmtSize(r.items.sumOf { it.size })}",
                            color = Brand.muted, fontSize = 13.sp)
                    }
                    items(r.items, key = { it.path }) { item ->
                        OrphanRow(
                            item = item,
                            canDelete = canManage,
                            onDelete = { confirm = item },
                            onOpen = { openFolder(ctx, item.path) { status = it } }
                        )
                    }
                }
            }
        }
    }

    // Диалог подтверждения удаления.
    confirm?.let { item ->
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { confirm = null },
            confirmButton = {
                TextButton(onClick = {
                    val ok = OrphanFinder.deleteDirectory(item.path)
                    status = if (ok) "Удалено: ${item.name}" else "Не удалось удалить — откройте папку вручную"
                    confirm = null
                    if (ok) reload++
                }) { Text("Удалить", color = Brand.red, fontWeight = FontWeight.Bold) }
            },
            dismissButton = {
                TextButton(onClick = { confirm = null }) { Text("Отмена", color = Brand.muted) }
            },
            title = { Text("Удалить папку?", color = Brand.text) },
            text = {
                Text(
                    "${item.name}\n${item.reason}\nРазмер: ${SystemInfo.fmtSize(item.size)}\n\nДействие необратимо.",
                    color = Brand.muted, fontSize = 13.sp
                )
            },
            containerColor = Brand.glass,
        )
    }
}

@Composable
private fun OrphanRow(item: OrphanItem, canDelete: Boolean, onDelete: () -> Unit, onOpen: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Brand.glass),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(item.name, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1)
            Text("${item.reason} · ${SystemInfo.fmtSize(item.size)}", color = Brand.muted, fontSize = 12.sp)
            Text(item.path, color = Brand.muted.copy(alpha = 0.7f), fontSize = 10.sp, maxLines = 1)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (canDelete) {
                    Box(
                        Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(Brand.red)
                            .clickable(onClick = onDelete).padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center
                    ) { Text("Удалить", color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.Bold) }
                }
                Box(
                    Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(Brand.track)
                        .clickable(onClick = onOpen).padding(vertical = 10.dp),
                    contentAlignment = Alignment.Center
                ) { Text("Открыть папку", color = Brand.cyan, fontSize = 13.sp, fontWeight = FontWeight.Bold) }
            }
        }
    }
}

@Composable
private fun ActionPill(label: String, onClick: () -> Unit) {
    Box(
        Modifier.clip(RoundedCornerShape(50)).background(Brand.green)
            .clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 10.dp)
    ) { Text(label, color = Color(0xFF0B1410), fontSize = 13.sp, fontWeight = FontWeight.Bold) }
}

/** Открывает системный экран «Доступ к управлению всеми файлами» (R+). */
private fun openAllFilesAccess(ctx: Context) {
    try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            ctx.startActivity(
                Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                    Uri.parse("package:" + ctx.packageName))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        } else {
            ctx.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + ctx.packageName)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    } catch (_: Exception) { /* нет экрана — игнорируем */ }
}

/** Пытается открыть папку в файловом менеджере. */
private fun openFolder(ctx: Context, path: String, onError: (String) -> Unit) {
    try {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(Uri.parse("file://$path"), "resource/folder")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        ctx.startActivity(intent)
    } catch (_: Exception) {
        onError("Не нашлось приложения для открытия папки. Путь: $path")
    }
}

private fun openDownloadFolder(ctx: Context, onError: (String) -> Unit) {
    @Suppress("DEPRECATION")
    val dl = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
    openFolder(ctx, dl.absolutePath, onError)
}
