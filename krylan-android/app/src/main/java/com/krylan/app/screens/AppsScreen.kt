// Менеджер приложений: список по размеру APK, удаление через системный диалог.
// Размер APK — честный ориентир без спец-разрешений (полный размер требует Usage Access).
package com.krylan.app.screens

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.Uri
import androidx.compose.foundation.background
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand
import java.io.File

data class AppEntry(val label: String, val pkg: String, val apkBytes: Long)

private fun installedApps(ctx: Context): List<AppEntry> {
    val pm = ctx.packageManager
    return pm.getInstalledApplications(0)
        .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 && it.packageName != ctx.packageName }
        .map { AppEntry(pm.getApplicationLabel(it).toString(), it.packageName, File(it.sourceDir).length()) }
        .sortedByDescending { it.apkBytes }
}

@Composable
fun AppsScreen(ctx: Context) {
    var reload by remember { mutableIntStateOf(0) }
    val apps = remember(reload) { installedApps(ctx) }

    LazyColumn(
        Modifier.fillMaxSize().background(Brand.bg0),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Приложений: ${apps.size} · сортировка по размеру APK",
                    color = Brand.muted, fontSize = 13.sp, modifier = Modifier.weight(1f))
                TextButton(onClick = { reload++ }) {
                    Text("Обновить", color = Brand.blue, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        items(apps, key = { it.pkg }) { a ->
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
                        Text(a.label, color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                        Text("${a.pkg} · APK ${SystemInfo.fmtSize(a.apkBytes)}",
                            color = Brand.muted, fontSize = 11.sp, maxLines = 1)
                    }
                    TextButton(onClick = {
                        ctx.startActivity(Intent(Intent.ACTION_DELETE, Uri.parse("package:${a.pkg}")))
                    }) {
                        Text("Удалить", color = Brand.red, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        if (apps.isEmpty()) item {
            Text("Список приложений недоступен.", color = Brand.muted, fontSize = 14.sp)
        }
    }
}
