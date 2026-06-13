// Крупные файлы и медиа-дубликаты через MediaStore (scoped storage, без root).
package com.krylan.app

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore

data class MediaFile(val id: Long, val name: String, val size: Long, val uri: Uri)

/** Разбивка занятого медиа-хранилища по типам (байты). */
data class StorageBreakdown(
    val images: Long, val video: Long, val audio: Long, val other: Long,
) {
    val total get() = images + video + audio + other
}

object MediaStoreUtils {

    /** Суммарный размер медиа по типам через MediaStore (без root, в рамках scoped storage). */
    fun storageBreakdown(ctx: Context): StorageBreakdown {
        fun sumOf(collection: Uri): Long {
            var total = 0L
            val proj = arrayOf(MediaStore.MediaColumns.SIZE)
            try {
                ctx.contentResolver.query(collection, proj, null, null, null)?.use { c ->
                    val idx = c.getColumnIndexOrThrow(MediaStore.MediaColumns.SIZE)
                    while (c.moveToNext()) total += c.getLong(idx)
                }
            } catch (_: Exception) { /* нет разрешения — 0 */ }
            return total
        }
        val images = sumOf(MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        val video = sumOf(MediaStore.Video.Media.EXTERNAL_CONTENT_URI)
        val audio = sumOf(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI)
        // «Прочее»: файлы из общего хранилища, не попавшие в медиа-коллекции (документы, архивы).
        var other = 0L
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            other = sumOf(MediaStore.Downloads.EXTERNAL_CONTENT_URI)
        }
        return StorageBreakdown(images, video, audio, other)
    }


    /** Разрешения на чтение медиа в зависимости от версии Android. */
    fun readPermissions(): Array<String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) arrayOf(
            android.Manifest.permission.READ_MEDIA_IMAGES,
            android.Manifest.permission.READ_MEDIA_VIDEO,
            android.Manifest.permission.READ_MEDIA_AUDIO,
        ) else arrayOf(android.Manifest.permission.READ_EXTERNAL_STORAGE)

    /** Топ крупных медиа-файлов, по убыванию размера. */
    fun largeFiles(ctx: Context, limit: Int = 100): List<MediaFile> =
        query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = limit)

    /** Скриншоты: по относительному пути (API 29+) или по DATA (старые версии). */
    fun screenshots(ctx: Context, limit: Int = 500): List<MediaFile> {
        val (sel, args) = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
            "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ?" to arrayOf("%Screenshots%")
        else
            "${MediaStore.Images.Media.DATA} LIKE ?" to arrayOf("%/Screenshots/%")
        return query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = limit,
                     collection = MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                     selection = sel, selectionArgs = args)
    }

    /** Содержимое папки Загрузки (API 29+: коллекция Downloads). */
    fun downloads(ctx: Context, limit: Int = 300): List<MediaFile> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
            query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = limit,
                  collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI)
        else
            query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = limit,
                  selection = "${MediaStore.Files.FileColumns.DATA} LIKE ?",
                  selectionArgs = arrayOf("%/Download/%"))

    /** Группы дубликатов: одинаковые имя+размер, групп больше одной записи. */
    fun duplicateGroups(ctx: Context): List<List<MediaFile>> =
        query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = 5000)
            .filter { it.size > 0 }
            .groupBy { it.name.lowercase() to it.size }
            .values.filter { it.size > 1 }
            .sortedByDescending { it.first().size * it.size }

    private fun query(
        ctx: Context, sort: String, limit: Int,
        collection: Uri = MediaStore.Files.getContentUri("external"),
        selection: String? = null, selectionArgs: Array<String>? = null,
    ): List<MediaFile> {
        val proj = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
        )
        val out = mutableListOf<MediaFile>()
        ctx.contentResolver.query(collection, proj, selection, selectionArgs, sort)?.use { c ->
            val idIdx = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
            val nameIdx = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            val sizeIdx = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            while (c.moveToNext() && out.size < limit) {
                val id = c.getLong(idIdx)
                out += MediaFile(
                    id = id,
                    name = c.getString(nameIdx) ?: "—",
                    size = c.getLong(sizeIdx),
                    uri = ContentUris.withAppendedId(collection, id),
                )
            }
        }
        return out
    }
}
