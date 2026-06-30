// CorpseFinder-lite: безопасный поиск осиротевших папок/файлов в общем хранилище под scoped storage.
// Ищем папки вида com.xxx.yyy, которых НЕТ среди установленных приложений (=мусор удалённых),
// и пустые папки. Только для ручного разбора — никакого авто-удаления.
package com.krylan.app

import android.content.Context
import android.os.Build
import android.os.Environment
import java.io.File

/**
 * Найденный осиротевший объект.
 * [path] — абсолютный путь; [size] — суммарный размер (байт); [reason] — почему помечен;
 * [accessible] — удалось ли реально прочитать содержимое (под scoped storage может быть false).
 */
data class OrphanItem(
    val path: String,
    val name: String,
    val size: Long,
    val reason: String,
    val accessible: Boolean,
    val isDir: Boolean,
)

/** Итог сканирования: список находок + флаг, был ли вообще доступ к общему хранилищу. */
data class OrphanScanResult(
    val items: List<OrphanItem>,
    val storageReadable: Boolean,
)

object OrphanFinder {

    // Системные/легитимные папки в корне хранилища — никогда не помечаем как сирот.
    private val SYSTEM_DIRS = setOf(
        "Android", "DCIM", "Download", "Downloads", "Pictures", "Movies", "Music",
        "Documents", "Podcasts", "Ringtones", "Alarms", "Notifications", "Audiobooks",
        "Recordings", "Screenshots", "lost.dir", "MIUI", "backups", "Telegram", "WhatsApp",
    )

    /** Имя выглядит как Android-пакет: 2+ сегмента через точку, латиница/цифры/_. */
    private fun looksLikePackage(name: String): Boolean =
        Regex("^[a-zA-Z][a-zA-Z0-9_]*(\\.[a-zA-Z0-9_]+){1,}$").matches(name)

    /**
     * Сканирует доступные общие каталоги (корень хранилища + Download).
     * Помечает:
     *  - папки с именем-пакетом, которого нет среди установленных приложений → «осиротевшая»;
     *  - пустые папки → «пустая папка».
     * Под scoped storage листинг чужих папок чаще всего недоступен — тогда storageReadable=false
     * и мы честно сообщаем об этом в UI (с предложением открыть папку вручную).
     */
    fun scan(ctx: Context): OrphanScanResult {
        val installed: Set<String> = try {
            ctx.packageManager.getInstalledApplications(0).map { it.packageName }.toSet()
        } catch (_: Exception) { emptySet() }

        val roots = buildList {
            @Suppress("DEPRECATION")
            add(Environment.getExternalStorageDirectory())
            @Suppress("DEPRECATION")
            add(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS))
        }.filterNotNull().distinctBy { it.absolutePath }

        val found = LinkedHashMap<String, OrphanItem>()
        var anyReadable = false

        for (root in roots) {
            val children = try { root.listFiles() } catch (_: Exception) { null }
            if (children == null) continue
            anyReadable = true
            for (child in children) {
                val name = child.name
                if (!child.isDirectory) continue
                if (name in SYSTEM_DIRS) continue

                val pkgLike = looksLikePackage(name)
                val orphanPkg = pkgLike && name !in installed
                val empty = isEffectivelyEmpty(child)

                val reason = when {
                    orphanPkg -> "Папка удалённого приложения ($name)"
                    empty -> "Пустая папка"
                    else -> null
                } ?: continue

                val size = try { dirSize(child) } catch (_: Exception) { 0L }
                found[child.absolutePath] = OrphanItem(
                    path = child.absolutePath,
                    name = name,
                    size = size,
                    reason = reason,
                    accessible = child.canRead(),
                    isDir = true,
                )
            }
        }

        return OrphanScanResult(
            items = found.values.sortedByDescending { it.size },
            storageReadable = anyReadable,
        )
    }

    /** Папка пуста или содержит только пустые подпапки. */
    private fun isEffectivelyEmpty(dir: File): Boolean {
        val kids = try { dir.listFiles() } catch (_: Exception) { return false } ?: return false
        if (kids.isEmpty()) return true
        return kids.all { it.isDirectory && isEffectivelyEmpty(it) }
    }

    private fun dirSize(dir: File): Long =
        dir.walkBottomUp().filter { it.isFile }.sumOf { it.length() }

    /**
     * Прямое удаление папки на диске. Работает только если у приложения есть доступ
     * (MANAGE_EXTERNAL_STORAGE / на старых версиях WRITE) — иначе вернёт false, и UI предложит
     * открыть папку вручную. Никогда не вызывается без подтверждения пользователя.
     */
    fun deleteDirectory(path: String): Boolean {
        return try {
            val f = File(path)
            if (!f.exists()) true else f.deleteRecursively()
        } catch (_: Exception) { false }
    }

    /** Можно ли в принципе пытаться удалять напрямую (есть ли широкий доступ к хранилищу). */
    fun hasManageStorage(): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) Environment.isExternalStorageManager()
        else true // до R удаление в общем хранилище работало по WRITE_EXTERNAL_STORAGE
}
