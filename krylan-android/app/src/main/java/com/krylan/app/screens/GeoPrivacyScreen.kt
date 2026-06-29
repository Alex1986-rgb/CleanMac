// Геолокация (приватность): открывает системные настройки локации + пошаговый гид.
// Честно: приложение не может выключить геолокацию за пользователя — только открывает настройки и подсказывает.
package com.krylan.app.screens

import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocationOff
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.ui.Brand

@Composable
fun GeoPrivacyScreen(ctx: Context) {

    fun openLocationSettings() {
        val opened = runCatching {
            ctx.startActivity(
                Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }.isSuccess
        if (!opened) runCatching {
            ctx.startActivity(
                Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Заголовок
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        Modifier.size(44.dp).background(Brand.blue.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                        contentAlignment = Alignment.Center
                    ) { Icon(Icons.Filled.LocationOff, contentDescription = null, tint = Brand.blue) }
                    Column {
                        Text("Геолокация", color = Brand.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        Text("Приватность и контроль", color = Brand.muted, fontSize = 12.sp)
                    }
                }
                Text(
                    "Управляйте тем, кто и когда определяет ваше местоположение. " +
                        "KRYLAN откроет нужный экран системы и подскажет шаги.",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }

        // Главная кнопка
        ActionButtonBig("Открыть настройки геолокации", Brand.blue) { openLocationSettings() }

        // Честная плашка
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = Brand.yellow)
                Text(
                    "Приложение не может выключить геолокацию за вас — это делает только система. " +
                        "KRYLAN открывает нужные настройки и подсказывает, что нажать.",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }

        // Пошаговый гид
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text("Как отключить геопозицию", color = Brand.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                Step(1, "Полностью выключить локацию",
                    "Настройки → Локация (Местоположение) → переключатель вверху в положение «Выкл».")
                Step(2, "Отключить по приложениям",
                    "Настройки → Локация → Разрешения приложений. Для ненужных приложений выберите «Не разрешать».")
                Step(3, "История местоположений Google",
                    "Настройки → Локация → Службы определения местоположения → История местоположений → выключите. " +
                        "Там же можно удалить уже сохранённую историю.")
                Step(4, "Режим «В самолёте»",
                    "Быстрые настройки (шторка сверху) → «В самолёте». Отключает GPS, мобильную сеть и Wi-Fi разом.")
            }
        }

        // Доп: гео в фото
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Геометки в фотографиях", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(
                    "Камера может записывать координаты в каждое фото. Чтобы это отключить: " +
                        "откройте приложение «Камера» → Настройки → выключите «Геотеги» / «Сохранять местоположение». " +
                        "При отправке фото в галерее Android можно выбрать «Удалить геоданные».",
                    color = Brand.muted, fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun Step(n: Int, title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(
            Modifier.size(28.dp).background(Brand.blue.copy(alpha = 0.18f), RoundedCornerShape(8.dp)),
            contentAlignment = Alignment.Center
        ) { Text("$n", color = Brand.blue, fontSize = 14.sp, fontWeight = FontWeight.Bold) }
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, color = Brand.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(body, color = Brand.muted, fontSize = 12.sp)
        }
    }
}

@Composable
private fun ActionButtonBig(label: String, color: Color, onClick: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(50))
            .background(color)
            .clickable(onClick = onClick)
            .padding(vertical = 15.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(label, color = Color(0xFF0B1410), fontSize = 16.sp, fontWeight = FontWeight.Bold)
    }
}
