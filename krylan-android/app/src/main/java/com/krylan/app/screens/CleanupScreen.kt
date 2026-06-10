// Очистка: размер кэша своего приложения + кнопка очистки (безопасно, в рамках политик Play).
package com.krylan.app.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.krylan.app.SystemInfo
import com.krylan.app.ui.Brand

@Composable
fun CleanupScreen(ctx: Context) {
    var cache by remember { mutableLongStateOf(SystemInfo.cacheBytes(ctx)) }
    var freedTotal by remember { mutableLongStateOf(0L) }

    Column(
        Modifier
            .fillMaxSize()
            .background(Brand.bg0)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                Modifier.fillMaxWidth().padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("КЭШ ПРИЛОЖЕНИЯ", color = Brand.muted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Text(SystemInfo.fmtSize(cache), color = Brand.text, fontSize = 40.sp, fontWeight = FontWeight.Bold)
                if (freedTotal > 0) {
                    Text("Освобождено: ${SystemInfo.fmtSize(freedTotal)}", color = Brand.green, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                Button(
                    onClick = {
                        freedTotal += SystemInfo.clearCache(ctx)
                        cache = SystemInfo.cacheBytes(ctx)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Brand.green, contentColor = Color(0xFF0B1410)),
                    shape = RoundedCornerShape(50),
                    modifier = Modifier.padding(top = 6.dp)
                ) {
                    Text("Очистить кэш", fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 12.dp, vertical = 2.dp))
                }
            }
        }

        Card(
            colors = CardDefaults.cardColors(containerColor = Brand.glass),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Почему только свой кэш?", color = Brand.text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                Text(
                    "Начиная с Android 11 система запрещает приложениям трогать данные других приложений. " +
                    "«Чистильщики всего» в Play Маркете либо не работают, либо нарушают правила. " +
                    "KRYLAN чистит только то, что реально можно: свой кэш — и помогает вам найти крупные файлы и дубликаты, чтобы решить самостоятельно.",
                    color = Brand.muted, fontSize = 13.sp
                )
            }
        }
    }
}
