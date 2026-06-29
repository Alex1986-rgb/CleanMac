// KRYLAN — Android. «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
package com.krylan.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.LocationOff
import androidx.compose.material.icons.filled.PermMedia
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.sp
import com.krylan.app.screens.AppsScreen
import com.krylan.app.screens.AutopilotScreen
import com.krylan.app.screens.CleanupScreen
import com.krylan.app.screens.DashboardScreen
import com.krylan.app.screens.GeoPrivacyScreen
import com.krylan.app.screens.MediaHubScreen
import com.krylan.app.screens.StorageScreen
import com.krylan.app.ui.Brand
import com.krylan.app.ui.KrylanTheme

private enum class Tab(val title: String, val icon: ImageVector) {
    Dashboard("Дашборд", Icons.Filled.Speed),
    Storage("Хранилище", Icons.Filled.Storage),
    Cleanup("Очистка", Icons.Filled.CleaningServices),
    Media("Медиа", Icons.Filled.PermMedia),
    Apps("Приложения", Icons.Filled.Apps),
    Autopilot("Автопилот", Icons.Filled.Bolt),
    Geo("Геолокация", Icons.Filled.LocationOff),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        androidx.work.WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "storage_check",
            androidx.work.ExistingPeriodicWorkPolicy.KEEP,
            androidx.work.PeriodicWorkRequestBuilder<StorageCheckWorker>(
                12, java.util.concurrent.TimeUnit.HOURS).build()
        )
        // Если пользователь включал Автопилот ранее — восстановим периодическую задачу.
        if (AutopilotPrefs(this).enabled) Autopilot.enable(this)
        setContent { KrylanTheme { Root() } }
    }
}

@Composable
private fun Root() {
    var tab by remember { mutableStateOf(Tab.Dashboard) }
    val ctx = androidx.compose.ui.platform.LocalContext.current

    Scaffold(
        containerColor = Brand.bg0,
        bottomBar = {
            NavigationBar(containerColor = Brand.glass) {
                Tab.entries.forEach { t ->
                    NavigationBarItem(
                        selected = tab == t,
                        onClick = { tab = t },
                        icon = { Icon(t.icon, contentDescription = t.title) },
                        label = { Text(t.title, fontSize = 10.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Brand.green,
                            selectedTextColor = Brand.green,
                            indicatorColor = Brand.green.copy(alpha = 0.15f),
                            unselectedIconColor = Brand.muted,
                            unselectedTextColor = Brand.muted,
                        )
                    )
                }
            }
        }
    ) { inner ->
        androidx.compose.foundation.layout.Box(Modifier.padding(inner)) {
            when (tab) {
                Tab.Dashboard -> DashboardScreen(ctx) { index ->
                    Tab.entries.getOrNull(index)?.let { tab = it }
                }
                Tab.Storage   -> StorageScreen(ctx)
                Tab.Cleanup   -> CleanupScreen(ctx)
                Tab.Media     -> MediaHubScreen(ctx)
                Tab.Apps      -> AppsScreen(ctx)
                Tab.Autopilot -> AutopilotScreen(ctx)
                Tab.Geo       -> GeoPrivacyScreen(ctx)
            }
        }
    }
}
