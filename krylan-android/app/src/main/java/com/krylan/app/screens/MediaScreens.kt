// Крупные файлы и медиа-дубликаты: список через MediaStore, удаление через системный диалог.
package com.krylan.app.screens

import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
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

/** Системный диалог удаления выбранных uri (Android 11+); ниже — прямое удаление. */
@Composable
private fun rememberDeleter(ctx: Context, onDone: () -> Unit): (List<MediaFile>) -> Unit {
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult()
    ) { result -> if (result.resultCode == Activity.RESULT_OK) onDone() }

    return { files ->
        if (files.isNotEmpty()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val pi = MediaStore.createDeleteRequest(ctx.contentResolver, files.map { it.uri })
                launcher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
            } else {
                files.forEach { runCatching { ctx.contentResolver.delete(it.uri, null, null) } }
                onDone()
            }
        }
    }
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
        val deleter = rememberDeleter(ctx) { reload++ }
        val total = files.sumOf { it.size }

        LazyColumn(
            Modifier.fillMaxSize().background(Brand.bg0),
            contentPadding = PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Text("$title · ${files.size} · ${SystemInfo.fmtSize(total)}",
                    color = Brand.muted, fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 4.dp))
            }
            items(files, key = { it.id }) { f ->
                FileRow(f, actionLabel = "Удалить") { deleter(listOf(f)) }
            }
            if (files.isEmpty()) item {
                Text("Ничего не найдено.", color = Brand.muted, fontSize = 14.sp)
            }
        }
    }
}

@Composable
fun DuplicatesScreen(ctx: Context) {
    MediaPermissionGate(ctx) {
        var reload by remember { mutableIntStateOf(0) }
        val groups = remember(reload) { MediaStoreUtils.duplicateGroups(ctx) }
        val deleter = rememberDeleter(ctx) { reload++ }
        val wastedBytes = groups.sumOf { g -> g.first().size * (g.size - 1) }

        LazyColumn(
            Modifier.fillMaxSize().background(Brand.bg0),
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
                        TextButton(onClick = { deleter(g.drop(1)) }) {
                            Text("Удалить лишние (${g.size - 1})", color = Brand.red, fontWeight = FontWeight.Bold, fontSize = 13.sp)
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
