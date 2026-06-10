// Крупные файлы и медиа-дубликаты через MediaStore (scoped storage, без root).
package com.krylan.app

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore

data class MediaFile(val id: Long, val name: String, val size: Long, val uri: Uri)

object MediaStoreUtils {

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

    /** Группы дубликатов: одинаковые имя+размер, групп больше одной записи. */
    fun duplicateGroups(ctx: Context): List<List<MediaFile>> =
        query(ctx, sort = "${MediaStore.Files.FileColumns.SIZE} DESC", limit = 5000)
            .filter { it.size > 0 }
            .groupBy { it.name.lowercase() to it.size }
            .values.filter { it.size > 1 }
            .sortedByDescending { it.first().size * it.size }

    private fun query(ctx: Context, sort: String, limit: Int): List<MediaFile> {
        val collection = MediaStore.Files.getContentUri("external")
        val proj = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
        )
        val out = mutableListOf<MediaFile>()
        ctx.contentResolver.query(collection, proj, null, null, sort)?.use { c ->
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
