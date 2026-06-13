// Виджет KRYLAN (Glance): занятость диска на рабочем столе Android.
package com.krylan.app.widget

import android.content.Context
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.LinearProgressIndicator
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.krylan.app.SystemInfo

class DiskWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val st = SystemInfo.storage()
        val used = st.usedPercent
        val accent = if (used < 60) Color(0xFF37D39A) else if (used < 85) Color(0xFFF6BB45) else Color(0xFFF2685F)

        provideContent {
            Column(
                modifier = GlanceModifier.fillMaxSize()
                    .background(Color(0xFF11151D)).cornerRadius(16.dp).padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("🪽 KRYLAN", style = TextStyle(
                    color = ColorProvider(Color(0xFF37D39A)), fontSize = 11.sp, fontWeight = FontWeight.Bold))
                Text("${used.toInt()}%", style = TextStyle(
                    color = ColorProvider(Color(0xFFEEF2F8)), fontSize = 32.sp, fontWeight = FontWeight.Bold))
                Text("диск занят", style = TextStyle(
                    color = ColorProvider(Color(0xFF8A94A6)), fontSize = 10.sp))
                Spacer(GlanceModifier.height(8.dp))
                LinearProgressIndicator(
                    progress = (used / 100f).coerceIn(0f, 1f),
                    modifier = GlanceModifier.fillMaxWidth(),
                    color = ColorProvider(accent),
                    backgroundColor = ColorProvider(Color(0xFF333D4E))
                )
                Spacer(GlanceModifier.height(6.dp))
                Text("${SystemInfo.fmtSize(st.freeBytes)} свободно", style = TextStyle(
                    color = ColorProvider(Color(0xFF8A94A6)), fontSize = 11.sp, fontWeight = FontWeight.Bold))
            }
        }
    }
}

class DiskWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = DiskWidget()
}
