// KRYLAN — Android. «Дай устройству крылья». Создатель: Кырлан Александр Сергеевич.
package com.krylan.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.FileCopy
import androidx.compose.material.icons.filled.InsertDriveFile
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
import com.krylan.app.screens.CleanupScreen
import com.krylan.app.screens.DashboardScreen
import com.krylan.app.screens.DuplicatesScreen
import com.krylan.app.screens.LargeFilesScreen
import com.krylan.app.screens.StorageScreen
import com.krylan.app.ui.Brand
import com.krylan.app.ui.KrylanTheme

private enum class Tab(val title: String, val icon: ImageVector) {
    Dashboard("Дашборд", Icons.Filled.Speed),
    Storage("Хранилище", Icons.Filled.Storage),
    Cleanup("Очистка", Icons.Filled.CleaningServices),
    Files("Файлы", Icons.Filled.InsertDriveFile),
    Dupes("Дубли", Icons.Filled.FileCopy),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
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
                Tab.Dashboard -> DashboardScreen(ctx)
                Tab.Storage   -> StorageScreen(ctx)
                Tab.Cleanup   -> CleanupScreen(ctx)
                Tab.Files     -> LargeFilesScreen(ctx)
                Tab.Dupes     -> DuplicatesScreen(ctx)
            }
        }
    }
}
